"""Fork-only database additions, kept out of ``database.py`` and ``schema.py``.

Timestamped transcript segments live in their own table so the shared
``lectures`` schema (mirrored by the frontend and merged by ``merge_db.py``)
stays untouched.
"""

from __future__ import annotations

import json

from src.data.database import Database
from src.runtime import fork_config

_SEGMENTS_SQL = """
CREATE TABLE IF NOT EXISTS transcript_segments (
    sub_id TEXT PRIMARY KEY,
    segments TEXT NOT NULL
);
"""


class ForkDatabase(Database):
    """``Database`` plus stored ASR segments and the stage-2 summary queue."""

    def __init__(self, db_path: str | None = None):
        super().__init__(db_path)
        with self._lock, self.conn:
            self.conn.executescript(_SEGMENTS_SQL)
            columns = {r[1] for r in self.conn.execute("PRAGMA table_info(lectures)")}
            if "transcript_segments" in columns:  # earlier fork versions stored it here
                self.conn.execute(
                    "INSERT OR IGNORE INTO transcript_segments "
                    "SELECT sub_id, transcript_segments FROM lectures "
                    "WHERE transcript_segments IS NOT NULL"
                )

    def get_segments(self, sub_id: str) -> list[dict] | None:
        """The stored timestamped segments of a lecture, if any."""
        with self._lock:
            row = self.conn.execute(
                "SELECT segments FROM transcript_segments WHERE sub_id = ?", (sub_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def set_segments(self, sub_id: str, segments: list[dict]) -> None:
        """Store the segments that belong to the lecture's current transcript."""
        with self._lock, self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO transcript_segments VALUES (?, ?)",
                (sub_id, json.dumps(segments, ensure_ascii=False)),
            )

    def update_transcript(self, sub_id: str, transcript: str) -> None:
        """Save a transcript and drop segments that belonged to the old one."""
        super().update_transcript(sub_id, transcript)
        with self._lock, self.conn:
            self.conn.execute(
                "DELETE FROM transcript_segments WHERE sub_id = ?", (sub_id,))

    def get_done_ppt_pages(self, sub_id: str) -> list[dict]:
        """OCR pages for the prompt; none for courses whose slides are unreadable."""
        lecture = self.get_lecture(sub_id)
        if lecture and lecture["course_id"] in fork_config.NO_OCR_COURSE_IDS:
            return []
        return super().get_done_ppt_pages(sub_id)

    def get_pending_summaries(self) -> list[dict]:
        """Lectures whose ASR/OCR stage is done but that have no summary yet."""
        with self._lock:
            rows = self.conn.execute(
                """SELECT l.sub_id, l.course_id, l.sub_title, l.date,
                          c.title AS course_title
                   FROM lectures l
                   JOIN courses c ON l.course_id = c.course_id
                   WHERE TRIM(COALESCE(l.transcript, ''), ' ' || char(9, 10, 13)) != ''
                     AND (l.summary IS NULL OR l.summary = '')
                   ORDER BY l.date, l.sub_id""",
            ).fetchall()
        return [dict(row) for row in rows]
