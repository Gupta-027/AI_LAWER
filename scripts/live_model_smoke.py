"""Optional real CPU model smoke test; transport is a local test harness.

This is not a hosted API or an evaluation of a production-size language model.
Downloads only the official public model assets into the ignored workspace cache.
Run: python scripts/live_model_smoke.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CACHE = ROOT / ".model-cache"
os.environ["HF_HOME"] = str(CACHE / "hf-home")
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
MODEL_ID = "HuggingFaceTB/SmolLM2-135M-Instruct"
MODEL_PATH = CACHE / "SMOL"
SYNTHETIC_INPUT = (
    "I bought headphones online for Rs 3799. The courier collected the return "
    "yesterday. The shop has not told me whether the refund was approved. "
    "I have a pickup receipt. Please help me ask for the actual refund status."
)


def main() -> int:
    started = time.perf_counter()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "raw_outputs" / ("live_model_smoke_" + stamp + ".json")
    result: dict = {
        "run_id": stamp,
        "synthetic_input": SYNTHETIC_INPUT,
        "model_id": MODEL_ID,
        "transport": "Actual localhost HTTP; stdlib server wraps true transformers model.generate output",
        "scope": "One CPU smoke test, not production model quality or general accuracy",
        "api_spend_usd": 0,
        "device": "cpu",
        "torch_threads": 4,
        "max_new_tokens": 180,
        "raw_model_text": None,
        "model_request_messages": None,
    }
    server = None
    try:
        import torch
        import transformers
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForCausalLM, AutoTokenizer
        result["versions"] = {"torch": torch.__version__, "transformers": transformers.__version__}
        torch.set_num_threads(4)
        torch.manual_seed(0)
        download_start = time.perf_counter()
        snapshot_download(
            MODEL_ID, local_dir=str(MODEL_PATH), cache_dir=str(CACHE / "hub"),
            allow_patterns=["config.json", "generation_config.json", "model.safetensors",
                            "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
                            "vocab.json", "merges.txt"], max_workers=4,
        )
        result["download_or_cache_check_seconds"] = round(time.perf_counter() - download_start, 3)
        result["model_assets_bytes"] = sum(p.stat().st_size for p in MODEL_PATH.iterdir() if p.is_file())
        load_start = time.perf_counter()
        tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH), local_files_only=True, trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(
            str(MODEL_PATH), local_files_only=True, trust_remote_code=False,
            use_safetensors=True, dtype=torch.float32,
        ).eval()
        result["load_seconds"] = round(time.perf_counter() - load_start, 3)
        warm_start = time.perf_counter()
        warm = tokenizer("Hello", return_tensors="pt")
        with torch.inference_mode():
            model.generate(**warm, max_new_tokens=1, do_sample=False, pad_token_id=tokenizer.eos_token_id)
        result["warmup_seconds"] = round(time.perf_counter() - warm_start, 3)
        done = threading.Event()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:
                pass

            def do_POST(self) -> None:
                if self.path != "/v1/chat/completions":
                    self.send_error(404)
                    return
                try:
                    request = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                    result["model_request_messages"] = request["messages"]
                    inputs = tokenizer.apply_chat_template(
                        request["messages"], add_generation_prompt=True,
                        return_tensors="pt", return_dict=True,
                    )
                    gen_start = time.perf_counter()
                    with torch.inference_mode():
                        generated = model.generate(
                            **inputs, max_new_tokens=180, do_sample=False,
                            pad_token_id=tokenizer.eos_token_id,
                        )
                    new_tokens = generated[0][inputs["input_ids"].shape[-1]:]
                    # Decoding is the only transformation: do not repair or hardcode JSON.
                    raw = tokenizer.decode(new_tokens, skip_special_tokens=True)
                    result["raw_model_text"] = raw
                    result["generation_seconds"] = round(time.perf_counter() - gen_start, 3)
                    result["input_tokens"] = int(inputs["input_ids"].shape[-1])
                    result["generated_tokens"] = int(new_tokens.shape[-1])
                    body = json.dumps({"choices": [{"message": {"role": "assistant", "content": raw}}]}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:
                    result["generation_error_type"] = type(exc).__name__
                    self.send_error(500, "Local smoke generation failed")
                finally:
                    done.set()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        # These changes apply only to this script's process, never the parent's shell.
        os.environ["NYAYA_PROVIDER"] = "ollama"
        os.environ["NYAYA_MODEL"] = MODEL_ID
        os.environ["NYAYA_BASE_URL"] = "http://127.0.0.1:" + str(server.server_address[1]) + "/v1"
        os.environ["NYAYA_API_KEY"] = ""
        from nyaya import CaseEngine, CaseRecord
        case = CaseRecord()
        engine = CaseEngine()
        call_start = time.perf_counter()
        reply = engine.process(case, SYNTHETIC_INPUT)
        result["engine_call_seconds"] = round(time.perf_counter() - call_start, 3)
        done.wait(timeout=30)
        engine.draft(case)
        result["engine_reply"] = reply
        result["engine_final_state"] = case.model_dump()
        result["guidance"] = engine.guidance(case)
        result["adapter_status"] = engine.adapter.status
        result["live_generation_observed"] = result["raw_model_text"] is not None
        try:
            decoded = json.loads(result["raw_model_text"] or "")
            result["model_returned_json_object"] = isinstance(decoded, dict)
        except (ValueError, TypeError):
            result["model_returned_json_object"] = False
    except Exception as exc:
        # Only type is recorded, avoiding accidental credential/proxy exception details.
        result["setup_error_type"] = type(exc).__name__
        result["live_generation_observed"] = False
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        result["total_seconds"] = round(time.perf_counter() - started, 3)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(json.dumps({"output": str(out), "live_generation_observed": result.get("live_generation_observed"),
                          "adapter_status": result.get("adapter_status"), "setup_error_type": result.get("setup_error_type"),
                          "total_seconds": result["total_seconds"]}, ensure_ascii=True))
    return 0 if result.get("live_generation_observed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
