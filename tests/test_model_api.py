import sys
from types import ModuleType, SimpleNamespace

import pytest


def test_get_gemini_client_uses_timeout_and_retry_env(monkeypatch):
    import upworthy_autosearch.model_api as model_api

    captured = {}

    class FakeHttpRetryOptions:
        def __init__(self, attempts):
            self.attempts = attempts

    class FakeHttpOptions:
        def __init__(self, timeout=None, retryOptions=None):
            self.timeout = timeout
            self.retryOptions = retryOptions

    class FakeClient:
        def __init__(self, api_key=None, http_options=None):
            captured["api_key"] = api_key
            captured["http_options"] = http_options

    google_mod = ModuleType("google")
    google_mod.genai = SimpleNamespace(Client=FakeClient)
    google_genai_mod = ModuleType("google.genai")
    google_genai_mod.types = SimpleNamespace(
        HttpOptions=FakeHttpOptions,
        HttpRetryOptions=FakeHttpRetryOptions,
    )

    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.genai", google_genai_mod)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_TIMEOUT_MS", "1234")
    monkeypatch.setenv("GEMINI_RETRY_ATTEMPTS", "7")
    if hasattr(model_api._get_gemini_client, "_local"):
        delattr(model_api._get_gemini_client, "_local")

    model_api._get_gemini_client()

    assert captured["api_key"] == "test-key"
    assert captured["http_options"].timeout == 1234
    assert captured["http_options"].retryOptions.attempts == 7


def test_gemini_predict_reports_timeout_bound(monkeypatch, capsys):
    import upworthy_autosearch.model_api as model_api
    import upworthy_autosearch.prompts as prompts

    class FakeModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("network stalled")

    monkeypatch.setattr(model_api, "_get_gemini_client", lambda: SimpleNamespace(models=FakeModels()))
    monkeypatch.setattr(prompts, "render_pairwise_judge", lambda **kwargs: "prompt")
    monkeypatch.setenv("GEMINI_TIMEOUT_MS", "4321")

    with pytest.raises(RuntimeError, match="network stalled"):
        model_api.gemini_predict("A", "B", {})

    assert "4321ms" in capsys.readouterr().err
