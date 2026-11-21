# Observed evaluation

Run `20261121T141432370456Z` · requested provider `gemini`

68/68 automated checks passed across 14 original synthetic conversations.

Live-provider run through the same case engine as the UI. Model calls, validated responses and fallbacks are counted separately. Unknown answers and refused fabrication requests may skip a model call. Synthetic checks are not independent legal review or proof of general language accuracy.

Observed native Gemini calls: 19; validated live responses: 19; fallback responses: 0.

| Case | Checks | Observed limitations |
| --- | --- | --- |
| rental_short_followups | 6/6 | No asserted failure observed in this run. |
| rental_written_deductions | 6/6 | No asserted failure observed in this run. |
| rental_no_explanation | 4/4 | No asserted failure observed in this run. |
| refund_pickup_only | 5/5 | No asserted failure observed in this run. |
| refund_payment_claim | 4/4 | No asserted failure observed in this run. |
| refund_status_correction | 5/5 | No asserted failure observed in this run. |
| salary_correction | 6/6 | No asserted failure observed in this run. |
| notice_no_response_date | 7/7 | No asserted failure observed in this run. |
| notice_explicit_response_date | 5/5 | No asserted failure observed in this run. |
| unsupported_legal_threat | 4/4 | No asserted failure observed in this run. |
| unknown_answer | 4/4 | No asserted failure observed in this run. |
| hindi_salary | 4/4 | No asserted failure observed in this run. |
| unfamiliar_issue | 3/3 | No asserted failure observed in this run. |
| holdout_headphone_refund | 5/5 | No asserted failure observed in this run. |

Raw outputs are generated directly from the engine and saved without editing. Expected behavior lives in `evaluation/cases.json` and `evaluation/runner.py`. A holdout label means the input is absent from the UI examples; it does not establish broad unseen-input generalization.

Human review still needed: translation nuance, factual completeness, the appropriateness of the next question, draft tone, and legal relevance to the user's specific jurisdiction.
