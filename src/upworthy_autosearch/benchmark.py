"""Fixed evaluator — do NOT edit in search mode.

Usage:
    python -m upworthy_autosearch.benchmark dev
    python -m upworthy_autosearch.benchmark test
"""
from __future__ import annotations

import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, log_loss

from upworthy_autosearch.model_api import get_predictor
from upworthy_autosearch.utils import strategy_hash

PROCESSED_DIR = Path(__file__).parents[2] / "data" / "processed"
RESULTS_TSV = Path(__file__).parents[2] / "results" / "results.tsv"
RESULTS_TSV.parent.mkdir(parents=True, exist_ok=True)

COLUMNS = [
    "timestamp",
    "split",
    "accuracy",
    "log_loss",
    "n_pairs",
    "strategy_hash",
    "notes",
]


def _ensure_results_tsv() -> None:
    if not RESULTS_TSV.exists():
        with open(RESULTS_TSV, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(COLUMNS)


def evaluate(split: str = "dev", notes: str = "") -> dict:
    """Run predictor on *split*, compute metrics, append to results.tsv."""
    parquet = PROCESSED_DIR / f"{split}.parquet"
    if not parquet.exists():
        raise FileNotFoundError(
            f"Split file not found: {parquet}\n"
            "Run: python -m upworthy_autosearch.prepare_dataset"
        )

    df = pd.read_parquet(parquet)
    predict = get_predictor()

    labels = []
    preds = []
    probs = []

    for _, row in df.iterrows():
        winner, confidence, _ = predict(
            headline_a=row["headline_a"],
            headline_b=row["headline_b"],
            context={
                "excerpt_a": row["excerpt_a"],
                "excerpt_b": row["excerpt_b"],
                "eyecatcher_same": row["eyecatcher_same"],
            },
        )
        labels.append(int(row["label"]))
        preds.append(int(winner))
        # Confidence as probability for label=1
        p1 = confidence if winner == 1 else (1 - confidence)
        probs.append(np.clip(p1, 1e-7, 1 - 1e-7))

    acc = accuracy_score(labels, preds)
    ll = log_loss(labels, probs)
    n = len(labels)
    shash = strategy_hash()
    ts = datetime.now(timezone.utc).isoformat()

    result = {
        "timestamp": ts,
        "split": split,
        "accuracy": round(acc, 6),
        "log_loss": round(ll, 6),
        "n_pairs": n,
        "strategy_hash": shash,
        "notes": notes,
    }

    _ensure_results_tsv()
    with open(RESULTS_TSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t")
        writer.writerow(result)

    print(
        f"[benchmark] split={split} acc={acc:.4f} log_loss={ll:.4f} "
        f"n={n} hash={shash[:8]}"
    )
    return result


def best_dev_accuracy() -> float:
    """Return best accuracy on dev split from results.tsv (0.0 if empty)."""
    if not RESULTS_TSV.exists():
        return 0.0
    df = pd.read_csv(RESULTS_TSV, sep="\t")
    dev = df[df["split"] == "dev"]
    if dev.empty:
        return 0.0
    return float(dev["accuracy"].max())


if __name__ == "__main__":
    split = sys.argv[1] if len(sys.argv) > 1 else "dev"
    evaluate(split)
