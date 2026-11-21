"""Native Gemini transport and transcription behavior; responses are mocked."""
from __future__ import annotations

from io import BytesIO
import json
import os
import unittest
from unittest.mock import patch
import wave

import httpx

from nyaya.gemini import DEFAULT_MODEL, GeminiClient, GeminiError, MAX_AUDIO_BYTES
from nyaya.llm import LLMAdapter

TEST_KEY = "synthetic-gemini-test-secret"
ENV = {"NYAYA_PROVIDER": "gemini", "GEMINI_API_KEY": TEST_KEY,
       "GEMINI_MODEL": DEFAULT_MODEL, "NYAYA_API_KEY": "", "NYAYA_MODEL": ""}
STORY = "My rental deposit was Rs 12000. I have a receipt."
MESSAGES = [{"role": "user", "content": STORY}]


def completion(data, *, finish="STOP"):
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": finish}],
        "usageMetadata": {"promptTokenCount": 21, "candidatesTokenCount": 9},
    })


def wav(seconds=0.05, *, silent=False):
    buffer = BytesIO()
    with wave.open(buffer, "wb") as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(16000)
        recording.writeframes((b"\0\0" if silent else b"\x01\0") * int(seconds * 16000))
    return buffer.getvalue()


def extraction(**overrides):
    data = {"kind": "rental", "goal": "", "facts": {"deposit": "Rs 12000"},
            "evidence": ["receipt"], "allegations": [], "notice_quotes": []}
    data.update(overrides)
    return data


