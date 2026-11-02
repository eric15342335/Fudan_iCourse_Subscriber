from src.ai.transcriber import _postprocess_segment


def test_collapses_decoder_loops_but_keeps_numbers():
    assert _postprocess_segment("前面特别特别特别特别特别特别") == "前面特别"
    assert _postprocess_segment("一个一个 WRITER 往往 1000") == "一个一个 WRITER 往往 1000"
