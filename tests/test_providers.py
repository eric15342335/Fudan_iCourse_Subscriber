from src.ai import summarizer
from src.runtime import config


def test_claude_provider_is_opt_in(monkeypatch):
    monkeypatch.delenv("USE_CLAUDE_SUBSCRIPTION", raising=False)
    assert "claude" not in [p["name"] for p in config.resolve_model_providers()]
    monkeypatch.setenv("USE_CLAUDE_SUBSCRIPTION", "1")
    assert config.resolve_model_providers()[0]["name"] == "claude"


def test_summarize_dispatches_to_claude(monkeypatch):
    monkeypatch.setenv("USE_CLAUDE_SUBSCRIPTION", "1")
    s = summarizer.Summarizer()
    monkeypatch.setattr(s, "_call_claude", lambda model, title, content: f"ok:{model}")
    assert s.summarize("t", "body") == ("ok:claude-opus-5-5", "claude/claude-opus-5-5")


def test_claude_effort_defaults_to_max():
    from src.runtime import config

    assert config.SUMMARY_EFFORT == "max"
