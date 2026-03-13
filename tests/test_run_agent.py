import os
import stat
import subprocess
from pathlib import Path


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _make_fake_repo(tmp_path: Path, agent_behavior: str) -> Path:
    repo_root = tmp_path / "repo"
    (repo_root / "scripts").mkdir(parents=True)
    (repo_root / "results").mkdir()
    (repo_root / "bin").mkdir()

    script_src = Path(__file__).resolve().parents[1] / "scripts" / "run_agent.sh"
    (repo_root / "scripts" / "run_agent.sh").write_text(script_src.read_text())
    (repo_root / ".env").write_text("MODEL_PROVIDER=heuristic\nGEMINI_MODEL=test-model\n")
    (repo_root / "program.md").write_text("# Program\n")
    (repo_root / "strategy.md").write_text("# Strategy\n")
    (repo_root / "results" / "results.tsv").write_text(
        "timestamp\tsplit\taccuracy\tlog_loss\tn_pairs\tstrategy_hash\tnotes\n"
    )

    _write_executable(repo_root / "bin" / "uv", "#!/bin/sh\nexit 0\n")

    if agent_behavior == "fast":
        agent_body = "#!/bin/sh\ncat >/dev/null\nprintf 'VERDICT:IMPROVED\\n'\n"
    elif agent_behavior == "slow":
        agent_body = "#!/bin/sh\ncat >/dev/null\nsleep 2\nprintf 'VERDICT:IMPROVED\\n'\n"
    elif agent_behavior == "timeout":
        agent_body = "#!/bin/sh\ntrap 'exit 0' TERM\ncat >/dev/null\nsleep 10\n"
    else:
        raise ValueError(f"Unknown behavior: {agent_behavior}")

    _write_executable(repo_root / "bin" / "claude", agent_body)
    _write_executable(repo_root / "bin" / "codex", agent_body)
    return repo_root


def _run_agent(repo_root: Path, timeout: int = 15, agent_cli: str = "claude") -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{repo_root / 'bin'}:{env['PATH']}"
    env["AGENT_HEARTBEAT_SECS"] = "1"
    env["AGENT_TIMEOUT_SECS"] = "3"
    env["AGENT_CLI"] = agent_cli
    return subprocess.run(
        ["bash", str(repo_root / "scripts" / "run_agent.sh"), "1"],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def test_run_agent_fast_success(tmp_path):
    repo_root = _make_fake_repo(tmp_path, "fast")

    result = _run_agent(repo_root)

    assert result.returncode == 0
    assert "VERDICT:IMPROVED" in result.stdout
    assert "[agent] Iteration 1 complete." in result.stdout


def test_run_agent_emits_heartbeat_for_slow_runs(tmp_path):
    repo_root = _make_fake_repo(tmp_path, "slow")

    result = _run_agent(repo_root)

    assert result.returncode == 0
    assert "still running" in result.stdout
    assert "VERDICT:IMPROVED" in result.stdout


def test_run_agent_times_out_and_preserves_log_path(tmp_path):
    repo_root = _make_fake_repo(tmp_path, "timeout")

    result = _run_agent(repo_root)

    assert result.returncode == 124
    assert "timed out" in result.stderr or "timed out" in result.stdout
    assert "Full log:" in result.stderr


def test_run_agent_supports_codex_backend(tmp_path):
    repo_root = _make_fake_repo(tmp_path, "fast")

    result = _run_agent(repo_root, agent_cli="codex")

    assert result.returncode == 0
    assert "outer_agent=codex" in result.stdout
    assert "VERDICT:IMPROVED" in result.stdout
