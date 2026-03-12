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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from upworthy_autosearch.benchmark import best_dev_accuracy, best_dev_log_loss, evaluate
from upworthy_autosearch.utils import (
    EXPERIMENT_LOG,
    ITERATION_FILE,
    LEADERBOARD_MD,
    append_experiment_log,
    get_and_increment_iteration,
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
    branch = f"autosearch/{experiment_id}"

    print(f"[search] Experiment: {experiment_id}")

    # Create branch
    _git(["checkout", "-b", branch], check=False)

    # Snapshot previous best
    prev_best_acc = best_dev_accuracy()
    prev_best_ll = best_dev_log_loss()

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

    if improved:
        print(f"[search] IMPROVED: {prev_best_acc:.4f} → {new_acc:.4f}")
        regenerate_leaderboard()
        _git(
            [
                "add",
                "strategy.md",
                "prompt_templates/",
                "results/results.tsv",
                "results/experiment_log.md",
                "results/leaderboard.md",
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
                "results/iteration.txt",
            ],
            check=False,
        )
        _git(
            ["commit", "-m", f"autosearch: rejected iteration {iteration} [{experiment_id}]"],
            check=False,
        )

    # Switch back to main/master
    _git(["checkout", "main"], check=False)
    _git(["checkout", "master"], check=False)

    print(f"VERDICT:{verdict}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run one autosearch iteration")
    parser.add_argument("--key-change", default="", help="One-line summary of the change made")
    parser.add_argument("--rationale", default="", help="1-2 sentence explanation of why")
    args = parser.parse_args()
    run_search(key_change=args.key_change, rationale=args.rationale)
