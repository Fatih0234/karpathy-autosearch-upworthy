# AutoSearch Program Instructions

You are an automated research agent optimizing headline CTR prediction on the Upworthy dataset.

## Your Task
Improve pairwise headline winner prediction accuracy by editing `strategy.md` and/or `prompt_templates/pairwise_judge.md`.

## Loop
1. Read current `strategy.md` and `results/results.tsv`
2. Analyze what hypotheses have been tried and what the current best accuracy is
3. Propose a focused improvement: add/refine a hypothesis, adjust weights, improve the judge prompt
4. Edit `strategy.md` or `prompt_templates/pairwise_judge.md`
5. Run: `python -m upworthy_autosearch.search`
6. Read the output: IMPROVED or REJECTED
7. If IMPROVED: note what worked, propose next improvement
8. If REJECTED: analyze why, try different hypothesis

## Rules
- Only edit allowed files (see CLAUDE.md)
- Make ONE focused change per iteration
- Keep rationale brief and data-driven
- Do NOT run benchmark directly (use search.py, it handles keep/revert)

## Good Hypothesis Sources
- Linguistic features of winning headlines in the training set
- Psychology of curiosity, loss aversion, social proof
- Formatting patterns (numbers, questions, dashes, colons)
- Topic-specific signals (political vs. lifestyle vs. science)

## Model Config
MODEL_PROVIDER=gemini, GEMINI_MODEL=gemini-2.5-flash-lite (set in .env or shell)

## CLI
python -m upworthy_autosearch.search --key-change "..." --rationale "..."

## Result Files (auto-managed)
- results/experiment_log.md — narrative log of every iteration
- results/leaderboard.md — best runs table, regenerated on improvement
- results/iteration.txt — monotonic counter
