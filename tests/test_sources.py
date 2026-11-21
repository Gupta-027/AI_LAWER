"""Citation checks ensure a valid-looking link cannot support arbitrary prose."""
from __future__ import annotations

import unittest

from nyaya.sources import load_sources, verified_guidance


class SourceTests(unittest.TestCase):
    def test_model_prose_cannot_replace_stored_claim(self):
        rendered = verified_guidance([{
            "text": "The government guarantees a refund within 24 hours.",
            "source_id": "nch",
            "claim_id": "nch_pre_litigation",
        }])
        expected = next(c["text"] for c in load_sources()["nch"]["claims"] if c["id"] == "nch_pre_litigation")
        self.assertEqual(rendered[0]["text"], expected)
        self.assertNotIn("24 hours", rendered[0]["text"])

    def test_cross_source_citation_rejected(self):
        with self.assertRaises(ValueError):
            verified_guidance([{"text": "A legal claim", "source_id": "nch", "claim_id": "nalsa_eligibility"}])

    def test_unknown_claim_rejected(self):
        with self.assertRaises(ValueError):
            verified_guidance([{"text": "A legal claim", "source_id": "nch", "claim_id": "imaginary_section_9999"}])

    def test_source_records_have_a_specific_locator(self):
        for source in load_sources().values():
            with self.subTest(source=source["id"]):
                self.assertTrue(source["url"].startswith("https://"))
                self.assertGreater(len(source["locator"]), 15)
                self.assertRegex(source["checked_on"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertTrue(source["jurisdiction"])


if __name__ == "__main__":
    unittest.main()
