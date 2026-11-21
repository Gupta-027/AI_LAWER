"""Exercise visible workflow and session isolation using Streamlit's test runtime."""
from __future__ import annotations

import os
from pathlib import Path
import unittest

os.environ["NYAYA_PROVIDER"] = "demo"

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class AppWorkflowTests(unittest.TestCase):
    def start(self):
        app = AppTest.from_file(str(ROOT / "detailed_app.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        return app

    def click(self, app, label):
        next(button for button in app.button if button.label == label).click().run()
        self.assertEqual(len(app.exception), 0)

    def test_conversation_draft_correction_and_clear(self):
        app = self.start()
        app.chat_input[0].set_value(
            "My employer has not paid my August salary of Rs 22000. I emailed payroll and have payslips."
        ).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state.case.kind, "salary")
        self.click(app, "Prepare draft")
        self.assertIn("22000", app.session_state.case.draft.replace(",", ""))
        original = app.session_state.case.draft
        next(t for t in app.text_area if t.label == "Edit draft").set_value(original + "\nPlease reply by email.")
        self.click(app, "Save draft edits")
        saved = app.session_state.case.draft
        app.chat_input[0].set_value("Correction: the total unpaid salary is Rs 25000, not Rs 22000.").run()
        self.assertEqual(app.session_state.case.draft, saved)
        self.click(app, "Preview updated draft")
        self.assertEqual(app.session_state.case.draft, saved)
        self.assertTrue(app.session_state.case.pending_draft)
        self.click(app, "Apply proposed draft")
        self.assertIn("25000", app.session_state.case.draft.replace(",", ""))
        self.click(app, "Clear case")
        self.assertEqual(app.session_state.case.messages, [])
        self.assertEqual(app.session_state.case.draft, "")
        self.assertEqual(len(app.text_area), 0)

    def test_sessions_do_not_share_case(self):
        first = self.start()
        first.chat_input[0].set_value("My landlord kept my Rs 18000 deposit.").run()
        second = self.start()
        self.assertTrue(first.session_state.case.messages)
        self.assertEqual(second.session_state.case.messages, [])

    def test_language_choices_are_independent(self):
        app = self.start()
        app.selectbox(key="conversation_language").select("Hindi").run()
        app.selectbox(key="document_language").select("English").run()
        app.chat_input[0].set_value("मेरी अगस्त की तनख्वाह नहीं मिली है। कुल बकाया 32000 रुपये है।").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state.case.conversation_language, "Hindi")
        self.assertEqual(app.session_state.case.document_language, "English")
        self.click(app, "Prepare draft")
        self.assertIn("Subject", app.session_state.case.draft)


if __name__ == "__main__":
    unittest.main()
