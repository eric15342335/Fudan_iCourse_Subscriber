#!/usr/bin/env python3
"""Stage 2: summarize lectures whose ASR + OCR are already stored in the DB.

    python -m scripts.summarize_pending --status           # show the queue
    python -m scripts.summarize_pending [--limit N]        # summarize the queue

Needs no iCourse login and no ASR model.  Stops after two failures in a row (usually
the Claude usage limit); lectures not summarized stay queued for the next run.
"""

from __future__ import annotations

import argparse
import os

from src.ai.summarizer import Summarizer
from src.data.fork_db import ForkDatabase
from src.pipeline.staged_runner import StagedLectureRunner
from src.runtime.reporter import Reporter


def main() -> None:
    """Command-line entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join("temp", "summaries"))
    ap.add_argument("--limit", type=int, default=0, help="at most N lectures")
    ap.add_argument("--status", action="store_true", help="list the queue and exit")
    args = ap.parse_args()

    db = ForkDatabase()
    pending = db.get_pending_summaries()
    if args.limit:
        pending = pending[:args.limit]
    for lec in pending:
        print(f"{lec['course_id']}:{lec['date']}  {lec['course_title']}  "
              f"sub_id={lec['sub_id']}")
    print(f"{len(pending)} lecture(s) waiting for a summary")
    if args.status or not pending:
        return

    os.makedirs(args.out_dir, exist_ok=True)
    # No client/scheduler/transcriber needed: summarize_stored only uses the DB.
    runner = StagedLectureRunner(None, db, None, None, Summarizer(), Reporter())  # type: ignore[arg-type]
    failures = 0
    for lec in pending:
        try:
            summary = runner.summarize_stored(lec["sub_id"], lec["course_title"])
        except RuntimeError as e:
            failures += 1
            print(f"[FAIL] {lec['date']} {lec['course_title']}: {e}")
            if failures >= 2:  # two in a row usually means the usage limit
                print("[STOP] leaving the rest queued")
                return
            continue
        failures = 0
        name = f"{lec['date']} {lec['course_title']}.md"
        path = os.path.join(args.out_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write((summary or "") + "\n")
        print(f"[OK] {path}")


if __name__ == "__main__":
    main()
