"""One-shot plain-language advice for a user's problem, plus spoken audio.

Anti-hallucination: the model is told never to cite sections/acts/cases, any line
that still does is dropped by code, and helpline numbers come only from the
checked data/sources.json, never from model text.
"""
from __future__ import annotations

from io import BytesIO
import re

from .gemini import GeminiClient, GeminiError
from .sources import load_sources

# Model may only pick from these; text shown is the verified claim, not the model's.
HELPLINES = {
    "nalsa": ("nalsa_faq", "nalsa_contact", "मुफ़्त कानूनी मदद (NALSA): 15100", "Free legal aid (NALSA): 15100"),
    "consumer": ("nch", "nch_register", "उपभोक्ता हेल्पलाइन: 1915", "Consumer Helpline: 1915"),
}
CITATION = re.compile(r"\b(?:section|sec\.|article|act,?\s+\d{4}|vs?\.|versus)\s*\d*|धारा\s*\d+|अनुच्छेद\s*\d+|अधिनियम", re.I)

SYSTEM = """You help ordinary people in India (often in villages, many cannot read) with everyday legal problems:
deposit not returned, refund not received, salary not paid, a notice they do not understand, and similar.
Reply in {lang}, in very simple spoken words a 10-year-old understands. Short sentences. No legal jargon.
Strict rules:
- NEVER mention any law name, act, section number, article, rule number or court case. Do not invent facts.
- Do not promise a result. If unsure, say so honestly.
- If it involves police, arrest, court summons, violence, eviction, land/property dispute, divorce or custody,
  or a deadline in a notice, set need_lawyer=true and explain why in one line.
This is a chat. You see the whole conversation; answer the LATEST user message.
- reply: 1 to 3 short sentences answering the latest message directly (warm and respectful: use आप, never call the user बेटा/beta or similar).
- On the first message give steps and proof. On later messages fill steps/proof ONLY if they change; otherwise leave them empty, do not repeat.
- follow_up: ONE short question to ask the user that would help you guide them better (e.g. amount, date, proof they have). Empty if nothing useful to ask.
- steps: 3 to 5 practical things the person can do now, in order (talk/write to the other side, keep proof, complain, get free help).
- proof: 2 to 4 documents or records they should keep or collect.
- helplines: choose from ["nalsa", "consumer"] only, and only when relevant to this reply (empty list on later turns unless asked). "consumer" only for shopping/refund/service complaints.
Return JSON only."""

SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}},
        "proof": {"type": "array", "items": {"type": "string"}},
        "need_lawyer": {"type": "boolean"},
        "lawyer_reason": {"type": "string"},
        "helplines": {"type": "array", "items": {"type": "string", "enum": list(HELPLINES)}},
        "follow_up": {"type": "string"},
    },
    "required": ["reply", "follow_up", "steps", "proof", "need_lawyer", "lawyer_reason", "helplines"],
}


def _clean(lines) -> list[str]:
    if not isinstance(lines, list):
        return []
    return [str(x).strip() for x in lines if str(x).strip() and not CITATION.search(str(x))][:5]


def _safe(value) -> str:
    text = str(value or "").strip()
    return "" if CITATION.search(text) else text


