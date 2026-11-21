# Hosted prototype interface direction

Reviewed the existing `app.py` and `docs/preview-desktop.png` before proposing
changes. The job remains: describe an everyday legal problem, review the record,
and leave with a factual draft or useful questions for a lawyer.

Research on 21 November 2026 inspected eight web screens returned by two Mobbin
searches. Refero style research in the earlier build returned `NO_SUBSCRIPTION`;
the Refero craft guidance and this inspected product evidence inform the new
direction. No unviewed style reference is claimed.

## References and bounded roles

- [Spellbook](https://mobbin.com/screens/6ce141af-d148-43ef-b9ee-582bb92fae37):
  a legal-document conversation sits beside a narrow file rail. Use the division
  between conversation and supporting material. Do not carry over its example
  contract content, account controls, claims or branding.
- [Dropbox Dash](https://mobbin.com/screens/f4ca9d48-c17a-40e5-98a2-f3a293483967):
  the active conversation has a compact title, constrained reading width and a
  left navigation rail. Use the compact active-case shell and readable transcript.
  Do not copy its storage navigation or introduce unsupported file uploads.
- [Plane](https://mobbin.com/screens/8d800a40-7843-4810-95a1-9206c3289efc):
  a short opening question leads directly to a composer, with suggestions below.
  Use that order for the empty state. Its project navigation is outside this app's
  scope.
- [Notion](https://mobbin.com/screens/7f5c8c5c-01c0-4b83-a505-cf3fe0bd49bc):
  the empty state also centers the request composer, with extra options alongside
  or below it. This supports putting case entry ahead of example choices. Do not
  add model-selection or attachment controls that this prototype does not support.
- [Fabric](https://mobbin.com/screens/c6048777-510b-4293-8bc7-7ca53f75a515):
  a document remains visible while an adjacent panel switches between comments,
  information and assistant content. Use the separation of a primary task from
  supporting views. Do not copy the dark panel or its file actions.

Lightfield, Pi and ManyChat were also inspected. Their screens are not anchors for
this direction: Lightfield added little beyond the compact chat shell, Pi's open
canvas leaves case preparation without a visible workspace, and ManyChat's source
setup is a different task.

## Reference lock

Primary direction: an active case workspace, informed by Spellbook and Dropbox
Dash structure, in Nyaya Saathi's own white canvas and restrained teal actions.
The request composer leads the empty state, supported by the Plane and Notion
examples. Desktop can show the conversation beside the case workspace; on narrow
screens the same material must stack without horizontal scrolling.

Preserve the user's ability to type naturally, the independent language choices,
the explicit demo/connection status, urgent-review wording, case corrections,
uncertainty, claim-specific source links, manual draft preview and TXT export.
The changes concern layout and presentation; they do not add legal capabilities.

## Decision ledger

| Existing issue seen in the source | Proposed move | Evidence and limit |
| --- | --- | --- |
| The initial composer follows four equally prominent example buttons. | Put the request field before examples; render examples as secondary ways to start. | Plane and Notion show composer-first empty states. |
| The same long opening heading remains above an active transcript. | Use a compact active-case heading after the first message. | Dropbox Dash and Spellbook show compact conversation titles. |
| Case details, steps and drafts require scrolling below the whole conversation. | Use a desktop conversation/workspace split; stack it on mobile. | Spellbook places supporting files beside its conversation. Adapting the rail to this app's case data is a product decision. |
| Four full-width disclosure rows repeat in the empty state before any outputs exist. | Use a clearly named case workspace with purposeful empty states and supporting views. | Fabric keeps supporting material in a separate panel with named views. Exact Nyaya labels remain this product's own. |
| Several sidebar status paragraphs repeat the main-page mode text. | Keep one short visible mode label and place the detailed explanation in the existing About disclosure. | Existing source contains the duplicated text; compact side rails in Dropbox Dash and Spellbook provide the structural example. Material connection/fallback warnings must remain visible. |

Implementation details selected for this product: keep text at a readable body
size, use dark ink for primary copy, teal only for meaningful actions, thin borders
for groupings, visible keyboard focus and no decorative metrics or stock imagery.
Do not claim a conversion, comprehension or accessibility outcome from these
references. Verify the rendered desktop, mobile, empty, active, stale-draft and
fallback states after implementation.
