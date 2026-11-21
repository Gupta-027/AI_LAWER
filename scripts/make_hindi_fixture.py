"""Optional original synthetic Hindi audio fixture; never records a real user.

Uses Gemini TTS solely for speech-input verification. This is not app startup.
Run from the prepared environment: python scripts/make_hindi_fixture.py
"""
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
import wave

from dotenv import load_dotenv
import httpx

ROOT = Path(__file__).resolve().parents[1]
TEXT = "मेरे मकान मालिक ने बारह हज़ार रुपये की जमा राशि वापस नहीं की है। मेरे पास रसीद है।"
MODEL = "gemini-3.1-flash-tts-preview"


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    key = os.getenv("GEMINI_API_KEY", "") or os.getenv("NYAYA_API_KEY", "")
    if not key:
        print("Set GEMINI_API_KEY on the server before generating the synthetic fixture.")
        return 1
    payload = {
        "contents": [{"parts": [{"text": "Read this synthetic test sentence clearly in Hindi, without adding anything: " + TEXT}]}],
        "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {
            "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}}},
    }
    started = time.perf_counter()
    try:
        response = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
                              headers={"x-goog-api-key": key}, json=payload, timeout=50, follow_redirects=False)
        data = response.json()
        if not response.is_success:
            print(json.dumps({"generated": False, "http_status": response.status_code,
                              "google_status": data.get("error", {}).get("status")}))
            return 1
        part = next(p["inlineData"] for p in data["candidates"][0]["content"]["parts"] if "inlineData" in p)
        audio = base64.b64decode(part["data"])
        mime = part["mimeType"]
        match = re.search(r"rate=(\d+)", mime)
        rate = int(match.group(1)) if match else 24000
        path = ROOT / "evaluation" / "audio" / "synthetic_hindi_deposit.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        if audio.startswith(b"RIFF"):
            path.write_bytes(audio)
        else:
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(rate)
                output.writeframes(audio)
        with wave.open(str(path), "rb") as recording:
            duration = recording.getnframes() / recording.getframerate()
        metadata = {"synthetic": True, "original_text": TEXT, "generator": "Google Gemini TTS",
                    "model": MODEL, "voice": "Kore", "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "audio_mime_received": mime, "sample_rate": rate, "duration_seconds": round(duration, 3),
                    "generation_seconds": round(time.perf_counter() - started, 3), "usage": data.get("usageMetadata", {}),
                    "purpose": "Original synthetic Hindi transcription test, not a real person or customer conversation"}
        path.with_suffix(".metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"generated": True, "file": str(path.relative_to(ROOT)), "duration_seconds": round(duration, 3)}))
        return 0
    except (httpx.HTTPError, ValueError, KeyError, IndexError, StopIteration, wave.Error) as error:
        print(json.dumps({"generated": False, "error_type": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
