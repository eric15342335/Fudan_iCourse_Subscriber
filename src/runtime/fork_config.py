"""Fork-only settings, kept out of ``config.py`` so upstream merges stay clean.

Read these as attributes (``fork_config.X``), not ``from ... import X``, so tests
can patch or reload them.
"""

import os


def _flag(name: str, default: str = "") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes")


USE_CLAUDE_SUBSCRIPTION = _flag("USE_CLAUDE_SUBSCRIPTION")
CLAUDE_MODELS = ["claude-opus-5-5", "claude-sonnet-5-5"]
# Claude reasoning effort for summaries: low / medium / high / xhigh / max.
SUMMARY_EFFORT = os.environ.get("SUMMARY_EFFORT", "high").strip().lower()

# onnxruntime execution provider for ASR: "cpu" (default) or "cuda"
# (needs the sherpa-onnx CUDA wheel, see requirements-cuda.txt).
ASR_PROVIDER = os.environ.get("ASR_PROVIDER", "cpu").strip().lower()
# Set USE_WEBVPN=0 when the network reaches icourse/id.fudan.edu.cn directly.
USE_WEBVPN = os.environ.get("USE_WEBVPN", "1").strip().lower() not in ("0", "false", "no")
# Courses whose slide OCR is unusable: the summary then uses the transcript only.
# Comma-separated course IDs.
NO_OCR_COURSE_IDS = {
    c.strip() for c in os.environ.get("NO_OCR_COURSE_IDS", "").split(",") if c.strip()
}
