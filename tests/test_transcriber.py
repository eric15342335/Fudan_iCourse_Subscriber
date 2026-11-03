import pytest

from src.ai.transcriber import Transcriber, _postprocess_segment
from src.runtime import config


def test_collapses_decoder_loops_but_keeps_numbers():
    assert _postprocess_segment("前面特别特别特别特别特别特别") == "前面特别"
    text = "一个一个 WRITER 往往 1000"
    assert _postprocess_segment(text) == text


# pylint: disable=protected-access
def test_provider_defaults_to_config_and_can_be_overridden(monkeypatch):
    monkeypatch.setattr(config, "ASR_PROVIDER", "cpu")
    assert Transcriber()._provider == "cpu"
    assert Transcriber(provider="CUDA")._provider == "cuda"


def test_unknown_backend_is_rejected():
    t = Transcriber()
    t._backend = "nope"
    with pytest.raises(ValueError, match="Unknown ASR_BACKEND"):
        t.load()
