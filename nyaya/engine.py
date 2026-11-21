"""One shared conversation entry point for the UI, evaluation and unseen inputs.

The free demo uses intentionally bounded rules. A configured language model helps
extract messy stories; legal guidance and correspondence remain code-controlled.
"""

import re
from difflib import SequenceMatcher
from .llm import LLMAdapter, ALLOWED_FACTS
from .models import CaseRecord

MONEY = r"(?:₹\s*|rs\.?\s*|inr\s*|rupees?\s*)(\d+(?:,\d+)*(?:\.\d{1,2})?)"
UNKNOWN = re.compile(r"^(?:i\s+(?:do\s*not|don't|dont)\s+know|not\s+sure|unknown|skip|pata\s+nahi|malum\s+nahi|पता\s*नहीं|मालूम\s*नहीं)[.!\s]*$", re.I)
FAKE = re.compile(r"(?:fake|invent|made.up|fabricat|झूठ|फर्जी).{0,65}(?:law|section|penalty|धारा|कानून)|(?:law|section|penalty).{0,65}(?:fake|invent|made.up)|(?:section\s*999|धारा\s*999)|(?:guarantee|guaranteed).{0,35}(?:win|refund|compensation)", re.I)
LEGAL_REQUEST = re.compile(r"\b(?:add|cite|invoke|include|threaten|insert|claim)\b.{0,90}\b(?:section|statute|penalty|penalties|compensation|imprisonment)\b|(?:धारा|जुर्माना).{0,35}(?:जोड़|लिख|लगाओ)|(?:section|penalty).{0,35}(?:jodo|likho|lagao)", re.I)

QUESTIONS = {
    "deposit": ("How much deposit did you pay?", "आपने कितनी जमा राशि दी थी?", "Aapne kitna deposit diya tha?"),
    "moved_out": ("Have you moved out and returned the keys?", "क्या आपने घर खाली करके चाबी लौटा दी है?", "Kya aap ghar khaali karke keys de chuke hain?"),
    "deduction_explanation": ("Has the landlord explained any deductions in writing?", "क्या मकान मालिक ने कटौती का कारण लिखकर बताया है?", "Kya landlord ne deductions ka reason likh kar diya hai?"),
    "evidence": ("What records do you have, such as messages, receipts or an agreement?", "आपके पास कौन से रिकॉर्ड हैं, जैसे संदेश, रसीद या समझौता?", "Aapke paas kaun se records hain, jaise messages, receipt ya agreement?"),
    "pickup_status": ("Has the return been picked up, or is pickup still pending?", "क्या सामान वापस ले लिया गया है या पिकअप बाकी है?", "Kya return pickup ho gaya hai ya abhi pending hai?"),
    "approval_status": ("Has the seller confirmed that the refund was approved?", "क्या विक्रेता ने रिफंड मंजूर होने की पुष्टि की है?", "Kya seller ne refund approve hone ki confirmation di hai?"),
    "payment_status": ("Has the seller said the refund payment was issued?", "क्या विक्रेता ने कहा है कि रिफंड भेज दिया गया है?", "Kya seller ne kaha hai ki refund payment bhej di hai?"),
    "order_id": ("What is the order number, if you have it?", "अगर आपके पास है, तो ऑर्डर नंबर क्या है?", "Agar aapke paas hai, order number kya hai?"),
    "periods": ("Which salary periods have not been paid?", "किन महीनों या अवधियों का वेतन नहीं मिला है?", "Kaun se months ya periods ki salary nahi mili?"),
    "amount": ("What amount is unpaid, if you know?", "अगर आपको पता है, तो कितनी राशि बकाया है?", "Agar pata hai, kitni amount unpaid hai?"),
    "prior_communication": ("Have you already written to payroll or your employer about this?", "क्या आपने इस बारे में पेरोल या नियोक्ता को पहले लिखा है?", "Kya aapne payroll ya employer ko pehle likha hai?"),
    "notice_text": ("Please paste the notice text, removing personal details you do not want to share.", "कृपया नोटिस का पाठ पेस्ट करें। जो निजी जानकारी साझा नहीं करना चाहते, उसे हटा दें।", "Notice ka text paste karein; jo personal details share nahi karni, hata dein."),
    "goal": ("What outcome would you like help with?", "आप किस नतीजे के लिए मदद चाहते हैं?", "Aap kis result ke liye help chahte hain?"),
}
GOALS = {"rental": "Request the deposit balance or a written deduction statement",
         "refund": "Clarify the refund status and request resolution",
         "salary": "Request payment and a written salary reconciliation",
         "notice": "Understand the notice and prepare questions for a qualified lawyer",
         "other": "Organize the problem and prepare questions for a lawyer"}


def lang_index(language: str) -> int:
    value = language.lower()
    return 2 if "hinglish" in value else 1 if "hindi" in value or "हिन्दी" in value or "हिंदी" in value else 0


def choose(case: CaseRecord, values: tuple[str, str, str]) -> str:
    return values[lang_index(case.conversation_language)]


def _money(text: str) -> list[str]:
    # A correction marker after an earlier amount supersedes that earlier amount.
    markers = list(re.finditer(r"\b(?:actually|correction|corrected|correct|meant|instead)\b", text, re.I))
    if markers and re.search(MONEY, text[:markers[-1].start()], re.I):
        text = text[markers[-1].end():]
    values = ["₹" + m.group(1) for m in re.finditer(MONEY, text, re.I)
              if not re.search(r"\bnot\s*$", text[max(0, m.start() - 8):m.start()], re.I)]
    if not values:
        values = ["₹" + m.group(1) for m in re.finditer(r"([\d,]+)\s*(?:rupees|रुपये|रुपए)", text, re.I)]
    return values


def _append_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value and value not in target:
            target.append(value)


