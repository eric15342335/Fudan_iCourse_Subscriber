import pytest

from src.ai.asr_extras import ForkTranscriber
from src.ai.asr_text import collapse_repeats
from src.ai.transcriber import _postprocess_segment
from src.runtime import fork_config


def test_collapses_decoder_loops_but_keeps_numbers():
    assert collapse_repeats("前面特别特别特别特别特别特别") == "前面特别"
    assert _postprocess_segment("前面特别特别特别特别特别特别") == "前面特别"
    text = "一个一个 WRITER 往往 1000"
    assert _postprocess_segment(text) == text


def test_provider_defaults_to_config_and_can_be_overridden(monkeypatch):
    monkeypatch.setattr(fork_config, "ASR_PROVIDER", "cpu")
    assert "provider=cpu" in ForkTranscriber().settings
    assert "provider=cuda" in ForkTranscriber(provider="CUDA").settings


def test_unknown_backend_is_rejected():
    with pytest.raises(ValueError, match="Unknown ASR_BACKEND"):
        ForkTranscriber(backend="nope").load()
