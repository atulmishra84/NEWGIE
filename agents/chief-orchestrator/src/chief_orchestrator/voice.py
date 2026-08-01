"""Text + voice ingress adapters (STT/TTS)."""

from __future__ import annotations

import re
from typing import BinaryIO

from gie_contracts import Channel, IntentType, NormalizedIntent

from chief_orchestrator.config import settings
from chief_orchestrator.voice_providers import synthesize_speech, transcribe_audio

_AMBIGUOUS = re.compile(r"^(uh+|um+|hmm+|maybe|something|whatever)\b", re.I)


async def stt_from_audio(transcript: str | None, audio_bytes: bytes | None = None) -> tuple[str, str]:
    """Normalize voice to text via commercial STT or transcript. Returns (text, provider)."""
    return await transcribe_audio(audio_bytes, transcript)


async def synthesize_tts(text: str) -> tuple[bytes, str]:
    """Return (wav_or_audio_bytes, provider)."""
    return await synthesize_speech(text)


def synthesize_tts_sync_stub(text: str) -> bytes:
    """Sync stub for unit tests that don't need commercial providers."""
    import io
    import struct
    import wave

    sample_rate = 16000
    duration_sec = min(2.0, max(0.3, len(text) / 40.0))
    n_frames = int(sample_rate * duration_sec)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack("<h", 0) * n_frames)
    return buf.getvalue()


def normalize_intent(
    *,
    text: str,
    channel: Channel,
    prod_confirm_phrase: str | None = None,
) -> NormalizedIntent:
    cleaned = " ".join(text.strip().split())
    lower = cleaned.lower()
    phrase = settings.prod_confirm_phrase.lower()

    if not cleaned or _AMBIGUOUS.match(cleaned):
        return NormalizedIntent(
            intent=IntentType.CLARIFY,
            text=cleaned or "(empty)",
            channel=channel,
            confidence=0.2,
            needs_clarification=True,
            clarification_prompt=(
                "I didn't catch a clear command. Please say or type what you want "
                "(status, golden run, change request, or prod approve)."
            ),
        )

    prod_confirmed = False
    if prod_confirm_phrase and prod_confirm_phrase.strip().lower() == phrase:
        prod_confirmed = True
    if phrase in lower and "approve" in lower and "production" in lower:
        prod_confirmed = True

    if "approve production" in lower or lower.strip() == phrase:
        return NormalizedIntent(
            intent=IntentType.PROD_APPROVE,
            text=cleaned,
            channel=channel,
            confidence=0.95,
            prod_confirmed=prod_confirmed,
            needs_clarification=not prod_confirmed,
            clarification_prompt=(
                None
                if prod_confirmed
                else f'Say or type the confirm phrase exactly: "{settings.prod_confirm_phrase}"'
            ),
        )

    if lower in {"status", "health", "fleet status"} or lower.startswith("status"):
        return NormalizedIntent(
            intent=IntentType.STATUS,
            text=cleaned,
            channel=channel,
            confidence=0.99,
        )

    if (
        lower.startswith("add ")
        or "change request" in lower
        or lower.startswith("fix ")
        or " to the golden" in lower
        or "feature x" in lower
    ):
        return NormalizedIntent(
            intent=IntentType.CHANGE_REQUEST,
            text=cleaned,
            channel=channel,
            confidence=0.9,
        )

    if "golden demo" in lower or (
        "build" in lower
        and "security" in lower
        and ("gie" in lower or "deploy" in lower)
    ):
        return NormalizedIntent(
            intent=IntentType.GOLDEN_RUN,
            text=cleaned,
            channel=channel,
            confidence=0.9,
        )

    return NormalizedIntent(
        intent=IntentType.UNKNOWN,
        text=cleaned,
        channel=channel,
        confidence=0.4,
        needs_clarification=True,
        clarification_prompt=(
            "Unrecognized command. Try: status | golden demo run | add a small feature | "
            f'"{settings.prod_confirm_phrase}"'
        ),
    )


def read_upload(file_obj: BinaryIO | None) -> bytes | None:
    if file_obj is None:
        return None
    data = file_obj.read()
    return data or None
