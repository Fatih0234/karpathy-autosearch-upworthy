#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
N=${1:-5}

set -a; source "$REPO_ROOT/.env"; set +a
export MODEL_PROVIDER=gemini
export GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash-lite}"
export EVAL_MAX_PAIRS="${EVAL_MAX_PAIRS:-100}"
export EVAL_WORKERS="${EVAL_WORKERS:-10}"

echo "[agent] Starting $N iterations with $GEMINI_MODEL (${EVAL_MAX_PAIRS} pairs, ${EVAL_WORKERS} workers)"

for i in $(seq 1 "$N"); do
    echo "=== Agent Iteration $i / $N ==="
    PROMPT="$(cat "$REPO_ROOT/program.md")

## Current strategy.md
$(cat "$REPO_ROOT/strategy.md")

## Recent results (tail 20 lines)
$(tail -n 20 "$REPO_ROOT/results/results.tsv")

## Recent experiment log (tail 60 lines)
$(tail -n 60 "$REPO_ROOT/results/experiment_log.md" 2>/dev/null || echo '(none yet)')

## Your task
1. Propose ONE focused edit to strategy.md or prompt_templates/pairwise_judge.md
2. Make the edit
3. Run: uv run python -m upworthy_autosearch.search --key-change '<1-line summary>' --rationale '<1-2 sentence why>'
4. Report the VERDICT line from output"

    claude --print --permission-mode bypassPermissions "$PROMPT"
    echo "[agent] Iteration $i complete."
done

echo "[agent] Done. Leaderboard:"
cat "$REPO_ROOT/results/leaderboard.md" 2>/dev/null || echo "(not yet generated)"
