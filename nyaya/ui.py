"""Presentation helpers. Case interpretation and legal guidance stay in the engine."""
from html import escape
from pathlib import Path

from .models import CaseRecord

FACT_LABELS = {
    "deposit": "Deposit paid", "moved_out": "Move-out and key return",
    "deductions": "Deductions mentioned", "deduction_explanation": "Explanation for deductions",
    "landlord_message": "Landlord’s message", "order_id": "Order number",
    "amount": "Amount", "pickup_status": "Return pickup", "approval_status": "Refund approval",
    "payment_status": "Refund payment", "seller_message": "Seller’s message",
    "periods": "Unpaid salary periods", "prior_communication": "Previous written communication",
    "sender": "Notice sender", "requested_action": "Action requested in the notice",
    "response_date": "Response date written in the notice", "notice_date": "Notice date",
    "notice_text": "Pasted notice", "user_name": "Your name", "other_party": "Other party or recipient",
    "location": "Location", "timeline": "Timeline", "summary": "Original account",
    "user_account": "Your account, separate from the notice",
}
EDIT_FIELDS = {
    "rental": ["deposit", "moved_out", "deductions", "deduction_explanation", "other_party", "user_name", "location"],
    "refund": ["order_id", "amount", "pickup_status", "approval_status", "payment_status", "other_party", "user_name"],
    "salary": ["periods", "amount", "prior_communication", "other_party", "user_name"],
    "notice": ["notice_text", "user_account"],
    "other": ["summary", "other_party", "location", "timeline"],
}
KINDS = {"rental": "Rental deposit", "refund": "Online refund", "salary": "Unpaid salary",
         "notice": "Notice explanation", "other": "Case preparation"}
MARK = '<svg viewBox="0 0 32 32" fill="none" aria-hidden="true"><path d="M16 6v20M10 26h12M6 11h20M8 11l-4 8h8l-4-8Zm16 0-4 8h8l-4-8Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><circle cx="16" cy="9" r="2.5" fill="currentColor"/></svg>'


def css() -> str:
    return "<style>" + Path(__file__).with_name("ui.css").read_text(encoding="utf-8") + "</style>"


def brand(*, compact: bool = False) -> str:
    return (f'<div class="wordmark {"compact" if compact else ""}"><span class="brand-mark">{MARK}</span>'
            '<div><span class="brand-name">Nyaya Saathi</span><span class="brand-caption">Legal help, in your words</span></div></div>')


def app_header(provider: str, status: str) -> str:
    live = provider != "demo" and status.startswith("Live model extraction connected")
    if provider == "demo":
        label, detail, tone = "Rules demo", "No AI model connected", "demo"
    elif live:
        label, detail, tone = "AI connected", "Review every extracted fact", "live"
    elif any(word in status.lower() for word in ("unavailable", "rejected", "incomplete", "unknown provider", "authentication failed", "quota", "missing")):
        label, detail, tone = "Rules fallback", "Model response unavailable", "demo"
    else:
        label, detail, tone = ("Gemini configured" if provider == "gemini" else "AI configured"), "Connection not yet verified", "demo"
    return (f'<div class="app-header">{brand()}<div class="mode-block"><span class="mode-pill {tone}">'
            f'<span class="mode-dot"></span>{escape(label)}</span><small>{escape(detail)}</small></div></div>')


def progress(case: CaseRecord) -> str:
    steps = ["Your story", "Check the facts", "Review your draft"]
    current = 2 if case.draft else 1 if case.messages else 0
    parts = []
    for i, title in enumerate(steps):
        state = "complete" if i < current else "current" if i == current else "upcoming"
        parts.append(f'<span class="journey-step {state}"><span class="journey-dot"></span>{title}</span>')
    return '<div class="journey" aria-label="Case preparation progress">' + "".join(parts) + "</div>"


def escaped_pills(values: list[str]) -> str:
    return '<div class="evidence-list">' + "".join(f'<span class="evidence-tag">{escape(v)}</span>' for v in values) + "</div>"
