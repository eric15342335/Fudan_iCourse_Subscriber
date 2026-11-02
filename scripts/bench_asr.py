#!/usr/bin/env python3
"""Time the ASR on the first N seconds of a decoded ``data/audio/<sub_id>.raw``.

    python scripts/bench_asr.py data/audio/695193.raw --seconds 300 --provider cuda

Prints the real-time factor (wall time / audio time) and writes the transcript
to ``--out`` so two providers can be diffed.  Honours ASR_* env like the pipeline.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai.transcriber import SAMPLE_RATE, Transcriber

BYTES_PER_SEC = SAMPLE_RATE * 4  # f32le mono


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("--seconds", type=float, default=300)
    ap.add_argument("--skip", type=float, default=0, help="start offset in seconds")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    tr = Transcriber(provider=args.provider, num_threads=args.threads)
    left = int(args.seconds * BYTES_PER_SEC)
    with open(args.raw, "rb") as f:
        f.seek(int(args.skip * SAMPLE_RATE) * 4)

        def read_fn(n: int) -> bytes:
            nonlocal left
            data = f.read(min(n, left))
            left -= len(data)
            return data

        tr._init()  # keep model load and GPU kernel warm-up out of the timing
        import numpy as np
        warm = tr._recognizer.create_stream()
        warm.accept_waveform(SAMPLE_RATE, (np.random.randn(SAMPLE_RATE * 5) * 0.01).astype("float32"))
        tr._recognizer.decode_stream(warm)
        t0 = time.time()
        text, segs = tr._consume_pcm_stream(
            read_fn, lambda: left <= 0, lambda: b"", lambda: 0, timeout=7200, label="bench")
        wall = time.time() - t0
    print(f"BENCH provider={tr._provider} threads={tr._num_threads} "
          f"audio={args.seconds:.0f}s wall={wall:.1f}s RTF={wall / args.seconds:.3f} "
          f"({args.seconds / wall:.1f}x realtime) segs={len(segs)} chars={len(text)}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)


if __name__ == "__main__":
    main()
