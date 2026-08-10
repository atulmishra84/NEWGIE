"""AWS voice services: Amazon Transcribe (STT) and Amazon Polly (TTS)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
from typing import Any

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bedrock-voice")


class AWSVoiceClient:
    """STT via Amazon Transcribe (batch + S3) and TTS via Amazon Polly."""

    def __init__(
        self,
        *,
        region: str = "us-east-1",
        polly_voice_id: str = "Joanna",
        polly_engine: str = "neural",
        transcribe_bucket: str = "",
        aws_access_key_id: str = "",
        aws_secret_access_key: str = "",
        aws_session_token: str = "",
    ) -> None:
        self._region = region
        self._polly_voice_id = polly_voice_id
        self._polly_engine = polly_engine
        self._transcribe_bucket = transcribe_bucket
        self._creds: dict[str, str] = {}
        if aws_access_key_id:
            self._creds["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            self._creds["aws_secret_access_key"] = aws_secret_access_key
        if aws_session_token:
            self._creds["aws_session_token"] = aws_session_token

    @cached_property
    def _polly(self) -> Any:
        import boto3

        return boto3.client("polly", region_name=self._region, **self._creds)

    @cached_property
    def _transcribe(self) -> Any:
        import boto3

        return boto3.client("transcribe", region_name=self._region, **self._creds)

    @cached_property
    def _s3(self) -> Any:
        import boto3

        return boto3.client("s3", region_name=self._region, **self._creds)

    # ------------------------------------------------------------------ TTS

    def _polly_tts_sync(self, text: str) -> bytes:
        resp = self._polly.synthesize_speech(
            Text=text[:3000],
            OutputFormat="mp3",
            VoiceId=self._polly_voice_id,
            Engine=self._polly_engine,
        )
        return resp["AudioStream"].read()

    async def synthesize(self, text: str) -> bytes:
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(_EXECUTOR, self._polly_tts_sync, text)
        except Exception as exc:
            logger.warning("Polly TTS failed: %s", exc)
            return b""

    # ------------------------------------------------------------------ STT

    def _transcribe_sync(self, audio_bytes: bytes, job_name: str) -> str:
        """Upload audio to S3, start Transcribe job, poll, return transcript."""
        if not self._transcribe_bucket:
            raise RuntimeError("aws_transcribe_bucket not configured")
        key = f"gie-voice/{job_name}.wav"
        self._s3.put_object(Bucket=self._transcribe_bucket, Key=key, Body=audio_bytes)
        s3_uri = f"s3://{self._transcribe_bucket}/{key}"
        self._transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": s3_uri},
            MediaFormat="wav",
            LanguageCode="en-US",
        )
        # Poll (max 60 s for short utterances)
        for _ in range(30):
            time.sleep(2)
            status = self._transcribe.get_transcription_job(
                TranscriptionJobName=job_name
            )
            state = status["TranscriptionJob"]["TranscriptionJobStatus"]
            if state == "COMPLETED":
                uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                import urllib.request

                with urllib.request.urlopen(uri) as r:  # noqa: S310
                    payload = json.loads(r.read())
                return payload["results"]["transcripts"][0]["transcript"].strip()
            if state == "FAILED":
                raise RuntimeError("Transcribe job failed")
        raise TimeoutError("Transcribe job timed out")

    async def transcribe(self, audio_bytes: bytes) -> str:
        job_name = f"gie-{uuid.uuid4().hex[:12]}"
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                _EXECUTOR, self._transcribe_sync, audio_bytes, job_name
            )
        except Exception as exc:
            logger.warning("Transcribe STT failed: %s", exc)
            return ""
