"""Grounded AI-update regressions using synthetic extraction fixtures, no API calls."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from nyaya.engine import CaseEngine, GOALS
from nyaya.llm import LLMAdapter
from nyaya.models import CaseRecord


class ExtractionFixture:
    """Exercise the real validator with a model-shaped response from each turn."""
    status = "Synthetic extraction fixture; no live model call"

    def __init__(self, *payloads):
        self.payloads = list(payloads)

    def extract(self, messages, _facts):
        payload = self.payloads.pop(0) if self.payloads else {}
        return LLMAdapter._validate(deepcopy(payload), messages)


class AIConversationTests(unittest.TestCase):
    def test_live_salary_payload_cannot_reintroduce_old_amount_as_evidence(self):
        path = Path(__file__).resolve().parents[1] / "raw_outputs" / "20261121T140205149688Z_salary_correction.json"
        recorded = json.loads(path.read_text(encoding="utf-8"))
        payloads = [json.loads(event["raw_model_text"]) for event in recorded["events"] if event.get("raw_model_text")]
        engine = CaseEngine(adapter=ExtractionFixture(*payloads))
        case = CaseRecord()
        for event in recorded["events"]:
            action = event["input"]["action"]
            if action == "say":
                engine.process(case, event["input"]["text"])
            elif action == "draft":
                engine.draft(case)
            elif action == "edit_append":
                engine.save_manual_draft(case, case.draft.rstrip() + "\n\n" + event["input"]["text"])
        self.assertEqual(case.facts["amount"], "₹42000")
        self.assertEqual(set(case.evidence), {"employment letter", "payslips", "email correspondence"})
        self.assertTrue(case.pending_draft)
        self.assertNotIn("48000", case.pending_draft)
        self.assertIn("42000", case.pending_draft)
        self.assertIn("Please reply to my personal email.", case.pending_draft)
        self.assertIn("48000", case.draft)  # Saved manual version still awaits approval.

    def test_negated_records_are_not_claimed_as_available(self):
        for text in (
            "My landlord kept my deposit. I have no receipt or agreement.",
            "My landlord kept my deposit. I don't have a receipt.",
            "मकान मालिक ने जमा नहीं लौटाया। मेरे पास रसीद नहीं है।",
        ):
            with self.subTest(text=text):
                case = CaseRecord()
                CaseEngine(adapter=ExtractionFixture()).process(case, text)
                self.assertNotIn("receipt", case.evidence)
                self.assertNotIn("agreement", case.evidence)

    def test_available_and_missing_records_keep_separate_scopes(self):
        case = CaseRecord()
        engine = CaseEngine(adapter=ExtractionFixture())
        engine.process(case, "My employer has not paid salary. I have photos and an employment letter, but no receipt or agreement. I emailed payroll but got no reply.")
        self.assertIn("photographs", case.evidence)
        self.assertIn("employment letter", case.evidence)
        self.assertIn("email correspondence", case.evidence)
        self.assertNotIn("receipt", case.evidence)
        self.assertNotIn("agreement", case.evidence)

    def test_later_record_withdrawal_is_not_undone_by_model_history(self):
        adapter = ExtractionFixture({"kind": "rental", "evidence": ["receipt"]},
                                    {"kind": "rental", "evidence": ["receipt"]})
        case = CaseRecord()
        engine = CaseEngine(adapter=adapter)
        engine.process(case, "My landlord kept my Rs 15000 deposit. I have a receipt and photographs.")
        self.assertIn("receipt", case.evidence)
        engine.process(case, "Correction: I no longer have the receipt, but I have photographs.")
        self.assertNotIn("receipt", case.evidence)
        self.assertIn("photographs", case.evidence)

    def test_requests_to_obtain_records_are_not_existing_evidence(self):
        case = CaseRecord()
        engine = CaseEngine(adapter=ExtractionFixture())
        engine.process(case, "My landlord kept my deposit. Please draft an email. Should I obtain a receipt?")
        self.assertNotIn("email correspondence", case.evidence)
        self.assertNotIn("receipt", case.evidence)

    def test_hindi_records_preserve_positive_items_and_exclude_missing_receipt(self):
        case = CaseRecord(conversation_language="Hindi")
        CaseEngine(adapter=ExtractionFixture()).process(case, "मकान मालिक ने जमा नहीं लौटाया। मेरे पास रसीद नहीं है, लेकिन फोटो और व्हाट्सऐप संदेश हैं।")
        self.assertNotIn("receipt", case.evidence)
        self.assertIn("photographs", case.evidence)
        self.assertIn("WhatsApp messages", case.evidence)

    def test_model_understands_hindi_salary_without_rule_keyword(self):
        story = "काव्या टेक में जुलाई की पगार 30000 रुपये रुकी है। मुझे भुगतान मांगना है।"
        adapter = ExtractionFixture({"kind": "salary", "facts": {
            "amount": "30000 रुपये", "periods": "जुलाई", "other_party": "काव्या टेक"}})
        case = CaseRecord(conversation_language="Hindi", document_language="Hindi")
        engine = CaseEngine(adapter=adapter)
        reply = engine.process(case, story)
        self.assertEqual(case.kind, "salary")
        self.assertEqual(case.goal, GOALS["salary"])
        self.assertEqual(case.facts["amount"], "₹30000")
        self.assertEqual(case.facts["other_party"], "काव्या टेक")
        self.assertIn("₹30000", reply)
        self.assertEqual(reply.count("?"), 1)
        self.assertNotIn("I have updated", reply)
        draft = engine.draft(case)
        self.assertIn("जुलाई", draft)
        self.assertIn("काव्या टेक", draft)
        self.assertIn("विषय:", draft)

    def test_historical_model_fact_cannot_undo_a_correction(self):
        adapter = ExtractionFixture(
            {"kind": "salary", "facts": {"amount": "Rs 48000"}},
            {"kind": "salary", "facts": {"amount": "Rs 48000"}},
            {"kind": "salary", "facts": {"amount": "Rs 48000"}},
        )
        case = CaseRecord()
        engine = CaseEngine(adapter=adapter)
        engine.process(case, "My August salary of Rs 48000 is unpaid.")
        engine.draft(case)
        engine.process(case, "Correction: the amount is Rs 42000, not Rs 48000.")
        self.assertEqual(case.facts["amount"], "₹42000")
        self.assertNotEqual(case.draft_revision, case.revision)
        engine.process(case, "I also have an email from payroll.")
        self.assertEqual(case.facts["amount"], "₹42000")
        self.assertNotIn("48000", engine.draft(case))

    def test_historical_model_party_cannot_replace_manual_edit(self):
        adapter = ExtractionFixture(
            {"kind": "salary", "facts": {"other_party": "Old Employer"}},
            {"kind": "salary", "facts": {"other_party": "Old Employer"}},
        )
        case = CaseRecord()
        engine = CaseEngine(adapter=adapter)
        engine.process(case, "Old Employer has not paid my August salary of Rs 12000.")
        engine.update_facts(case, {"other_party": "Corrected Employer"})
        engine.process(case, "I found my payslip.")
        self.assertEqual(case.facts["other_party"], "Corrected Employer")

    def test_one_question_and_grounded_amount_acknowledgement(self):
        case = CaseRecord()
        engine = CaseEngine(adapter=ExtractionFixture())
        reply = engine.process(case, "My landlord kept my Rs 19000 deposit.")
        self.assertIn("₹19000", reply)
        self.assertIn("your account", reply)
        self.assertEqual(reply.count("?"), 1)
        self.assertNotIn("entitled", reply)
        self.assertNotIn("Section", reply)

    def test_unknown_response_acknowledges_and_moves_on(self):
        case = CaseRecord(conversation_language="Hinglish")
        engine = CaseEngine(adapter=ExtractionFixture())
        engine.process(case, "My landlord has not returned my deposit.")
        reply = engine.process(case, "I don't know")
        self.assertIn("Koi baat nahi", reply)
        self.assertIn("deposit", case.skipped_fields)
        self.assertNotEqual(case.last_field, "deposit")
        self.assertEqual(reply.count("?"), 1)

    def test_hindi_written_deductions_selects_matching_factual_draft(self):
        explanation = "मालिक ने लिखित कटौती विवरण भेजा है।"
        story = "मकान का जमा 30000 रुपये था। " + explanation + " सफाई के 2000 रुपये काटे हैं।"
        adapter = ExtractionFixture({"kind": "rental", "facts": {
            "deposit": "30000 रुपये", "deductions": "2000 रुपये", "deduction_explanation": explanation}})
        case = CaseRecord(conversation_language="Hindi", document_language="Hindi")
        engine = CaseEngine(adapter=adapter)
        engine.process(case, story)
        self.assertEqual(case.facts["deduction_explanation"], "Written deductions provided")
        draft = engine.draft(case)
        self.assertIn("आपके लिखित कटौती विवरण", draft)
        self.assertIn("₹2000", draft)

    def test_hindi_refund_draft_localizes_known_statuses_and_placeholders(self):
        case = CaseRecord(kind="refund", conversation_language="Hindi", document_language="Hindi",
                          facts={"amount": "₹1200", "pickup_status": "Pickup confirmed", "approval_status": "Unknown"})
        draft = CaseEngine(adapter=ExtractionFixture()).draft(case)
        self.assertIn("पिकअप की पुष्टि है", draft)
        self.assertIn("[स्थिति अज्ञात है]", draft)
        self.assertIn("[ऑर्डर नंबर]", draft)
        self.assertNotIn("Pickup confirmed", draft)
        self.assertNotIn("status not known", draft)

    def test_model_status_keeps_hindi_uncertainty_instead_of_weak_rule_summary(self):
        status = "मेरे ऑनलाइन ऑर्डर का रिफंड मंजूर हुआ है या नहीं, मुझे नहीं पता।"
        story = status
        adapter = ExtractionFixture({"kind": "refund", "facts": {"approval_status": status}})
        case = CaseRecord(conversation_language="Hindi", document_language="Hindi")
        engine = CaseEngine(adapter=adapter)
        engine.process(case, story)
        self.assertEqual(case.facts["approval_status"], status)
        self.assertNotIn("Refund approved according to user", engine.draft(case))

    def test_hindi_fallback_negation_does_not_assert_refund_approval(self):
        engine = CaseEngine(adapter=ExtractionFixture())
        for text, expected in (
            ("मेरे ऑर्डर का रिफंड मंजूर हुआ है या नहीं, मुझे नहीं पता।", "Unknown"),
            ("मेरे ऑर्डर का रिफंड मंजूर नहीं हुआ है।", "Not confirmed / pending"),
        ):
            with self.subTest(text=text):
                case = CaseRecord(conversation_language="Hindi")
                engine.process(case, text)
                self.assertEqual(case.facts["approval_status"], expected)

    def test_non_rental_word_does_not_trigger_rent_classification(self):
        case = CaseRecord()
        engine = CaseEngine(adapter=ExtractionFixture())
        engine.process(case, "A neighbour keeps giving me different explanations about a shared gate.")
        self.assertEqual(case.kind, "other")

    def test_model_recognized_goal_is_not_asked_again(self):
        goal = "I want to prepare questions for a lawyer."
        case = CaseRecord()
        engine = CaseEngine(adapter=ExtractionFixture({"kind": "other", "goal": goal, "facts": {}}))
        reply = engine.process(case, "My neighbour blocks our shared gate. " + goal)
        self.assertEqual(case.goal, goal)
        self.assertEqual(case.last_field, "evidence")
        self.assertNotIn("What outcome would you like", reply)


if __name__ == "__main__":
    unittest.main()
