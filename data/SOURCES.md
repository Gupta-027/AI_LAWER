# Source verification and scope

Checked on **21 November 2026** using the browser retrieval tool. All URLs in `sources.json` returned readable official-page text. The checked date records retrieval, not a guarantee that legal content is current or complete. Each allowed claim is a short paraphrase, associated with a specific page and section locator. No page is reproduced in full.

| Source ID | Actual retrieval | Scope |
| --- | --- | --- |
| `nch` | Successful HTML retrieval, 152 extracted lines | Questions 1, 3 and 8 support the pre-litigation route, registration channels and absence of guaranteed remedy. |
| `nalsa_faq` | Successful HTML retrieval, 581 extracted lines | Questions 8, 11 and 12 support advice/aid distinctions, 15100 and routes to the appropriate institution. |
| `nalsa_aid` | Successful HTML retrieval, 345 extracted lines | Legal Services and Eligibility headings support conditional eligibility and possible services. |
| `consumer_acts` | Successful HTML retrieval, 191 extracted lines | Reference directory only; not evidence of a particular deadline, penalty or right. |

The initial NALSA candidate `https://nalsa.gov.in/services/legal-aid/` timed out. Search located the functioning current `/legal-aid/` and `/faqs/` pages. Only the working URLs are included in the collection.

## Deliberate limits

- The NCH page's process-duration description is **not** a seller's legal refund deadline. The prototype must not convert it into one, promise resolution, or treat NCH as a court order.
- Do not assume a return pickup means a refund was approved or issued. Ask for the status; this is factual workflow logic, not a legal rule.
- The NALSA pages contain differing income figures in their own sections and compared with some current state authority pages. No precise income cutoff is stored as an allowed claim. Refer eligibility questions to the appropriate authority and its current rules.
- The legislation index now lists a 2026 e-commerce amendment. This prototype has not compared the operative legislation, amendments, commencement or applicability. Do not claim an e-commerce statutory deadline from the index or from a remembered older rule.
- No source here establishes a universal rental-deposit return deadline, permissible deduction, salary-recovery forum, interest amount, statutory notice-response period, penalty or guaranteed outcome. Rental and salary output should remain a factual request, with location, agreement or employment details sought when needed for further advice.
- A notice's allegations are not verified facts. Extract only dates actually written in the supplied text; absence of a written response date does not establish that no legal time limit applies. Formal notices and urgent matters require prompt qualified review.

## Data contract

`sources.json` contains a top-level `sources` array. Each source has `id`, `title`, `url`, `jurisdiction`, `checked_on`, `locator`, `summary`, and a `claims` array of `{id, text}` objects. The application should select allowed claims in code and render their associated source beside each claim. Merely accepting a model-provided source ID does not validate a new claim.

Claim IDs: `nch_pre_litigation`, `nch_register`, `nch_no_guarantee`, `nalsa_contact`, `nalsa_application`, `nalsa_advice`, `nalsa_eligibility`, `nalsa_services`, `consumer_official_text`.
