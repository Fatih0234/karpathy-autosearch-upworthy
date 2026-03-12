"""Shared utilities."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

STRATEGY_FILE = Path(__file__).parents[2] / "strategy.md"
RESULTS_DIR = Path(__file__).parents[2] / "results"
ITERATION_FILE = RESULTS_DIR / "iteration.txt"
EXPERIMENT_LOG = RESULTS_DIR / "experiment_log.md"
LEADERBOARD_MD = RESULTS_DIR / "leaderboard.md"


def strategy_hash() -> str:
    """SHA-256 of strategy.md (first 16 hex chars)."""
    if not STRATEGY_FILE.exists():
        return "no-strategy"
    content = STRATEGY_FILE.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def get_and_increment_iteration() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    n = int(ITERATION_FILE.read_text().strip()) if ITERATION_FILE.exists() else 0
    n += 1
    ITERATION_FILE.write_text(str(n))
    return n


def append_experiment_log(
    *,
    iteration: int,
    experiment_id: str,
    strategy_hash_val: str,
    key_change: str,
    acc_before: float,
    acc_after: float,
    ll_before: float,
    ll_after: float,
    verdict: str,
    rationale: str,
) -> None:
    if not EXPERIMENT_LOG.exists():
        EXPERIMENT_LOG.write_text("# Experiment Log\n\n")
    badge = "✅ IMPROVED" if verdict == "IMPROVED" else "❌ REJECTED"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = (
        f"## Iteration {iteration} — {badge}\n\n"
        f"| Field | Value |\n|---|---|\n"
        f"| experiment_id | `{experiment_id}` |\n"
        f"| strategy_hash | `{strategy_hash_val}` |\n"
        f"| timestamp | {ts} |\n"
        f"| key_change | {key_change} |\n"
        f"| accuracy | {acc_before:.4f} → {acc_after:.4f} |\n"
        f"| log_loss | {ll_before:.4f} → {ll_after:.4f} |\n\n"
        f"**Rationale:** {rationale}\n\n---\n\n"
    )
    with open(EXPERIMENT_LOG, "a") as f:
        f.write(entry)


def regenerate_leaderboard() -> None:
    import pandas as pd

    tsv = RESULTS_DIR / "results.tsv"
    if not tsv.exists():
        return
    df = pd.read_csv(tsv, sep="\t")
    dev = df[df["split"] == "dev"].sort_values("accuracy", ascending=False).reset_index(drop=True)
    lines = [
        "# Leaderboard\n",
        "Auto-generated. Sorted by dev accuracy descending.\n\n",
        "| Rank | Accuracy | Log Loss | Iteration | Provider | Experiment ID | Timestamp |",
        "|------|----------|----------|-----------|----------|---------------|-----------|",
    ]
    for i, row in dev.iterrows():
        lines.append(
            f"| {i+1} | {row['accuracy']:.4f} | {row['log_loss']:.4f} "
            f"| {row.get('iteration', '—')} | {row.get('provider', '—')} "
            f"| {row.get('notes', '—')} | {str(row.get('timestamp', ''))[:16]} |"
        )
    LEADERBOARD_MD.write_text("\n".join(lines) + "\n")
