#!/usr/bin/env python3
"""Run the lecture pipeline (ASR + PPT OCR, then summary) for chosen lectures only.

    python -m scripts.run_lectures 37744:2026-10-26 40309:2026-10-29 ...
    python -m scripts.run_lectures 37744 40309         # all still-unsummarized lectures
    python -m scripts.run_lectures --no-summary 37744  # stage 1 only (queue for later)

``COURSE_ID:YYYY-MM-DD`` picks one lecture, a bare ``COURSE_ID`` every playback
lecture of that course without a summary.  ``--list`` only prints the picks.
No semester crawl and no email; summaries are also written to ``--out-dir`` as
``<date> <course>.md``.  Stage 2 for queued lectures: ``summarize_pending.py``.
"""

import importlib

from src.ai.asr_extras import ForkTranscriber


def main() -> None:
    """Load the ASR model first, then run the pipeline."""
    transcriber = ForkTranscriber()
    transcriber.load()
    # rapidocr ships its own onnxruntime.dll; if it loads before the sherpa-onnx CUDA
    # build, the CUDA provider fails and ASR silently falls back to CPU.
    importlib.import_module("scripts.lecture_batch").main(transcriber)


if __name__ == "__main__":
    main()