# Evidence is a collection of reported records, not arbitrary factual sentences.
# A valid verbatim model excerpt can still be assigned the wrong semantic role.
RECORD_PATTERNS = [
    ("employment letter", r"\b(?:employment|appointment|offer)\s+letters?\b|नियुक्ति\s*पत्र|रोजगार\s*पत्र"),
    ("bank statement", r"\bbank\s+statements?\b|बैंक\s*स्टेटमेंट"),
    ("bank transfer record", r"\bbank\s+transfers?\b|बैंक\s*ट्रांसफर"),
    ("payment proof", r"\bpayment\s+(?:proof|confirmation|records?)\b|भुगतान\s*(?:प्रमाण|सबूत)"),
    ("WhatsApp messages", r"\bWhatsApp(?:\s+(?:messages?|chats?))?\b|व्हाट्स(?:ऐप|एप)(?:\s+(?:संदेश|चैट))?"),
    ("agreement", r"\b(?:(?:rental|rent|tenancy|employment)\s+)?(?:agreements?|contracts?)\b|समझौता|किरायानामा|अनुबंध|एग्रीमेंट"),
    ("receipt", r"\b(?:(?:deposit|payment|pickup|return)\s+)?receipts?\b|रसीद(?:ें|ों)?"),
    ("payslips", r"\b(?:payslips?|pay\s+slips?|salary\s+slips?|wage\s+slips?)\b|वेतन\s*पर्ची|तनख्वाह\s*पर्ची|पेस्लिप"),
    ("screenshots", r"\bscreenshots?\b|स्क्रीनशॉट"),
    ("photographs", r"\b(?:(?:checkout|check-out|move[- ]?out|handover)\s+)?(?:photographs?|photos?|pictures?)\b|फोटो|तस्वीर(?:ें|ों)?"),
    ("email correspondence", r"\be-?mails?\b|\bemailed\b|ईमेल|इमेल"),
    ("SMS messages", r"\bSMS\b|एसएमएस"),
    ("messages", r"\bmessages?\b|\bmessaged\b|संदेश"),
    ("recording", r"\b(?:(?:audio|video|call)\s+)?recordings?\b|रिकॉर्डिंग"),
    ("order confirmation", r"\border\s+confirmation\b|ऑर्डर\s*पुष्टि"),
]
RECORD_QUALIFIERS = r"(?:(?:a|an|any|the|my|our|some|original|actual|written|supporting|digital|valid|copy|copies|rental|deposit|payment|pickup|return|bank|employment|salary)\s+)*"
RECORD_NEGATIVE_BEFORE = re.compile(
    r"(?:\b(?:no|without)\s+|\b(?:don.t|do\s+not|haven.t|have\s+not|doesn.t|does\s+not)\s+(?:have|hold|possess|keep|got)\s+|"
    r"\bno\s+longer\s+have\s+|\b(?:lost|cannot\s+find|can.t\s+find)\s+)" + RECORD_QUALIFIERS + r"$", re.I)
RECORD_NEGATIVE_AFTER = re.compile(
    r"^\s*(?:(?:is|are|was|were)\s+)?(?:not\s+available|unavailable|missing|lost)\b|"
    r"^\s*(?:मेरे\s+पास\s+|हमारे\s+पास\s+)?(?:नहीं|नही|nahi|nahin)(?=\s|[.!?।,]|$)", re.I)
RECORD_FUTURE_BEFORE = re.compile(
    r"(?:\b(?:write|draft|prepare|create|compose|send|obtain|request|produce|gather)\s+|\bask\s+for\s+)"
    r"(?:(?:a|an|the|me|my|some|new|formal|complaint|request|factual|supporting|any)\s+)*$|"
    r"(?:कृपया|मुझे).{0,30}(?:लिख|तैयार|चाहिए)", re.I)


def _record_mentions(text: str) -> list[tuple[str, bool, bool]]:
    """Return (record label, negated, available) with local negation scope."""
    mentions = []
    clauses = re.split(r"(?<=[.!?।;])\s+|\n+|\b(?:but|however|although|lekin|magar)\b|लेकिन|परंतु|मगर", text, flags=re.I)
    for clause in clauses:
        candidates = []
        for label, pattern in RECORD_PATTERNS:
            for match in re.finditer(pattern, clause, re.I):
                candidates.append((match.start(), match.end(), label))
        candidates.sort(key=lambda item: (item[0], -(item[1] - item[0])))
        previous_end, previous_negative = -1, False
        for start, end, label in candidates:
            if start < previous_end:
                continue  # Prefer "WhatsApp messages" to a second "messages".
            before, after = clause[:start], clause[end:]
            inherited_negative = previous_negative and bool(re.fullmatch(r"[\s,]*(?:(?:and|or|aur|ya|और|या)[\s,]*)?", clause[previous_end:start], re.I))
            negative = bool(RECORD_NEGATIVE_BEFORE.search(before) or RECORD_NEGATIVE_AFTER.search(after) or inherited_negative)
            future = bool(RECORD_FUTURE_BEFORE.search(before))
            # An unconfirmed question about obtaining a record is not possession.
            if "?" in clause and re.search(r"\b(?:do|should|can|could)\s+(?:I|we).{0,25}(?:need|get|obtain|find)\b", clause, re.I):
                future = True
            mentions.append((label, negative, not negative and not future))
            previous_end, previous_negative = end, negative
    return mentions


def _clean_record_labels(values: list[str]) -> list[str]:
    clean = []
    for text in values:
        for label, _negative, available in _record_mentions(text):
            if available:
                _append_unique(clean, [label])
    return clean


