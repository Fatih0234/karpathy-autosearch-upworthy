# Upworthy AutoSearch

Minimal agentic optimization for headline CTR prediction on the [Upworthy Research Archive](https://osf.io/jd64p/).

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch): fixed evaluator, one editable strategy file, keep/revert loop.

## What It Does

- **V1**: Pairwise winner prediction — given two headlines for the same A/B test, predict which got higher CTR
- **Metric**: Accuracy on held-out test pairs (dev split during search, test split for final eval)
- **Loop**: Agent edits `strategy.md`, runs benchmark, keeps changes if dev accuracy improves, reverts if not

## Quick Start

```bash
# Install
pip install uv
uv sync

# Download data + build splits (~600MB download)
uv run python -m upworthy_autosearch.prepare_dataset

# Evaluate dev split (heuristic mode, no API key needed)
uv run python -m upworthy_autosearch.benchmark dev

# One search iteration
uv run python -m upworthy_autosearch.search

# Run tests
uv run pytest tests/
```

## Providers

Set `MODEL_PROVIDER` env var:

| Value | Requires |
|-------|----------|
| `heuristic` | Nothing (default) |
| `openai` | `OPENAI_API_KEY` |
| `gemini` | `GOOGLE_API_KEY` |
| `openai_compat` | `OPENAI_BASE_URL` |

## Files

| File | Editable by agent? |
|------|-------------------|
| `strategy.md` | YES |
| `prompt_templates/pairwise_judge.md` | YES |
| `src/upworthy_autosearch/benchmark.py` | NO |
| `src/upworthy_autosearch/prepare_dataset.py` | NO |
| `results/results.tsv` | Append only |

## Loop Mechanics

1. Agent proposes a change to `strategy.md` or the judge prompt
2. `search.py` creates a branch, runs `benchmark.py` on dev split
3. If new accuracy > best historical accuracy → commit kept
4. If not → `git checkout --` reverts editable files

## Dataset

Upworthy Research Archive: ~32,000 A/B tests from 2012–2014. Each test has 2+ headline variants shown to different user segments. We use CTR (clicks/impressions) as ground truth.

Preprocessing: exclude broken rows (`problem==1`), exclude zero-impression rows, exclude ties (|CTR_a - CTR_b| < 0.001), split by test_id to avoid leakage.
