"""Pipeline driver for ``run_lectures.py`` (imported once the ASR model is loaded)."""

from __future__ import annotations

import argparse
import os
import time
import traceback

import requests

from main import _check_session
from src.ai.summarizer import Summarizer
from src.ai.transcriber import Transcriber
from src.api.icourse import ICourseClient
from src.api.webvpn import WebVPNSession
from src.data.database import Database
from src.pipeline.lecture_runner import LectureRunner
from src.runtime.reporter import Reporter
from src.runtime.scheduler import Scheduler


def login() -> ICourseClient:
    """Log in to iCourse, retrying transient network errors."""
    for attempt in range(5):
        try:
            vpn = WebVPNSession()
            vpn.login()
            vpn.authenticate_icourse()
            return ICourseClient(vpn)
        except (requests.RequestException, RuntimeError) as e:
            # Retry network blips and a cold WebVPN session only; real auth
            # failures ("Authentication failed (code=...)") raise at once.
            transient = isinstance(e, requests.RequestException) or "cold" in str(e)
            if not transient or attempt == 4:
                raise
            print(f"  Transient login error ({type(e).__name__}); retrying...")
            time.sleep(10)
    raise RuntimeError("unreachable")


def pick_lectures(client: ICourseClient, db: Database, specs: list[str]) -> list:
    """Resolve ``COURSE_ID[:DATE]`` specs to playback lectures and register them."""
    picks, seen = [], set()
    for spec in specs:
        cid, _, date = spec.partition(":")
        detail = client.get_course_detail(cid)
        found = [
            lec for lec in detail["lectures"]
            if lec.get("has_playback") and (
                lec.get("date") == date if date else not _has_summary(db, lec)
            )
        ]
        if not found:
            print(f"[SKIP] {spec}: no matching lecture with playback")
        for lec in sorted(found, key=lambda x: x.get("date", "")):
            if lec["sub_id"] in seen:
                continue
            seen.add(lec["sub_id"])
            db.upsert_course(cid, detail["title"], detail["teacher"])
            db.insert_lecture(
                str(lec["sub_id"]), cid, lec.get("sub_title", ""), lec.get("date", ""))
            picks.append((cid, detail["title"], lec))
    return picks


def _has_summary(db: Database, lec: dict) -> bool:
    """True if the lecture already has a summary in the DB."""
    row = db.get_lecture(str(lec["sub_id"]))
    return bool(row and row.get("summary"))


def run_picks(runner: LectureRunner, client: ICourseClient, picks: list,
              out_dir: str) -> None:
    """Run each pick, writing any new summary to ``out_dir``."""
    for i, (cid, title, lec) in enumerate(picks):
        nxt = None
        if i + 1 < len(picks):
            nxt = (picks[i + 1][0], str(picks[i + 1][2]["sub_id"]))
        _check_session(client)
        try:
            summary = runner.run(cid, title, lec, next_info=nxt)
        except (RuntimeError, OSError):
            traceback.print_exc()  # the runner already recorded the error
            continue
        if summary:
            path = os.path.join(out_dir, f"{lec['date']} {title}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(summary + "\n")
            print(f"[OK] {path}")


def main(transcriber: Transcriber) -> None:
    """Parse arguments and run (or list) the picks."""
    ap = argparse.ArgumentParser()
    ap.add_argument("lectures", nargs="+", metavar="COURSE_ID[:YYYY-MM-DD]")
    ap.add_argument("--out-dir", default=os.path.join("temp", "summaries"))
    ap.add_argument("--no-summary", action="store_true",
                    help="stage 1 only: ASR + OCR, queue the summary for later")
    ap.add_argument("--list", action="store_true", help="print the picks and exit")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    db, reporter = Database(), Reporter()
    client = login()
    picks = pick_lectures(client, db, args.lectures)
    if args.list:
        for cid, title, lec in picks:
            print(f"{cid}:{lec['date']}  {title}  sub_id={lec['sub_id']}")
        return

    scheduler = Scheduler(reporter=reporter)
    runner = LectureRunner(client, db, scheduler, transcriber, Summarizer(), reporter,
                           summarize=not args.no_summary)
    try:
        if picks:
            runner.prefetch_first(picks[0][0], str(picks[0][2]["sub_id"]))
        run_picks(runner, client, picks, args.out_dir)
    finally:
        scheduler.shutdown()
