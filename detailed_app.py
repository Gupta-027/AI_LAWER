"""Nyaya Saathi: session-only case preparation with an accessible chat workspace."""
from __future__ import annotations

import difflib
from html import escape
import os
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

load_dotenv(Path(__file__).parent / ".env", override=False)

from nyaya.engine import CaseEngine
from nyaya.gemini import GeminiClient
from nyaya.models import CaseRecord
from nyaya.sources import load_sources, verified_guidance
from nyaya.ui import EDIT_FIELDS, FACT_LABELS, KINDS, app_header, brand, css, escaped_pills, progress
from nyaya.voice import VoiceDraft, confirm_transcript, recording_id, stage_transcript

st.set_page_config(page_title="Nyaya Saathi | Legal help, in your words", page_icon="⚖", layout="wide")
st.markdown(css(), unsafe_allow_html=True)

if "case" not in st.session_state:
    st.session_state.case = CaseRecord()
if "case_generation" not in st.session_state:
    st.session_state.case_generation = 0
if "voice_round" not in st.session_state:
    st.session_state.voice_round = 0
case: CaseRecord = st.session_state.case
engine = CaseEngine()
LANGUAGES = ["English", "Hindi", "Hinglish"]
provider = os.getenv("NYAYA_PROVIDER", "demo").lower().strip()
workspace_key = f"workspace_{st.session_state.case_generation}"


def send(text: str) -> None:
    with st.spinner("Organising your case…"):
        engine.process(case, text)
    st.rerun()


def prepare_draft() -> None:
    engine.draft(case)
    st.session_state[workspace_key] = "My draft"
    st.rerun()


def clear_case() -> None:
    for key in list(st.session_state):
        if key != "case_generation":
            del st.session_state[key]
    st.session_state.case_generation += 1


def safety_note() -> None:
    st.markdown('<div class="safety-note"><span aria-hidden="true">ⓘ</span><span>'
                '<strong>A practical starting point, not a lawyer.</strong> '
                'For a court summons, police matter, threatened eviction or time-sensitive notice, '
                'get qualified help promptly.</span></div>', unsafe_allow_html=True)


def render_voice_input() -> None:
    with st.expander("Tell your story by voice · हिन्दी / English", icon=":material/mic:"):
        st.write("Speak naturally. Review the transcript before adding it to your case.")
        language_options = ["Auto", "Hindi", "English", "Hinglish"]
        default_language = case.conversation_language if case.conversation_language in language_options else "Auto"
        language = st.selectbox("Spoken language", language_options,
                               index=language_options.index(default_language), key="spoken_language",
                               format_func=lambda value: "हिन्दी" if value == "Hindi" else "Auto · Hindi / English" if value == "Auto" else value)
        client = GeminiClient()
        if not client.configured:
            st.info("Voice transcription needs a Gemini API key configured on this server. You can still type your story.")
        audio = st.audio_input("Record your story", sample_rate=16000,
                               key=f"recording_{st.session_state.case_generation}_{st.session_state.voice_round}",
                               disabled=not client.configured,
                               help="Allow microphone access. Recording works on localhost or an HTTPS site. Use clips of two minutes or less.")
        st.caption("Up to 2 minutes. On transcription, this recording is sent to Google Gemini. The app keeps it only in session memory.")
        audio_id = recording_id(audio.getvalue()) if audio is not None else None
        pending: VoiceDraft | None = st.session_state.get("voice_review")
        if pending and audio_id and pending.recording_id != audio_id:
            st.session_state.pop("voice_review", None)
            pending = None
            st.session_state.pop("voice_error", None)
        if st.button("Transcribe recording", disabled=audio is None or not client.configured,
                     width="stretch", icon=":material/transcribe:"):
            with st.spinner("Transcribing your story…"):
                result = client.transcribe_audio(audio.getvalue(), audio.type or "audio/wav", language)
            if result.ok:
                try:
                    pending = stage_transcript(result, audio_id)
                    st.session_state.voice_review = pending
                    st.session_state["voice_revision"] = st.session_state.get("voice_revision", 0) + 1
                    st.session_state.pop("voice_error", None)
                except ValueError as error:
                    st.session_state.voice_error = str(error)
            else:
                st.session_state.voice_error = result.status
        if st.session_state.get("voice_error"):
            st.error(st.session_state.voice_error)
        if pending:
            st.markdown("**Check what we heard**")
            st.caption("Check names, amounts and dates. You can change any word before sending.")
            with st.form("voice_review_form"):
                text = st.text_area("Review your transcript", value=pending.text, height=160,
                                    key=f"voice_review_{st.session_state.case_generation}_{st.session_state.get('voice_revision', 0)}")
                st.caption(f"Detected language: {pending.language}")
                use, discard = st.columns([1.5, 1])
                use_transcript = use.form_submit_button("Use this transcript", type="primary", width="stretch")
                discard_transcript = discard.form_submit_button("Discard transcript", width="stretch")
            if use_transcript:
                try:
                    message = confirm_transcript(pending, text, audio_id)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.session_state.pop("voice_review", None)
                    st.session_state.pop("voice_error", None)
                    st.session_state.voice_round += 1
                    send(message)
            if discard_transcript:
                st.session_state.pop("voice_review", None)
                st.session_state.pop("voice_error", None)
                st.session_state.voice_round += 1
                st.rerun()


