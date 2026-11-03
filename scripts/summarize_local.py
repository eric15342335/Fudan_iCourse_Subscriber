#!/usr/bin/env python3
"""Transcribe + summarize local lecture recordings (no iCourse login needed).

    python scripts/summarize_local.py "<video>" [--title T] [--out-dir temp/summaries]

Writes ``<stem>.segments.json`` (ASR cache, reused on re-run so a failed LLM
call doesn't redo hours of ASR) and ``<stem>.md`` (the summary).
"""
# pylint: disable=wrong-import-position

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai import bucketer
from src.ai.summarizer import Summarizer
from src.ai.transcriber import Transcriber


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--title", help="course title for the prompt (default: file name)")
    ap.add_argument("--out-dir", default=os.path.join("temp", "summaries"))
    args = ap.parse_args()

    stem = os.path.splitext(os.path.basename(args.video))[0]
    os.makedirs(args.out_dir, exist_ok=True)
    cache = os.path.join(args.out_dir, f"{stem}.segments.json")

    if os.path.isfile(cache):
        with open(cache, encoding="utf-8") as f:
            segments = json.load(f)
    else:
        _, segments = Transcriber().transcribe_video(args.video)
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False)

    transcript = " ".join(s["text"] for s in segments)
    prompt_text, _ = bucketer.assemble(transcript, segments, [])
    summary, model = Summarizer().summarize(args.title or stem, prompt_text)

    out = os.path.join(args.out_dir, f"{stem}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"<!-- model: {model} -->\n\n{summary}\n")
    print(f"[OK] {out} ({len(summary)} chars, {model})")


if __name__ == "__main__":
    main()
