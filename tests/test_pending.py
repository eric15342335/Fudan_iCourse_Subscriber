from src.data.database import Database


def _db(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    db.upsert_course("c1", "Course", "T")
    db.insert_lecture("s1", "c1", "L1", "2026-01-01")
    db.insert_lecture("s2", "c1", "L2", "2026-01-08")
    return db


def test_lecture_is_pending_until_summarized(tmp_path):
    db = _db(tmp_path)
    assert db.get_pending_summaries() == []
    segs = [{"start_ms": 0, "end_ms": 1000, "text": "hi"}]
    db.update_transcript("s1", "hi", segs)
    assert [p["sub_id"] for p in db.get_pending_summaries()] == ["s1"]
    assert '"text": "hi"' in db.get_lecture("s1")["transcript_segments"]
    db.update_summary("s1", "done", "m")
    assert db.get_pending_summaries() == []


def test_update_transcript_without_segments_keeps_stored_ones(tmp_path):
    db = _db(tmp_path)
    db.update_transcript("s1", "a", [{"start_ms": 0, "end_ms": 1, "text": "a"}])
    db.update_transcript("s1", "b")
    assert db.get_lecture("s1")["transcript_segments"]
