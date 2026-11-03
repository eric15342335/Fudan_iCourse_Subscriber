"""Claude subscription backend for ``Summarizer``, shaped like an OpenAI client.

``Summarizer`` calls ``client.chat.completions.create(...)``; ``_Client`` answers
that through the Claude Agent SDK (``claude login``, no API key).  This module
must not import ``summarizer`` (the system prompt arrives in ``messages``).
"""

from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace

from src.runtime import fork_config

NAME = "claude"


def providers() -> list[dict]:
    """The Claude entry for ``Summarizer.providers`` (empty unless opted in)."""
    if not fork_config.USE_CLAUDE_SUBSCRIPTION:
        return []
    return [{"name": NAME, "models": list(fork_config.CLAUDE_MODELS)}]


def client(provider: dict):
    """A client for the Claude provider, or None for any other provider."""
    return _CLIENT if provider["name"] == NAME else None


def _ask(model: str, system: str, prompt: str) -> str:
    """One-shot, tool-less Claude call through the Agent SDK (subscription auth)."""
    sdk = importlib.import_module("claude_agent_sdk")  # optional dependency

    opts = sdk.ClaudeAgentOptions(
        model=model, system_prompt=system, tools=[], max_turns=1,
        effort=fork_config.SUMMARY_EFFORT,  # type: ignore[arg-type]
        setting_sources=[],  # don't load CLAUDE.md / hooks from cwd
        env={"ANTHROPIC_API_KEY": ""},  # force subscription, not API billing
    )

    async def run() -> str:
        async for msg in sdk.query(prompt=prompt, options=opts):
            if isinstance(msg, sdk.ResultMessage):
                if msg.is_error or not msg.result:
                    raise RuntimeError(f"Claude SDK error: {msg.subtype}: {msg.result}")
                return msg.result
        raise RuntimeError("Claude SDK returned no result")

    return asyncio.run(run())


def _create(model: str, messages: list[dict], **_ignored) -> SimpleNamespace:
    """Stand-in for ``chat.completions.create``; extra kwargs (timeout) are ignored."""
    by_role = {m["role"]: m["content"] for m in messages}
    message = SimpleNamespace(content=_ask(model, by_role["system"], by_role["user"]))
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)


_COMPLETIONS = SimpleNamespace(create=_create)
_CLIENT = SimpleNamespace(chat=SimpleNamespace(completions=_COMPLETIONS))
