#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
N=${1:-5}

fail() {
    echo "[agent] Error: $*" >&2
    exit 1
}

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

require_env() {
    local name="$1"
    [[ -n "${!name:-}" ]] || fail "Missing required env var: $name"
}

is_positive_int() {
    [[ "$1" =~ ^[0-9]+$ ]] && (( "$1" > 0 ))
}

run_agent_iteration() {
    local prompt_file="$1"
    local output_file="$2"
    local iteration="$3"
    local start_ts elapsed remaining sleep_for status claude_pid

    start_ts=$(date +%s)
    case "$AGENT_CLI" in
        claude)
            claude --print --permission-mode bypassPermissions < "$prompt_file" > "$output_file" 2>&1 &
            ;;
        codex)
            codex exec --dangerously-bypass-approvals-and-sandbox -C "$REPO_ROOT" - < "$prompt_file" > "$output_file" 2>&1 &
            ;;
        *)
            fail "Unsupported AGENT_CLI=$AGENT_CLI"
            ;;
    esac
    claude_pid=$!

    echo "[agent] Iteration $iteration launched (timeout=${AGENT_TIMEOUT_SECS}s, heartbeat=${AGENT_HEARTBEAT_SECS}s)."
    while kill -0 "$claude_pid" 2>/dev/null; do
        elapsed=$(( $(date +%s) - start_ts ))
        if (( elapsed >= AGENT_TIMEOUT_SECS )); then
            echo "[agent] Iteration $iteration timed out after ${elapsed}s. Terminating Claude."
            kill "$claude_pid" 2>/dev/null || true
            sleep 1
            if kill -0 "$claude_pid" 2>/dev/null; then
                kill -9 "$claude_pid" 2>/dev/null || true
            fi
            wait "$claude_pid" 2>/dev/null || true
            return 124
        fi

        remaining=$(( AGENT_TIMEOUT_SECS - elapsed ))
        sleep_for=$AGENT_HEARTBEAT_SECS
        if (( remaining < sleep_for )); then
            sleep_for=$remaining
        fi
        sleep "$sleep_for"
        if ! kill -0 "$claude_pid" 2>/dev/null; then
            break
        fi

        elapsed=$(( $(date +%s) - start_ts ))
        if (( elapsed >= AGENT_TIMEOUT_SECS )); then
            continue
        fi
        echo "[agent] Iteration $iteration still running (${elapsed}s elapsed)..."
    done

    set +e
    wait "$claude_pid"
    status=$?
    set -e
    return "$status"
}

is_positive_int "$N" || fail "Iteration count must be a positive integer"
require_cmd uv
[[ -f "$REPO_ROOT/.env" ]] || fail "Missing .env at $REPO_ROOT/.env"

set -a; source "$REPO_ROOT/.env"; set +a
export MODEL_PROVIDER="${MODEL_PROVIDER:-gemini}"
export AGENT_CLI="${AGENT_CLI:-claude}"
export GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash-lite}"
export EVAL_MAX_PAIRS="${EVAL_MAX_PAIRS:-100}"
export EVAL_WORKERS="${EVAL_WORKERS:-10}"
export AGENT_HEARTBEAT_SECS="${AGENT_HEARTBEAT_SECS:-15}"
export AGENT_TIMEOUT_SECS="${AGENT_TIMEOUT_SECS:-900}"

require_cmd "$AGENT_CLI"
is_positive_int "$AGENT_HEARTBEAT_SECS" || fail "AGENT_HEARTBEAT_SECS must be a positive integer"
is_positive_int "$AGENT_TIMEOUT_SECS" || fail "AGENT_TIMEOUT_SECS must be a positive integer"
case "$MODEL_PROVIDER" in
    heuristic)
        ;;
    gemini)
        require_env GOOGLE_API_KEY
        ;;
    openai)
        require_env OPENAI_API_KEY
        ;;
    openai_compat)
        require_env OPENAI_BASE_URL
        ;;
    *)
        fail "Unsupported MODEL_PROVIDER=$MODEL_PROVIDER"
        ;;
esac

echo "[agent] Starting $N iterations with outer_agent=$AGENT_CLI provider=$MODEL_PROVIDER model=$GEMINI_MODEL (${EVAL_MAX_PAIRS} pairs, ${EVAL_WORKERS} workers)"

for i in $(seq 1 "$N"); do
    echo "=== Agent Iteration $i / $N ==="
    PROMPT_FILE="$(mktemp -t autosearch_prompt)"
    OUTPUT_FILE="$(mktemp -t autosearch_output)"
    cat > "$PROMPT_FILE" <<PROMPT_EOF
$(cat "$REPO_ROOT/program.md")

## Current strategy.md
$(cat "$REPO_ROOT/strategy.md")

## Recent results (tail 20 lines)
$(tail -n 20 "$REPO_ROOT/results/results.tsv" 2>/dev/null || echo '(none yet)')

## Recent experiment log (tail 60 lines)
$(tail -n 60 "$REPO_ROOT/results/experiment_log.md" 2>/dev/null || echo '(none yet)')

## Your task
1. Propose ONE focused edit to strategy.md or prompt_templates/pairwise_judge.md
2. Make the edit
3. Run: uv run python -m upworthy_autosearch.search --key-change '<1-line summary>' --rationale '<1-2 sentence why>'
4. Report the VERDICT line from output
PROMPT_EOF

    if run_agent_iteration "$PROMPT_FILE" "$OUTPUT_FILE" "$i"; then
        cat "$OUTPUT_FILE"
    else
        status=$?
        echo "[agent] Claude failed during iteration $i (exit=$status)." >&2
        echo "[agent] Last output lines:" >&2
        tail -n 40 "$OUTPUT_FILE" >&2 || true
        echo "[agent] Full log: $OUTPUT_FILE" >&2
        rm -f "$PROMPT_FILE"
        exit "$status"
    fi

    rm -f "$PROMPT_FILE"
    rm -f "$OUTPUT_FILE"
    echo "[agent] Iteration $i complete."
done

echo "[agent] Done. Leaderboard:"
cat "$REPO_ROOT/results/leaderboard.md" 2>/dev/null || echo "(not yet generated)"
