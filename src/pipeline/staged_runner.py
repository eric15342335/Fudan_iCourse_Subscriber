"""Fork-only ``LectureRunner``: optional stage-1-only runs and later summaries.

``summarize=False`` stops after ASR + OCR and leaves the lecture queued
(``ForkDatabase.get_pending_summaries``); ``summarize_stored`` then summarizes
it from the stored transcript, segments and OCR pages.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from src.data.fork_db import ForkDatabase
from src.pipeline.lecture_runner import LectureRunner
from src.runtime import fork_config

if TYPE_CHECKING:
    from src.ai.summarizer import Summarizer

NO_OCR_NOTE = (
    "【注意】本课程没有可用的PPT文字，以下只有录音识别文本，"
    "其中的同音字、专有名词和英文术语错误较多，请结合上下文尽力还原。\n\n"
)


class StagedLectureRunner(LectureRunner):
    """``LectureRunner`` that can defer the summary and resume it later."""

    _db: ForkDatabase

    def __init__(self, *args, summarize: bool = True):
        super().__init__(*args)
        self._summarize_enabled = summarize

    def _get_transcript(self, existing, course_id, sub_id):
        transcript, segments = super()._get_transcript(existing, course_id, sub_id)
        if transcript is not None:
            if existing and existing.get("transcript"):
                segments = self._db.get_segments(sub_id)  # cached transcript
            elif segments:
                self._db.set_segments(sub_id, segments)
        return transcript, segments

    def _no_ocr(self, sub_id: str) -> bool:
        lecture = self._db.get_lecture(sub_id) or {}
        return lecture.get("course_id") in fork_config.NO_OCR_COURSE_IDS

    def _summarize(self, sub_id, course_title, transcript, transcript_segments):
        args = (sub_id, course_title, transcript, transcript_segments)
        if not self._summarize_enabled:
            self._reporter.info("    Summary deferred (stage 1 only); queued.")
            return None
        if not self._no_ocr(sub_id):
            return super()._summarize(*args)
        real = self._summarizer
        noted = SimpleNamespace(
            summarize=lambda title, text: real.summarize(title, NO_OCR_NOTE + text)
        )
        self._summarizer = cast("Summarizer", noted)
        try:
            return super()._summarize(*args)
        finally:
            self._summarizer = real

    def summarize_stored(self, sub_id: str, course_title: str):
        """Stage 2: summarize from the stored transcript, segments and OCR pages."""
        lecture = self._db.get_lecture(sub_id) or {}
        summary = self._summarize(
            sub_id, course_title, lecture["transcript"], self._db.get_segments(sub_id)
        )
        if summary is not None:
            self._db.mark_processed(sub_id)
            self._db.clear_error(sub_id)
        return summary
