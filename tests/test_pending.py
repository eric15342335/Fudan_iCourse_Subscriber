import inspect
from types import SimpleNamespace

from src.ai.transcriber import Transcriber
from src.data.database import Database
from src.data.fork_db import ForkDatabase
from src.pipeline.lecture_runner import LectureRunner
from src.pipeline.staged_runner import NO_OCR_NOTE, StagedLectureRunner
from src.runtime import fork_config

SEGS = [{"start_ms": 0, "end_ms": 1000, "text": "hi"}]


def _db(tmp_path):
    db = ForkDatabase(str(tmp_path / "t.db"))
    db.upsert_course("c1", "Course", "T")
    db.insert_lecture("s1", "c1", "L1", "2026-01-01")
    db.insert_lecture("s2", "c1", "L2", "2026-01-08")
    return db


def _runner(db, summarizer=None):
    reporter = SimpleNamespace(info=lambda *a: None)
    return StagedLectureRunner(None, db, None, None, summarizer, reporter)


def test_lecture_is_pending_until_summarized(tmp_path):
    db = _db(tmp_path)
    assert db.get_pending_summaries() == []
    db.update_transcript("s1", "hi")
    db.set_segments("s1", SEGS)
    assert [p["sub_id"] for p in db.get_pending_summaries()] == ["s1"]
    assert db.get_segments("s1") == SEGS
    db.update_summary("s1", "done", "m")
    assert db.get_pending_summaries() == []


def test_new_transcript_drops_stale_segments(tmp_path):
    db = _db(tmp_path)
    db.update_transcript("s1", "a")
    db.set_segments("s1", SEGS)
    db.update_transcript("s1", "b")
    assert db.get_segments("s1") is None


def test_blank_transcript_is_not_pending(tmp_path):
    db = _db(tmp_path)
    db.update_transcript("s1", "  \n")
    assert db.get_pending_summaries() == []


def test_segments_move_out_of_the_old_column(tmp_path):
    db = _db(tmp_path)
    db.conn.execute("ALTER TABLE lectures ADD COLUMN transcript_segments TEXT")
    db.conn.execute(
        "UPDATE lectures SET transcript_segments = '[1]' WHERE sub_id = 's1'")
    db.conn.commit()
    path = db.db_path
    db.conn.close()
    assert ForkDatabase(path).get_segments("s1") == [1]


def test_summarize_stored_marks_the_lecture_done(tmp_path):
    db = _db(tmp_path)
    db.update_transcript("s1", "hi")
    db.set_segments("s1", SEGS)
    seen: dict = {}

    def summarize(title, content):
        seen.update(title=title, content=content)
        return "SUMMARY", "m"

    runner = _runner(db, SimpleNamespace(summarize=summarize))
    assert runner.summarize_stored("s1", "Course") == "SUMMARY"
    assert "hi" in seen["content"] and seen["title"] == "Course"
    lecture = db.get_lecture("s1")
    assert lecture["summary"] == "SUMMARY" and lecture["processed_at"]
    assert db.get_pending_summaries() == []


def test_deferred_runner_leaves_lecture_queued(tmp_path):
    db = _db(tmp_path)
    db.update_transcript("s1", "hi")
    reporter = SimpleNamespace(info=lambda *a: None)
    runner = StagedLectureRunner(None, db, None, None, None, reporter, summarize=False)
    assert runner.summarize_stored("s1", "Course") is None
    assert [p["sub_id"] for p in db.get_pending_summaries()] == ["s1"]
    assert db.get_lecture("s1")["processed_at"] is None


def test_no_ocr_course_gets_the_note_and_no_slides(tmp_path, monkeypatch):
    monkeypatch.setattr(fork_config, "NO_OCR_COURSE_IDS", {"c1"})
    db = _db(tmp_path)
    db.update_transcript("s1", "hi")
    page = {"page_num": 1, "created_sec": 1, "pptimgurl": "u"}
    db.insert_ppt_pages_pending("s1", [page])
    db.update_ppt_page("s1", 1, "SLIDE TEXT", "done")
    seen: dict = {}

    def summarize(_title, content):
        seen["content"] = content
        return "S", "m"

    _runner(db, SimpleNamespace(summarize=summarize)).summarize_stored("s1", "Course")
    assert seen["content"].startswith(NO_OCR_NOTE)
    assert "SLIDE TEXT" not in seen["content"]


def _params(func):
    return list(inspect.signature(func).parameters)


def test_upstream_hooks_still_exist():
    """A merge can rename methods the fork overrides without any git conflict."""
    assert _params(LectureRunner._summarize) == [
        "self", "sub_id", "course_title", "transcript", "transcript_segments"]
    assert _params(LectureRunner._get_transcript) == [
        "self", "existing", "course_id", "sub_id"]
    assert _params(Database.update_transcript) == ["self", "sub_id", "transcript"]
    assert _params(Database.get_done_ppt_pages) == ["self", "sub_id"]
    assert _params(Transcriber._init) == ["self"]
    assert _params(Transcriber._init_firered) == ["self"]
