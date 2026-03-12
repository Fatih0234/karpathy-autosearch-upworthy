"""End-to-end smoke test with 10 fake pairs using heuristic predictor."""
import pandas as pd
import pytest
from pathlib import Path


FAKE_PAIRS = [
    ("10 shocking reasons to try this today", "A new thing exists"),
    ("The secret truth about your health revealed", "Health article"),
    ("Why this amazing discovery will change everything", "Scientists find result"),
    ("7 ways this will blow your mind", "Study published"),
    ("This heartbreaking story will move you", "A story about people"),
    ("What really happens when you do this?", "Report on activity"),
    ("The devastating truth no one talks about", "Background information"),
    ("Can you believe this incredible find?", "Researchers announce"),
    ("5 surprising facts that will shock you", "Information compiled"),
    ("This beautiful moment captured forever", "Photo taken"),
]
FAKE_LABELS = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]  # all A wins by design


def test_heuristic_smoke():
    """Heuristic predictor should score >50% on obviously-winning A headlines."""
    import os
    os.environ["MODEL_PROVIDER"] = "heuristic"
    from upworthy_autosearch.model_api import get_predictor

    predict = get_predictor()
    correct = 0
    for (ha, hb), label in zip(FAKE_PAIRS, FAKE_LABELS):
        winner, confidence, _ = predict(ha, hb, {})
        if winner == label:
            correct += 1

    acc = correct / len(FAKE_PAIRS)
    print(f"Heuristic accuracy on smoke set: {acc:.0%}")
    assert acc >= 0.6, f"Expected >=60% accuracy, got {acc:.0%}"


def test_strategy_hash_stable():
    from upworthy_autosearch.utils import strategy_hash
    h1 = strategy_hash()
    h2 = strategy_hash()
    assert h1 == h2
    assert len(h1) == 16


def test_prompt_render():
    from upworthy_autosearch.prompts import render_pairwise_judge
    rendered = render_pairwise_judge(
        headline_a="Test headline A",
        headline_b="Test headline B",
        excerpt_a="Excerpt A",
        excerpt_b="Excerpt B",
    )
    assert "Test headline A" in rendered
    assert "Test headline B" in rendered
    assert "Winner:" in rendered
