"""Tests for benchmark evaluator metrics."""
import numpy as np
import pytest
from sklearn.metrics import accuracy_score, log_loss


def test_accuracy_perfect():
    labels = [1, 0, 1, 0, 1]
    preds = [1, 0, 1, 0, 1]
    assert accuracy_score(labels, preds) == 1.0


def test_accuracy_random():
    labels = [1, 0, 1, 0]
    preds = [0, 1, 0, 1]
    assert accuracy_score(labels, preds) == 0.0


def test_log_loss_perfect():
    labels = [1, 0, 1]
    probs = [0.999, 0.001, 0.999]
    ll = log_loss(labels, probs)
    assert ll < 0.01


def test_log_loss_random():
    labels = [1, 0, 1, 0]
    probs = [0.5, 0.5, 0.5, 0.5]
    ll = log_loss(labels, probs)
    assert abs(ll - np.log(2)) < 0.01


def test_benchmark_evaluate_synthetic(tmp_path, monkeypatch):
    """benchmark.evaluate on synthetic parquet with heuristic predictor."""
    import pandas as pd
    from pathlib import Path

    # Build tiny synthetic parquet
    data = {
        "test_id": ["t1", "t1", "t2"],
        "pair_id": ["t1_1", "t1_2", "t2_1"],
        "headline_a": [
            "7 shocking reasons this will amaze you",
            "The secret truth revealed today",
            "Breaking news: amazing discovery",
        ],
        "headline_b": [
            "A headline",
            "Something happened",
            "News update",
        ],
        "excerpt_a": ["", "", ""],
        "excerpt_b": ["", "", ""],
        "ctr_a": [0.05, 0.04, 0.06],
        "ctr_b": [0.02, 0.01, 0.03],
        "label": [1, 1, 1],
        "eyecatcher_same": [True, False, True],
    }
    df = pd.DataFrame(data)
    proc_dir = tmp_path / "data" / "processed"
    proc_dir.mkdir(parents=True)
    df.to_parquet(proc_dir / "dev.parquet", index=False)

    results_dir = tmp_path / "results"
    results_dir.mkdir()

    import upworthy_autosearch.benchmark as bm
    monkeypatch.setattr(bm, "PROCESSED_DIR", proc_dir)
    monkeypatch.setattr(bm, "RESULTS_TSV", results_dir / "results.tsv")

    result = bm.evaluate("dev")
    assert 0.0 <= result["accuracy"] <= 1.0
    assert result["n_pairs"] == 3
    assert "log_loss" in result
