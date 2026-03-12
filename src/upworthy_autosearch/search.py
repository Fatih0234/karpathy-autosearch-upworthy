"""Experiment search loop.

One iteration:
  1. Create experiment branch
  2. Run benchmark on dev split
  3. Compare to best historical score
  4. Keep if improved, revert if not
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from upworthy_autosearch.benchmark import best_dev_accuracy, evaluate
from upworthy_autosearch.utils import strategy_hash


def _git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        check=check,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[2],
    )


def run_search() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    shash = strategy_hash()[:8]
    experiment_id = f"{ts}_{shash}"
    branch = f"autosearch/{experiment_id}"

    print(f"[search] Experiment: {experiment_id}")

    # Create branch
    _git(["checkout", "-b", branch], check=False)

    # Benchmark current strategy
    prev_best = best_dev_accuracy()
    result = evaluate("dev", notes=f"autosearch/{experiment_id}")
    new_acc = result["accuracy"]

    if new_acc > prev_best:
        print(f"[search] IMPROVED: {prev_best:.4f} → {new_acc:.4f}")
        _git(["add", "strategy.md", "prompt_templates/", "results/results.tsv"], check=False)
        _git(
            [
                "commit",
                "-m",
                f"autosearch: improve dev acc {prev_best:.4f}→{new_acc:.4f} [{experiment_id}]",
            ],
            check=False,
        )
        print("[search] Changes committed.")
    else:
        print(f"[search] REJECTED: {new_acc:.4f} ≤ best {prev_best:.4f}")
        _git(["checkout", "--", "strategy.md", "prompt_templates/"], check=False)

    # Switch back to main/master
    _git(["checkout", "main"], check=False)
    _git(["checkout", "master"], check=False)


if __name__ == "__main__":
    run_search()
