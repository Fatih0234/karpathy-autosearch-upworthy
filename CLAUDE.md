# Claude Instructions for Upworthy AutoSearch

## Editable Files (agent may modify)
- `strategy.md` — prediction strategy, hypotheses, scoring rules
- `prompt_templates/pairwise_judge.md` — LLM judge prompt
- `results/experiment_log.md` — narrative log (append-only, managed by search.py)
- `results/leaderboard.md` — auto-generated leaderboard (managed by search.py)

## Forbidden Files (agent must NEVER edit)
- `src/upworthy_autosearch/benchmark.py` — fixed evaluator
- `src/upworthy_autosearch/prepare_dataset.py` — fixed data pipeline
- `src/upworthy_autosearch/data.py` — fixed downloader
- `results/results.tsv` — append only (search.py handles this)
- `results/iteration.txt` — monotonic counter (search.py handles this)
- Any file in `data/` directory

## Logging Rules
- Every benchmark run appends one TSV row to `results/results.tsv`
- Never delete rows from results.tsv
- Never modify past rows in results.tsv

## Keep/Revert Rules
- If dev accuracy improves: commit strategy.md + prompt_templates/ changes
- If dev accuracy does not improve: `git checkout -- strategy.md prompt_templates/`
- Never commit changes to forbidden files

## Optimization Goal
Maximize accuracy on `dev` split for pairwise headline winner prediction.
Current best is in `results/results.tsv` (max accuracy where split=dev).
