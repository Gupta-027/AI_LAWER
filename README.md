# Nyaya Saathi

A working case-preparation prototype for Kuku's **Problem 2: Build an AI Lawyer**. Describe an everyday Indian legal problem, answer one follow-up at a time, review the case record, and prepare factual correspondence.

Gemini can interpret typed stories and transcribe recorded Hindi, English or Hinglish. Review the case facts and voice transcript before using them. Python controls the follow-up question, citations, correction handling and factual draft; the model does not invent legal guidance.

Without an environment file or provider variables, the app opens a **limited rules demo**. For live AI and voice, configure Gemini server-side below. The mode badge distinguishes an unverified configuration, a successful extraction connection and a rules fallback.

## Deploy on Render

The app includes a ready-to-use [Render Blueprint](render.yaml). Push this folder
to your Git repository, then choose **New → Blueprint** in Render and select that
repository. The configuration creates a Python Web Service configured for Gemini
and asks you to enter `GEMINI_API_KEY` securely. Follow [the complete Render setup guide](docs/RENDER.md) for account,
repository, environment-variable and model-provider setup.

For manual Web Service setup:

| Setting | Value |
| --- | --- |
| Build command | `python -m pip install -r requirements.txt` |
| Start command | `python scripts/start_render.py` |
| Health check | `/_stcore/health` |
| Environment | `NYAYA_PROVIDER=gemini`, `GEMINI_MODEL=gemini-3.5-flash-lite`, secret `GEMINI_API_KEY` |

The launcher binds to Render's assigned `PORT` on `0.0.0.0`; local development
continues to use the command below. The hosted build installs only the application
runtime. It does not download model weights or run your laptop's Ollama server.
The included Gemini integration uses Google's native REST API for text and
audio. Keep the key in Render's secret environment settings. Set
`NYAYA_PROVIDER=demo` if you want only the offline rules workflow.

The interface has a composer-first welcome screen and a conversation beside
the case workspace on desktop. **My case**, **Next steps** and **My draft** keep
the supporting material together; narrow screens stack the panels. Preparing a
draft opens its tab automatically. Fact editing uses readable labels, and saved
manual wording still receives a replacement preview.

See the [desktop preview](docs/preview-desktop.png), [active workspace](docs/preview-case.png),
[draft preview](docs/preview-draft.png) and [mobile preview](docs/preview-mobile.png).
The [voice transcript review](docs/preview-voice-review.png) and
[mobile recorder](docs/preview-mobile-voice.png) show the recording workflow.

## Start on Windows

