def test_run_search_rejects_when_below_historical_best(monkeypatch, capsys):
    import upworthy_autosearch.search as search

    git_calls = []
    log_entry = {}
    analysis_calls = []
    leaderboard_calls = []

    monkeypatch.setenv("MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("EVAL_MAX_PAIRS", "20")
    monkeypatch.setenv("EVAL_WORKERS", "3")
    def fake_git(args, check=True):
        git_calls.append((args, check))
        if args[:3] == ["rev-parse", "--abbrev-ref", "HEAD"]:
            class Result:
                stdout = "master\n"
            return Result()
        return None

    monkeypatch.setattr(search, "_git", fake_git)
    captured_filters = {}
    def fake_best_metrics(**kwargs):
        captured_filters.update(kwargs)
        return (0.54, 0.739083)

    monkeypatch.setattr(search, "get_best_dev_metrics", fake_best_metrics)
    monkeypatch.setattr(search, "get_and_increment_iteration", lambda: 4)
    monkeypatch.setattr(search, "strategy_hash", lambda: "adf3f7598d7b9c12")
    monkeypatch.setattr(
        search,
        "evaluate",
        lambda *args, **kwargs: {"accuracy": 0.53, "log_loss": 0.81},
    )
    monkeypatch.setattr(search, "append_experiment_log", lambda **kwargs: log_entry.update(kwargs))
    monkeypatch.setattr(search, "regenerate_leaderboard", lambda: leaderboard_calls.append(True))
    monkeypatch.setattr(search, "regenerate_analysis_artifacts", lambda: analysis_calls.append(True))

    search.run_search(key_change="prompt tweak", rationale="keep current best threshold")

    output = capsys.readouterr().out

    assert "Branch=master Provider=gemini EVAL_MAX_PAIRS=20 EVAL_WORKERS=3" in output
    assert "REJECTED: 0.5300 ≤ best 0.5400" in output
    assert "VERDICT:REJECTED" in output
    assert captured_filters == {"provider": "gemini", "n_pairs": 20}
    assert log_entry["acc_before"] == 0.54
    assert log_entry["ll_before"] == 0.739083
    assert leaderboard_calls == [True]
    assert analysis_calls == [True]
    assert any(call[0][:3] == ["checkout", "--", "strategy.md"] for call in git_calls)
    assert not any(call[0][:2] == ["checkout", "-b"] for call in git_calls)
    assert not any(call[0] == ["checkout", "master"] for call in git_calls)