def get_advice(history: list[dict], hindi: bool, client: GeminiClient | None = None) -> dict:
    """history: [{"role": "user"|"assistant", "content": str}], latest user message last.

    Returns {reply, follow_up, steps, proof, need_lawyer, lawyer_reason, helplines, error}.
    """
    client = client or GeminiClient()
    first_turn = sum(m["role"] == "user" for m in history) <= 1
    # ponytail: whole chat resent each turn; trim to last 12 messages, summarise if chats get long
    transcript = "\n".join(f"{'USER' if m['role'] == 'user' else 'YOU'}: {m['content'][:2000]}" for m in history[-12:])
    try:
        data = client.generate_json(SYSTEM.format(lang="Hindi (Devanagari script)" if hindi else "simple English"),
                                    transcript, schema=SCHEMA, max_output_tokens=1500)
    except GeminiError as error:
        return {"reply": "", "follow_up": "", "steps": [], "proof": [], "need_lawyer": False, "lawyer_reason": "",
                "helplines": _helpline_text(["nalsa"], hindi), "error": error.status}
    picked = [h for h in data.get("helplines", []) if h in HELPLINES]
    if first_turn:
        picked.append("nalsa")
    return {
        "reply": _safe(data.get("reply")),
        "follow_up": _safe(data.get("follow_up")),
        "steps": _clean(data.get("steps")),
        "proof": _clean(data.get("proof")),
        "need_lawyer": bool(data.get("need_lawyer")),
        "lawyer_reason": _safe(data.get("lawyer_reason")),
        "helplines": _helpline_text(dict.fromkeys(picked), hindi),
        "error": "",
    }


def _helpline_text(keys, hindi: bool) -> list[str]:
    sources = load_sources()
    out = []
    for key in keys:
        source_id, claim_id, hi, en = HELPLINES[key]
        # Only show a number whose claim is still present in the checked sources file.
        if any(c["id"] == claim_id for c in sources.get(source_id, {}).get("claims", [])):
            out.append(hi if hindi else en)
    return out


def speech_text(advice: dict, hindi: bool) -> str:
    if advice.get("error"):
        return ("माफ़ कीजिए, अभी जवाब नहीं मिल पाया। थोड़ी देर बाद फिर कोशिश करें। मुफ़्त कानूनी मदद के लिए 1 5 1 0 0 पर फ़ोन करें।"
                if hindi else "Sorry, no answer right now. Please try again. For free legal help call 1 5 1 0 0.")
    parts = [advice["reply"]]
    if advice["steps"]:
        parts.append("आप ये कर सकते हैं।" if hindi else "Here is what you can do.")
    parts += [f"{'कदम' if hindi else 'Step'} {i}. {s}" for i, s in enumerate(advice["steps"], 1)]
    if advice["proof"]:
        parts.append(("ये सबूत संभाल कर रखें: " if hindi else "Keep this proof: ") + ", ".join(advice["proof"]))
    if advice["need_lawyer"]:
        parts.append(("इसमें वकील की मदद ज़रूर लें। " if hindi else "Please get a lawyer's help. ") + advice["lawyer_reason"])
    parts += advice["helplines"]
    parts.append(advice["follow_up"])
    return " ".join(p for p in parts if p)


def to_audio(text: str, hindi: bool) -> bytes | None:
    """MP3 bytes via Google Translate TTS (free, needs internet). None on failure."""
    try:
        from gtts import gTTS
        buffer = BytesIO()
        gTTS(text[:3000], lang="hi" if hindi else "en", tld="co.in").write_to_fp(buffer)
        return buffer.getvalue()
    except Exception:  # network/library failure: page still shows the text
        return None


if __name__ == "__main__":
    class Fake:
        def generate_json(self, *a, **k):
            return {"reply": "Landlord kept deposit", "follow_up": "How much was it?",
                    "steps": ["Write to landlord", "Under Section 420 file case", "Keep receipts"],
                    "proof": ["Rent agreement"], "need_lawyer": False, "lawyer_reason": "", "helplines": ["consumer", "bogus"]}
    a = get_advice([{"role": "user", "content": "deposit nahi mila"}], False, Fake())
    assert a["steps"] == ["Write to landlord", "Keep receipts"], a["steps"]  # invented section dropped
    assert a["helplines"] == ["Consumer Helpline: 1915", "Free legal aid (NALSA): 15100"], a["helplines"]
    said = speech_text(a, False)
    assert "Step 2. Keep receipts" in said and said.endswith("How much was it?"), said
    later = get_advice([{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}, {"role": "user", "content": "c"}], False, Fake())
    assert later["helplines"] == ["Consumer Helpline: 1915"], later["helplines"]  # NALSA auto-added on first turn only
    print("ok")