Python 3.11 or newer is recommended; development used Python 3.13. Run these commands in PowerShell from this project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m streamlit run app.py
```

Open the local URL printed by Streamlit, normally <http://localhost:8501>. `app.py` is a simple chat: speak or type a problem, get plain-language advice in Hindi or English, read aloud automatically, with a follow-up question each turn and a "New chat" button (needs `GEMINI_API_KEY`; audio uses free Google TTS via gTTS and needs internet). The older step-by-step case builder with drafts runs with `streamlit run detailed_app.py`. No environment file is needed for that builder's rules demo. Once dependencies are installed, the last line is the only launch command. Press `Ctrl+C` in the terminal to stop.

If using an already prepared Python environment:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

On macOS/Linux, create the same virtual environment, then use `.venv/bin/python` in place of `.\.venv\Scripts\python`.

## What to try

Type naturally in English, Hindi in Devanagari, or Hinglish. Choose conversation and draft languages independently. The case record is editable when extraction misses a detail.

To speak, expand **Tell your story by voice · हिन्दी / English**, choose the
spoken language, record a short story and select **Transcribe recording**.
Edit **Review your transcript**, then select **Use this transcript**. Recording
or transcribing alone does not update the case. See [voice setup and privacy](docs/VOICE.md).

| Situation | Bounded output |
| --- | --- |
| Rental deposit | Request the balance, supporting details for stated deductions, or an itemized explanation. |
| Online refund | Distinguish pickup, approval and claimed payment; request status or a transaction reference; offer cited NCH guidance. |
| Unpaid salary | Record periods and amount, then prepare a factual employer/payroll request. |
| Notice explanation | Separate quoted allegations, requested action and dates from the user's account; prepare questions for qualified review. |
| Another issue | Organize facts and questions for a lawyer, with an explicit scope limit. |

Use **Prepare draft** even with missing details. Replace bracketed placeholders, save edits, copy or download as TXT. In **My case**, expand **Edit case details** to correct a fact. Correcting case details marks an existing draft for review. When replacing a manually edited draft, review the proposed replacement and diff before applying it. **Clear case** resets session state. Nothing is sent or filed by the app.

The buttons on the first screen are labeled synthetic examples. They enter their text into the same conversation engine used by typed messages. They are not recorded model responses. A short interview sequence is in [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md).

## Connect Gemini for text and voice

Create `.env` from `.env.example` if it does not already exist:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set your actual key in that ignored file, then restart Streamlit:

```dotenv
NYAYA_PROVIDER=gemini
GEMINI_API_KEY=YOUR_SERVER_SIDE_GEMINI_KEY
GEMINI_MODEL=gemini-3.5-flash-lite
```

`YOUR_SERVER_SIDE_GEMINI_KEY` is a placeholder, not a usable credential. The
native adapter sends authentication only in Google's request header. The selected
model must be available to your API project and support audio plus structured
output. Existing process environment variables take precedence over `.env`.
Keep the key out of Git, browser fields, test fixtures and shared archives.

After sending a message, inspect the mode badge and **How this works** status.
Authentication, quota, model, network or rejected-output errors are shown without
provider error bodies or credentials. Failed extraction uses an explicit rules
fallback; failed transcription does not invent or submit a story.

The English and Hindi synthetic voice fixtures produced usable transcripts from
`gemini-3.5-flash-lite` in **3.01 seconds** and **2.794 seconds**, respectively.
The Hindi result preserved the amount and receipt but changed a possessive phrase
and omitted the spoken rupee unit, so it was not word-perfect. Raw results and
usage are preserved in the [English run](raw_outputs/gemini_english_voice_20261121T140012353451Z.json)
and [Hindi run](raw_outputs/gemini_hindi_voice_20261121T140623277162Z.json).
These are small measured tests, not accuracy claims for every speaker. The
latest conversational evaluation and any additional voice runs are documented
under [evaluation](evaluation/report.md) and `raw_outputs/`.

## Alternative local model for typed input

Install [Ollama from its official site](https://ollama.com/download), then download the model:

```powershell
ollama pull qwen2.5:3b
```

Ollama must be running. Open its desktop application or run `ollama serve` in a separate terminal if the server is not already running. If it reports that the port is already in use, the existing server may already be active.

Set these values in `.env`, then restart Streamlit. This switches typed-case
extraction to Ollama; the voice recorder still needs a Gemini key:

```dotenv
NYAYA_PROVIDER=ollama
NYAYA_BASE_URL=http://localhost:11434/v1
NYAYA_MODEL=qwen2.5:3b
NYAYA_API_KEY=
```

This adapter calls Ollama's [OpenAI-compatible local endpoint](https://docs.ollama.com/api/openai-compatibility). Local model use needs no paid API account, but requires a model download and suitable memory/compute. [The selected model's official listing](https://ollama.com/library/qwen2.5:3b) includes its size and license; review those before wider use. Small-model multilingual and extraction quality must be evaluated rather than assumed.

Check the provider status after sending a new message. A configured provider label alone does not prove a successful model call. The historical local smoke used a separate tiny model and observed rejection followed by fallback; it did not verify successful extraction with Ollama or Qwen. Run a separate evaluation for your chosen endpoint.

## Connect another compatible server

Use an existing provider that supports `/v1/chat/completions`, with its actual endpoint, model ID and server-side key:

```dotenv
NYAYA_PROVIDER=openai
NYAYA_BASE_URL=https://YOUR-COMPATIBLE-SERVER/v1
NYAYA_MODEL=YOUR-MODEL-ID
NYAYA_API_KEY=YOUR-SERVER-SIDE-KEY
```

The placeholders above are not a working service. `openai` is the adapter mode for a compatible protocol, not a promise that every model/provider supports the same options. Restart after changing settings. Existing process environment variables take precedence over `.env`.

Keep `.env` out of source control. Keys and model settings stay in the Python server, not browser-side configuration. In AI mode, the configured model service receives case text and may retain its own logs. In local Ollama mode, check that the endpoint really points to your local server and that the chosen model runs locally.

## Verify and regenerate artifacts

From the project root, using the same Python environment as the app:

```powershell
python -m unittest discover -s tests -v
python scripts/evaluate.py
python -m pip install -r requirements-artifacts.txt
python scripts/build_solution_pdf.py
```

For the virtual environment, replace `python` with `.\.venv\Scripts\python` on Windows. To exercise a configured model explicitly:

```powershell
python scripts/evaluate.py --provider ollama
# Or: python scripts/evaluate.py --provider openai
# Native Gemini:
python scripts/evaluate.py --provider gemini
```

`python scripts/evaluate.py --help` lists the actual provider choices. The default evaluation explicitly selects `demo`, regardless of the app provider. The original synthetic inputs and expected behavior are in [evaluation/cases.json](evaluation/cases.json); assertions are in [evaluation/runner.py](evaluation/runner.py).

Each evaluation creates new timestamped JSON files under `raw_outputs/`, directly from engine inputs, responses and state snapshots. Earlier raw files are preserved. [evaluation/report.md](evaluation/report.md) and `evaluation/report.json` describe the latest run separately from the raw evidence. They record the requested provider and observed provider status; a fallback must not be presented as measured LLM success. A failed check remains visible in those artifacts.

[evaluation/review_notes.md](evaluation/review_notes.md) records real development failures and the stricter checks added after manual review. Check counts grew as coverage improved; intermediate percentages are not directly comparable. Adapter tests use mocked HTTP responses and do not establish successful live-model inference.

The first 14-case Gemini run (`20261121T140205149688Z`) passed **67/68** assertions.
Its salary case updated the amount to 42000 but mislabeled an old 48000 clause as
evidence, which then appeared in the draft. Six final case statuses reported a
temporary-provider fallback. That unedited run remains archived. The latest
report records whether the repair and subsequent Gemini run passed; do not
reinterpret a fallback as a successful model extraction.

After the evidence-type repair and bounded temporary-error retries, the recorded
Gemini run `20261121T141432370456Z` passed **68/68** checks across all 14 cases.
All **19/19 recorded extraction calls** validated live Gemini output, with **0
fallbacks**. All 14 final case statuses also reported validated live extraction.
Code-handled refusals do not need an API call. These are recorded outcomes, not
a guarantee that every possible input or future API call will succeed.

## Optional real-model CPU smoke test

A separate smoke test runs `HuggingFaceTB/SmolLM2-135M-Instruct` through actual model generation, a temporary localhost HTTP endpoint, `CaseEngine` and `LLMAdapter`. It is a reproducible integration experiment, not the default UI provider or a recommended legal-help model.

```powershell
python -m pip install -r requirements-local-model.txt
python scripts/live_model_smoke.py
```

Use your virtual-environment Python as above. The first run downloads approximately **272 MB of model assets**, plus the optional Python dependencies; later runs reuse the ignored `.model-cache/` directory. The script writes a new raw artifact and stops its temporary server. It does not change `.env` or the app's default mode. Read the raw JSON: script success means generation was observed, not that the model returned valid extraction.

The actual recorded run took **76.592 seconds total**, including **62.994 seconds** for model download/cache checking and **7.553 seconds** to generate **180 tokens** on CPU. API spend was **$0**; hardware and electricity are not measured. The model ignored the JSON schema and repeated irrelevant return-address advice. The adapter rejected that response and fell back to rules; the case kept pickup confirmed and approval unknown. This is **one observed schema failure and fallback**, not an inference benchmark or successful live extraction. See [the unedited raw run](raw_outputs/live_model_smoke_20261121T131818078377Z.json) and [the live-model review](evaluation/live_model_review.md). Repeated timings may differ.

The historical rules evaluation passed **68/68 behavioral assertions across 14 synthetic conversations**. The latest provider, actual per-case connection status and asserted results are in [evaluation/report.md](evaluation/report.md). The final Gemini/voice revision passed **68 unit test methods**, covering mocked Gemini responses, voice-review gates, notice integrity, workspace editing and Render startup. Run the test command for current results after changes; the PDF generator counts defined methods without treating that count alone as a pass result. Unit tests do not replace the separately recorded live model and voice runs.

The suite covers paired rental deductions, pickup without approval, seller payment claims, salary correction after manual drafting, notices with and without a stated response date, invented-law requests, unknown answers, Hindi and an unfamiliar issue. A held-out synthetic refund input goes through the same `CaseEngine.process` entry point as UI messages. It is absent from the UI examples; that does not establish broad generalization.

The PDF generator reads the latest actual evaluation report, writes [docs/solution-draft.pdf](docs/solution-draft.pdf), and checks its page count. It labels missing results instead of inventing them. Review and personalize the candidate details, rationale and AI-use statement before submission. Keep the PDF at two pages or fewer.

## Architecture and evidence

```text
app.py                 Streamlit UI and session state
nyaya/                 Validated record, conversation engine, model adapter, drafts, sources
nyaya/ui.py, ui.css     Presentation helpers, responsive workspace and visual tokens
nyaya/gemini.py         Native Gemini text/audio requests and safe provider errors
nyaya/voice.py          Transcript staging and explicit review gate
render.yaml            Render service, health check and server-side environment configuration
scripts/start_render.py Port-aware hosted launcher
requirements-artifacts.txt Optional local PDF generation dependencies
data/sources.json      Allowed claim text with official URL, locator, jurisdiction and check date
data/SOURCES.md        Retrieval evidence and limits of the source collection
evaluation/            Original synthetic inputs, separate checks and latest report
raw_outputs/           Actual unedited synthetic evaluation runs
tests/                 Workflow and adapter/state regression checks
scripts/               Evaluation entry point and reproducible solution-PDF generator
docs/PLAN.md           Assignment review, scope decisions and design references
docs/WALKTHROUGH.md    Short live-demo sequence
```

Python handles case state, revision tracking, draft-review controls, source selection/validation and exports. A configured LLM helps interpret language and propose structured facts; the rules path provides an explicit offline fallback. The small source collection supports narrow procedural statements. A source ID by itself is insufficient evidence for a new legal claim.

The app stores active conversations, real recordings and draft transcripts only in Streamlit server session memory. It does not create case files, a database or chat logs. Google receives audio only when you select **Transcribe recording**, and receives reviewed case text in Gemini mode. A refresh, disconnect or server restart may lose a case. Synthetic evaluation files are intentionally saved; do not put real conversations or recordings in the evaluation fixtures. Model services, hosting and infrastructure can have their own retention policies.

## Limitations to discuss

- This is a case-preparation prototype, not an advocate or a legal-rights determination service. Formal or urgent matters need qualified review.
- No universal rental-deposit, salary or notice-response deadline is asserted. State rules, the agreement, employment arrangement and the actual notice may change the advice.
- NCH is a pre-litigation grievance option, with no guaranteed remedy; its process-duration description is not a seller refund deadline. See [source scope notes](data/SOURCES.md).
- Rules-demo extraction is limited. Check spelling, amounts, dates, parties and translation; edit the record before using a draft.
- A historical tiny-model smoke produced unusable extraction and exercised fallback. Current Gemini tests and voice runs provide bounded evidence, not representative production latency, broad multilingual accuracy or independent legal review. Actual API charges depend on your model, account and quota; no billing total is inferred from token counts.
- Voice uses browser microphone permissions on HTTPS or localhost, with a two-minute/10 MiB limit and transcript review. Recognition can miss accents, background speech, names and numbers. There is no OCR pipeline, automatic filing, durable storage or production authentication. Sources are an English-language checked snapshot, not continuously updated legal research.

The assignment allows a focused issue; four bounded workflows are an implementation choice retained from the earlier ChatGPT proposal. This project is ready for local running and a Render Web Service. A public URL is created when you connect your repository and deploy it in your Render account. Before handing it in, share the actual app or repository link, include the reviewed two-page PDF, and use your own name/roll number/branch and explanation.
