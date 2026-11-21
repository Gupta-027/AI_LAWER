# Live local model smoke test

This is one measured experiment, separate from the deterministic behavior suite and mocked HTTP tests. It does not measure general legal, Hindi, Hinglish or production model quality.

- Run: `20261121T131818078377Z` (21 November 2026, 18:48:18 IST start).
- Input: a new synthetic English headphone-return story; no real user data.
- Model: public `HuggingFaceTB/SmolLM2-135M-Instruct`, CPU float32, four Torch threads, deterministic generation, maximum 180 new tokens.
- Installed libraries: Torch `2.13.0+cpu`, Transformers `5.16.1`.
- Transport: a genuine localhost HTTP server created by the smoke script wraps `transformers` inference. The existing `CaseEngine` calls the existing `LLMAdapter`, which makes an actual HTTP request. This is a local transport harness, not an external commercial API or Ollama itself.
- Unedited evidence: `raw_outputs/live_model_smoke_20261121T131818078377Z.json` contains the model request, raw decoded model response, final case state, application reply and timings. Special generation tokens are removed by the normal tokenizer decoder; JSON is never repaired or hardcoded.

## Observed result

True model generation ran, but useful model extraction **failed**. The model ignored the JSON-only instruction and repeated advice about checking a return address. It reached the 180-token cap. The adapter rejected the non-JSON response and explicitly reported `Model unavailable or response rejected; using demo rules`.

The fallback retained `pickup_status = Pickup confirmed`, `approval_status = Unknown`, and amount `₹3799`. The application then asked whether the seller said payment had been issued. This demonstrates rejection and fallback for this one failure; it does not establish successful live AI understanding.

This is a real AI mistake to discuss in the assignment: a small instruction model failed the requested extraction schema and produced irrelevant repetitive text. The raw output supports this account. A larger model, stronger structured-output enforcement, and a broader adversarial evaluation are still needed before relying on live extraction.

## Measured resources

| Measurement | Observed |
|---|---:|
| Model assets downloaded | 272,437,573 bytes |
| Download/cache check | 62.994 seconds |
| Model load | 0.701 seconds |
| Warm-up | 0.094 seconds |
| Prompt tokens | 361 |
| Generated tokens | 180 |
| Generation | 7.553 seconds |
| Engine HTTP call | 7.751 seconds |
| Total script time | 76.592 seconds |
| Paid API spend | USD 0 |

Electricity, network cost and deployment capacity were not measured. These timings describe one warmed local CPU generation, not service latency at scale.

## Reproduce

With the optional dependencies in `requirements-local-model.txt`, run `python scripts/live_model_smoke.py`. It downloads only official model/tokenizer files into ignored `.model-cache/SMOL`, starts a temporary loopback server, runs the synthetic case and writes a fresh exclusive-created raw JSON artifact. First run requires internet and about 273 MB of disk space for model assets, plus runtime/cache overhead. Existing process environment is unchanged outside the child script. Model binaries are excluded from the submission archive.