class CaseEngine:
    def __init__(self, adapter: LLMAdapter | None = None) -> None:
        self.adapter = adapter or LLMAdapter()

    def process(self, case: CaseRecord, user_text: str) -> str:
        text = user_text.strip()[:20000]
        if not text:
            return choose(case, ("Please describe what happened.", "कृपया बताएं कि क्या हुआ।", "Batayein kya hua."))
        case.messages.append({"role": "user", "content": text})
        if FAKE.search(text) or LEGAL_REQUEST.search(text):
            reply = choose(case, (
                "I cannot add an invented legal section, penalty or guaranteed result. I can help write a factual request using the details you provide.",
                "मैं मनगढ़ंत कानूनी धारा, जुर्माना या निश्चित नतीजा नहीं जोड़ सकता। आपके बताए तथ्यों के आधार पर अनुरोध लिखने में मदद कर सकता हूँ।",
                "Main fake legal section, penalty ya guaranteed result add nahi kar sakta. Aapke facts se ek factual request likh sakta hoon."))
            case.messages.append({"role": "assistant", "content": reply})
            return reply
        before = self._material(case)
        unknown_answer = bool(UNKNOWN.fullmatch(text) and case.last_field)
        if unknown_answer:
            _append_unique(case.skipped_fields, [case.last_field])
            _append_unique(case.unknowns, [case.last_field])
        else:
            extracted = self.adapter.extract(case.messages, case.facts)
            case.provider_status = self.adapter.status
            self._extract_rules(case, text)
            self._merge_model(case, extracted, text)
            if case.kind == "notice" and "notice_text" not in case.facts and len(text) > 90:
                self._read_notice(case, text)
        if self._material(case) != before:
            case.revision += 1
            case.pending_draft = None
            case.pending_generated_draft = None
        question = self._next_question(case)
        changed_draft = bool(case.draft and case.draft_revision != case.revision)
        prefix = self._acknowledgement(case, unknown_answer=unknown_answer)
        if changed_draft:
            prefix += " " + choose(case, ("Your existing draft is now out of date; review a refreshed draft before using it.", "पुराना ड्राफ्ट अब अद्यतन नहीं है; इस्तेमाल से पहले नया ड्राफ्ट जांचें।", "Purana draft ab outdated hai; use karne se pehle refreshed draft review karein."))
        if question:
            reply = prefix + "\n\n" + question
        else:
            reply = prefix + "\n\n" + choose(case, (
                "You can prepare a factual draft now. Missing details will appear in brackets; review them before sending.",
                "अब तथ्यों पर आधारित ड्राफ्ट बना सकते हैं। अधूरी जानकारी कोष्ठक में होगी; भेजने से पहले जांचें।",
                "Ab factual draft bana sakte hain. Missing details brackets mein hongi; bhejne se pehle review karein."))
        case.messages.append({"role": "assistant", "content": reply})
        return reply

    @staticmethod
    def _material(case: CaseRecord) -> tuple:
        return (case.kind, case.goal, tuple(sorted(case.facts.items())), tuple(case.evidence), tuple(case.allegations), tuple(case.notice_quotes), tuple(case.skipped_fields))

    @staticmethod
    def _acknowledgement(case: CaseRecord, *, unknown_answer: bool = False) -> str:
        """A grounded conversational response without a second legal-prose model call."""
        if unknown_answer:
            return choose(case, (
                "That’s okay. I’ll leave that detail unknown and work with what you do know.",
                "कोई बात नहीं। उस जानकारी को अज्ञात रखकर, जो आपको पता है उससे आगे बढ़ते हैं।",
                "Koi baat nahi. Us detail ko unknown rakhte hain aur jo aapko pata hai usse aage badhte hain."))
        acknowledgements = {
            "rental": ("Let’s organise your deposit issue and prepare a clear factual request.",
                       "जमा राशि से जुड़े आपके मामले के तथ्य व्यवस्थित करके एक स्पष्ट अनुरोध तैयार करते हैं।",
                       "Aapke deposit ke facts organise karke ek clear factual request taiyar karte hain."),
            "refund": ("We’ll keep return pickup, refund approval and payment separate so the request reflects the actual status.",
                       "पिकअप, रिफंड की मंजूरी और भुगतान को अलग रखेंगे, ताकि अनुरोध में सही स्थिति लिखी जाए।",
                       "Pickup, refund approval aur payment ko alag rakhenge, taaki request mein actual status aaye."),
            "salary": ("Let’s organise the salary periods and amount you report as unpaid before preparing a request to your employer.",
                       "नियोक्ता को अनुरोध तैयार करने से पहले, आपके बताए बकाया वेतन की अवधि और रकम व्यवस्थित करते हैं।",
                       "Employer ko request taiyar karne se pehle, aapke bataye unpaid salary periods aur amount organise karte hain."),
            "notice": ("I’ll keep the sender’s allegations separate from your account. A qualified lawyer should review a formal notice promptly.",
                       "भेजने वाले के आरोप आपके बताए तथ्यों से अलग रखूंगा। औपचारिक नोटिस की जल्द योग्य वकील से समीक्षा कराएं।",
                       "Sender ke allegations ko aapke account se alag rakhenge. Formal notice ko jaldi qualified lawyer se review karayein."),
            "other": ("I can help organise your account and prepare questions for a qualified lawyer. This issue is outside the prototype’s verified guidance.",
                      "आपका विवरण व्यवस्थित करके योग्य वकील के लिए प्रश्न तैयार कर सकता हूँ। इस विषय पर प्रोटोटाइप में सत्यापित मार्गदर्शन उपलब्ध नहीं है।",
                      "Aapka account organise karke qualified lawyer ke liye questions taiyar kar sakta hoon. Yeh issue prototype ki verified guidance se bahar hai."),
        }
        prefix = choose(case, acknowledgements.get(case.kind, acknowledgements["other"]))
        amount_key = "deposit" if case.kind == "rental" else "amount"
        amount = case.facts.get(amount_key, "")
        # Only echo a compact explicit currency value, not arbitrary model/user prose.
        if case.kind in {"rental", "refund", "salary"} and re.fullmatch(r"₹[\d,]+(?:\.\d{1,2})?", amount):
            prefix += " " + choose(case, (
                f"Amount recorded from your account: {amount}.",
                f"आपके विवरण में दर्ज राशि: {amount}।",
                f"Aapke account se recorded amount: {amount}."))
        return prefix

    @staticmethod
    def _merge_model(case: CaseRecord, data: dict, latest_text: str = "") -> None:
        previous_kind = case.kind
        if data.get("kind") and (data["kind"] != "other" or len(case.messages) == 1):
            case.kind = data["kind"]
        if case.kind != previous_kind and case.goal in GOALS.values():
            case.goal = GOALS.get(case.kind, GOALS["other"])
        if data.get("goal") and (not case.goal or not latest_text or data["goal"] in latest_text):
            case.goal = data["goal"]
            if case.kind == "other":
                case.facts["goal_answered"] = "yes"
        proposed_facts = data.get("facts", {})
        if case.kind == "notice":
            # Exact excerpts can still be assigned the wrong meaning by a model.
            # Sender, dates and allegations are derived from the pasted notice
            # by code, never from a user's introductory or later dispute text.
            derived = {"notice_text", "sender", "requested_action", "response_date", "notice_date"}
            proposed_facts = {key: value for key, value in proposed_facts.items() if key not in derived}
        for key, value in proposed_facts.items():
            if not isinstance(value, str) or not value.strip():
                continue
            # A model sees conversation history. It must not resurrect a historical
            # amount or party after a correction or manual edit in a later turn.
            if latest_text and key in case.facts and value not in latest_text:
                continue
            if key in {"deposit", "amount", "deductions"}:
                explicit = _money(value)
                if not explicit and re.fullmatch(r"[\d,]+(?:\.\d{1,2})?", value.strip()):
                    explicit = ["₹" + value.strip()]
                if key != "deductions" and len(explicit) > 1:
                    continue  # A paragraph with multiple amounts is not one amount.
                current = _money(latest_text)
                if explicit and current and key != "deductions":
                    if re.sub(r"\D", "", explicit[0]) not in {re.sub(r"\D", "", v) for v in current}:
                        continue  # Exclude the negated old amount in “new, not old”.
                value = ", ".join(explicit) if explicit else value.strip()
            if key == "deduction_explanation":
                value = CaseEngine._deduction_explanation(value)
            case.facts[key] = value
            if value and not UNKNOWN.fullmatch(value):
                for unresolved in (case.unknowns, case.skipped_fields):
                    if key in unresolved:
                        unresolved.remove(key)
        # The model's evidence array is deliberately not ingested. Exact wording
        # alone does not make a salary amount or accusation a supporting record.

    @staticmethod
    def _deduction_explanation(value: str) -> str:
        lower = value.lower()
        if re.search(r"no\s+(?:written\s+)?(?:explanation|reason|deduction|breakdown)|without.{0,15}(?:explanation|reason)|(?:नहीं|nahi|nahin).{0,15}(?:बताया|दिया|bataya|diya)|(?:कारण|विवरण|reason|explanation).{0,30}(?:नहीं|nahi|nahin)", lower):
            return "No explanation provided"
        if re.search(r"unknown|not sure|(?:don.t|do not) know|पता\s*नहीं|नहीं\s*पता", lower):
            return "Unknown"
        if re.search(r"written|in writing|email|whatsapp|लिखित|लिखकर|लिख कर|ईमेल|व्हाट्सऐप", lower):
            return "Written deductions provided"
        return value

    def _extract_rules(self, case: CaseRecord, text: str) -> None:
        lower = text.lower()
        old_kind = case.kind
        if re.search(r"\bnotice\b|legal notice|नोटिस", lower):
            case.kind = "notice"
        elif re.search(r"deposit|landlord|\brent(?:al)?\b|मकान|जमा राशि|किराय|security money", lower):
            case.kind = "rental"
        elif re.search(r"refund|seller|return pickup|order\b|रिफंड|विक्रेता|ऑर्डर", lower):
            case.kind = "refund"
        elif re.search(r"salary|payroll|employer|वेतन|तनख्वाह|सैलरी", lower):
            case.kind = "salary"
        if not case.goal or old_kind != case.kind:
            case.goal = GOALS[case.kind]
        amounts = _money(text)
        # Save the original story verbatim, rather than pretending the demo understood everything.
        if "summary" not in case.facts:
            case.facts["summary"] = text
        correction = bool(re.search(r"actually|correction|correct|instead|not .+ but|गलती|सुधार|असल|sahi|galat", lower))
        if case.kind == "rental":
            if amounts:
                only_deduction = bool(re.search(r"deduct|कटौती|kaat|काट", lower)) and not re.search(r"deposit|जमा", lower)
                if only_deduction:
                    case.facts["deductions"] = ", ".join(amounts)
                else:
                    case.facts["deposit"] = amounts[0]
                    if len(amounts) > 1:
                        case.facts["deductions"] = ", ".join(amounts[1:])
            if re.search(r"(?:not|haven.t|abhi|नहीं).{0,20}(?:moved out|vacat|khaali|खाली)|still living|अभी रहता", lower):
                case.facts["moved_out"] = "Not yet moved out"
            elif re.search(r"moved out|move\s*out.{0,20}(?:kar|kiya|ho)|vacated|returned.{0,10}keys|keys.{0,10}returned|khaali|khali|खाली कर|चाबी.*लौटा", lower):
                case.facts["moved_out"] = "Moved out / keys returned as described by user"
            no_reason = re.search(r"no\s+(?:written\s+)?(?:explanation|reason|deduction|breakdown)|without.{0,15}(?:explanation|reason)|(?:nahi|nahin|नहीं).{0,15}(?:bataya|diya|दिया|बताया)|(?:reason|explanation|breakdown).{0,25}(?:nahi|nahin|नहीं)", lower)
            if no_reason:
                case.facts["deduction_explanation"] = "No explanation provided"
            elif re.search(r"deduct|कटौती|kaat|काट|painting|cleaning", lower) and re.search(r"writ|email|whatsapp|message|लिख|संदेश|भेज|likh", lower):
                case.facts["deduction_explanation"] = "Written deductions provided"
                case.facts["landlord_message"] = text
            elif re.search(r"deduct|कटौती|kaat|काट", lower):
                case.facts["deduction_explanation"] = case.facts.get("deduction_explanation", "")
        elif case.kind == "refund":
            if amounts:
                case.facts["amount"] = amounts[0]
            order = re.search(r"(?:order\s*(?:id|number|no\.?|#)?|ऑर्डर)\s*[:#-]?\s*([A-Z0-9][A-Z0-9_-]{3,})", text, re.I)
            if order:
                case.facts["order_id"] = order.group(1)
            if re.search(r"pickup.{0,20}(?:pending|not done|nahi|नहीं)|not.{0,15}picked|पिकअप.*बाकी", lower):
                case.facts["pickup_status"] = "Pickup pending"
            elif re.search(r"picked\s*up|pickup.{0,15}(?:done|confirmed|complete|ho gaya)|collected|पिकअप.*(?:हो गया|पूरा)|वापस ले लिया", lower):
                case.facts["pickup_status"] = "Pickup confirmed"
            if re.search(r"(?:approval|approved|approve).{0,30}(?:unknown|not sure|don.t know|do not know|nahi pata)|(?:don.t know|do not know|not sure|unknown|no idea|whether|\bif\b|hasn.t told|not told).{0,85}(?:approv)|(?:मंजूर|स्वीकृत).{0,75}(?:पता\s*नहीं|नहीं\s*पता|मालूम\s*नहीं|नहीं\s*मालूम)", lower):
                case.facts["approval_status"] = "Unknown"
            elif re.search(r"not.{0,8}approv|approval.{0,12}pending|approve nahi|(?:मंजूर|स्वीकृत).{0,15}नहीं|मंजूरी.{0,15}(?:बाकी|लंबित|नहीं)", lower):
                case.facts["approval_status"] = "Not confirmed / pending"
            elif re.search(r"refund.{0,15}approv|approv.{0,15}refund|रिफंड मंजूर", lower):
                case.facts["approval_status"] = "Refund approved according to user"
            if re.search(r"(?:seller|merchant|they).{0,35}(?:issued|processed|sent).{0,20}(?:refund|payment)|refund.{0,20}(?:issued|processed|sent)", lower):
                case.facts["payment_status"] = "Seller says refund issued; receipt not independently verified"
            elif re.search(r"not received|never came|nahi aaya|नहीं मिला", lower):
                case.facts["payment_status"] = "User has not received refund; issue status unknown"
        elif case.kind == "salary":
            if amounts:
                case.facts["amount"] = amounts[0]
            period_text = text
            if case.last_field != "periods":
                # Dates of reminder emails are not automatically unpaid periods.
                period_text = re.split(r"\b(?:i\s+)?(?:emailed|wrote|messaged)\b|ईमेल|मैंने लिखा", text, maxsplit=1, flags=re.I)[0]
                if "periods" in case.facts and not re.search(r"salary|unpaid|not paid|वेतन|तनख्वाह|सैलरी", period_text, re.I):
                    period_text = ""
            months = re.findall(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:\s+20\d{2})?\b|जनवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितंबर|अक्टूबर|नवंबर|दिसंबर", period_text, re.I)
            if months:
                case.facts["periods"] = ", ".join(months)
            if re.search(r"(?:haven.t|have not|not|never|nahi|नहीं).{0,20}(?:written|email|emailed|likha|लिख)|(?:email|likha|लिख).{0,15}(?:nahi|नहीं)", lower):
                case.facts["prior_communication"] = "No prior written communication reported"
            elif re.search(r"emailed|wrote|written to|messaged|email ki|ईमेल|लिखा", lower):
                communication = re.search(r"(?:I\s+)?(?:emailed|wrote|written to|messaged|email ki|ईमेल|लिखा)[^\n.!?।]*", text, re.I)
                case.facts["prior_communication"] = communication.group(0).strip() if communication else "Prior written communication reported"
        elif case.kind == "notice":
            if "notice_text" not in case.facts and (len(text) > 90 or re.search(r"sender:|from:|allege|pay|दावा", lower)):
                self._read_notice(case, text)
        # A short direct reply can answer the last question. Full stories use extracted fields.
        if case.last_field and len(text) <= 450 and not correction:
            field = case.last_field
            if field == "evidence":
                if not any(available for _label, _negative, available in _record_mentions(text)) and re.search(r"\b(?:no|none|nothing)\b|कोई.*नहीं|कुछ.*नहीं|nahi|nahin", text, re.I):
                    _append_unique(case.skipped_fields, ["evidence"])
                    _append_unique(case.unknowns, ["evidence"])
            elif field == "goal":
                case.goal = text
                case.facts["goal_answered"] = "yes"
            elif field == "notice_text" and case.kind == "notice" and "notice_text" not in case.facts:
                self._read_notice(case, text)
            elif field not in case.facts or not case.facts[field]:
                case.facts[field] = text
        case.evidence = _clean_record_labels(case.evidence)
        for label, negative, available in _record_mentions(text):
            if negative:
                case.evidence = [item for item in case.evidence if item != label]
            elif available:
                _append_unique(case.evidence, [label])
        if case.evidence:
            for unresolved in (case.unknowns, case.skipped_fields):
                if "evidence" in unresolved:
                    unresolved.remove("evidence")
        for key in list(case.facts):
            if case.facts[key] and key in case.unknowns and case.facts[key].lower() != "unknown":
                case.unknowns.remove(key)

    @staticmethod
    def _read_notice(case: CaseRecord, text: str) -> None:
        case.facts["notice_text"] = text
        header = re.search(r"(?:^|\n)\s*(?:LEGAL NOTICE\b|From\s*:|Sender\s*:)|(?:notice\s*:\s*)(?=From\s*:)", text, re.I)
        notice_body = text[header.start():] if header else text
        sentences = [x.strip() for x in re.split(r"(?<=[.!?।])\s+|\n+", notice_body) if x.strip()]
        user_context = re.compile(r"^(?:I\s+(?:dispute|deny|say|do not accept|don't accept|have not accepted)|मैं\s+(?:इस|यह|इन)).*", re.I)
        user_sentences = [s for s in sentences if user_context.match(s)]
        if header and text[:header.start()].strip():
            user_sentences.insert(0, text[:header.start()].strip())
        if user_sentences:
            case.facts["user_account"] = "\n".join(user_sentences)
        sentences = [s for s in sentences if not user_context.match(s)]
        notice_body = "\n".join(sentences)
        sender = re.search(r"(?:sender|from|भेजने वाला)\s*:\s*([^\n]+)", notice_body, re.I)
        if sender:
            case.facts["sender"] = sender.group(1).strip().rstrip(".")
        for sentence in sentences:
            if re.search(r"alleg|claim|owe|outstanding|debt|due|बकाया|दावा|कर्ज", sentence, re.I):
                _append_unique(case.allegations, [sentence])
                _append_unique(case.notice_quotes, [sentence])
            if re.search(r"\b(?:pay|respond|reply|appear|provide|demand|contact|return)\b|भुगतान|जवाब|उपस्थित", sentence, re.I):
                case.facts.setdefault("requested_action", sentence)
                _append_unique(case.notice_quotes, [sentence])
        # Record only a deadline explicitly tied to a requested action, verbatim.
        deadline = re.search(r"\b(?:within\s+\d+\s+(?:working\s+)?days?|(?:respond|reply|pay|appear).{0,25}\bby\s+[^.\n;]+)|\d+\s*दिन.{0,8}भीतर", notice_body, re.I)
        case.facts["response_date"] = deadline.group(0) if deadline else "Not stated in the pasted notice"
        if deadline:
            _append_unique(case.notice_quotes, [deadline.group(0)])
        date = re.search(r"(?:dated|date)\s*:\s*([^\n]+)", notice_body, re.I)
        if date:
            case.facts["notice_date"] = date.group(1).strip()

    def _next_question(self, case: CaseRecord) -> str | None:
        fields = {
            "rental": ["deposit", "moved_out", "deduction_explanation", "evidence"],
            "refund": ["pickup_status", "approval_status", "payment_status", "order_id"],
            "salary": ["periods", "amount", "prior_communication", "evidence"],
            "notice": ["notice_text"], "other": ["goal", "evidence"],
        }[case.kind]
        for field in fields:
            known = bool(case.evidence) if field == "evidence" else bool(case.facts.get("goal_answered")) if field == "goal" else bool(case.facts.get(field))
            if not known and field not in case.skipped_fields:
                case.last_field = field
                case.last_question = choose(case, QUESTIONS[field])
                return case.last_question
        case.last_field = None
        case.last_question = None
        return None

    def update_facts(self, case: CaseRecord, patch: dict[str, str]) -> None:
        changed = False
        if case.kind == "notice" and "notice_text" in patch and patch["notice_text"] != case.facts.get("notice_text", ""):
            for field in ("sender", "requested_action", "response_date", "notice_date", "user_account"):
                case.facts.pop(field, None)
            case.allegations.clear()
            case.notice_quotes.clear()
            new_notice = patch["notice_text"].strip()[:20000]
            if new_notice:
                self._read_notice(case, new_notice)
            else:
                case.facts.pop("notice_text", None)
            changed = True
        for key, value in patch.items():
            if key not in ALLOWED_FACTS or not isinstance(value, str):
                continue
            value = value.strip()[:20000 if key == "notice_text" else 1200]
            if case.kind == "notice" and key in {"sender", "requested_action", "response_date", "notice_date"}:
                # Derived wording must come from the current notice, not a stale
                # editor snapshot accompanying an updated pasted document.
                continue
            if value and not UNKNOWN.fullmatch(value):
                for unresolved in (case.unknowns, case.skipped_fields):
                    if key in unresolved:
                        unresolved.remove(key)
                        changed = True
            if value != case.facts.get(key, ""):
                if value:
                    case.facts[key] = value
                else:
                    case.facts.pop(key, None)
                changed = True
        if changed:
            case.revision += 1
            case.pending_draft = None
            case.pending_generated_draft = None
            self._next_question(case)

    def save_manual_draft(self, case: CaseRecord, text: str) -> None:
        if text != case.draft:
            if not case.generated_draft:
                case.generated_draft = case.draft
            case.draft = text
            case.manually_edited = True
            case.pending_draft = None
            case.pending_generated_draft = None

    @staticmethod
    def apply_pending(case: CaseRecord) -> None:
        if case.pending_draft is not None:
            case.draft = case.pending_draft
            case.generated_draft = case.pending_generated_draft or case.pending_draft
            case.draft_revision = case.revision
            case.pending_draft = None
            case.pending_generated_draft = None
            case.manually_edited = case.draft != case.generated_draft

    def draft(self, case: CaseRecord) -> str:
        # Also protect sessions created before the stricter evidence ingestion.
        clean_evidence = _clean_record_labels(case.evidence)
        if clean_evidence != case.evidence:
            case.evidence = clean_evidence
            case.revision += 1
        result = self._render_draft(case)
        if case.manually_edited and case.draft:
            case.pending_generated_draft = result
            case.pending_draft = self._preserve_edits(case.generated_draft, case.draft, result)
            return case.pending_draft
        else:
            case.draft = result
            case.generated_draft = result
            case.draft_revision = case.revision
            case.manually_edited = False
        return result

    @staticmethod
    def _preserve_edits(base: str, edited: str, refreshed: str) -> str:
        """Reapply manual text edits to a refresh; the UI always previews this merge.

        Character alignment maps the original generation to new facts. This is a
        prototype merge, so users must inspect overlapping fact/wording changes.
        """
        if not base:
            return refreshed + "\n\n[Previous manual text for review]\n" + edited
        mapping = SequenceMatcher(None, base, refreshed, autojunk=False).get_opcodes()
        def position(index: int, right: bool = False) -> int:
            if index == len(base):
                return len(refreshed)
            for tag, i1, i2, j1, j2 in mapping:
                if i1 <= index < i2 or i1 == i2 == index:
                    if tag == "equal":
                        return j1 + index - i1
                    return j2 if right else j1
            return len(refreshed)
        changes = SequenceMatcher(None, base, edited, autojunk=False).get_opcodes()
        result = refreshed
        for tag, i1, i2, j1, j2 in reversed(changes):
            if tag != "equal":
                start, end = position(i1), position(i2, right=True)
                result = result[:start] + edited[j1:j2] + result[end:]
        return result

    @staticmethod
    def _render_draft(case: CaseRecord) -> str:
        f = case.facts
        hindi = lang_index(case.document_language) == 1
        hinglish = lang_index(case.document_language) == 2
        localized_statuses = {
            "Pickup confirmed": ("Pickup confirmed", "पिकअप की पुष्टि है", "Pickup confirm hai"),
            "Pickup pending": ("Pickup pending", "पिकअप बाकी है", "Pickup abhi pending hai"),
            "Refund approved according to user": ("Refund approved according to user", "आपके बताए अनुसार रिफंड मंजूर है", "Aapke mutabik refund approve hai"),
            "Not confirmed / pending": ("Not confirmed / pending", "पुष्टि नहीं हुई / लंबित", "Confirmation nahi hui / pending"),
            "Seller says refund issued; receipt not independently verified": (
                "Seller says refund issued; receipt not independently verified",
                "विक्रेता का कहना है कि रिफंड भेजा गया है; प्राप्ति की स्वतंत्र पुष्टि नहीं है",
                "Seller ke mutabik refund bheja gaya hai; receipt independently verify nahi hui"),
            "User has not received refund; issue status unknown": (
                "User has not received refund; issue status unknown",
                "आपको रिफंड नहीं मिला है; भेजे जाने की स्थिति अज्ञात है",
                "Aapko refund nahi mila; payment bhejne ka status unknown hai"),
            "Not yet moved out": ("Not yet moved out", "अभी घर खाली नहीं किया है", "Abhi move out nahi kiya"),
            "Moved out / keys returned as described by user": (
                "Moved out / keys returned as described by user",
                "आपके बताए अनुसार घर खाली करने / चाबी लौटाने की स्थिति",
                "Aapke bataye mutabik move-out / keys return ki sthiti"),
            "No prior written communication reported": (
                "No prior written communication reported", "पहले लिखित संपर्क की जानकारी नहीं दी गई है",
                "Pehle written communication report nahi hui"),
            "Not stated in the pasted notice": (
                "Not stated in the pasted notice", "पेस्ट किए गए नोटिस में नहीं लिखी है",
                "Pasted notice mein nahi likhi hai"),
        }
        def value(key: str, placeholder: str) -> str:
            known = f.get(key, "")
            if not known or UNKNOWN.fullmatch(known):
                return "[" + placeholder + "]"
            if known in localized_statuses:
                return localized_statuses[known][lang_index(case.document_language)]
            return known
        name = value("user_name", "आपका नाम" if hindi else "your name")
        other = value("other_party", "प्राप्तकर्ता" if hindi else "recipient")
        if case.kind == "rental":
            deposit = value("deposit", "जमा राशि" if hindi else "deposit amount")
            move = value("moved_out", "घर खाली करने और चाबी लौटाने की स्थिति" if hindi else "move-out and key-return status")
            explanation = f.get("deduction_explanation", "").lower()
            written = "written deductions" in explanation or "provided" in explanation and "no explanation" not in explanation
            if hindi:
                body = f"विषय: जमा राशि का हिसाब और शेष राशि के लिए अनुरोध\n\nप्रिय {other},\n\nमेरे रिकॉर्ड के अनुसार मैंने {deposit} जमा किए थे। घर खाली करने की स्थिति: {move}।\n\n"
                body += "आपके लिखित कटौती विवरण के संबंध में, कृपया प्रत्येक मद का आधार और उपलब्ध रसीदें साझा करें तथा शेष राशि का हिसाब बताएं।" if written else "कृपया जमा राशि लौटाने की स्थिति बताएं। यदि कोई कटौती प्रस्तावित है, तो प्रत्येक मद, राशि और आधार का लिखित विवरण साझा करें।"
                body += " कृपया शेष राशि लौटाने की प्रस्तावित तारीख भी बताएं।"
            elif hinglish:
                body = f"Subject: Deposit ka hisaab aur balance return karne ka request\n\nDear {other},\n\nMere records ke mutabik maine {deposit} deposit diya tha. Move-out status: {move}.\n\n"
                body += "Aapke written deductions ke liye har item ka basis aur available receipts share karein, aur balance ka hisaab batayein." if written else "Deposit return ka status batayein. Koi deduction propose kar rahe hain toh item, amount aur reason ka written breakdown share karein."
                body += " Balance return ki proposed date bhi batayein."
            else:
                body = f"Subject: Request for deposit reconciliation and return of balance\n\nDear {other},\n\nAccording to my records, I paid a deposit of {deposit}. Move-out/key-return status: {move}.\n\n"
                body += "Regarding the written deductions you provided, please share the basis and available receipts for each item, reconcile the deductions, and confirm the remaining balance." if written else "Please confirm the status of my deposit return. If you propose any deductions, please provide an itemized written statement showing each amount and its basis."
                if f.get("deductions"):
                    body += f" Deductions mentioned: {f['deductions']}."
                body += " Please also confirm the proposed date for returning the balance."
            if f.get("deductions") and hindi:
                body += f" उल्लिखित कटौतियाँ: {f['deductions']}।"
            elif f.get("deductions") and hinglish:
                body += f" Batayi gayi deductions: {f['deductions']}."
        elif case.kind == "refund":
            order, amount = value("order_id", "ऑर्डर नंबर" if hindi else "order number"), value("amount", "राशि" if hindi else "amount")
            pickup, approval, payment = (value(k, "स्थिति अज्ञात है" if hindi else "status not known") for k in ("pickup_status", "approval_status", "payment_status"))
            if hindi:
                body = f"विषय: ऑर्डर {order} के रिफंड की स्थिति\n\nप्रिय {other},\n\nमेरे ऑर्डर {order}, राशि {amount}, की स्थिति स्पष्ट करें। मेरे रिकॉर्ड:\nपिकअप: {pickup}\nरिफंड मंजूरी: {approval}\nभुगतान: {payment}\n\nकृपया मंजूरी की स्थिति और अगला कदम लिखकर बताएं। यदि भुगतान भेज दिया है, तो तारीख और लेनदेन संदर्भ साझा करें ताकि मैं अपने रिकॉर्ड से मिलान कर सकूं।"
            elif hinglish:
                body = f"Subject: Order {order} ka refund status\n\nDear {other},\n\nOrder {order}, amount {amount}, ka status clear karein. Mere records:\nPickup: {pickup}\nRefund approval: {approval}\nPayment: {payment}\n\nApproval status aur next step written mein batayein. Agar payment bhej di hai, date aur transaction reference share karein taaki main records check kar sakun."
            else:
                body = f"Subject: Refund status clarification for order {order}\n\nDear {other},\n\nPlease clarify the refund status for order {order}, amount {amount}. My current records are:\nReturn pickup: {pickup}\nRefund approval: {approval}\nRefund payment: {payment}\n\nPlease confirm whether the refund has been approved and explain the next step. If payment has been issued, please share the issue date and transaction reference so I can reconcile my records."
        elif case.kind == "salary":
            periods = value("periods", "बकाया वेतन की अवधि" if hindi else "unpaid periods")
            amount = value("amount", "बकाया राशि; कृपया मिलान करें" if hindi else "unpaid amount; please reconcile")
            prior = value("prior_communication", "पहले किया गया लिखित संपर्क, यदि कोई हो" if hindi else "previous written communication, if any")
            if hindi:
                body = f"विषय: बकाया वेतन का मिलान और भुगतान अनुरोध\n\nप्रिय {other},\n\nमेरे रिकॉर्ड के अनुसार {periods} का वेतन {amount} बकाया है। कृपया पेरोल रिकॉर्ड से राशि का मिलान करें और कोई अंतर हो तो बताएं।\nपहले किया गया संवाद: {prior}\n\nकृपया भुगतान की स्थिति, किसी अंतर का कारण और प्रस्तावित भुगतान तारीख लिखकर बताएं।"
            elif hinglish:
                body = f"Subject: Unpaid salary ka reconciliation aur payment request\n\nDear {other},\n\nMere records ke mutabik {periods} ki salary, amount {amount}, unpaid hai. Payroll records se reconcile karke koi difference batayein.\nPrevious communication: {prior}\n\nPayment status, difference ka reason aur proposed payment date written mein share karein."
            else:
                body = f"Subject: Request to reconcile and pay outstanding salary\n\nDear {other},\n\nAccording to my records, salary for {periods}, totaling {amount}, remains unpaid. Please reconcile this with payroll records and explain any difference.\nPrevious written communication: {prior}\n\nPlease confirm the payment status and proposed payment date in writing."
        elif case.kind == "notice":
            sender = value("sender", "नोटिस में लिखा भेजने वाले का नाम" if hindi else "sender named in notice")
            quotes = "\n".join("• " + q for q in case.allegations) or ("[कोई आरोप पहचाना नहीं गया; मूल नोटिस जांचें।]" if hindi else "[No allegation identified by the extraction rules; review the original notice.]")
            if hindi:
                body = f"वकील से समीक्षा के लिए नोट्स — भेजने से पहले जांचें\n\nभेजने वाला: {sender}\nभेजने वाले के आरोप, स्वीकार किए तथ्य नहीं:\n{quotes}\n\nमांगी गई कार्रवाई: {value('requested_action', 'मूल नोटिस में देखें')}\nलिखी हुई जवाब तारीख: {value('response_date', 'मूल नोटिस में देखें')}\n\nवकील के लिए प्रश्न: क्या कोई जवाब या उपस्थिति जरूरी है, और किस तारीख तक? किन दस्तावेजों की जरूरत है? कौन से आरोप की जांच करनी है?\n\nतथ्यात्मक अनुरोध का प्रारूप: कृपया अपने दावों का आधार, हिसाब और सहायक दस्तावेज साझा करें। यह प्रारूप किसी आरोप को स्वीकार नहीं करता।"
            elif hinglish:
                body = f"Lawyer review notes — bhejne se pehle review karein\n\nSender: {sender}\nSender ke allegations, accepted facts nahi:\n{quotes}\n\nRequested action: {value('requested_action', 'original notice check karein')}\nWritten response date: {value('response_date', 'original notice check karein')}\n\nLawyer ke liye questions: Kya response ya appearance chahiye, aur kis date tak? Kaun se documents chahiye? Kaun se allegations verify karne hain?\n\nFactual request ka draft: Apne claims ka basis, account statement aur supporting records share karein. Yeh draft allegations accept nahi karta."
            else:
                body = f"Lawyer review notes — review before sending any response\n\nSender: {sender}\nSender's allegations, not facts accepted by you:\n{quotes}\n\nRequested action (quoted): {value('requested_action', 'check original notice')}\nResponse date actually written: {value('response_date', 'check original notice')}\n\nQuestions for a qualified lawyer: Is a response or appearance required, and by when? What records should I gather? Which allegations need checking?\n\nPossible factual request for review: Please provide the basis, account statement and documents supporting your claims. This draft makes no admission about the allegations."
        else:
            summary = value("summary", "your account of what happened")
            if hindi:
                body = f"वकील से चर्चा के लिए तथ्य\n\nआपका विवरण: {summary}\nउद्देश्य: {case.goal}\n\nअधूरी जानकारी: [लोग, तारीखें, रकम और उपलब्ध रिकॉर्ड जांचें]\n\nवकील के लिए प्रश्न: कौन से विकल्प लागू हैं? कौन सी समय सीमा लागू है? कौन से दस्तावेज चाहिए? इस प्रकार के मामले के लिए ऐप में सत्यापित कानूनी मार्गदर्शन उपलब्ध नहीं है।"
            elif hinglish:
                body = f"Lawyer discussion ke liye facts\n\nAapka account: {summary}\nGoal: {case.goal}\n\nMissing details: [parties, dates, amount aur records verify karein]\n\nLawyer se poochein: Kaun se options apply hote hain? Koi time limit hai? Kaun se documents chahiye? Is issue ke liye app mein verified legal guidance available nahi hai."
            else:
                body = f"Facts for a discussion with a qualified lawyer\n\nYour account: {summary}\nYour goal: {case.goal}\n\nDetails to check: [parties, dates, amounts and available records]\n\nQuestions: Which options apply to these facts? Are there applicable time limits? What documents should I bring? This app has no verified issue-specific legal guidance for this problem."
        if case.evidence and case.kind != "notice":
            body += "\n\n" + ("आपके बताए उपलब्ध रिकॉर्ड: " if hindi else "Records you say you have: ") + ", ".join(case.evidence)
        if case.kind in {"rental", "refund", "salary"}:
            body += "\n\n" + ("धन्यवाद,\n" if hindi else "Regards,\n") + name
        return body

    @staticmethod
    def guidance(case: CaseRecord) -> list[dict]:
        items = [{"text": choose(case, (
            "Keep a copy of your correspondence and the records you already have. Check every draft before sending; the app sends nothing.",
            "अपने पत्राचार और उपलब्ध रिकॉर्ड की प्रतियां रखें। भेजने से पहले ड्राफ्ट जांचें; ऐप कुछ नहीं भेजता।",
            "Correspondence aur apne records ki copy rakhein. Bhejne se pehle draft check karein; app kuch send nahi karta.")), "source_id": None, "claim_id": None}]
        if case.kind == "refund":
            items.append({"text": choose(case, (
                "The National Consumer Helpline offers a pre-litigation route for consumer grievances.",
                "राष्ट्रीय उपभोक्ता हेल्पलाइन उपभोक्ता शिकायतों के लिए मुकदमे से पहले का एक रास्ता देती है।",
                "National Consumer Helpline consumer grievances ke liye pre-litigation route deti hai.")), "source_id": "nch", "claim_id": "nch_pre_litigation"})
            items.append({"text": choose(case, (
                "You can register a grievance through the National Consumer Helpline portal.",
                "आप राष्ट्रीय उपभोक्ता हेल्पलाइन पोर्टल पर शिकायत दर्ज कर सकते हैं।",
                "Aap National Consumer Helpline portal par grievance register kar sakte hain.")), "source_id": "nch", "claim_id": "nch_register"})
        elif case.kind in {"rental", "salary"}:
            items.append({"text": choose(case, (
                "This prototype has not verified a law, deadline or entitlement for your agreement, state or employment arrangement. The draft is a factual request; ask a qualified lawyer about legal remedies.",
                "इस प्रोटोटाइप ने आपके समझौते, राज्य या रोजगार व्यवस्था के लिए कानून, समय सीमा या अधिकार सत्यापित नहीं किए हैं। ड्राफ्ट तथ्यों पर आधारित अनुरोध है; कानूनी उपाय वकील से पूछें।",
                "Is prototype ne aapke agreement, state ya employment arrangement ke liye law, deadline ya entitlement verify nahi kiya hai. Draft factual request hai; legal options qualified lawyer se poochein.")), "source_id": None, "claim_id": None})
        elif case.kind == "notice":
            items.append({"text": choose(case, (
                "Get prompt review by a qualified lawyer, especially for court, police, criminal, eviction or hearing-related documents. The absence of a response date in the pasted text does not establish that no deadline applies.",
                "खासकर अदालत, पुलिस, आपराधिक मामले, बेदखली या सुनवाई से जुड़े दस्तावेज की जल्द योग्य वकील से समीक्षा कराएं। पेस्ट किए पाठ में जवाब तारीख न होने का मतलब यह नहीं कि कोई समय सीमा लागू नहीं होती।",
                "Court, police, criminal, eviction ya hearing documents ko jaldi qualified lawyer se review karayein. Pasted text mein response date na hone se yeh confirm nahi hota ki koi deadline apply nahi hoti.")), "source_id": None, "claim_id": None})
        else:
            items.append({"text": choose(case, (
                "Verified guidance for this issue is outside this prototype. Use the case summary and questions for a qualified lawyer.",
                "यह मामला प्रोटोटाइप के सत्यापित मार्गदर्शन के दायरे से बाहर है। तथ्य और प्रश्न योग्य वकील से चर्चा के लिए इस्तेमाल करें।",
                "Yeh issue prototype ke verified guidance ke scope se bahar hai. Summary aur questions qualified lawyer ke saath discuss karein.")), "source_id": None, "claim_id": None})
        items.append({"text": choose(case, (
            "You can approach a State or District Legal Services Authority to ask about legal aid.",
            "कानूनी सहायता के बारे में पूछने के लिए राज्य या जिला विधिक सेवा प्राधिकरण से संपर्क कर सकते हैं।",
            "Legal aid ke baare mein State ya District Legal Services Authority se pooch sakte hain.")), "source_id": "nalsa_faq", "claim_id": "nalsa_contact"})
        return items
