#!/usr/bin/env python3
"""Time the ASR on a decoded ``data/audio/<sub_id>.raw``.

    python -m scripts.bench_asr data/audio/695193.raw --seconds 300 --provider cuda

Prints the real-time factor (wall time / audio time) and writes the transcript
to ``--out`` so two providers can be diffed.  Honours ASR_* env like the pipeline.
"""

from __future__ import annotations

import argparse
import json
import time

from src.ai.asr_extras import ForkTranscriber
from src.ai.transcriber import SAMPLE_RATE

BYTES_PER_SEC = SAMPLE_RATE * 4  # f32le mono


def main() -> None:
    """Command-line entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("--seconds", type=float, default=300)
    ap.add_argument("--skip", type=float, default=0, help="start offset in seconds")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    tr = ForkTranscriber(provider=args.provider, num_threads=args.threads)
    left = int(args.seconds * BYTES_PER_SEC)
    with open(args.raw, "rb") as f:
        f.seek(int(args.skip * SAMPLE_RATE) * 4)

        def read_fn(n: int) -> bytes:
            nonlocal left
            data = f.read(min(n, left))
            left -= len(data)
            return data

        tr.warm_up()  # keep model load and GPU kernel setup out of the timing
        t0 = time.time()
        text, segs = tr.consume_pcm_stream(
            read_fn, lambda: left <= 0, lambda: b"", lambda: 0,
            timeout=7200, label="bench")
        wall = time.time() - t0
    print(f"BENCH {tr.settings} "
          f"audio={args.seconds:.0f}s wall={wall:.1f}s RTF={wall / args.seconds:.3f} "
          f"({args.seconds / wall:.1f}x realtime) segs={len(segs)} chars={len(text)}")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as out:
            out.write(text)
        # Segments keep timestamps (offset by --skip) so two runs can be aligned.
        for s in segs:
            s["start_ms"] += int(args.skip * 1000)
            s["end_ms"] += int(args.skip * 1000)
        with open(args.out + ".json", "w", encoding="utf-8") as out:
            json.dump(segs, out, ensure_ascii=False)


if __name__ == "__main__":
    main()
