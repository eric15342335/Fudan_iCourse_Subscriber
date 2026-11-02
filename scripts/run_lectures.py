#!/usr/bin/env python3
"""Run the full lecture pipeline (ASR + PPT OCR + summary) for chosen lectures only.

    python scripts/run_lectures.py 37744:2026-10-26 40309:2026-10-29 ...

Each ``course_id:date`` picks one lecture.  No semester crawl and no email;
summaries are also written to ``--out-dir`` as ``<date> <course>.md``.
Logs in once (no retry loop: repeated failures trigger a captcha).
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import _check_session
from src.ai.summarizer import Summarizer
from src.ai.transcriber import Transcriber
from src.api.icourse import ICourseClient
from src.api.webvpn import WebVPNSession
from src.data.database import Database
from src.pipeline.lecture_runner import LectureRunner
from src.runtime.reporter import Reporter
from src.runtime.scheduler import Scheduler


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("lectures", nargs="+", metavar="COURSE_ID:YYYY-MM-DD")
    ap.add_argument("--out-dir", default=os.path.join("temp", "summaries"))
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    db, reporter = Database(), Reporter()
    vpn = WebVPNSession()
    vpn.login()
    vpn.authenticate_icourse()
    client = ICourseClient(vpn)

    picks = []
    for spec in args.lectures:
        cid, date = spec.split(":")
        detail = client.get_course_detail(cid)
        lec = next((l for l in detail["lectures"]
                    if l.get("date") == date and l.get("has_playback")), None)
        if lec is None:
            print(f"[SKIP] {spec}: no lecture with playback on that date")
            continue
        db.upsert_course(cid, detail["title"], detail["teacher"])
        db.insert_lecture(str(lec["sub_id"]), cid, lec.get("sub_title", ""), date)
        picks.append((cid, detail["title"], lec))

    scheduler = Scheduler(reporter=reporter)
    runner = LectureRunner(client, db, scheduler, Transcriber(), Summarizer(), reporter)
    try:
        if picks:
            runner.prefetch_first(picks[0][0], str(picks[0][2]["sub_id"]))
        for i, (cid, title, lec) in enumerate(picks):
            nxt = None
            if i + 1 < len(picks):
                nxt = (picks[i + 1][0], str(picks[i + 1][2]["sub_id"]))
            _check_session(client)
            summary = runner.run(cid, title, lec, next_info=nxt)
            if summary:
                path = os.path.join(args.out_dir, f"{lec['date']} {title}.md")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(summary + "\n")
                print(f"[OK] {path}")
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
