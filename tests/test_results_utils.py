from pathlib import Path


def test_load_results_rows_handles_mixed_schema_header(tmp_path):
    from upworthy_autosearch.utils import load_results_rows

    results_tsv = tmp_path / "results.tsv"
    results_tsv.write_text(
        "timestamp\tsplit\taccuracy\tlog_loss\tn_pairs\tstrategy_hash\tnotes\n"
        "2026-03-13T00:39:54.663003+00:00\tdev\t0.51\t0.827126\t100\tadf3f7598d7b9c12\t"
        "autosearch/20260313T003945_adf3f759\tgemini\t1\tprompt refinement\n"
        "2026-03-13T00:41:30.507789+00:00\ttest\t0.49\t0.810000\t100\tadf3f7598d7b9c12\t"
        "autosearch/20260313T004120_adf3f759\tgemini\t2\ttest split sanity\n"
    )

    rows = load_results_rows(results_tsv)

    assert len(rows) == 2
    assert rows[0]["split"] == "dev"
    assert rows[0]["accuracy"] == 0.51
    assert rows[0]["provider"] == "gemini"
    assert rows[0]["iteration"] == 1
    assert rows[0]["key_change"] == "prompt refinement"


def test_load_results_rows_handles_legacy_rows(tmp_path):
    from upworthy_autosearch.utils import load_results_rows

    results_tsv = tmp_path / "results.tsv"
    results_tsv.write_text(
        "timestamp\tsplit\taccuracy\tlog_loss\tn_pairs\tstrategy_hash\tnotes\n"
        "2026-03-13T00:39:54.663003+00:00\tdev\t0.51\t0.827126\t100\tadf3f7598d7b9c12\t"
        "autosearch/20260313T003945_adf3f759\n"
    )

    rows = load_results_rows(results_tsv)

    assert len(rows) == 1
    assert rows[0]["provider"] == "—"
    assert rows[0]["iteration"] == "—"
    assert rows[0]["key_change"] == ""


def test_load_results_rows_handles_empty_and_header_only(tmp_path):
    from upworthy_autosearch.utils import load_results_rows

    empty_tsv = tmp_path / "empty.tsv"
    empty_tsv.write_text("")
    assert load_results_rows(empty_tsv) == []

    header_only_tsv = tmp_path / "header.tsv"
    header_only_tsv.write_text("timestamp\tsplit\taccuracy\tlog_loss\tn_pairs\tstrategy_hash\tnotes\n")
    assert load_results_rows(header_only_tsv) == []


