"""Anthropic API LLM client — Claude inference via anthropic SDK."""

from __future__ import annotations

import json
import logging
from functools import cached_property
from typing import Any

logger = logging.getLogger(__name__)


class AnthropicLLMClient:
    """Async wrapper around the Anthropic SDK for Claude models."""

    def __init__(
        self,
        *,
        api_key: str = "",
        model_id: str = "claude-opus-5",
        max_tokens: int = 2048,
    ) -> None:
        self._api_key = api_key
        self._model_id = model_id
        self._max_tokens = max_tokens

    @cached_property
    def _client(self) -> Any:
        import anthropic  # lazy import so tests can mock easily

        return anthropic.AsyncAnthropic(api_key=self._api_key or None)

    async def invoke(self, *, system: str = "", user: str) -> str:
        """Invoke Claude and return the text response."""
        kwargs: dict[str, Any] = {
            "model": self._model_id,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": user}],
            "thinking": {"type": "adaptive"},
        }
        if system:
            kwargs["system"] = system
        try:
            async with self._client.messages.stream(**kwargs) as stream:
                message = await stream.get_final_message()
            for block in message.content:
                if block.type == "text":
                    return block.text.strip()
            return ""
        except Exception as exc:
            logger.warning("Anthropic LLM invoke failed: %s", exc)
            return ""

    async def enhance(
        self,
        *,
        agent_name: str,
        deterministic_output: dict[str, Any],
        context_summary: str = "",
        max_tokens: int | None = None,
    ) -> dict[str, str]:
        """Standard enhancement call — returns {narrative, key_insights, recommendations}."""
        if max_tokens:
            self._max_tokens = max_tokens

        system = (
            f"You are the {agent_name} agent in the GIE (Guardrails Intelligence Engine) platform. "
            "You receive deterministic analysis output and enrich it with expert narrative, "
            "actionable insights, and clear recommendations. Be concise and structured."
        )
        user_parts = ["## Deterministic Analysis Output\n```json"]
        user_parts.append(json.dumps(deterministic_output, default=str, indent=2)[:6000])
        user_parts.append("```")
        if context_summary:
            user_parts.append(f"\n## Additional Context\n{context_summary[:1000]}")
        user_parts.append(
            "\n## Task\nProvide a JSON response with exactly these keys:\n"
            '{"narrative": "<2-3 sentence expert summary>", '
            '"key_insights": ["<insight 1>", "<insight 2>", "<insight 3>"], '
            '"recommendations": ["<action 1>", "<action 2>", "<action 3>"]}'
        )
        raw = await self.invoke(system=system, user="\n".join(user_parts))
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(raw[start:end])
                return {
                    "narrative": str(parsed.get("narrative", "")),
                    "key_insights": [str(x) for x in parsed.get("key_insights", [])],
                    "recommendations": [
                        str(x) for x in parsed.get("recommendations", [])
                    ],
                }
        except Exception:
            pass
        return {
            "narrative": raw[:500] if raw else "",
            "key_insights": [],
            "recommendations": [],
        }
