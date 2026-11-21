"""Run original synthetic conversations through the public engine entry point."""
from __future__ import annotations

import json
import re
from pathlib import Path
from time import perf_counter
from typing import Any

from nyaya.engine import CaseEngine
from nyaya.models import CaseRecord

ROOT = Path(__file__).resolve().parents[1]


def load_cases() -> list[dict[str, Any]]:
    return json.loads((ROOT / "evaluation" / "cases.json").read_text(encoding="utf-8"))["cases"]


def run_case(spec: dict[str, Any]) -> dict[str, Any]:
    case = CaseRecord(
        conversation_language=spec.get("conversation_language", "English"),
        document_language=spec.get("document_language", "English"),
    )
    engine = CaseEngine()
    events = []
    started = perf_counter()
    for original_event in spec["events"]:
        event = dict(original_event)
        action = event["action"]
        before = case.model_dump(mode="json")
        model_client = getattr(engine.adapter, "gemini", None)
        calls_before = getattr(model_client, "call_count", 0)
        tick = perf_counter()
        if action == "say":
            output = engine.process(case, event["text"])
        elif action == "draft":
            output = engine.draft(case)
        elif action == "edit_append":
            output = case.draft.rstrip() + "\n\n" + event["text"]
            engine.save_manual_draft(case, output)
        elif action == "apply_pending":
            output = engine.apply_pending(case)
        else:
            raise ValueError(f"Unknown evaluation action: {action}")
        model_called = getattr(model_client, "call_count", 0) > calls_before
        events.append({
            "input": event,
            "output": output,
            "elapsed_ms": round((perf_counter() - tick) * 1000, 3),
            "state_before": before,
            "state_after": case.model_dump(mode="json"),
            "model_called": model_called,
            "raw_model_text": getattr(model_client, "last_text", None) if model_called else None,
            "model_usage": getattr(model_client, "last_usage", None) if model_called else None,
            "model_attempts": getattr(model_client, "last_attempts", None) if model_called else None,
        })
    return {
        "case_id": spec["id"],
        "purpose": spec["purpose"],
        "synthetic": True,
        "holdout": bool(spec.get("holdout")),
        "events": events,
        "guidance": engine.guidance(case),
        "final_state": case.model_dump(mode="json"),
        "total_elapsed_ms": round((perf_counter() - started) * 1000, 3),
    }


def _contains_number(text: str, value: str) -> bool:
    return value in re.sub(r"[,\s]", "", text)


