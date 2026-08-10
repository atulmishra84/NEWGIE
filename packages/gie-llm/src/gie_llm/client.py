"""AWS Bedrock LLM client — Claude inference via bedrock-runtime."""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
from typing import Any

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="bedrock-llm")


class BedrockLLMClient:
    """Thin async wrapper around boto3 bedrock-runtime for Claude models."""

    def __init__(
        self,
        *,
        region: str = "us-east-1",
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        max_tokens: int = 1024,
        temperature: float = 0.3,
        aws_access_key_id: str = "",
        aws_secret_access_key: str = "",
        aws_session_token: str = "",
    ) -> None:
        self._region = region
        self._model_id = model_id
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._creds: dict[str, str] = {}
        if aws_access_key_id:
            self._creds["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            self._creds["aws_secret_access_key"] = aws_secret_access_key
        if aws_session_token:
            self._creds["aws_session_token"] = aws_session_token

    @cached_property
    def _boto_client(self) -> Any:
        import boto3  # lazy import so tests can mock easily

        return boto3.client("bedrock-runtime", region_name=self._region, **self._creds)

    def _invoke_sync(self, system: str, user: str) -> str:
        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "messages": [{"role": "user", "content": user}],
        }
        if system:
            body["system"] = system
        response = self._boto_client.invoke_model(
            modelId=self._model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        return str(result["content"][0]["text"]).strip()

    async def invoke(self, *, system: str = "", user: str) -> str:
        """Invoke the model and return the text response."""
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                _EXECUTOR, self._invoke_sync, system, user
            )
        except Exception as exc:
            logger.warning("Bedrock LLM invoke failed: %s", exc)
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
        user_parts.append(
            json.dumps(deterministic_output, default=str, indent=2)[:6000]
        )
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
            # Extract JSON from the response (model may wrap in markdown)
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
