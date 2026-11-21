"""Build a two-page review draft using actual evaluation metrics when available."""
from __future__ import annotations

import ast
import json
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "solution-draft.pdf"


def observed_results() -> tuple[str, str]:
    """Describe what was recorded, including failures and provider uncertainty."""
    path = ROOT / "evaluation" / "report.json"
    if not path.exists():
        return (
            "No evaluation report is available yet. Run python scripts/evaluate.py, "
            "then regenerate this PDF. No pass count or model-quality result is claimed.",
            "Evaluation pending. Raw-output paths and run identifiers will be recorded by the runner.",
        )
    report = json.loads(path.read_text(encoding="utf-8"))
    unit_methods = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
        for test_path in (ROOT / "tests").glob("test_*.py")
        for node in ast.walk(ast.parse(test_path.read_text(encoding="utf-8-sig")))
    )
    passed = report.get("checks_passed", "unknown")
    total = report.get("checks_total", "unknown")
    cases = report.get("cases", "unknown")
    provider = str(report.get("requested_provider", "unknown"))
    run_id = str(report.get("run_id", "unknown"))
    results = (
        f"Latest recorded run: {passed}/{total} automated checks passed across {cases} "
        f"original synthetic conversations; requested provider: {provider}. "
        "These checks measure the asserted behavior of the model-and-code workflow, not "
        "legal correctness or broad language quality. A rules-demo run does not measure an LLM. "
        f"The unit suite has {unit_methods} methods, including mocked adapter HTTP responses; mocks "
        "are separate from recorded live inference. "
    )
    if provider != "demo":
        statuses = [str(item.get("provider_status", "")) for item in report.get("observations", [])]
        live = sum(status.startswith("Live model extraction connected") for status in statuses)
        fallback = sum("fallback" in status.lower() or "using demo rules" in status.lower() for status in statuses)
        results += (f"Final case statuses: validated live extraction in {live}/{len(statuses)}; "
                    f"fallback in {fallback}; other/unverified in {len(statuses) - live - fallback}. "
                    "A final status does not prove every turn used a model.")
        call_fields = (report.get("model_calls"), report.get("live_model_calls"), report.get("fallback_model_calls"))
        if all(isinstance(value, int) for value in call_fields):
            calls, live_calls, fallback_calls = call_fields
            results += (f" Recorded extraction calls: {live_calls}/{calls} validated live, "
                        f"{fallback_calls} fallbacks. Code-handled refusals need no model call.")
    failed = [
        f"{item.get('case_id', 'unknown')}: {check.get('check', 'unknown')}"
        for item in report.get("observations", [])
        for check in item.get("checks", [])
        if not check.get("passed")
    ]
    notes = (
        "Asserted failures in this run: " + "; ".join(failed[:6]) + ". "
        if failed
        else "No asserted check failure was recorded in this run. "
    )
    notes += (
        f"Run ID: {run_id}. See evaluation/report.md and its matching raw_outputs/*.json. "
        "Raw responses and state snapshots are saved directly; expectations are stored separately."
    )
    return results, notes


