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
