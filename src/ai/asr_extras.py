"""Fork-only ASR features on top of ``Transcriber``: CUDA and FireRedASR2 AED.

Must not import OCR code: the ASR model has to load before rapidocr brings its own
``onnxruntime.dll`` (see ``scripts/run_lectures.py``).
"""

from __future__ import annotations

import glob
import os
import site

import numpy as np
import sherpa_onnx

from src.ai.transcriber import SAMPLE_RATE, Transcriber
from src.runtime import fork_config

AED_BACKEND = "firered-aed"
# AED loops ("嗯嗯嗯…") on long chunks; 12 s was clean in testing.
AED_MAX_SPEECH_S = 12.0


def _add_cuda_dll_dirs() -> None:
    """Make the pip-installed ``nvidia-*-cu12`` runtime DLLs findable (Windows)."""
    if not hasattr(os, "add_dll_directory"):
        return
    for root in site.getsitepackages():
        for d in glob.glob(os.path.join(root, "nvidia", "*", "bin")):
            os.add_dll_directory(d)
            os.environ["PATH"] = d + os.pathsep + os.environ["PATH"]


class ForkTranscriber(Transcriber):
    """``Transcriber`` with ``ASR_PROVIDER=cuda`` and ``ASR_BACKEND=firered-aed``."""

    def __init__(self, backend: str | None = None, model_dir: str | None = None,
                 num_threads: int | None = None, provider: str | None = None):
        super().__init__(backend, model_dir, num_threads)
        self._provider = (provider or fork_config.ASR_PROVIDER).lower()
        self._aed = self._backend == AED_BACKEND
        if self._aed:  # upstream's loader table only knows "firered"
            self._backend = "firered"

    def load(self) -> None:
        """Load the model now (instead of on first use)."""
        self._init()

    def warm_up(self) -> None:
        """Decode 5 s of noise so GPU kernel setup doesn't count in benchmarks."""
        self._init()
        rec = self._recognizer
        assert rec is not None
        stream = rec.create_stream()
        noise = np.random.randn(SAMPLE_RATE * 5) * 0.01
        stream.accept_waveform(SAMPLE_RATE, noise.astype("float32"))
        rec.decode_stream(stream)

    def consume_pcm_stream(self, *args, **kwargs):
        """Public entry to ``_consume_pcm_stream`` for benchmarks."""
        return self._consume_pcm_stream(*args, **kwargs)

    @property
    def settings(self) -> str:
        """Provider and thread count, for benchmark output."""
        return f"provider={self._provider} threads={self._num_threads}"

    def _init(self):
        if self._recognizer is not None:
            return
        if self._provider == "cuda":
            _add_cuda_dll_dirs()
        super()._init()
        if self._aed:
            assert self._vad_config is not None
            self._vad_config.silero_vad.max_speech_duration = AED_MAX_SPEECH_S
            self._reset_vad()

    def _init_firered(self):
        if not self._aed:
            return super()._init_firered()
        # FireRedASR2 AED (encoder + decoder): the best reported Mandarin CER of the
        # sherpa-onnx models; the 12 s VAD cap keeps segments well under AED's
        # 60 s hallucination limit.
        enc = self._resolve_first(
            self._model_dir, ["encoder.int8.onnx", "encoder.onnx"])
        dec = self._resolve_first(
            self._model_dir, ["decoder.int8.onnx", "decoder.onnx"])
        tokens_path = os.path.join(self._model_dir, "tokens.txt")
        if not os.path.isfile(tokens_path):
            raise FileNotFoundError(f"tokens.txt missing in {self._model_dir}")
        print(f"[Transcriber] Loading FireRedASR2 AED from {self._model_dir}...")
        return sherpa_onnx.OfflineRecognizer.from_fire_red_asr(
            encoder=enc, decoder=dec, tokens=tokens_path,
            num_threads=self._num_threads, debug=False,
            provider=self._provider,
        )
