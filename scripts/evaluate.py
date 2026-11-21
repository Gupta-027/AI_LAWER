"""Write actual synthetic runs and a separate evaluation report.

Run: python scripts/evaluate.py
Select a real configured model explicitly: python scripts/evaluate.py --provider ollama
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["demo", "ollama", "openai", "gemini"], default="demo")
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
    os.environ["NYAYA_PROVIDER"] = args.provider
    from evaluation.runner import assess, load_cases, run_case

    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%dT%H%M%S%fZ")
    out_dir = ROOT / "raw_outputs"
    out_dir.mkdir(exist_ok=True)
    observed = []
    model_calls = live_model_calls = fallback_model_calls = 0
    for spec in load_cases():
        raw = run_case(spec)
        for event in raw["events"]:
            if event.get("model_called"):
                model_calls += 1
                if event["state_after"].get("provider_status", "").startswith("Live model extraction connected"):
                    live_model_calls += 1
                else:
                    fallback_model_calls += 1
        raw["run_id"] = run_id
        raw["recorded_at_utc"] = now.isoformat()
        raw["requested_provider"] = args.provider
        path = out_dir / f"{run_id}_{spec['id']}.json"
        # Exclusive creation prevents accidental rewriting of previous evidence.
        with path.open("x", encoding="utf-8") as stream:
            json.dump(raw, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        checks = assess(spec, raw)
        observed.append({"case_id": spec["id"], "holdout": bool(spec.get("holdout")), "raw_output": str(path.relative_to(ROOT)).replace("\\", "/"), "elapsed_ms": raw["total_elapsed_ms"], "provider_status": raw["final_state"].get("provider_status"), "checks": checks})
    total = sum(len(x["checks"]) for x in observed)
    passed = sum(c["passed"] for x in observed for c in x["checks"])
    report = {
        "run_id": run_id, "requested_provider": args.provider,
        "cases": len(observed), "checks_passed": passed, "checks_total": total,
        "model_calls": model_calls, "live_model_calls": live_model_calls, "fallback_model_calls": fallback_model_calls,
        "interpretation": ("Demo runs measure deterministic workflow behavior. They do not measure an LLM's language understanding or legal accuracy. Synthetic checks are not external legal review."
                           if args.provider == "demo" else
                           "Live-provider run through the same case engine as the UI. Model calls, validated responses and fallbacks are counted separately. Unknown answers and refused fabrication requests may skip a model call. Synthetic checks are not independent legal review or proof of general language accuracy."),
        "observations": observed,
    }
    history = ROOT / "evaluation" / "history"
    history.mkdir(exist_ok=True)
    with (history / f"{run_id}.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    (ROOT / "evaluation" / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Observed evaluation", "", f"Run `{run_id}` · requested provider `{args.provider}`", "", f"{passed}/{total} automated checks passed across {len(observed)} original synthetic conversations.", "", report["interpretation"], "", "| Case | Checks | Observed limitations |", "| --- | --- | --- |"]
    if args.provider == "gemini":
        lines[8:8] = [f"Observed native Gemini calls: {model_calls}; validated live responses: {live_model_calls}; fallback responses: {fallback_model_calls}.", ""]
    for item in observed:
        failures = [c for c in item["checks"] if not c["passed"]]
        count = len(item["checks"]) - len(failures)
        note = "; ".join(c["check"] + ": " + c["note"] for c in failures) or "No asserted failure observed in this run."
        lines.append(f"| {item['case_id']} | {count}/{len(item['checks'])} | {note.replace('|', '/')} |")
    lines.extend(["", "Raw outputs are generated directly from the engine and saved without editing. Expected behavior lives in `evaluation/cases.json` and `evaluation/runner.py`. A holdout label means the input is absent from the UI examples; it does not establish broad unseen-input generalization.", "", "Human review still needed: translation nuance, factual completeness, the appropriateness of the next question, draft tone, and legal relevance to the user's specific jurisdiction.", ""])
    (ROOT / "evaluation" / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{passed}/{total} checks passed; {len(observed)} conversations. Raw run: {run_id}")
    print("Evaluation report: evaluation/report.md")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
