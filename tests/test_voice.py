"""Voice review-gate behavior. Provider responses here are synthetic, not live STT."""
from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from nyaya.gemini import TranscriptResult
from nyaya.voice import VoiceDraft, confirm_transcript, recording_id, stage_transcript

ROOT = Path(__file__).resolve().parents[1]
NO_NETWORK_CONFIG = {"NYAYA_PROVIDER": "demo", "GEMINI_API_KEY": "", "NYAYA_API_KEY": ""}


class VoiceGateTests(unittest.TestCase):
    def test_failed_or_empty_transcription_cannot_enter_review(self):
        results = [
            TranscriptResult(text="", status="No speech detected", ok=False),
            TranscriptResult(text="untrusted partial text", status="Provider failed", ok=False),
            TranscriptResult(text="   ", status="Empty", ok=True),
        ]
        for result in results:
            with self.subTest(result=result):
                with self.assertRaises(ValueError):
                    stage_transcript(result, "recording-a")

    def test_confirmation_keeps_the_users_hindi_correction(self):
        draft = VoiceDraft("recording-a", "मेरी जमा राशि 12000 रुपये है।", "Hindi")
        edited = "  मेरी जमा राशि 14000 रुपये है। मेरे पास रसीद है।  "
        self.assertEqual(confirm_transcript(draft, edited, "recording-a"), edited.strip())
        self.assertEqual(draft.text, "मेरी जमा राशि 12000 रुपये है।")

    def test_changed_recording_cannot_send_a_previous_transcript(self):
        first_id = recording_id(b"synthetic-first-recording")
        second_id = recording_id(b"synthetic-replacement-recording")
        draft = VoiceDraft(first_id, "My deposit is unpaid.", "English")
        with self.assertRaisesRegex(ValueError, "recording changed"):
            confirm_transcript(draft, draft.text, second_id)

    def test_empty_and_inaudible_review_cannot_be_sent(self):
        draft = VoiceDraft("recording-a", "Original transcript", "English")
        for reviewed in ("", "  ", "[inaudible]", "[unclear]", "[INAUDIBLE]"):
            with self.subTest(reviewed=reviewed):
                with self.assertRaises(ValueError):
                    confirm_transcript(draft, reviewed)

    def test_oversized_text_is_rejected_before_case_processing(self):
        too_long = "x" * 12001
        with self.assertRaises(ValueError):
            stage_transcript(TranscriptResult(text=too_long, language="English", ok=True), "recording-a")
        with self.assertRaises(ValueError):
            confirm_transcript(VoiceDraft("recording-a", "Short", "English"), too_long)


class VoiceReviewUITests(unittest.TestCase):
    def stage_app(self):
        app = AppTest.from_file(str(ROOT / "detailed_app.py"), default_timeout=30)
        app.session_state["voice_review"] = VoiceDraft(
            "synthetic-recording", "मेरी जमा राशि 12000 रुपये है।", "Hindi"
        )
        app.session_state["voice_revision"] = 1
        app.run()
        self.assertFalse(app.exception)
        return app

    def click(self, app, label):
        next(button for button in app.button if button.label == label).click().run()
        self.assertFalse(app.exception)

    def test_review_does_not_update_case_until_explicit_confirmation(self):
        with patch.dict(os.environ, NO_NETWORK_CONFIG):
            app = self.stage_app()
            self.assertEqual(app.session_state.case.messages, [])
            edited = "मेरे मकान मालिक ने 14000 रुपये की जमा राशि वापस नहीं की है। मेरे पास रसीद है।"
            next(area for area in app.text_area if area.label == "Review your transcript").set_value(edited)
            self.assertEqual(app.session_state.case.messages, [])
            self.click(app, "Use this transcript")
            user_messages = [message["content"] for message in app.session_state.case.messages if message["role"] == "user"]
            self.assertEqual(user_messages, [edited])
            self.assertNotIn("voice_review", app.session_state)

    def test_discard_and_clear_do_not_submit_pending_audio_text(self):
        with patch.dict(os.environ, NO_NETWORK_CONFIG):
            app = self.stage_app()
            self.click(app, "Discard transcript")
            self.assertEqual(app.session_state.case.messages, [])
            self.assertNotIn("voice_review", app.session_state)
            # Start a distinct session so this checks Clear itself rather than
            # AppTest's stale widget tree after a discarded textarea vanishes.
            app = self.stage_app()
            self.click(app, "Clear case")
            self.assertEqual(app.session_state.case.messages, [])
            self.assertNotIn("voice_review", app.session_state)


if __name__ == "__main__":
    unittest.main()
