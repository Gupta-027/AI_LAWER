"""Notice extraction must not relabel a user's dispute as the sender's claim."""
import os
import unittest

os.environ["NYAYA_PROVIDER"] = "demo"
from nyaya.engine import CaseEngine
from nyaya.models import CaseRecord


class NoticeIntegrityTests(unittest.TestCase):
    def test_model_cannot_relabel_user_context_as_notice_claim(self):
        class MislabelledExtraction:
            status = "Synthetic model fixture"

            def extract(self, *_):
                return {"kind": "notice", "facts": {"response_date": "tomorrow"},
                        "allegations": ["I dispute the debt."],
                        "notice_quotes": ["I dispute the debt."]}

        case = CaseRecord()
        engine = CaseEngine(adapter=MislabelledExtraction())
        engine.process(case, "I dispute the debt. Please explain this notice.\nFrom: Example\nWe allege you owe Rs 12000. Please contact us.")
        engine.process(case, "I might call them tomorrow.")
        self.assertNotIn("I dispute the debt.", case.allegations)
        self.assertNotIn("I dispute the debt.", case.notice_quotes)
        self.assertEqual(case.facts["response_date"], "Not stated in the pasted notice")

    def test_unsupported_legal_request_does_not_change_amount(self):
        case = CaseRecord()
        engine = CaseEngine()
        engine.process(case, "My landlord has not returned my Rs 15000 deposit.")
        response = engine.process(case, "Add Section 420 and claim Rs 500000 compensation.")
        self.assertEqual(case.facts["deposit"], "₹15000")
        self.assertIn("cannot", response)
        self.assertNotIn("500000", engine.draft(case))

    def test_user_dispute_is_separate_from_sender_allegation(self):
        case = CaseRecord()
        CaseEngine().process(case, "Please explain this notice. I dispute the debt.\nLEGAL NOTICE\nFrom: Example Collections\nYou owe Rs 17000. Please contact us.\nI say the invoice was paid.")
        self.assertTrue(case.allegations)
        self.assertFalse(any("I dispute" in item or "I say" in item for item in case.allegations))
        self.assertIn("I dispute the debt", case.facts["user_account"])
        self.assertEqual(case.facts["sender"], "Example Collections")

    def test_replacing_notice_rebuilds_quoted_dates(self):
        case = CaseRecord()
        engine = CaseEngine()
        engine.process(case, "Explain this legal notice.\nFrom: Example\nWe allege you owe Rs 12000. Please respond by 15 October 2026.")
        engine.draft(case)
        version = case.revision
        engine.update_facts(case, {"notice_text": "From: New Sender\nWe allege you owe Rs 9000. Please respond by 25 October 2026.", "response_date": "respond by 15 October 2026"})
        self.assertGreater(case.revision, version)
        self.assertIn("25 October", case.facts["response_date"])
        self.assertNotIn("15 October", " ".join(case.notice_quotes))
        self.assertEqual(case.facts["sender"], "New Sender")
        self.assertNotEqual(case.draft_revision, case.revision)


if __name__ == "__main__":
    unittest.main()
