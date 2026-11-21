# Review and implementation plan

The later Render/UI revision uses the reference lock in `docs/UI_REFERENCES.md`.
It replaces the original stacked disclosure layout with a desktop conversation
and tabbed case workspace, stacked on mobile, and adds the hosting setup in
`docs/RENDER.md`. The original scope and legal limits below still apply.

The assignment PDF is the primary product brief. The pasted ChatGPT prompt is a
proposal to review, not a requirement from Kuku. We retain its useful safety and
evaluation ideas while limiting the legal depth.

## Requirements versus choices

Kuku asks for conversational help for ordinary Indian users, text OR voice,
honesty about uncertainty, referral to qualified help when appropriate, original
tests and raw outputs. A rerunnable prototype/repository and a solution PDF of at
most two pages are required. One issue in depth is acceptable. No precise
submission deadline can be inferred without the brief's delivery time.

Our choices: text first, English/Hindi/Hinglish, four bounded workflows, session
memory, configurable OpenAI-compatible model, no account/database, a limited
offline rules demo. Consumer help has verified procedural guidance. Rental and
salary produce factual correspondence, not legal determinations. Notice analysis
distinguishes quoted allegations from accepted facts. Other issues produce a
lawyer-preparation summary.

## Execution order

1. Review the actual assignment and inspect the empty repository.
2. Verify a small official source collection, with claim-level support and dates.
3. Implement validated state, one-question intake, corrections and factual drafts.
4. Add a server-side configurable model adapter, with explicit failure status.
5. Build a single-page editable UI and TXT export.
6. Run original paired/edge/adversarial and unseen cases through the same engine.
7. Package actual raw outputs, separate evaluation notes, README and <=2-page PDF.

## Scope boundaries

No automatic sending/filing, universal statutory deadlines, litigation strategy,
legal merits determination, fabricated law, live source search, voice recognition,
document OCR, or production storage. Model inference quality is not measured by a
rules-demo run. Manual fact editing gives users a correction path when extraction
is incomplete. Local Ollama is the free LLM path; its installation/model download
is a separate prerequisite.

## Design reference lock

Refero live style searches were attempted in three directions and returned
NO_SUBSCRIPTION. Used the skill's bundled typography and craft references plus
GOV.UK Design System question-page and details patterns as the available research.

Primary direction: a functional public-service question interface. Preserve one
main question, readable labels, clear focus, narrow reading width and restrained
surfaces. Borrow progressive disclosure for supporting case details, while keeping
the next question and material warnings visible. Do not imply government affiliation.
No imagery is needed for the user's task.

| Decision | Source | Role | Purpose |
| --- | --- | --- | --- |
| One question at a time | Assignment proposal + GOV.UK question pages | Main task | Reduce effort without hiding uncertainty |
| Chat first, case/options/draft below | User-supplied proposal | Page structure | Keep the narrative entry natural |
| Neutral sans, 16px body, generous line height | Refero typography | Reading | English and Devanagari readability |
| White canvas, dark text, green action | Functional service direction | Actions only | Keep drafts and facts dominant |
| Thin borders, 8px radius, no gradients | Refero craft + service pattern | Grouping | Avoid decorative dashboard clutter |
| Visible labels/focus, editable facts | Refero craft | Forms | Keyboard access and error recovery |
| Clear case and model status | Assignment honesty and session choice | User control | Make state and limitations visible |

References: https://design-system.service.gov.uk/patterns/question-pages/ and
https://design-system.service.gov.uk/components/details/. Full style research was
unavailable; this limitation is explicit rather than claiming unseen references.
