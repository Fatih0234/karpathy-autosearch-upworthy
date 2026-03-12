"""Shared utilities."""
from __future__ import annotations

import hashlib
from pathlib import Path

STRATEGY_FILE = Path(__file__).parents[2] / "strategy.md"


def strategy_hash() -> str:
    """SHA-256 of strategy.md (first 16 hex chars)."""
    if not STRATEGY_FILE.exists():
        return "no-strategy"
    content = STRATEGY_FILE.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]
