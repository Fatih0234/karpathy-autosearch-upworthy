# Experiment Log

## Iteration 1 — ✅ IMPROVED

| Field | Value |
|---|---|
| experiment_id | `20260313T003945_adf3f759` |
| strategy_hash | `adf3f7598d7b9c12` |
| timestamp | 2026-03-13 00:39 UTC |
| key_change | enrich judge prompt with explicit scoring signals and tie-breaking rules from strategy.md |
| accuracy | 0.0000 → 0.5100 |
| log_loss | inf → 0.8271 |

**Rationale:** The generic prompt lacked concrete signals; adding specific keywords, number patterns, length rules, and tie-breakers gives the LLM judge clearer criteria to apply.

---

## Iteration 2 — ✅ IMPROVED

| Field | Value |
|---|---|
| experiment_id | `20260313T004120_adf3f759` |
| strategy_hash | `adf3f7598d7b9c12` |
| timestamp | 2026-03-13 00:41 UTC |
| key_change | add chain-of-thought analysis step + confidence calibration guidance |
| accuracy | 0.0000 → 0.5300 |
| log_loss | inf → 0.7998 |

**Rationale:** Log_loss was 0.827 (worse than random), suggesting overconfidence in wrong answers; forcing explicit per-signal analysis and a 0.55-0.90 confidence range should reduce miscalibration.

---

## Iteration 3 — ✅ IMPROVED

| Field | Value |
|---|---|
| experiment_id | `20260313T004208_adf3f759` |
| strategy_hash | `adf3f7598d7b9c12` |
| timestamp | 2026-03-13 00:42 UTC |
| key_change | add personal-relevance and surprise/reversal signals (Upworthy-specific) |
| accuracy | 0.0000 → 0.5400 |
| log_loss | inf → 0.7391 |

**Rationale:** Upworthy content is famous for "you/your" framing and unexpected reversals; these are high-CTR signals not yet in the prompt.

---

