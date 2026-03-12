"""Load and render prompt templates."""
from __future__ import annotations

from pathlib import Path

TEMPLATE_DIR = Path(__file__).parents[2] / "prompt_templates"


def load_template(name: str) -> str:
    path = TEMPLATE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text()


def render_pairwise_judge(
    headline_a: str,
    headline_b: str,
    excerpt_a: str = "",
    excerpt_b: str = "",
) -> str:
    template = load_template("pairwise_judge.md")
    return template.format(
        headline_a=headline_a,
        headline_b=headline_b,
        excerpt_a=excerpt_a or "(none)",
        excerpt_b=excerpt_b or "(none)",
    )
