"""Fork-only ASR text clean-up (no heavy imports, so ``transcriber`` can use it)."""

import re

# Decoder loops / stutters: a CJK run of 1-8 chars repeated 3+ times.
# CJK-only so digits ("1000") and Latin text are never collapsed.
_REPEAT_RE = re.compile(r"([一-鿿]{1,8}?)\1{2,}")


def collapse_repeats(text: str) -> str:
    """Collapse decoder loops such as "特别特别特别特别" to one copy."""
    return _REPEAT_RE.sub(r"\1", text)
