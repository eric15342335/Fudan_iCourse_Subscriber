#!/usr/bin/env python3
"""Export a lecture's de-duplicated slide screenshots as one PDF.

    python scripts/export_slides.py SUB_ID [SUB_ID ...] [--out-dir temp/slides]

Reads the page list from the local DB (read-only), re-downloads the images from
iCourse and writes ``<date> <course>.pdf``.  These are the platform's screen
captures, not the original slide files.
"""
# pylint: disable=wrong-import-position

from __future__ import annotations

import argparse
import io
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

from src.api.icourse import ICourseClient, fetch_ppt_image
from src.api.webvpn import WebVPNSession
from src.runtime import config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sub_ids", nargs="+")
    ap.add_argument("--out-dir", default=os.path.join("temp", "slides"))
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    db = sqlite3.connect(f"file:{config.DB_PATH}?mode=ro", uri=True)
    vpn = WebVPNSession()
    vpn.login()
    vpn.authenticate_icourse()
    client = ICourseClient(vpn)

    for sub_id in args.sub_ids:
        title, date, course = db.execute(
            "SELECT l.sub_title, l.date, c.title FROM lectures l "
            "JOIN courses c ON c.course_id = l.course_id WHERE l.sub_id = ?",
            (sub_id,),
        ).fetchone()
        urls = [r[0] for r in db.execute(
            "SELECT pptimgurl FROM ppt_pages WHERE sub_id = ? AND ocr_status = 'done' "
            "ORDER BY created_sec", (sub_id,))]
        with ThreadPoolExecutor(8) as pool:
            blobs = list(pool.map(
                lambda u: fetch_ppt_image(client, {"pptimgurl": u}), urls))
        pages = [Image.open(io.BytesIO(b)).convert("RGB") for b in blobs if b]
        if not pages:
            print(f"[SKIP] {sub_id}: no pages downloaded")
            continue
        path = os.path.join(args.out_dir, f"{date or title} {course}.pdf")
        pages[0].save(path, "PDF", save_all=True, append_images=pages[1:])
        print(f"[OK] {path}: {len(pages)}/{len(urls)} pages, "
              f"{os.path.getsize(path) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