def observed_voice() -> str:
    """Describe actual audio runs when present; never substitute a mocked result."""
    latest = {}
    for path in sorted((ROOT / "raw_outputs").glob("gemini_*voice_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError):
            continue
        if isinstance(payload.get("result"), dict):
            latest[payload.get("fixture", path.name)] = payload
    if not latest:
        return ("No recorded Gemini audio run is available in this copy. Voice review-gate "
                "unit tests do not establish transcription accuracy; run a synthetic clip and save its actual output.")
    observations = []
    for payload in latest.values():
        result = payload["result"]
        language = str(result.get("language", "unknown language"))
        outcome = "usable transcript" if result.get("ok") is True else "failed transcription"
        elapsed = payload.get("elapsed_seconds", "unmeasured")
        observations.append(f"{language}: {outcome}, {elapsed} seconds")
    return ("Separate actual Gemini audio runs: " + "; ".join(observations) + ". "
            "Original synthetic fixtures and unedited responses are retained. These runs do not "
            "measure every accent, real microphone or noisy environment. User review remains required.")


def observed_mistake() -> str:
    gemini_failure = ROOT / "raw_outputs" / "20261121T140205149688Z_salary_correction.json"
    if gemini_failure.exists():
        text = (
            "The first Gemini conversation run passed 67/68 checks. In the salary correction, "
            "the amount field became Rs 42000, but the model labelled an old Rs 48000 fact "
            "clause as evidence, so the draft repeated the stale amount. Exact quotation alone "
            "did not establish the right semantic type. Evidence: " + gemini_failure.name + ". "
        )
        report_path = ROOT / "evaluation" / "report.json"
        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            repaired = any(
                check.get("check") == "salary_correction" and check.get("passed")
                for item in report.get("observations", []) if item.get("case_id") == "salary_correction"
                for check in item.get("checks", [])
            )
            if repaired:
                text += "Evidence-type filtering and the corrected-amount regression pass in the latest recorded run. "
            else:
                text += "The latest result above shows the current regression status. "
        return text + "An earlier tiny SmolLM2 schema failure and initial coding failures are also preserved."
    smoke_paths = sorted((ROOT / "raw_outputs").glob("live_model_smoke_*.json"))
    if smoke_paths:
        smoke_path = smoke_paths[-1]
        smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
        if smoke.get("live_generation_observed") and not smoke.get("model_returned_json_object"):
            return (
                f"Actual CPU generation with {smoke.get('model_id', 'a tiny local model')} "
                "ignored the requested JSON schema and repeated irrelevant return-address "
                "advice. True localhost HTTP connected the engine and adapter to generation; "
                "the adapter rejected the response and rules fallback preserved pickup "
                "confirmed and approval unknown. One input is not a model benchmark or "
                "successful extraction. This historical experiment is separate from current Gemini "
                f"results. Raw evidence: {smoke_path.name}. "
                "Separately, the first AI-generated code mishandled a corrected salary "
                "amount and manual draft text (40/42 initial checks); that raw run remains "
                "archived. The repaired, expanded rules checks are reported above."
            )
    original = ROOT / "raw_outputs" / "20261121T131114701274Z_salary_correction.json"
    if not original.exists():
        return (
            "The earlier ChatGPT proposal expanded the brief into four workflows although "
            "one focused issue is allowed. Reviewing the brief made that scope a deliberate "
            "choice. No archived runtime error is available to cite in this copy; do not "
            "invent an observed model failure."
        )
    text = (
        "The first AI-assisted implementation mishandled 'Rs 42000, not Rs 48000': "
        "the saved amount stayed at Rs 48000 and the proposed replacement dropped a "
        "user-added personal-email sentence. The initial run passed 40/42 checks; both "
        "salary checks failed. This is a real coding error, not a claimed live-LLM "
        "hallucination. Original evidence is preserved in raw_outputs/"
        "20261121T131114701274Z_salary_correction.json. "
    )
    report_path = ROOT / "evaluation" / "report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        checks = {
            check.get("check"): check.get("passed")
            for item in report.get("observations", [])
            if item.get("case_id") == "salary_correction"
            for check in item.get("checks", [])
        }
        if checks.get("salary_correction") and checks.get("manual_preview"):
            text += (
                "The repair corrected amount selection and preserved manual additions; "
                "both regression checks pass in the latest recorded run. Check coverage "
                "expanded during review, so intermediate percentages are not directly comparable."
            )
        else:
            text += "The latest report above states whether the repair has been verified."
    return text


def footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D9E3DE"))
    canvas.line(17 * mm, 16 * mm, A4[0] - 17 * mm, 16 * mm)
    canvas.setFillColor(colors.HexColor("#49635B"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(17 * mm, 11 * mm, "Nyaya Saathi | Draft for candidate review | 21 November 2026")
    canvas.drawRightString(A4[0] - 17 * mm, 11 * mm, str(document.page))
    canvas.restoreState()


def main() -> int:
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "NyayaTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=23, leading=27, alignment=TA_LEFT,
        textColor=colors.HexColor("#182B27"), spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        "NyayaHeading", fontName="Helvetica-Bold", fontSize=11,
        leading=14, textColor=colors.HexColor("#182B27"), spaceBefore=10, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "NyayaBody", fontName="Helvetica", fontSize=9.4,
        leading=13.2, textColor=colors.HexColor("#263A33"), spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "NyayaSmall", parent=styles["NyayaBody"], fontSize=8.2, leading=11.2,
        textColor=colors.HexColor("#49635B"),
    ))
    story = []

    def paragraph(text: str, style: str = "NyayaBody") -> None:
        story.append(Paragraph(escape(text), styles[style]))

    def section(title: str, body: str) -> None:
        paragraph(title, "NyayaHeading")
        paragraph(body)

    paragraph("Nyaya Saathi", "NyayaTitle")
    paragraph("Problem 2: Build an AI Lawyer | Solution draft", "NyayaHeading")
    paragraph("Candidate: [YOUR NAME]   Roll number: [YOUR ROLL NUMBER]   Branch: [YOUR BRANCH]", "NyayaSmall")
    paragraph(
        "Review and personalize before submission: add your own reasons, verify the observed "
        "results and AI-use statement, and include a readable repository link with run steps.",
        "NyayaSmall",
    )
    section(
        "Problem and scope",
        "An ordinary Indian user describes a problem without knowing legal terminology. "
        "The prototype organizes facts, asks one useful follow-up at a time, and produces a "
        "reviewable next step. English, Hindi and Hinglish can be typed or recorded; Gemini "
        "transcribes voice and extracts case facts. Conversation and draft languages are independent. The assignment "
        "allows one issue in depth; four bounded workflows are my implementation choice: rental "
        "deposit, online refund, unpaid salary and notice explanation. Other issues become a "
        "lawyer-preparation summary. [Add why this scope fits your approach.]",
    )
    section(
        "Journey and assumptions",
        "Chat leads to an editable case record, cited options and an editable TXT draft. "
        "Voice is record, transcribe, review/edit, then explicitly use the text; recording alone "
        "does not update the case. The recorder needs browser microphone permission on HTTPS or localhost. "
        "Unknown answers are accepted; missing details remain explicit placeholders. Corrections "
        "mark existing drafts for review. A proposed replacement and diff protect saved manual "
        "edits. Notice allegations stay attributed, and only written dates are extracted. "
        "The app assumes an Indian context and user-provided facts; it does not verify evidence, "
        "decide entitlement or send/file anything. Formal and urgent matters need qualified review.",
    )
    section(
        "AI, code and human responsibility",
        "OpenAI Codex assisted implementation, research, test design and debugging; ChatGPT "
        "provided the earlier proposal reviewed here. Native Gemini REST handles audio transcription "
        "and proposes structured case updates. Python/Pydantic validate facts, select one follow-up, "
        "manage revisions, select sources, render factual drafts and export. Without provider configuration, "
        "the app has an explicit rules demo; failed AI extraction reports fallback. The candidate must own the "
        "submission; a user or qualified lawyer must check facts, translation, legal fit and "
        "the final correspondence. [Confirm tools actually used in your final workflow.]",
    )
    section(
        "Grounding and privacy",
        "A small English-language collection records official NCH, NALSA and Consumer Affairs URLs, "
        "claim-level text, locators, jurisdiction and retrieval date. It supports narrow "
        "procedural guidance rather than remembered legal sections or universal deadlines. "
        "Cases, real recordings and draft transcripts remain in session memory; only synthetic "
        "evaluation runs are saved. Keys stay server-side and outside the archive. Google receives "
        "audio when transcription is requested and reviewed case text in AI mode; provider retention may differ.",
    )

    section(
        "Test coverage and interpretation",
        "Original paired rental cases change whether a deduction explanation already exists. "
        "Refund cases separate pickup, approval and a seller's payment claim. Salary tests "
        "correct the amount after manual drafting. Notice cases include missing and explicit "
        "response dates. Adversarial input asks for invented law and a guaranteed penalty. "
        "Other cases cover unknown answers, Hindi and an unfamiliar issue. One synthetic "
        "holdout runs through the same process entry point as a real user and is absent from "
        "UI examples. Review-gate tests reject stale, empty, inaudible and oversized transcript "
        "submissions. This authored set is not independent legal review or proof of general accuracy.",
    )
    story.append(PageBreak())
    paragraph("Evidence, limits and scale", "NyayaTitle")
    measured, notes = observed_results()
    section("Measured behavior", measured)
    paragraph(notes, "NyayaSmall")
    section("Measured voice entry", observed_voice())
    section(
        "Observed AI failure and code controls",
        observed_mistake(),
    )
    section(
        "Material limitations",
        "Models and rules can miss facts, negation, speech or translations; users must review "
        "the transcript and case record. Audio is limited to two minutes and 10 MiB. "
        "Sources are a checked snapshot; they do not establish a universal rental, salary "
        "or notice deadline. NCH is a pre-litigation option without guaranteed remedy. "
        "No OCR, production authentication, durable storage or litigation strategy "
        "is included. Refresh or restart can lose a session. New providers need their own "
        "evaluation; passing synthetic tests cannot establish safety for public legal use.",
    )
    section(
        "Cost and scale: estimates, not measured prices",
        "Rules mode has no model API charge. Gemini charges and quotas depend on model and "
        "API account. Estimate requests x (text/audio input tokens x applicable input rate + "
        "output tokens x output rate), plus hosting and human review. The app's measured "
        "latency and usage do not establish invoice totals or production throughput. At Indian-user "
        "scale, measure tokens and concurrency first; add language evaluation, source-update "
        "ownership, rate limits, consent/retention controls, secure access and lawyer escalation. "
        "Session memory alone is insufficient for a production service.",
    )
    section(
        "Reproduce and submit",
        "Install requirements; configure NYAYA_PROVIDER=gemini, GEMINI_MODEL and a server-side "
        "GEMINI_API_KEY; run python -m streamlit run app.py. Run unittest and evaluate.py "
        "--provider gemini separately from demo mode. The Render Blueprint requests the secret "
        "key without committing it. README and docs/RENDER.md contain exact setup. Share the "
        "actual app/repository link and this personalized PDF; do not invent a public deployment URL.",
    )
    paragraph(
        "Official source links: consumerhelpline.gov.in/public/about | nalsa.gov.in/faqs/ | "
        "nalsa.gov.in/legal-aid/ | consumeraffairs.gov.in/pages/consumer-protection-acts. "
        "Full claim locators and retrieval limits: data/SOURCES.md.",
        "NyayaSmall",
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=17 * mm, leftMargin=17 * mm,
        topMargin=16 * mm, bottomMargin=22 * mm,
        title="Nyaya Saathi - Problem 2 solution draft",
        author="Candidate review draft",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    pages = len(PdfReader(str(OUTPUT)).pages)
    if pages > 2:
        raise RuntimeError(f"PDF exceeds assignment limit: {pages} pages; edit the source content.")
    print(f"Created {OUTPUT.relative_to(ROOT)} ({pages} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