def render_case() -> None:
    st.caption(f"{KINDS.get(case.kind, 'Case preparation')} · Updated as you talk")
    st.markdown("**What you want to achieve**")
    st.write(case.goal or "Tell us what you would like help with.")
    large_fields = {"summary", "notice_text", "landlord_message", "seller_message", "user_account", "goal_answered"}
    for field, value in case.facts.items():
        if field in large_fields or not value:
            continue
        label = FACT_LABELS.get(field, field.replace("_", " ").capitalize())
        st.markdown(f'<div class="fact-label">{escape(label)}</div>'
                    f'<div class="fact-value">{escape(value)}</div>', unsafe_allow_html=True)
    if case.evidence:
        st.markdown("**Records you say you have**")
        st.markdown(escaped_pills(case.evidence), unsafe_allow_html=True)
    if case.unknowns:
        labels = [FACT_LABELS.get(field, field.replace("_", " ")) for field in case.unknowns]
        st.caption("Still unknown: " + ", ".join(labels))
    if case.allegations:
        st.markdown("**The sender’s allegations**")
        st.caption("These are claims in the notice, not facts you have accepted.")
        for item in case.allegations:
            st.write("• " + item)
    if case.facts.get("user_account"):
        st.markdown("**Your account**")
        st.write(case.facts["user_account"])
    if case.notice_quotes:
        with st.expander("See the notice wording"):
            for quote in case.notice_quotes:
                st.text(quote)
    if case.facts.get("summary"):
        with st.expander("Your original story"):
            st.write(case.facts["summary"])

    with st.expander("Edit case details"):
        st.caption("Correct a detail or fill in something missing. An existing draft will be marked for review.")
        with st.form("edit_case"):
            goal_edit = st.text_input("Your goal", value=case.goal)
            fields = list(EDIT_FIELDS.get(case.kind, EDIT_FIELDS["other"]))
            derived = {"sender", "requested_action", "response_date", "notice_date", "goal_answered"}
            for field in case.facts:
                if field not in fields and field not in derived and field not in {"summary", "notice_text"}:
                    fields.append(field)
            patch = {}
            for field in fields:
                label = FACT_LABELS.get(field, field.replace("_", " ").capitalize())
                widget_key = f"edit_{field}_{case.revision}_{st.session_state.case_generation}"
                value = case.facts.get(field, "")
                if field in {"notice_text", "summary", "prior_communication", "user_account", "landlord_message", "seller_message"}:
                    patch[field] = st.text_area(label, value=value, height=130, key=widget_key)
                else:
                    patch[field] = st.text_input(label, value=value, key=widget_key)
            if st.form_submit_button("Save case changes", type="primary"):
                engine.update_facts(case, patch)
                if goal_edit != case.goal:
                    case.goal = goal_edit
                    case.revision += 1
                st.rerun()


def render_next_steps() -> None:
    st.markdown("**A practical next step**")
    try:
        steps = verified_guidance(engine.guidance(case))
    except ValueError:
        st.error("A guidance source could not be verified. Please use the factual draft and seek qualified advice.")
        return
    for item in steps:
        if item["type"] == "practical":
            st.write(item["text"])
    grouped = {}
    for item in steps:
        if item["type"] == "verified":
            grouped.setdefault(item["source"]["id"], []).append(item)
    if grouped:
        st.markdown("**Official options**")
    for items in grouped.values():
        source = items[0]["source"]
        with st.container(border=True):
            for item in items:
                st.write(item["text"])
            st.markdown(f"[{source['title']}]({source['url']})")
            with st.expander("Source details"):
                st.caption(f"{source['locator']} · {source['jurisdiction']} · Checked {source['checked_on']}")
    st.caption("Sources support only the statements beside them. They do not determine your entitlement or a deadline in your case. Source summaries are in English.")