def test_best_metrics_and_leaderboard_use_parsed_rows(tmp_path, monkeypatch):
    import upworthy_autosearch.utils as utils

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    results_tsv = results_dir / "results.tsv"
    results_tsv.write_text(
        "timestamp\tsplit\taccuracy\tlog_loss\tn_pairs\tstrategy_hash\tnotes\n"
        "2026-03-13T00:39:54.663003+00:00\tdev\t0.51\t0.827126\t100\tadf3f7598d7b9c12\t"
        "autosearch/20260313T003945_adf3f759\tgemini\t1\tprompt refinement\n"
        "2026-03-13T00:41:30.507789+00:00\tdev\t0.54\t0.739083\t100\tadf3f7598d7b9c12\t"
        "autosearch/20260313T004208_adf3f759\tgemini\t3\tupworthy signals\n"
        "2026-03-13T00:42:18.149311+00:00\ttest\t0.60\t0.701000\t100\tadf3f7598d7b9c12\t"
        "autosearch/20260313T004318_adf3f759\tgemini\t4\ttest-only row\n"
        "2026-03-13T00:45:00.000000+00:00\tdev\t0.52\t0.760000\t100\tadf3f7598d7b9c12\t"
        "legacy-run\n"
    )
    leaderboard_md = results_dir / "leaderboard.md"

    monkeypatch.setattr(utils, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(utils, "RESULTS_TSV", results_tsv)
    monkeypatch.setattr(utils, "LEADERBOARD_MD", leaderboard_md)

    assert utils.get_best_dev_metrics() == (0.54, 0.739083)

    utils.regenerate_leaderboard()
    leaderboard = leaderboard_md.read_text()

    assert "primary reporting cohort (provider=gemini, n_pairs=100; 2/3 dev runs)" in leaderboard
    assert "| 1 | 0.5400 | 0.7391 | 3 | gemini | 100 | autosearch/20260313T004208_adf3f759 |" in leaderboard
    assert "| 2 | 0.5100 | 0.8271 | 1 | gemini | 100 | autosearch/20260313T003945_adf3f759 |" in leaderboard
    assert "legacy-run" not in leaderboard


def test_get_best_dev_metrics_can_filter_by_provider_and_n_pairs(tmp_path):
    from upworthy_autosearch.utils import get_best_dev_metrics

    results_tsv = tmp_path / "results.tsv"
    results_tsv.write_text(
        "timestamp\tsplit\taccuracy\tlog_loss\tn_pairs\tstrategy_hash\tnotes\n"
        "2026-03-13T00:39:54.663003+00:00\tdev\t0.51\t0.827126\t100\tadf3f7598d7b9c12\t"
        "run-1\tgemini\t1\tbaseline\n"
        "2026-03-13T00:41:30.507789+00:00\tdev\t0.60\t0.700000\t20\tadf3f7598d7b9c12\t"
        "run-2\tgemini\t2\tsmall sample\n"
        "2026-03-13T00:42:18.149311+00:00\tdev\t0.58\t0.710000\t100\tadf3f7598d7b9c12\t"
        "run-3\topenai\t3\tother provider\n"
    )

    assert get_best_dev_metrics(results_tsv) == (0.6, 0.7)
    assert get_best_dev_metrics(results_tsv, provider="gemini", n_pairs=100) == (0.51, 0.827126)


def test_analysis_artifacts_use_primary_cohort_instead_of_smoke_tests(tmp_path, monkeypatch):
    import upworthy_autosearch.utils as utils

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    results_tsv = results_dir / "results.tsv"
    results_tsv.write_text(
        "timestamp\tsplit\taccuracy\tlog_loss\tn_pairs\tstrategy_hash\tnotes\n"
        "2026-03-13T00:39:54.663003+00:00\tdev\t0.57\t0.740000\t100\tadf3f7598d7b9c12\t"
        "run-1\tgemini\t1\tfull baseline\n"
        "2026-03-13T00:40:54.663003+00:00\tdev\t0.60\t0.720000\t100\tadf3f7598d7b9c12\t"
        "run-2\tgemini\t2\tfull winner\n"
        "2026-03-13T00:41:54.663003+00:00\tdev\t0.666667\t0.790000\t3\tadf3f7598d7b9c12\t"
        "run-3\tgemini\t3\tsmoke test\n"
    )

    monkeypatch.setattr(utils, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(utils, "RESULTS_TSV", results_tsv)
    monkeypatch.setattr(utils, "ANALYSIS_SUMMARY_MD", results_dir / "analysis_summary.md")
    monkeypatch.setattr(utils, "LEADERBOARD_MD", results_dir / "leaderboard.md")
    monkeypatch.setattr(utils, "METRICS_CSV", results_dir / "metrics.csv")
    monkeypatch.setattr(utils, "ACCURACY_SVG", results_dir / "accuracy_over_time.svg")
    monkeypatch.setattr(utils, "LOG_LOSS_SVG", results_dir / "log_loss_over_time.svg")
    monkeypatch.setattr(utils, "EXTENDED_ANALYSIS_MD", results_dir / "extended_analysis.md")

    utils.regenerate_analysis_artifacts()
    utils.regenerate_leaderboard()

    summary = (results_dir / "analysis_summary.md").read_text()
    leaderboard = (results_dir / "leaderboard.md").read_text()
    metrics = (results_dir / "metrics.csv").read_text()
    extended = (results_dir / "extended_analysis.md").read_text()

    assert "- Total dev runs: 3" in summary
    assert "- Reporting cohort: provider=gemini, n_pairs=100 (2 runs)" in summary
    assert "- Best accuracy: 0.6000 (run 2, iteration 2)" in summary
    assert "0.6667" not in summary

    assert "primary reporting cohort (provider=gemini, n_pairs=100; 2/3 dev runs)" in leaderboard
    assert "smoke test" not in leaderboard
    assert "| 1 | 0.6000 | 0.7200 | 2 | gemini | 100 | run-2 |" in leaderboard

    assert metrics.count("\n") == 3
    assert ",3," not in metrics
    assert "- Reporting cohort: provider=gemini, n_pairs=100" in extended


def test_analysis_summary_breaks_accuracy_ties_with_log_loss(tmp_path, monkeypatch):
    import upworthy_autosearch.utils as utils

    results_dir = tmp_path / "results"
    results_dir.mkdir()
    results_tsv = results_dir / "results.tsv"
    results_tsv.write_text(
        "timestamp\tsplit\taccuracy\tlog_loss\tn_pairs\tstrategy_hash\tnotes\n"
        "2026-03-13T00:39:54.663003+00:00\tdev\t0.60\t0.740000\t100\tadf3f7598d7b9c12\t"
        "run-1\tgemini\t1\ttied accuracy worse log loss\n"
        "2026-03-13T00:40:54.663003+00:00\tdev\t0.60\t0.720000\t100\tadf3f7598d7b9c12\t"
        "run-2\tgemini\t2\ttied accuracy better log loss\n"
    )

    monkeypatch.setattr(utils, "RESULTS_DIR", results_dir)
    monkeypatch.setattr(utils, "RESULTS_TSV", results_tsv)
    monkeypatch.setattr(utils, "ANALYSIS_SUMMARY_MD", results_dir / "analysis_summary.md")
    monkeypatch.setattr(utils, "METRICS_CSV", results_dir / "metrics.csv")
    monkeypatch.setattr(utils, "ACCURACY_SVG", results_dir / "accuracy_over_time.svg")
    monkeypatch.setattr(utils, "LOG_LOSS_SVG", results_dir / "log_loss_over_time.svg")
    monkeypatch.setattr(utils, "EXTENDED_ANALYSIS_MD", results_dir / "extended_analysis.md")

    utils.regenerate_analysis_artifacts()

    summary = (results_dir / "analysis_summary.md").read_text()
    assert "- Best accuracy: 0.6000 (run 2, iteration 2)" in summary
