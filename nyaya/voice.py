"""Review gate between speech transcription and the ordinary case entry point."""
from dataclasses import dataclass
from hashlib import sha256

from .gemini import TranscriptResult


@dataclass(frozen=True)
class VoiceDraft:
    recording_id: str
    text: str
    language: str


def recording_id(audio: bytes) -> str:
    return sha256(audio).hexdigest()


def stage_transcript(result: TranscriptResult, audio_id: str) -> VoiceDraft:
    if not result.ok or not result.text.strip():
        raise ValueError("No usable transcript is available. Record your story again.")
    if len(result.text) > 12000:
        raise ValueError("The transcript is too long. Please record a shorter clip.")
    return VoiceDraft(recording_id=audio_id, text=result.text.strip(), language=result.language)


def confirm_transcript(draft: VoiceDraft, edited_text: str, current_audio_id: str | None = None) -> str:
    """Return only explicitly reviewed text; never mutate a case from an STT result."""
    if current_audio_id is not None and current_audio_id != draft.recording_id:
        raise ValueError("The recording changed. Transcribe the new recording before sending.")
    text = edited_text.strip()
    if not text:
        raise ValueError("Please add or correct the transcript before sending it.")
    if len(text) > 12000:
        raise ValueError("The transcript is too long. Keep it below 12,000 characters.")
    if text.lower() in {"[inaudible]", "[unclear]"}:
        raise ValueError("The speech was unclear. Please record again or type your story.")
    return text
