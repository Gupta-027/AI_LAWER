# What the checks found

These are observations from development, not simulated failures. The raw conversations and per-run assessments are retained. Only synthetic inputs were used.

- The first run (`20261121T131114701274Z`) passed 40 of 42 original assertions. In the salary correction, the code selected the old amount from “Rs 42000, not Rs 48000.” A regenerated draft also dropped a manually appended sentence. Both failures are visible in that run's unedited salary output.
- Manual review found that the initial assertions were too permissive: an “unknown refund approval” was classified as approved; a second deduction item was lost; a Hinglish move-out statement was missed; and a payroll email's month was included among unpaid periods. Assertions were strengthened before fixing the extraction rules. Run `20261121T131308241496Z` retains that stricter failing assessment.
- Additional conversations test short answers across turns and a corrected pickup status. The latest report describes the final run against the expanded checks. Check counts changed as coverage improved, so the intermediate percentages are not directly comparable.

The observed AI-tool mistake is an AI-generated implementation choosing the last currency amount in a correction. It is not evidence about a live language model's extraction quality. The developer tests use mocked model HTTP responses; no inference benchmark was run against a hosted or local language model in this environment.

A separate genuine CPU model smoke test was subsequently run. SmolLM2-135M failed
the JSON extraction schema and the adapter correctly fell back. Its unedited
output and measured timing are described in `evaluation/live_model_review.md`.
This one integration experiment does not establish successful live extraction.

The tests assert specific behavior, including preservation of uncertainty, citation identifiers, exact quotation provenance, and draft updates. They do not establish complete legal accuracy, broad language understanding, or jurisdiction-specific suitability. A person still needs to check each fact and review any document before using it. The rules demo can miss phrasing outside its tested patterns; editing the structured record provides a correction path.