def render_draft() -> None:
    if not case.draft:
        st.markdown("**Your words, ready for the next step**")
        st.write("Prepare a factual draft now, even if you don’t have every detail. Missing information will appear in brackets.")
        if st.button("Prepare a draft here", type="primary", width="stretch"):
            engine.draft(case)
            st.rerun()
        return
    stale = case.draft_revision != case.revision
    state_label = "Details changed · review this draft" if stale else "Draft ready for your review"
    tone = "stale" if stale else ""
    st.markdown(f'<span class="draft-state {tone}">{state_label}</span>', unsafe_allow_html=True)
    if stale:
        st.warning("Case details or draft language changed. Review an updated draft before using this version.")
        if st.button("Preview updated draft", width="stretch"):
            engine.draft(case)
            st.rerun()
    if case.pending_draft:
        st.markdown("**Proposed replacement**")
        st.caption("Your saved draft remains below. Check the changes before applying them.")
        st.code(case.pending_draft, language=None, wrap_lines=True)
        with st.expander("Compare the changes"):
            diff = "\n".join(difflib.unified_diff(case.draft.splitlines(), case.pending_draft.splitlines(),
                                                fromfile="Saved draft", tofile="Proposed draft", lineterm=""))
            st.code(diff or "No textual changes.", language="diff", wrap_lines=True)
        left, right = st.columns(2)
        if left.button("Apply proposed draft", type="primary", width="stretch"):
            engine.apply_pending(case)
            st.rerun()
        if right.button("Keep my saved draft", width="stretch"):
            case.pending_draft = None
            case.pending_generated_draft = None
            st.rerun()
    st.caption("Replace [bracketed details], check the facts and save your edits before continuing the conversation.")
    with st.form("draft_form"):
        draft_text = st.text_area("Edit draft", value=case.draft, height=440,
                                  key=f"draft_{case.revision}_{case.draft_revision}_{case.manually_edited}_{st.session_state.case_generation}")
        if st.form_submit_button("Save draft edits", type="primary", width="stretch"):
            engine.save_manual_draft(case, draft_text)
            st.rerun()
    st.download_button("Download draft as TXT", data=case.draft.encode("utf-8"),
                       file_name="nyaya-saathi-draft.txt", mime="text/plain; charset=utf-8", width="stretch",
                       icon=":material/download:")
    with st.expander("Copy saved draft"):
        st.caption("Use the copy control at the top right of the block.")
        st.code(case.draft, language=None, wrap_lines=True)
    st.caption("Review before sending. Nothing is sent or filed by this app.")


with st.sidebar:
    st.markdown(brand(compact=True), unsafe_allow_html=True)
    st.caption("A little clarity. A practical next step.")
    st.divider()
    st.markdown("**Your preferences**")
    conversation_language = st.selectbox("Conversation language", LANGUAGES,
                                        index=LANGUAGES.index(case.conversation_language), key="conversation_language",
                                        format_func=lambda x: "हिन्दी" if x == "Hindi" else x)
    document_language = st.selectbox("Draft language", LANGUAGES,
                                    index=LANGUAGES.index(case.document_language), key="document_language",
                                    format_func=lambda x: "हिन्दी" if x == "Hindi" else x)
    case.conversation_language = conversation_language
    if document_language != case.document_language:
        case.document_language = document_language
        case.revision += 1
    st.caption("Type in English, हिन्दी or Hinglish. Choose a different language for your draft if you prefer.")
    if case.messages:
        st.divider()
        st.markdown("**In this session**")
        st.write(KINDS.get(case.kind, "Case preparation"))
        st.caption("Draft needs review" if case.draft and case.draft_revision != case.revision else "Draft prepared" if case.draft else "Building your case")
    st.divider()
    with st.expander("How this works"):
        st.write("Organise the facts, consider practical options and prepare correspondence. This prototype cannot determine legal rights or replace a qualified lawyer.")
        if provider == "demo":
            st.write("Rules demo: no language model is connected. Understanding is limited, so check the record and edit any missed detail.")
        else:
            st.write("A model provider is configured. Its status after your latest message is shown below.")
        if provider == "gemini":
            st.caption("Gemini helps understand your story. Voice recording uses Gemini transcription, with your review before it enters the case.")
        st.caption(case.provider_status)
    with st.expander("Your privacy"):
        st.write("This app keeps your case only in server session memory. It does not save case files or chat logs. Refreshing, a restart or the host sleeping can lose the case.")
        st.write("In AI mode, your configured model service receives the case text and may keep its own logs. Use synthetic details for demonstrations.")
        st.write("Recordings are sent to Google only when you select Transcribe recording. Review and confirm the text before it enters the conversation.")
        st.write("You decide whether to download or send a draft. The app sends and files nothing.")
    st.button("Clear case", on_click=clear_case, width="stretch", icon=":material/restart_alt:")

