# Fork notes

This fork (eric15342335) tracks `origin` (LeafCreeper). Fork code lives in fork-only files;
upstream files carry only tiny hooks, so `git merge origin/main` stays easy.

## Sync

```bash
git config rerere.enabled true
git config merge.conflictstyle zdiff3
git fetch origin && git merge origin/main
python -m pytest tests   # includes a guard test for every upstream method the fork overrides
```

## Hooks in upstream files

| File | Hook |
|------|------|
| `src/ai/summarizer.py` | `claude_sdk.providers()` / `claude_sdk.client(p)` (2 lines + import) |
| `src/ai/transcriber.py` | `provider=self._provider` kwargs (3), one attribute, `collapse_repeats` call |
| `src/api/webvpn.py` | early return in `get_vpn_url`, `direct.install(self)` in `__init__` |
| `src/api/icourse.py` | no cookies for the video host in direct mode (1 expression) |
| `.gitignore`, `README.md`, `requirements-*.txt` | fork settings and docs |

`src/runtime/config.py`, `src/data/*` and `src/pipeline/lecture_runner.py` are identical to upstream.

## Fork-only files

- `src/runtime/fork_config.py`: `ASR_PROVIDER`, `SUMMARY_EFFORT`, `NO_OCR_COURSE_IDS`, `USE_WEBVPN`, `USE_CLAUDE_SUBSCRIPTION`
- `src/ai/claude_sdk.py`: Claude subscription backend behind the OpenAI client shape
- `src/ai/asr_extras.py`, `src/ai/asr_text.py`: `ForkTranscriber` (CUDA, `firered-aed`), repeat collapse
- `src/api/direct.py`: `USE_WEBVPN=0` mode
- `src/data/fork_db.py`: `ForkDatabase` (segments table, pending-summary queue)
- `src/pipeline/staged_runner.py`: `StagedLectureRunner` (stage 1 only, `summarize_stored`, no-OCR note)
- `scripts/{run_lectures,lecture_batch,summarize_pending,summarize_local,export_slides,bench_asr}.py`,
  `requirements-cuda.txt`, `tests/`, this file

Upstream's own `main.py` still uses the plain classes, so the fork features apply to the fork scripts only.
