"""Experiment search loop.

One iteration:
  1. Get/increment iteration counter
  2. Run benchmark on dev split
  3. Compare to best historical score
  4. Keep if improved, revert if not
  5. Append experiment log; regenerate leaderboard on improvement
"""
from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from upworthy_autosearch.benchmark import evaluate
from upworthy_autosearch.utils import (
    append_experiment_log,
    get_best_dev_metrics,
    get_and_increment_iteration,
    regenerate_analysis_artifacts,
    regenerate_leaderboard,
    strategy_hash,
)

REPO_ROOT = Path(__file__).parents[2]


def _git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        check=check,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def run_search(key_change: str = "", rationale: str = "") -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    shash = strategy_hash()[:8]
    experiment_id = f"{ts}_{shash}"
    provider = os.environ.get("MODEL_PROVIDER", "heuristic")
    workers = os.environ.get("EVAL_WORKERS", "1")
    max_pairs = os.environ.get("EVAL_MAX_PAIRS", "all")
    target_n_pairs = int(max_pairs) if str(max_pairs).isdigit() else None
    current_branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], check=False).stdout.strip() or "unknown"

    print(f"[search] Experiment: {experiment_id}")
    print(f"[search] Branch={current_branch} Provider={provider} EVAL_MAX_PAIRS={max_pairs} EVAL_WORKERS={workers}")

    # Snapshot previous best
    prev_best_acc, prev_best_ll = get_best_dev_metrics(provider=provider, n_pairs=target_n_pairs)

    # Get iteration number
    iteration = get_and_increment_iteration()

    # Run benchmark
    result = evaluate(
        "dev",
        notes=f"autosearch/{experiment_id}",
        iteration=iteration,
        key_change=key_change,
    )
    new_acc = result["accuracy"]
    new_ll = result["log_loss"]
    full_hash = strategy_hash()

    improved = new_acc > prev_best_acc

    verdict = "IMPROVED" if improved else "REJECTED"
    append_experiment_log(
        iteration=iteration,
        experiment_id=experiment_id,
        strategy_hash_val=full_hash,
        key_change=key_change,
        acc_before=prev_best_acc,
        acc_after=new_acc,
        ll_before=prev_best_ll,
        ll_after=new_ll,
        verdict=verdict,
        rationale=rationale,
    )
    regenerate_leaderboard()
    regenerate_analysis_artifacts()

    if improved:
        print(f"[search] IMPROVED: {prev_best_acc:.4f} → {new_acc:.4f}")
        _git(
            [
                "add",
                "strategy.md",
                "prompt_templates/",
                "results/results.tsv",
                "results/experiment_log.md",
                "results/leaderboard.md",
                "results/analysis_summary.md",
                "results/metrics.csv",
                "results/accuracy_over_time.svg",
                "results/log_loss_over_time.svg",
                "results/iteration.txt",
            ],
            check=False,
        )
        _git(
            [
                "commit",
                "-m",
                f"autosearch: improve dev acc {prev_best_acc:.4f}→{new_acc:.4f} [{experiment_id}]",
            ],
            check=False,
        )
        print("[search] Changes committed.")
    else:
        print(f"[search] REJECTED: {new_acc:.4f} ≤ best {prev_best_acc:.4f}")
        _git(["checkout", "--", "strategy.md", "prompt_templates/"], check=False)
        _git(
            [
                "add",
                "results/results.tsv",
                "results/experiment_log.md",
                "results/leaderboard.md",
                "results/analysis_summary.md",
                "results/metrics.csv",
                "results/accuracy_over_time.svg",
                "results/log_loss_over_time.svg",
                "results/iteration.txt",
            ],
            check=False,
        )
        _git(
            ["commit", "-m", f"autosearch: rejected iteration {iteration} [{experiment_id}]"],
            check=False,
        )

    print(f"VERDICT:{verdict}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run one autosearch iteration")
    parser.add_argument("--key-change", default="", help="One-line summary of the change made")
    parser.add_argument("--rationale", default="", help="1-2 sentence explanation of why")
    args = parser.parse_args()
    run_search(key_change=args.key_change, rationale=args.rationale)
