"""Tests for dataset preparation pipeline."""
import pandas as pd
import pytest


def make_fake_raw(n_tests: int = 5, n_variants_per_test: int = 3) -> pd.DataFrame:
    """Generate minimal fake raw data with the required columns."""
    rows = []
    for t in range(n_tests):
        for v in range(n_variants_per_test):
            rows.append({
                "clickability_test_id": f"test_{t}",
                "eyecatcher_id": f"eye_{t}",
                "headline": f"Headline test={t} variant={v}",
                "excerpt": f"Excerpt for test {t} variant {v}",
                "impressions": 1000 + v * 100 + t * 10,
                "clicks": 50 + v * 15 + t * 3,
                "problem": 0,
            })
    return pd.DataFrame(rows)


def test_filter_removes_problem_rows():
    from upworthy_autosearch.prepare_dataset import _filter
    df = make_fake_raw()
    df.loc[0, "problem"] = 1
    filtered = _filter(df)
    assert len(filtered) == len(df) - 1


def test_filter_removes_zero_impressions():
    from upworthy_autosearch.prepare_dataset import _filter
    df = make_fake_raw()
    df.loc[0, "impressions"] = 0
    filtered = _filter(df)
    assert len(filtered) == len(df) - 1


def test_filter_computes_ctr():
    from upworthy_autosearch.prepare_dataset import _filter
    df = make_fake_raw()
    filtered = _filter(df)
    assert "ctr" in filtered.columns
    assert (filtered["ctr"] >= 0).all()
    assert (filtered["ctr"] <= 1).all()


def test_make_pairs_excludes_ties():
    from upworthy_autosearch.prepare_dataset import _filter, _make_pairs, TIE_THRESHOLD
    df = make_fake_raw(n_tests=1, n_variants_per_test=2)
    df = _filter(df)
    # Force a tie
    df.loc[df.index[0], "clicks"] = df.loc[df.index[1], "clicks"]
    df.loc[df.index[0], "impressions"] = df.loc[df.index[1], "impressions"]
    df["ctr"] = df["clicks"] / df["impressions"]
    pairs = _make_pairs(df)
    for _, row in pairs.iterrows():
        assert abs(row["ctr_a"] - row["ctr_b"]) >= TIE_THRESHOLD


def test_split_no_test_id_leakage():
    from upworthy_autosearch.prepare_dataset import _filter, _make_pairs, _split
    df = make_fake_raw(n_tests=20, n_variants_per_test=4)
    df = _filter(df)
    pairs = _make_pairs(df)
    train, dev, test = _split(pairs)

    train_ids = set(train["test_id"].unique())
    dev_ids = set(dev["test_id"].unique())
    test_ids = set(test["test_id"].unique())

    # No test_id should appear in more than one split
    assert train_ids.isdisjoint(test_ids), "Test IDs leaked into train"
    assert dev_ids.isdisjoint(test_ids), "Test IDs leaked into dev"
    assert train_ids.isdisjoint(dev_ids), "Dev IDs leaked into train"


def test_split_covers_all_pairs():
    from upworthy_autosearch.prepare_dataset import _filter, _make_pairs, _split
    df = make_fake_raw(n_tests=20, n_variants_per_test=4)
    df = _filter(df)
    pairs = _make_pairs(df)
    train, dev, test = _split(pairs)
    assert len(train) + len(dev) + len(test) == len(pairs)
