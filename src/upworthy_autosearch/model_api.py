"""Provider abstraction for pairwise headline prediction.

Providers (selected via MODEL_PROVIDER env var):
  heuristic      — no API key required
  openai         — OPENAI_API_KEY
  gemini         — GOOGLE_API_KEY
  openai_compat  — OPENAI_BASE_URL + optional OPENAI_API_KEY
"""
from __future__ import annotations

import os
import re
from typing import Callable

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

PredictFn = Callable[[str, str, dict], tuple[int, float, str]]


# ---------------------------------------------------------------------------
# Heuristic predictor
# ---------------------------------------------------------------------------

CURIOSITY_GAP_WORDS = {
    "secret", "surprising", "shocking", "unexpected", "reveal", "revealed",
    "hidden", "untold", "real reason", "truth", "you didn't know",
    "what happens", "will shock", "won't believe",
}

EMOTIONAL_WORDS = {
    "amazing", "incredible", "heartbreaking", "devastating", "inspiring",
    "terrifying", "stunning", "outrage", "beautiful", "tragic", "powerful",
    "moving", "unbelievable", "emotional",
}


def _score_headline(headline: str) -> float:
    """Higher = more likely to win (heuristic)."""
    h = headline.lower()
    score = 0.0

    # Curiosity-gap signals
    for w in CURIOSITY_GAP_WORDS:
        if w in h:
            score += 1.5

    # Emotional words
    for w in EMOTIONAL_WORDS:
        if w in h:
            score += 1.0

    # Numbers signal specificity
    if re.search(r"\b\d+\b", h):
        score += 1.0

    # Questions drive engagement
    if "?" in headline:
        score += 0.5

    # List formats ("X things", "X ways", etc.)
    if re.search(r"\b\d+\s+(things|ways|reasons|facts|tips|steps|signs)\b", h):
        score += 1.0

    # Optimal length 60-100 chars
    l = len(headline)
    if 60 <= l <= 100:
        score += 0.5
    elif l < 30 or l > 150:
        score -= 0.5

    return score


def heuristic_predict(headline_a: str, headline_b: str, context: dict) -> tuple[int, float, str]:
    sa = _score_headline(headline_a)
    sb = _score_headline(headline_b)
    total = abs(sa) + abs(sb) + 1e-9
    if sa >= sb:
        confidence = 0.5 + (sa - sb) / (2 * (abs(sa - sb) + 1))
        confidence = max(0.51, min(0.95, confidence))
        return 1, confidence, f"A scored {sa:.2f} vs B {sb:.2f}"
    else:
        confidence = 0.5 + (sb - sa) / (2 * (abs(sa - sb) + 1))
        confidence = max(0.51, min(0.95, confidence))
        return 0, confidence, f"B scored {sb:.2f} vs A {sa:.2f}"


# ---------------------------------------------------------------------------
# OpenAI predictor
# ---------------------------------------------------------------------------

def _parse_llm_response(text: str) -> tuple[int, float, str]:
    """Parse LLM response: expect Winner: A/B, Confidence: 0.X, Rationale: ..."""
    winner = 1  # default A
    confidence = 0.6
    rationale = text[:200]

    m = re.search(r"Winner\s*:\s*([AB])", text, re.IGNORECASE)
    if m:
        winner = 1 if m.group(1).upper() == "A" else 0

    m = re.search(r"Confidence\s*:\s*([\d.]+)", text, re.IGNORECASE)
    if m:
        try:
            confidence = float(m.group(1))
            confidence = max(0.01, min(0.99, confidence))
        except ValueError:
            pass

    m = re.search(r"Rationale\s*:\s*(.+?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL)
    if m:
        rationale = m.group(1).strip()[:500]

    return winner, confidence, rationale


def openai_predict(headline_a: str, headline_b: str, context: dict) -> tuple[int, float, str]:
    from openai import OpenAI
    from upworthy_autosearch.prompts import render_pairwise_judge

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    prompt = render_pairwise_judge(
        headline_a=headline_a,
        headline_b=headline_b,
        excerpt_a=context.get("excerpt_a", ""),
        excerpt_b=context.get("excerpt_b", ""),
    )
    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return _parse_llm_response(resp.choices[0].message.content or "")


def gemini_predict(headline_a: str, headline_b: str, context: dict) -> tuple[int, float, str]:
    import google.generativeai as genai
    from upworthy_autosearch.prompts import render_pairwise_judge

    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"))
    prompt = render_pairwise_judge(
        headline_a=headline_a,
        headline_b=headline_b,
        excerpt_a=context.get("excerpt_a", ""),
        excerpt_b=context.get("excerpt_b", ""),
    )
    resp = model.generate_content(prompt)
    return _parse_llm_response(resp.text or "")


def openai_compat_predict(headline_a: str, headline_b: str, context: dict) -> tuple[int, float, str]:
    from openai import OpenAI
    from upworthy_autosearch.prompts import render_pairwise_judge

    client = OpenAI(
        base_url=os.environ["OPENAI_BASE_URL"],
        api_key=os.environ.get("OPENAI_API_KEY", "dummy"),
    )
    prompt = render_pairwise_judge(
        headline_a=headline_a,
        headline_b=headline_b,
        excerpt_a=context.get("excerpt_a", ""),
        excerpt_b=context.get("excerpt_b", ""),
    )
    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return _parse_llm_response(resp.choices[0].message.content or "")


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, PredictFn] = {
    "heuristic": heuristic_predict,
    "openai": openai_predict,
    "gemini": gemini_predict,
    "openai_compat": openai_compat_predict,
}


def get_predictor() -> PredictFn:
    provider = os.environ.get("MODEL_PROVIDER", "heuristic").lower()
    if provider not in _PROVIDERS:
        raise ValueError(f"Unknown MODEL_PROVIDER={provider!r}. Choose from {list(_PROVIDERS)}")
    return _PROVIDERS[provider]
