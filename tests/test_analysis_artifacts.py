def test_regenerate_analysis_artifacts_creates_summary_csv_and_svgs(tmp_path, monkeypatch):
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
    )

    monkeypatch.setattr(utils, "RESULTS_TSV", results_tsv)
    monkeypatch.setattr(utils, "ANALYSIS_SUMMARY_MD", results_dir / "analysis_summary.md")
    monkeypatch.setattr(utils, "METRICS_CSV", results_dir / "metrics.csv")
    monkeypatch.setattr(utils, "ACCURACY_SVG", results_dir / "accuracy_over_time.svg")
    monkeypatch.setattr(utils, "LOG_LOSS_SVG", results_dir / "log_loss_over_time.svg")

    utils.regenerate_analysis_artifacts()

    summary = (results_dir / "analysis_summary.md").read_text()
    metrics_csv = (results_dir / "metrics.csv").read_text()
    accuracy_svg = (results_dir / "accuracy_over_time.svg").read_text()
    log_loss_svg = (results_dir / "log_loss_over_time.svg").read_text()

    assert "Total dev runs: 2" in summary
    assert "Best accuracy: 0.5400" in summary
    assert "running_best_accuracy" in metrics_csv
    assert "svg" in accuracy_svg
    assert "Dev Log Loss by Run" in log_loss_svg
