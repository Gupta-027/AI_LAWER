"""User-facing workspace regression checks using Streamlit's real test runtime."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class WorkspaceTests(unittest.TestCase):
    def start(self):
        app = AppTest.from_file(str(ROOT / "detailed_app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        return app

    def click(self, app, label):
        next(button for button in app.button if button.label == label).click().run()
        self.assertFalse(app.exception)

    def test_friendly_fact_edit_marks_saved_draft_stale_and_opens_draft(self):
        with patch.dict(os.environ, {"NYAYA_PROVIDER": "demo"}):
            app = self.start()
            app.chat_input[0].set_value("My August salary of Rs 22000 is unpaid. I emailed payroll and have a payslip.").run()
            self.click(app, "Prepare draft")
            self.assertEqual(app.session_state["workspace_0"], "My draft")
            saved = app.session_state.case.draft
            version = app.session_state.case.revision
            next(field for field in app.text_input if field.label == "Amount").set_value("Rs 25000")
            self.click(app, "Save case changes")
            case = app.session_state.case
            self.assertEqual(case.facts["amount"], "Rs 25000")
            self.assertGreater(case.revision, version)
            self.assertEqual(case.draft, saved)
            self.assertNotEqual(case.draft_revision, case.revision)
            self.assertTrue(any("Case details or draft language changed" in warning.value for warning in app.warning))
            self.click(app, "Preview updated draft")
            self.assertIn("25000", app.session_state.case.draft.replace(",", ""))
            self.assertEqual(app.session_state.case.draft_revision, app.session_state.case.revision)

    def test_failed_provider_shows_fallback_instead_of_connected_status(self):
        config = {"NYAYA_PROVIDER": "openai", "NYAYA_MODEL": "", "NYAYA_API_KEY": ""}
        with patch.dict(os.environ, config):
            app = self.start()
            app.chat_input[0].set_value("My landlord kept my Rs 12000 deposit.").run()
            self.assertFalse(app.exception)
            rendered = "\n".join(mark.value for mark in app.markdown)
            self.assertIn("Rules fallback", rendered)
            self.assertNotIn(">AI connected<", rendered)
            self.assertTrue(any("incomplete" in warning.value.lower() for warning in app.warning))

    def test_filling_unknown_fact_removes_unknown_label(self):
        with patch.dict(os.environ, {"NYAYA_PROVIDER": "demo"}):
            app = self.start()
            app.chat_input[0].set_value("My landlord has not returned my deposit.").run()
            app.chat_input[0].set_value("I don't know").run()
            self.assertIn("deposit", app.session_state.case.unknowns)
            next(field for field in app.text_input if field.label == "Deposit paid").set_value("Rs 15000")
            self.click(app, "Save case changes")
            self.assertEqual(app.session_state.case.facts["deposit"], "Rs 15000")
            self.assertNotIn("deposit", app.session_state.case.unknowns)
            self.assertNotIn("deposit", app.session_state.case.skipped_fields)

    def test_fact_edit_escapes_html_in_custom_fact_markup(self):
        with patch.dict(os.environ, {"NYAYA_PROVIDER": "demo"}):
            app = self.start()
            app.chat_input[0].set_value("My landlord kept my Rs 12000 deposit.").run()
            payload = '<img src=x onerror="alert(1)">'
            next(field for field in app.text_input if field.label == "Other party or recipient").set_value(payload)
            self.click(app, "Save case changes")
            fact_markup = [mark.value for mark in app.markdown if 'class="fact-value"' in mark.value]
            self.assertTrue(any("&lt;img" in value and "&quot;" in value for value in fact_markup))
            self.assertFalse(any(payload in value for value in fact_markup))


if __name__ == "__main__":
    unittest.main()
