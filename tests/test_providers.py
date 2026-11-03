import importlib

from src.ai import claude_sdk, summarizer
from src.runtime import fork_config


def test_claude_provider_is_opt_in(monkeypatch):
    monkeypatch.setattr(fork_config, "USE_CLAUDE_SUBSCRIPTION", False)
    assert not claude_sdk.providers()
    monkeypatch.setattr(fork_config, "USE_CLAUDE_SUBSCRIPTION", True)
    assert claude_sdk.providers()[0]["name"] == "claude"


def test_summarize_goes_through_claude(monkeypatch):
    monkeypatch.setattr(fork_config, "USE_CLAUDE_SUBSCRIPTION", True)
    seen: dict = {}

    def fake_ask(model, system, prompt):
        seen.update(model=model, system=system, prompt=prompt)
        return "ok"

    monkeypatch.setattr(claude_sdk, "_ask", fake_ask)
    result = summarizer.Summarizer().summarize("t", "body")
    assert result == ("ok", "claude/claude-opus-5-5")
    assert seen["system"] == summarizer.SYSTEM_PROMPT
    assert "《t》" in seen["prompt"]


def test_claude_effort_defaults_to_high():
    assert fork_config.SUMMARY_EFFORT == "high"


def test_no_ocr_course_ids_parsed(monkeypatch):
    monkeypatch.setenv("NO_OCR_COURSE_IDS", " 38985, 1 ,")
    importlib.reload(fork_config)
    try:
        assert {"38985", "1"} == fork_config.NO_OCR_COURSE_IDS
    finally:
        monkeypatch.delenv("NO_OCR_COURSE_IDS")
        importlib.reload(fork_config)
