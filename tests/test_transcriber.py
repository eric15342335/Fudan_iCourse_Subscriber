from src.ai.transcriber import _postprocess_segment


def test_collapses_decoder_loops_but_keeps_numbers():
    assert _postprocess_segment("前面特别特别特别特别特别特别") == "前面特别"
    assert _postprocess_segment("一个一个 WRITER 往往 1000") == "一个一个 WRITER 往往 1000"


def test_provider_defaults_to_config_and_can_be_overridden(monkeypatch):
    from src.ai.transcriber import Transcriber
    from src.runtime import config

    monkeypatch.setattr(config, "ASR_PROVIDER", "cpu")
    assert Transcriber()._provider == "cpu"
    assert Transcriber(provider="CUDA")._provider == "cuda"
