# Deploy Nyaya Saathi on Render

The project is prepared for a **Python Web Service** on Render. It is a Streamlit
server, so use a Web Service rather than a Static Site. This guide configures the
existing application; a Git repository and your Render account are needed to
create its actual public URL.

## Deploy with the included Blueprint

1. Put this project in a GitHub, GitLab or Bitbucket repository. Keep `app.py`,
   `render.yaml`, `.python-version`, `requirements.txt`, `.streamlit/`, `nyaya/`,
   `data/` and `scripts/start_render.py` in the repository. The root of this
   project should be the Render service's root directory.
2. Keep `.env`, `.streamlit/secrets.toml`, `.model-cache/`, virtual environments
   and the generated submission ZIP out of Git. `.gitignore` already excludes
   them. Model files are unnecessary for this deployment.
3. In [Render Dashboard](https://dashboard.render.com/), choose **New > Blueprint**,
   connect the repository, and select its branch.
4. Review the `nyaya-saathi` service before creating it. The included Blueprint
   chooses the **Free** plan and **Singapore** region. It sets
   `NYAYA_PROVIDER=gemini` and `GEMINI_MODEL=gemini-3.5-flash-lite`. Enter your
   `GEMINI_API_KEY` when Render asks for that unsynced secret. Change the service
   name if it conflicts with one you already use. Deploy the Blueprint.
5. Wait for the service to become healthy, then open the actual `onrender.com`
   URL shown by Render. Try a synthetic example, prepare a draft, and download
   the TXT file. Send a fresh message and check the actual Gemini connection
   status; then try recording, reviewing and confirming a short synthetic story.

An existing `render.yaml` is sufficient for this Blueprint flow. A deploy-button
URL is intentionally not hardcoded because this checkout has no repository URL.
After pushing your own repository, Render's documented deploy-button format is
`https://render.com/deploy?repo=YOUR_REPOSITORY_HTTPS_URL`. The Blueprint uses
`autoDeployTrigger: commit` for your own connected repository. If sharing this as
a deploy-button template for other people, change it to `off`, as Render
recommends for independently deployed template copies.

## Manual Web Service setup

Use these settings if creating the service manually instead of using a Blueprint:

| Setting | Value |
| --- | --- |
| Service type | Web Service |
| Language/runtime | Python |
| Branch | The branch containing this project |
| Root directory | Blank if this project is at the repository root |
| Build command | `python -m pip install -r requirements.txt` |
| Start command | `python scripts/start_render.py` |
| Health check path | `/_stcore/health` |
| Instance plan | Free for this assignment demo |
| Region | Singapore, or your chosen available region |
| `NYAYA_PROVIDER` | `gemini` |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` |
| `GEMINI_API_KEY` | Your key, stored as a secret environment variable |
| `PYTHONUNBUFFERED` | `1` |

The `.python-version` file pins Python 3.13.1, matching the local development
runtime. The launcher reads Render's `PORT` environment variable, defaults to
10000, and binds to `0.0.0.0`. It overrides the local loopback setting without
weakening CORS or XSRF protection. File watching and telemetry are disabled for
the hosted process. The Blueprint also generates a server-side Streamlit cookie
secret; for a manual service, set `STREAMLIT_SERVER_COOKIE_SECRET` to a long random
value in Render's environment settings.

## Gemini text and voice on the hosted service

The Blueprint expects a server-side Gemini key. For a manually created service,
add the following in **Environment**, using your actual key, then redeploy:

```dotenv
NYAYA_PROVIDER=gemini
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=YOUR_SERVER_SIDE_GEMINI_KEY
```

The key shown above is a placeholder. Keep the real value in Render's secret
environment settings; do not commit it or put it in a browser field. Native
Gemini uses Google's `generateContent` REST API with header authentication and
structured responses. The chosen model must support structured text extraction
and audio input for your API project. Check the status after a new message:
configuration alone does not establish that a response was valid. Failed or
rejected text extraction uses an explicit rules fallback. Failed voice
transcription does not submit a transcript.

To run only the no-key rules demo, set `NYAYA_PROVIDER=demo`. Voice transcription
still needs a Gemini key. Alternative compatible text endpoints remain supported;
see the README for their separate environment variables.

The microphone recorder uses the HTTPS Render URL and browser permission.
Recording uploads a WAV to session memory. **Transcribe recording** sends it to
Google; **Use this transcript** sends only the reviewed text into the case. Check
names, amounts and dates before confirming. No extra Node build, model download
or speech service is installed on Render. See [the voice guide](VOICE.md).

`localhost:11434` inside Render points to Render's container, not your laptop.
Your local Ollama server is therefore not a hosted model endpoint. This free web
service does not install Torch, Transformers, model files or Ollama. For this
demo, use native Gemini or another reachable compatible API for AI extraction;
otherwise leave rules mode enabled.

## Sessions, resource use and free-plan behavior

Cases, recordings and draft transcripts stay in server session memory. A restart,
deploy, expired connection or free-service spin-down can lose them. Download a useful draft before leaving.
The app does not write real conversations to its evaluation files. Use synthetic
details for the public assignment demo, particularly with an external provider.

Render's free web services currently spin down after 15 minutes without inbound
traffic and can take about a minute to restart. Open the app before the interview
and allow that initial wait. Free services can restart and have ephemeral local
filesystems. This deployment is an assignment prototype, not a production legal
service.

`requirements.txt` contains only the application runtime dependencies. Generating
the assignment PDF locally requires `python -m pip install -r
requirements-artifacts.txt`; those PDF tools are not installed by the Render
build. The optional local-model experiment has its own requirements file and is
not part of hosted startup.

## Troubleshooting

- **No open port detected:** use the exact start command above. The launcher
  binds to `0.0.0.0` and honors `PORT`; running Streamlit with only its local
  loopback configuration cannot serve public requests.
- **Import error during deploy:** confirm the root directory points at the folder
  containing `requirements.txt`, `app.py`, `nyaya/` and `data/`.
- **Health check fails:** confirm `/_stcore/health`, inspect startup logs, and do
  not add a trailing `/` to the configured health path.
- **AI falls back:** verify the actual compatible endpoint, model ID, key and JSON
  mode support in the provider's documentation. The UI reports a fallback instead
  of treating it as a successful AI response.
- **Gemini rejects authentication or quota:** verify the secret key, API project,
  available model and account limits in Google AI Studio. These are provider
  responses, not an indication that changing the frontend will repair the key.
- **Microphone is unavailable:** open the HTTPS app URL and allow microphone
  access in both the browser and operating system. A remote plain-HTTP address
  may not support recording. Typed input remains available.
- **Transcription is wrong:** edit it before selecting **Use this transcript**.
  An inaccurate transcript should not be accepted just because the request worked.
- **Case disappeared:** in-memory sessions do not survive all disconnects or
  restarts. Start a fresh case; this prototype has no account or case database.

Sources checked on 21 November 2026: [Render web services and port binding](https://render.com/docs/web-services#port-binding),
[Blueprint fields](https://render.com/docs/blueprint-spec),
[Python version selection](https://render.com/docs/python-version), and
[free-service behavior](https://render.com/docs/free), and
[deploy-button guidance](https://render.com/docs/deploy-to-render). Render's old
`/docs/deploy-streamlit` path returned 404; the current general Python web-service
instructions are used instead.
