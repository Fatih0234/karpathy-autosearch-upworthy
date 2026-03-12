"""Build benchmark splits from raw Upworthy CSVs.

Fixed pipeline — agent must never edit this file.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from upworthy_autosearch.data import ensure_raw_data

PROCESSED_DIR = Path(__file__).parents[2] / "data" / "processed"
TIE_THRESHOLD = 0.001
RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_raw() -> pd.DataFrame:
    paths = ensure_raw_data()
    frames = []
    for name, path in paths.items():
        df = pd.read_csv(path, low_memory=False)
        df["_source"] = name
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _filter(df: pd.DataFrame) -> pd.DataFrame:
    # 1. Exclude problem rows
    if "problem" in df.columns:
        df = df[df["problem"] != 1]
    # 2. Exclude missing / zero impressions
    df = df[df["impressions"].notna() & (df["impressions"] > 0)]
    # 3. Compute CTR
    df = df.copy()
    df["ctr"] = df["clicks"] / df["impressions"]
    return df


def _make_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Create pairwise comparison rows within each clickability_test_id."""
    records = []
    pair_counter: dict[str, int] = {}

    for test_id, group in df.groupby("clickability_test_id"):
        rows = group.reset_index(drop=True)
        n = len(rows)
        for i in range(n):
            for j in range(i + 1, n):
                a = rows.iloc[i]
                b = rows.iloc[j]

                # Prefer same eyecatcher_id pairs
                same_eye = (
                    pd.notna(a.get("eyecatcher_id"))
                    and pd.notna(b.get("eyecatcher_id"))
                    and a.get("eyecatcher_id") == b.get("eyecatcher_id")
                )

                ctr_a = float(a["ctr"])
                ctr_b = float(b["ctr"])

                # Exclude ties
                if abs(ctr_a - ctr_b) < TIE_THRESHOLD:
                    continue

                label = 1 if ctr_a > ctr_b else 0

                tid = str(test_id)
                pair_counter[tid] = pair_counter.get(tid, 0) + 1
                pair_id = f"{tid}_{pair_counter[tid]}"

                records.append(
                    {
                        "test_id": test_id,
                        "pair_id": pair_id,
                        "headline_a": str(a.get("headline", "")),
                        "headline_b": str(b.get("headline", "")),
                        "excerpt_a": str(a.get("excerpt", "")),
                        "excerpt_b": str(b.get("excerpt", "")),
                        "ctr_a": ctr_a,
                        "ctr_b": ctr_b,
                        "label": label,
                        "eyecatcher_same": same_eye,
                    }
                )

    return pd.DataFrame(records)


def _split(pairs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by test_id to avoid row-level leakage: 70/15/15."""
    test_ids = pairs["test_id"].values
    unique_tests = np.array(pairs["test_id"].unique())

    # First split off test (15%)
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=RANDOM_SEED)
    train_dev_idx, test_idx = next(splitter.split(pairs, groups=test_ids))
    train_dev = pairs.iloc[train_dev_idx].reset_index(drop=True)
    test_df = pairs.iloc[test_idx].reset_index(drop=True)

    # Then split dev (15% of original ≈ 15/85 of train_dev)
    dev_frac = 0.15 / 0.85
    splitter2 = GroupShuffleSplit(
        n_splits=1, test_size=dev_frac, random_state=RANDOM_SEED
    )
    train_idx2, dev_idx2 = next(
        splitter2.split(train_dev, groups=train_dev["test_id"].values)
    )
    train_df = train_dev.iloc[train_idx2].reset_index(drop=True)
    dev_df = train_dev.iloc[dev_idx2].reset_index(drop=True)

    return train_df, dev_df, test_df


def build_splits() -> None:
    """Full pipeline: download → filter → pair → split → save."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading raw data …")
    raw = _load_raw()
    print(f"  Raw rows: {len(raw)}")

    print("Filtering …")
    filtered = _filter(raw)
    print(f"  After filter: {len(filtered)}")

    print("Making pairs …")
    pairs = _make_pairs(filtered)
    print(f"  Pairs: {len(pairs)}")

    print("Splitting …")
    train, dev, test = _split(pairs)
    print(f"  Train: {len(train)}  Dev: {len(dev)}  Test: {len(test)}")

    for name, df in [("train", train), ("dev", dev), ("test", test)]:
        out = PROCESSED_DIR / f"{name}.parquet"
        df.to_parquet(out, index=False)
        print(f"  Saved {out}")

    print("Done.")


if __name__ == "__main__":
    build_splits()