st.markdown(app_header(provider, case.provider_status), unsafe_allow_html=True)
st.markdown(progress(case), unsafe_allow_html=True)

if not case.messages:
    with st.container(key="welcome"):
        st.markdown('<div class="eyebrow">Everyday problems. A place to start.</div>', unsafe_allow_html=True)
        st.title("Let’s work through your legal problem.")
        st.markdown('<p class="intro">Type or record what happened, in your own words. We’ll organise the facts, '
                    'ask one question at a time and help you prepare what to say next.</p>', unsafe_allow_html=True)
        user_text = st.chat_input("What happened, and what would you like help with?", max_chars=12000)
        if user_text:
            send(user_text)
        render_voice_input()
        st.caption("English, हिन्दी and Hinglish welcome. You don’t need to know the legal terms.")
        st.write("")
        st.markdown("**Not sure where to begin?**")
        st.caption("Try a synthetic example. These start a new conversation with editable facts.")
        examples = [
            ("Rental deposit", "Request a deposit back or understand deductions.", ":material/home:", "rental", "Maine Bengaluru ka flat vacate kar diya. ₹30,000 deposit tha. Landlord ₹8,000 kaat raha hai, reason nahi bataya. Mere paas agreement aur payment receipt hai. Deposit wapas chahiye."),
            ("Online refund", "Check what happened after a return pickup.", ":material/local_shipping:", "refund", "My ₹2,499 headphones were picked up for return. I have the pickup receipt but do not know whether the seller approved my refund. Please help me write to the seller."),
            ("Unpaid salary", "Prepare a factual request to your employer.", ":material/work:", "salary", "My employer has not paid my August and September salary, totalling ₹64,000. I emailed payroll last week. I need a written request for payment."),
            ("Understand a notice", "Separate the claims, dates and requested action.", ":material/description:", "notice", "Please explain this notice: From: Example Collections. We allege you owe ₹18,000 under account X. Please contact us about repayment. I do not accept that I owe this debt."),
        ]
        for row in range(2):
            columns = st.columns(2)
            for column, example in zip(columns, examples[row * 2:row * 2 + 2]):
                label, description, icon, kind, story = example
                with column, st.container(key=f"example_{kind}"):
                    if st.button(label, icon=icon, width="stretch"):
                        send(story)
                    st.markdown(f'<p class="example-description">{description}</p>', unsafe_allow_html=True)
        st.write("")
        safety_note()
else:
    st.subheader("Your case, one step at a time.")
    st.caption("Check the record as you go. You can prepare a draft before every detail is known.")
    with st.container(key="case_columns"):
        conversation, workspace = st.columns([1.12, 1], gap="large")
        with conversation, st.container(key="conversation"):
            st.markdown('<div class="panel-kicker">Your story</div>', unsafe_allow_html=True)
            st.subheader("Conversation")
            with st.container(height=430, key="transcript", autoscroll=True):
                for message in case.messages:
                    with st.chat_message(message["role"]):
                        st.write(message["content"])
            user_text = st.chat_input("Answer, add a detail or correct a fact…", max_chars=12000)
            if user_text:
                send(user_text)
            render_voice_input()
            if case.provider_status and any(word in case.provider_status.lower() for word in ("failed", "unavailable", "rejected", "incomplete", "unknown provider")):
                st.warning(case.provider_status)
            st.caption("You can say “I don’t know”. Missing details won’t stop you preparing a draft.")
            left, right = st.columns([1.2, 1])
            if left.button("Prepare draft", type="primary", width="stretch", icon=":material/edit_document:"):
                prepare_draft()
            if right.button("I don’t know", width="stretch", disabled=not bool(case.last_field)):
                send("I don't know")
        with workspace, st.container(key="workspace"):
            st.markdown('<div class="panel-kicker">Put it together</div>', unsafe_allow_html=True)
            st.subheader("Your case workspace")
            case_tab, next_tab, draft_tab = st.tabs(["My case", "Next steps", "My draft"],
                                                  default="My draft" if case.draft else "My case",
                                                  key=workspace_key, on_change="rerun")
            with case_tab:
                render_case()
            with next_tab:
                render_next_steps()
            with draft_tab:
                render_draft()
    st.write("")
    safety_note()

with st.expander("Official sources used in this prototype"):
    st.caption("A small checked collection, not a search of all Indian law.")
    for source in load_sources().values():
        st.markdown(f"[{source['title']}]({source['url']})")
        st.caption(f"{source['summary']} Checked {source['checked_on']}.")
st.markdown('<div class="page-footer">Made for everyday problems in India. '
            'Your case stays in this app’s session memory; AI providers may retain requests. '
            'Review every fact and draft before using it.</div>', unsafe_allow_html=True)

