"""Commercial STT/TTS providers with stub fallback."""

from __future__ import annotations

import io
import logging
import struct
import wave

import httpx

from chief_orchestrator.config import settings

logger = logging.getLogger(__name__)


def _stub_wav(text: str) -> bytes:
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


async def transcribe_audio(audio_bytes: bytes | None, transcript: str | None) -> tuple[str, str]:
    """Return (text, provider_used). Prefers explicit transcript, else commercial STT."""
    if transcript and transcript.strip():
        return transcript.strip(), "transcript"

    if not audio_bytes:
        return "", "none"

    provider = (settings.stt_provider or "stub").lower()
    if provider == "openai" and settings.openai_api_key:
        try:
            text = await _openai_stt(audio_bytes)
            if text:
                return text, "openai"
        except Exception as exc:  # noqa: BLE001
            logger.warning("openai STT failed: %s", exc)
    if provider == "deepgram" and settings.deepgram_api_key:
        try:
            text = await _deepgram_stt(audio_bytes)
            if text:
                return text, "deepgram"
        except Exception as exc:  # noqa: BLE001
            logger.warning("deepgram STT failed: %s", exc)

    return "", "stub"


async def synthesize_speech(text: str) -> tuple[bytes, str]:
    """Return (audio_bytes, provider_used)."""
    provider = (settings.tts_provider or "stub").lower()
    if provider == "openai" and settings.openai_api_key:
        try:
            audio = await _openai_tts(text)
            if audio:
                return audio, "openai"
        except Exception as exc:  # noqa: BLE001
            logger.warning("openai TTS failed: %s", exc)
    if provider == "deepgram" and settings.deepgram_api_key:
        try:
            audio = await _deepgram_tts(text)
            if audio:
                return audio, "deepgram"
        except Exception as exc:  # noqa: BLE001
            logger.warning("deepgram TTS failed: %s", exc)
    return _stub_wav(text), "stub"


async def _openai_stt(audio_bytes: bytes) -> str:
    url = f"{settings.openai_base_url.rstrip('/')}/audio/transcriptions"
    files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
    data = {"model": "whisper-1"}
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, data=data, files=files)
        resp.raise_for_status()
        payload = resp.json()
    return str(payload.get("text") or "").strip()


async def _openai_tts(text: str) -> bytes:
    url = f"{settings.openai_base_url.rstrip('/')}/audio/speech"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "content-type": "application/json",
    }
    body = {"model": "gpt-4o-mini-tts", "voice": "alloy", "input": text[:4000]}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        return resp.content


async def _deepgram_stt(audio_bytes: bytes) -> str:
    url = f"{settings.deepgram_base_url.rstrip('/')}/listen?model=nova-2"
    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "content-type": "audio/wav",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, content=audio_bytes)
        resp.raise_for_status()
        payload = resp.json()
    try:
        return (
            payload["results"]["channels"][0]["alternatives"][0]["transcript"]
        ).strip()
    except (KeyError, IndexError, TypeError):
        return ""


async def _deepgram_tts(text: str) -> bytes:
    url = f"{settings.deepgram_base_url.rstrip('/')}/speak?model=aura-asteria-en"
    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json={"text": text[:4000]})
        resp.raise_for_status()
        return resp.content