class GeminiTests(unittest.TestCase):
    def test_native_request_uses_header_auth_schema_and_instance_configuration(self):
        with patch.dict(os.environ, ENV), patch("nyaya.gemini.httpx.Client") as transport:
            post = transport.return_value.__enter__.return_value.post
            post.return_value = completion({"answer": "ok"})
            client = GeminiClient()
            result = client.generate_json("Return the requested object.", "A synthetic input.",
                                          schema={"type": "object"})
            self.assertEqual(result, {"answer": "ok"})
            url, = post.call_args.args
            request = post.call_args.kwargs
            self.assertEqual(url, f"https://generativelanguage.googleapis.com/v1beta/models/{DEFAULT_MODEL}:generateContent")
            self.assertNotIn(TEST_KEY, url)
            self.assertEqual(request["headers"]["x-goog-api-key"], TEST_KEY)
            self.assertNotIn(TEST_KEY, json.dumps(request["json"]))
            self.assertIn("responseJsonSchema", request["json"]["generationConfig"])
            self.assertEqual(client.last_usage["promptTokenCount"], 21)

    def test_explicit_gemini_model_precedes_shared_adapter_model(self):
        with patch.dict(os.environ, {**ENV, "NYAYA_MODEL": "unrelated-model", "GEMINI_MODEL": "models/gemini-test"}):
            client = GeminiClient()
            self.assertEqual(client.model, "gemini-test")
        with patch.dict(os.environ, {**ENV, "GEMINI_MODEL": "", "NYAYA_MODEL": "gemini-shared"}):
            self.assertEqual(GeminiClient().model, "gemini-shared")

    def test_missing_key_does_not_call_network(self):
        with patch.dict(os.environ, {**ENV, "GEMINI_API_KEY": ""}), patch("nyaya.gemini.httpx.Client") as transport:
            client = GeminiClient()
            self.assertFalse(client.configured)
            with self.assertRaises(GeminiError) as caught:
                client.generate_json("Task", "Input")
            self.assertEqual(caught.exception.code, "missing_key")
            transport.assert_not_called()

    def test_native_auth_quota_and_model_errors_are_distinct_and_redacted(self):
        cases = [(400, "API_KEY_INVALID", "authentication"), (401, "", "authentication"),
                 (403, "", "authentication"), (429, "", "quota"), (404, "", "model"),
                 (503, "", "unavailable"), (400, "", "request")]
        for status, reason, expected in cases:
            with self.subTest(status=status, reason=reason), patch.dict(os.environ, ENV), patch("nyaya.gemini.httpx.Client") as transport:
                transport.return_value.__enter__.return_value.post.return_value = httpx.Response(status, json={"error": {
                    "message": "Unsafe provider echo " + TEST_KEY, "details": [{"reason": reason}],
                }})
                with self.assertRaises(GeminiError) as caught:
                    GeminiClient().generate_json("Task", "Input")
                self.assertEqual(caught.exception.code, expected)
                self.assertNotIn(TEST_KEY, str(caught.exception))
                self.assertNotIn("provider echo", str(caught.exception))

    def test_network_error_never_returns_original_exception(self):
        with patch.dict(os.environ, ENV), patch("nyaya.gemini.httpx.Client") as transport:
            transport.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError("private " + TEST_KEY)
            with self.assertRaises(GeminiError) as caught:
                GeminiClient().generate_json("Task", "Input")
            self.assertEqual(caught.exception.code, "network")
            self.assertNotIn(TEST_KEY, str(caught.exception))

    def test_malformed_or_incomplete_model_response_is_rejected(self):
        for response in (completion("not json"), completion("[]"), completion({}, finish="MAX_TOKENS"),
                         httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})):
            with self.subTest(response=response), patch.dict(os.environ, ENV), patch("nyaya.gemini.httpx.Client") as transport:
                transport.return_value.__enter__.return_value.post.return_value = response
                with self.assertRaises(GeminiError):
                    GeminiClient().generate_json("Task", "Input")

    def test_gemini_adapter_validates_excerpts_and_reports_live_only_after_success(self):
        with patch.dict(os.environ, ENV), patch("nyaya.gemini.httpx.Client") as transport:
            transport.return_value.__enter__.return_value.post.return_value = completion(extraction())
            adapter = LLMAdapter()
            result = adapter.extract(MESSAGES, {})
            self.assertEqual(result["facts"]["deposit"], "Rs 12000")
            self.assertTrue(adapter.status.startswith("Live model extraction connected"))

    def test_wrong_or_empty_extraction_schema_cannot_claim_live_connection(self):
        for payload in ({}, {"answer": "helpful words"}, extraction(kind="other", facts={}, evidence=[]),
                        extraction(facts={"invented_field": "value"}), extraction(evidence="receipt")):
            with self.subTest(payload=payload), patch.dict(os.environ, ENV), patch("nyaya.gemini.httpx.Client") as transport:
                transport.return_value.__enter__.return_value.post.return_value = completion(payload)
                adapter = LLMAdapter()
                self.assertEqual(adapter.extract(MESSAGES, {}), {})
                self.assertIn("rejected", adapter.status)
                self.assertFalse(adapter.status.startswith("Live model extraction connected"))

    def test_hindi_and_english_transcripts_preserve_the_original_words(self):
        for language, text in [("Hindi", "मकान मालिक ने मेरी जमा राशि नहीं लौटाई है।"),
                               ("English", "The seller has not confirmed my refund."),
                               ("Hinglish", "Mera refund abhi nahi aaya.")]:
            with self.subTest(language=language), patch.dict(os.environ, ENV), patch("nyaya.gemini.httpx.Client") as transport:
                post = transport.return_value.__enter__.return_value.post
                post.return_value = completion({"transcript": text, "language": language, "is_speech": True})
                result = GeminiClient().transcribe_audio(wav(), "audio/wav", language)
                self.assertTrue(result.ok)
                self.assertEqual(result.text, text)
                self.assertEqual(result.language, language)
                request = post.call_args.kwargs["json"]
                self.assertIn("inlineData", request["contents"][0]["parts"][0])
                self.assertIn("Do not answer", request["systemInstruction"]["parts"][0]["text"])

    def test_silence_empty_oversize_long_or_bad_mime_does_not_call_api(self):
        clips = [(wav(silent=True), "audio/wav"), (b"", "audio/wav"),
                 (b"x" * (MAX_AUDIO_BYTES + 1), "audio/mpeg"),
                 (wav(120.1), "audio/wav"), (b"not a wave", "audio/wav"),
                 (b"audio-like", "application/octet-stream")]
        for audio, mime in clips:
            with self.subTest(size=len(audio), mime=mime), patch.dict(os.environ, ENV), patch("nyaya.gemini.httpx.Client") as transport:
                result = GeminiClient().transcribe_audio(audio, mime)
                self.assertFalse(result.ok)
                self.assertEqual(result.text, "")
                transport.assert_not_called()

    def test_webm_and_mp3_are_inline_and_mime_aliases_normalize(self):
        for mime, expected in [("audio/webm;codecs=opus", "audio/webm"), ("audio/mp3", "audio/mpeg")]:
            with self.subTest(mime=mime), patch.dict(os.environ, ENV), patch("nyaya.gemini.httpx.Client") as transport:
                post = transport.return_value.__enter__.return_value.post
                post.return_value = completion({"transcript": "My salary is unpaid.", "language": "English", "is_speech": True})
                result = GeminiClient().transcribe_audio(b"synthetic-compressed-audio", mime)
                self.assertTrue(result.ok)
                self.assertEqual(post.call_args.kwargs["json"]["contents"][0]["parts"][0]["inlineData"]["mimeType"], expected)

    def test_audio_nonspeech_bad_schema_or_provider_failure_never_becomes_case_text(self):
        responses = [completion({"transcript": "", "language": "Unknown", "is_speech": False}),
                     completion({"transcript": "[inaudible]", "language": "Unknown", "is_speech": True}),
                     completion({"transcript": "Advice instead of transcript"}),
                     completion({"transcript": "A story", "language": [], "is_speech": True}),
                     httpx.Response(429, json={"error": {"message": TEST_KEY}})]
        for response in responses:
            with self.subTest(response=response), patch.dict(os.environ, ENV), patch("nyaya.gemini.httpx.Client") as transport:
                transport.return_value.__enter__.return_value.post.return_value = response
                result = GeminiClient().transcribe_audio(wav(), "audio/wav")
                self.assertFalse(result.ok)
                self.assertEqual(result.text, "")
                self.assertNotIn(TEST_KEY, result.status)


if __name__ == "__main__":
    unittest.main()
