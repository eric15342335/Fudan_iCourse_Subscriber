# Fork notes

This fork (eric15342335) tracks `origin` (LeafCreeper). Keep edits to upstream files
small so `git merge origin/main` stays easy; put new code in new files.

## Sync

```bash
git config rerere.enabled true
git config merge.conflictstyle zdiff3
git fetch origin && git merge origin/main
python -m pytest tests
```

## Edits to upstream files

| File | Change |
|------|--------|
| `src/ai/transcriber.py` | `provider` argument, `firered-aed` backend, CUDA DLL setup, 12 s VAD cap, repeat collapse |
| `src/ai/summarizer.py` | `claude-sdk` provider (`_call_claude`), `SUMMARY_EFFORT` |
| `src/runtime/config.py` | `ASR_PROVIDER`, `SUMMARY_EFFORT`, `NO_OCR_COURSE_IDS`, `USE_WEBVPN`, Claude provider entry |
| `src/api/webvpn.py`, `src/api/icourse.py` | `USE_WEBVPN=0` direct mode |
| `src/pipeline/lecture_runner.py` | `summarize=False` (stage 1 only), `summarize_stored`, `NO_OCR_COURSE_IDS` prompt |
| `src/data/schema.py`, `src/data/database.py` | `lectures.transcript_segments`, `get_pending_summaries` |
| `.gitignore`, `README.md`, `requirements-*.txt` | fork settings and docs |

## Fork-only files

`scripts/{run_lectures,lecture_batch,summarize_pending,summarize_local,export_slides,bench_asr}.py`,
`requirements-cuda.txt`, `tests/`, this file.
