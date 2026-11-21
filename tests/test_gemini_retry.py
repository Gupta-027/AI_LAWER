"""Retry temporary server errors, keeping authentication and quota errors explicit."""
import unittest
from unittest.mock import patch

import httpx

from nyaya.gemini import GeminiClient, GeminiError


class GeminiRetryTests(unittest.TestCase):
    def test_temporary_unavailability_retries_then_returns_actual_json(self):
        with patch("nyaya.gemini.httpx.Client") as transport, patch("nyaya.gemini.time.sleep") as pause:
            post = transport.return_value.__enter__.return_value.post
            post.side_effect = [httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}}),
                                httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}, "finishReason": "STOP"}]})]
            client = GeminiClient(api_key="synthetic-test-key")
            self.assertEqual(client.generate_json("Return JSON.", "Synthetic input"), {"ok": True})
            self.assertEqual(client.last_attempts, 2)
            self.assertEqual(post.call_count, 2)
            pause.assert_called_once_with(0.5)

    def test_auth_and_quota_errors_are_not_retried(self):
        for status, code in [(401, "authentication"), (429, "quota")]:
            with self.subTest(status=status), patch("nyaya.gemini.httpx.Client") as transport, patch("nyaya.gemini.time.sleep") as pause:
                post = transport.return_value.__enter__.return_value.post
                post.return_value = httpx.Response(status, json={"error": {"message": "private response"}})
                client = GeminiClient(api_key="synthetic-test-key")
                with self.assertRaises(GeminiError) as raised:
                    client.generate_json("Return JSON.", "Synthetic input")
                self.assertEqual(raised.exception.code, code)
                self.assertEqual(post.call_count, 1)
                pause.assert_not_called()

    def test_persistent_unavailability_has_a_finite_retry_limit(self):
        with patch("nyaya.gemini.httpx.Client") as transport, patch("nyaya.gemini.time.sleep") as pause:
            post = transport.return_value.__enter__.return_value.post
            post.return_value = httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}})
            client = GeminiClient(api_key="synthetic-test-key")
            with self.assertRaises(GeminiError) as raised:
                client.generate_json("Return JSON.", "Synthetic input")
            self.assertEqual(raised.exception.code, "unavailable")
            self.assertEqual(post.call_count, 3)
            self.assertEqual(pause.call_count, 2)


if __name__ == "__main__":
    unittest.main()
