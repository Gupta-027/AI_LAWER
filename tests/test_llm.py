"""Mock HTTP adapter tests. These are not live model-inference measurements."""
from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

import httpx

from nyaya.llm import LLMAdapter


CONFIG = {
    "NYAYA_PROVIDER": "openai",
    "NYAYA_MODEL": "mock-test-model",
    "NYAYA_BASE_URL": "https://model.invalid/v1/",
    "NYAYA_API_KEY": "synthetic-test-key-do-not-print",
}
MESSAGES = [{"role": "user", "content": "My rental deposit was Rs 12000. I have a receipt. The landlord says I owe cleaning charges."}]


def response_with(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": content}}]},
        request=httpx.Request("POST", "https://model.invalid/v1/chat/completions"),
    )


class AdapterTests(unittest.TestCase):
    def test_demo_never_opens_network(self):
        with patch.dict(os.environ, {"NYAYA_PROVIDER": "demo"}), patch("nyaya.llm.httpx.Client") as client:
            adapter = LLMAdapter()
            self.assertEqual(adapter.extract(MESSAGES, {}), {})
            client.assert_not_called()
            self.assertIn("no language model", adapter.status.lower())

    def test_configurable_chat_completion_request_and_valid_extraction(self):
        payload = {"kind": "rental", "facts": {"deposit": "Rs 12000"}, "evidence": ["receipt"]}
        with patch.dict(os.environ, CONFIG), patch("nyaya.llm.httpx.Client") as client:
            post = client.return_value.__enter__.return_value.post
            post.return_value = response_with(json.dumps(payload))
            adapter = LLMAdapter()
            result = adapter.extract(MESSAGES, {})
            self.assertEqual(result["facts"]["deposit"], "Rs 12000")
            args, kwargs = post.call_args
            self.assertEqual(args[0], "https://model.invalid/v1/chat/completions")
            self.assertEqual(kwargs["json"]["model"], "mock-test-model")
            self.assertEqual(kwargs["headers"]["Authorization"], "Bearer " + CONFIG["NYAYA_API_KEY"])
            self.assertNotIn(CONFIG["NYAYA_API_KEY"], json.dumps(kwargs["json"]))
            self.assertIn("Live model", adapter.status)

    def test_endpoint_configuration_read_at_instance_time(self):
        with patch.dict(os.environ, CONFIG):
            first = LLMAdapter()
        with patch.dict(os.environ, {**CONFIG, "NYAYA_MODEL": "replacement-model"}):
            second = LLMAdapter()
        self.assertEqual(first.model, "mock-test-model")
        self.assertEqual(second.model, "replacement-model")

    def test_ollama_needs_no_api_key(self):
        with patch.dict(os.environ, {"NYAYA_PROVIDER": "ollama", "NYAYA_MODEL": "local-test-model", "NYAYA_BASE_URL": "http://127.0.0.1:11434/v1", "NYAYA_API_KEY": ""}), patch("nyaya.llm.httpx.Client") as client:
            post = client.return_value.__enter__.return_value.post
            post.return_value = response_with('{"kind":"rental","facts":{}}')
            adapter = LLMAdapter()
            adapter.extract(MESSAGES, {})
            self.assertNotIn("Authorization", post.call_args.kwargs["headers"])
            self.assertIn("Live model", adapter.status)

    def test_missing_key_falls_back_without_network(self):
        with patch.dict(os.environ, {**CONFIG, "NYAYA_API_KEY": ""}), patch("nyaya.llm.httpx.Client") as client:
            adapter = LLMAdapter()
            self.assertEqual(adapter.extract(MESSAGES, {}), {})
            client.assert_not_called()
            self.assertIn("incomplete", adapter.status)

    def test_network_failure_falls_back_without_leaking_error_or_key(self):
        with patch.dict(os.environ, CONFIG), patch("nyaya.llm.httpx.Client") as client:
            client.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError("private server error " + CONFIG["NYAYA_API_KEY"])
            adapter = LLMAdapter()
            self.assertEqual(adapter.extract(MESSAGES, {}), {})
            self.assertNotIn(CONFIG["NYAYA_API_KEY"], adapter.status)
            self.assertNotIn("private server", adapter.status)
            self.assertIn("demo", adapter.status)

    def test_invalid_json_falls_back(self):
        for content in ("not json", "[]", '{"kind":'):
            with self.subTest(content=content), patch.dict(os.environ, CONFIG), patch("nyaya.llm.httpx.Client") as client:
                client.return_value.__enter__.return_value.post.return_value = response_with(content)
                adapter = LLMAdapter()
                self.assertEqual(adapter.extract(MESSAGES, {}), {})
                self.assertIn("rejected", adapter.status)

    def test_fabricated_law_deadline_amount_and_quote_filtered(self):
        data = {
            "kind": "rental",
            "goal": "Apply Section 9999 with a guaranteed result",
            "facts": {
                "deposit": "Rs 99000",
                "penalty": "Rs 500000",
                "response_date": "Respond by 1 December 2026",
                "summary": "Under Section 9999 the tenant is legally entitled to a refund",
                "requested_action": "Pay within 7 days",
            },
            "evidence": ["receipt", "a witness who was never mentioned"],
            "allegations": ["The landlord says I owe cleaning charges.", "You committed theft"],
            "notice_quotes": ["You committed theft"],
        }
        result = LLMAdapter._validate(data, MESSAGES)
        self.assertNotIn("goal", result)
        self.assertEqual(result["facts"], {})
        self.assertEqual(result["evidence"], ["receipt"])
        self.assertEqual(result["allegations"], ["The landlord says I owe cleaning charges."])
        self.assertEqual(result["notice_quotes"], [])

    def test_assistant_text_is_not_user_evidence(self):
        messages = MESSAGES + [{"role": "assistant", "content": "Invented supporting witness"}]
        result = LLMAdapter._validate({"evidence": ["Invented supporting witness"]}, messages)
        self.assertEqual(result["evidence"], [])


if __name__ == "__main__":
    unittest.main()