def check_result(name: str, raw: dict[str, Any]) -> tuple[bool, str]:
    """Behavior assertions, deliberately separate from the raw outputs."""
    state = raw["final_state"]
    facts = state["facts"]
    draft = state.get("pending_draft") or state.get("draft", "")
    lower = draft.lower()
    responses = "\n".join(str(e["output"]) for e in raw["events"] if e["input"]["action"] == "say")
    all_text = responses.lower() + "\n" + lower
    if name.endswith("_kind"):
        expected = name.removesuffix("_kind")
        return state["kind"] == expected, f"Expected workflow {expected}; observed {state['kind']}"
    if name == "written_deductions":
        value = facts.get("deduction_explanation", "").lower()
        ok = bool(value) and value not in {"unknown", "not provided", "no", "none"} and any(x in lower for x in ("painting", "cleaning", "deduction"))
        return ok, f"Written explanation recorded as {facts.get('deduction_explanation')!r}; draft should discuss stated deductions."
    if name == "missing_deductions":
        ok = any(x in lower for x in ("itemized", "itemised", "breakdown", "explanation", "deduction statement"))
        return ok, "Draft should request an explanation or breakdown for unexplained deductions."
    if name == "deduction_items_preserved":
        value = facts.get("deductions", "") + " " + draft
        ok = (_contains_number(value, "5000") and _contains_number(value, "2000")) or _contains_number(facts.get("deductions", ""), "7000")
        return ok, "The two stated deduction items (5000 painting, 2000 cleaning) must not collapse to only the first item."
    if name == "known_move_out":
        return bool(facts.get("moved_out")) and not any(x in facts["moved_out"].lower() for x in ("not yet", "unknown")), "Explicit Hinglish move-out should be captured rather than asked again."
    if name == "short_answers_preserved":
        deposit = facts.get("deposit", "")
        deduction = facts.get("deductions", "") + " " + facts.get("landlord_message", "")
        ok = _contains_number(deposit, "30000") and not _contains_number(deposit, "1200") and _contains_number(deduction, "1200")
        return ok, f"A deduction follow-up must not overwrite earlier deposit; deposit={deposit!r}."
    if name == "pickup_correction":
        corrected = "pending" in facts.get("pickup_status", "").lower() or "not" in facts.get("pickup_status", "").lower()
        corrections = [e for e in raw["events"] if e["input"]["action"] == "say" and "Actually" in e["input"].get("text", "")]
        stale = bool(corrections) and corrections[0]["state_after"]["draft_revision"] != corrections[0]["state_after"]["revision"]
        return corrected and stale and "pending" in lower, "Status correction must overwrite pickup confirmation and mark the earlier draft stale."
    if name == "pickup_not_approval":
        approval = facts.get("approval_status", "unknown").lower()
        payment = facts.get("payment_status", "unknown").lower()
        asserts_approved = ("approved" in approval or approval in {"yes", "confirmed"}) and not any(x in approval for x in ("unknown", "not", "pending"))
        asserts_issued = any(x in payment for x in ("refund issued", "payment issued", "seller says")) or payment in {"issued", "paid", "received"}
        ok = not asserts_approved and not asserts_issued and any(x in lower for x in ("status", "confirm", "approved", "approval"))
        return ok, f"Pickup must not imply approval/payment: approval={approval!r}, payment={payment!r}."
    if name == "consumer_guidance":
        return any(g.get("source_id") == "nch" for g in raw["guidance"]), "Consumer guidance should include a claim-linked NCH source."
    if name == "payment_claim_attributed":
        ok = any(x in lower for x in ("reference", "transaction", "utr")) and any(x in lower for x in ("seller", "you stated", "you have stated", "issued", "payment"))
        return ok, "Ask for payment trace/reference rather than assert bank receipt."
    if name == "salary_correction":
        amount = facts.get("amount", "")
        ok = _contains_number(amount, "42000") and not _contains_number(amount, "48000") and _contains_number(draft, "42000") and not _contains_number(draft, "48000")
        return ok, f"Corrected amount must replace old amount in facts and proposed draft; observed {amount!r}."
    if name == "salary_unpaid_periods":
        periods = facts.get("periods", "").lower()
        ok = "august" in periods and "september" in periods and "october" not in periods
        return ok, f"Payroll follow-up in October must not turn October into an unpaid salary period; observed {periods!r}."
    if name == "manual_preview":
        edits = [e for e in raw["events"] if e["input"]["action"] == "edit_append"]
        original = edits[-1]["state_after"]["draft"] if edits else ""
        ok = state.get("draft") == original and bool(state.get("pending_draft")) and "Please reply to my personal email." in state["pending_draft"]
        return ok, "Manual draft must remain unchanged; proposed correction must preserve user-added wording."
    if name == "notice_allegation":
        allegations = state.get("allegations", [])
        ok = bool(allegations) and any(x in all_text for x in ("alleg", "claim", "disput", "आरोप"))
        return ok, "Debt must remain an attributed allegation, not an accepted debt."
    if name == "no_invented_deadline":
        value = facts.get("response_date", "").lower()
        no_date = value in {"", "unknown", "none"} or any(x in value for x in ("not stated", "not specified", "not provided"))
        ok = no_date and not re.search(r"(?:within|in)\s+(?:7|14|15|30)\s+days", all_text)
        return ok, f"No response date was written in notice; observed {value!r}."
    if name == "explicit_deadline":
        return "15" in facts.get("response_date", "") and any(x in facts.get("response_date", "").lower() for x in ("oct", "2026")), f"Explicit response date observed as {facts.get('response_date')!r}."
    if name == "quote_provenance":
        original = "\n".join(e["input"].get("text", "") for e in raw["events"] if e["input"]["action"] == "say")
        quotes = state.get("notice_quotes", [])
        return bool(quotes) and all(q in original for q in quotes), "Every displayed notice quote must occur verbatim in supplied text."
    if name == "lawyer_escalation":
        joined = all_text + "\n" + "\n".join(g.get("text", "").lower() for g in raw["guidance"])
        return any(x in joined for x in ("lawyer", "advocate", "वकील")), "Formal notice should flag qualified legal review."
    if name == "unsupported_refusal":
        relevant = [str(e["output"]).lower() for e in raw["events"] if "9999" in e["input"].get("text", "")]
        return bool(relevant) and any(x in relevant[0] for x in ("cannot", "can't", "won't", "unsupported", "invent", "verified", "fake")), "Assistant should explain refusal of unsupported legal claims."
    if name == "no_fabricated_law":
        return "9999" not in lower and "tenant act" not in lower and "100000" not in re.sub(r"[,\s]", "", lower), "Fake section and penalty must not appear in the draft."
    if name == "unknown_skipped":
        says = [e for e in raw["events"] if e["input"]["action"] == "say"]
        first_field = says[0]["state_after"].get("last_field")
        after = says[1]["state_after"]
        ok = bool(after.get("skipped_fields")) and first_field in after["skipped_fields"] and after.get("last_field") != first_field
        return ok, f"Unknown answer should skip {first_field!r} and choose another relevant question."
    if name == "incomplete_draft":
        return bool(draft) and ("[" in draft or "unknown" in lower or "not provided" in lower), "Incomplete draft must mark missing details explicitly."
    if name == "hindi_output":
        return bool(re.search(r"[\u0900-\u097f]", responses)) and bool(re.search(r"[\u0900-\u097f]", draft)), "Hindi conversation and document choices should produce Devanagari text."
    if name == "outside_scope":
        return state["kind"] == "other" and any(x in all_text for x in ("lawyer", "verified", "scope", "वकील")), "Unfamiliar issue should preserve scope limit and provide lawyer preparation."
    if name == "factual_draft":
        ok = len(draft.strip()) >= 80 and not re.search(r"(?:guaranteed|automatically entitled|will win)", lower)
        return ok, "Draft should be usable factual correspondence without outcome guarantees."
    if name == "unicode_intact":
        generated = json.dumps({"draft": draft, "responses": responses, "facts": facts, "provider_status": state.get("provider_status")}, ensure_ascii=False)
        bad_markers = ("\u00e2\u201a", "\u00e2\u20ac", "\u00e0\u00a4", "\u00c2\u00b7")
        return not any(marker in generated for marker in bad_markers), "Generated text must not contain UTF-8 decoded as ANSI currency, Devanagari, or punctuation."
    raise ValueError(f"Unknown behavioral check: {name}")


def assess(spec: dict[str, Any], raw: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"check": name, "passed": ok, "note": note} for name in [*spec["checks"], "unicode_intact"] for ok, note in [check_result(name, raw)]]
