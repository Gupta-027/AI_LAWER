# Verification record

Gemini and voice completion: the final live run
`20261121T141432370456Z` passed 68/68 assertions across 14 conversations, with
19 actual Gemini extraction calls, 19 validated responses and zero fallbacks.
This is a measured run, not a future availability or legal-accuracy guarantee.

The real browser voice workflow was also checked with Chrome's synthetic
microphone input: record, transcribe, review, edit 12,000 to 12,500, explicitly
confirm, and prepare a draft. The case was unchanged before confirmation; both
the final case and draft used the reviewed 12,500 amount. Observations are in
`evaluation/voice_browser_check.json`. This checks the browser/recorder/API path,
not the user's physical microphone or every accent. The first automation
attempt did not commit its synthetic edit; the confirmation uses an atomic form
and the final check used trusted browser text input. Its earlier observation is
preserved in `evaluation/history/voice_browser_before_atomic_form.json`.

Checked locally on 21 November 2026 with Python 3.13 and Streamlit 1.58.

- `python -m unittest discover -s tests -v`: the final Gemini/voice revision passed 68 test methods. The behavior test
  executes 14 conversations and their assertions; other tests exercise UI state,
  independent languages, manual draft protection, session separation, source
  validation, model-adapter failures, notice provenance, friendly fact editing,
  clearing resolved unknowns, escaped fact HTML and Render launch configuration.
  New tests cover Gemini authentication/quota/malformed-response handling, audio
  limits and no-speech results, and the explicit transcript review gate. Voice
  UI tests verify that edited text enters the case only after confirmation and
  that discarding or clearing never submits a pending transcript.
- Historical `demo` evaluation: 68/68 asserted behaviors passed across the 14
  synthetic conversations. Use `python scripts/evaluate.py --provider gemini` to
  measure the configured Gemini path. The latest report records its requested
  provider, exact run ID, raw paths and final per-case connection statuses.
  A Gemini-requested run must not be treated as fully live if some calls fell
  back. Earlier failures are preserved, not replaced.
- Live Gemini authentication: the official models endpoint returned HTTP 200.
  This establishes authentication, not extraction or transcription quality.
- Live English voice test: an original 6.565-second Microsoft David synthetic
  recording was transcribed successfully by `gemini-3.5-flash-lite` in 3.01
  seconds. The raw provider text, transcript and usage are preserved in
  `raw_outputs/gemini_english_voice_20261121T140012353451Z.json`. Additional
  voice runs have separate raw files and fixture metadata. Synthetic speech is
  not a test of every human accent, microphone or noisy environment.
- Live Hindi voice test: a 6.8-second Gemini-TTS synthetic Hindi clip produced a
  usable transcript in 2.794 seconds. It kept the amount and receipt but altered
  a possessive phrase and omitted the spoken rupee unit. The result in
  `raw_outputs/gemini_hindi_voice_20261121T140623277162Z.json` supports a bounded
  success claim with required review, not word-perfect recognition.
- First actual Gemini conversation run `20261121T140205149688Z`: 67/68 checks
  passed across 14 cases; six final case statuses reported temporary-provider
  fallback. The salary correction's amount field was right, but stale amount
  wording mislabeled as evidence appeared in the draft. The raw failure remains
  preserved. The latest report records repair/re-run results separately.
- Repaired Gemini run `20261121T141432370456Z`: 68/68 checks passed across 14
  conversations. All 19/19 recorded extraction calls validated live Gemini output,
  with zero fallbacks; all 14 final statuses reported live extraction. Code-handled
  refusals need no API call. Passing this authored set is not a guarantee for
  future inputs, provider availability or legal accuracy.
- Streamlit served HTTP 200 at the local address. A real headless Chrome session
  opened the app with the Render launcher, selected the synthetic refund example,
  prepared a draft, verified the actual selected tab was My draft, and cleared
  the case. Screenshots were inspected on desktop (1440px) and mobile
  (390px); no mobile horizontal overflow was observed in empty or active states. Streamlit's AppTest also
  exercised correction, manual edits, replacement approval and clearing.
- The solution PDF is generated with ReportLab and checked with pypdf to contain
  at most two pages. It requires the candidate's review and personal details.

These are prototype checks, not an accessibility audit, independent legal review,
or a representative benchmark of model language quality. HTTP adapter unit tests
use mocked responses; the separately recorded live Gemini text/audio runs do not.
One historical CPU-model smoke test is recorded in `evaluation/live_model_review.md`:
SmolLM2-135M generated an invalid extraction response, and the adapter rejected it
and fell back to the rules. That result is a measured model failure and fallback
success, not successful live extraction or a quality benchmark. It does not change
what the historical 68 demo evaluation assertions measure. Provider-specific
results must be interpreted with their recorded connection/fallback statuses.

Snapshots: `preview-desktop.png`, `preview-mobile.png`, `preview-case.png`,
`preview-draft.png`, `preview-mobile-case.png`. Original-layout screenshots are
preserved as `ui-before-desktop.png` and `ui-before-mobile.png`.

Deployment verification is local: the Render-style launcher bound to `0.0.0.0`
on the supplied port, and `/_stcore/health` returned HTTP 200 with `ok`. CORS and
XSRF protection remain enabled. A real Render deployment requires the repository
and account connection; no public URL or successful remote deploy is claimed.
