"""Measure latency for one local Ollama model. Writes the `ollama_probe` key of report.json.

python -m router.probe                      # OLLAMA_HOST (default http://localhost:11434)
python -m router.probe --model qwen2.5:1.5b --runs 5

If Ollama is not reachable, records status "not_measured" and exits 0.
Records latency and token counts only. Cost and quality are NOT measured here:
local inference has no per-token price, and no eval runs in this script.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report.json"

PROMPTS = [
    "Classify this ticket as return, billing, or support: 'invoice did not arrive'. Reply with one word.",
    "Classify this ticket as return, billing, or support: 'I want to send back a shirt'. Reply with one word.",
    "Classify this ticket as return, billing, or support: 'status page shows an outage'. Reply with one word.",
]


def _get(url: str, timeout: float) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310
        return json.loads(r.read())


def _post(url: str, payload: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        return json.loads(r.read())


def probe(host: str, model: str | None = None, runs: int = 3, timeout: float = 120.0) -> dict:
    base = {
        "host": host,
        "cost_usd": None,
        "quality": None,
        "cost_note": "not measured: local inference, hardware and power cost not tracked",
        "quality_note": "not measured: no eval in this probe",
    }
    try:
        tags = _get(f"{host}/api/tags", timeout=3.0)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {**base, "status": "not_measured", "reason": f"Ollama not reachable at {host}: {exc}"}
    names = [m.get("name") for m in tags.get("models", [])]
    if not names:
        return {**base, "status": "not_measured", "reason": "Ollama is up but has no models pulled"}
    model = model or names[0]
    if model not in names:
        return {**base, "status": "not_measured", "reason": f"model {model!r} not pulled; have {names}"}

    # Warm-up call so model load time is reported separately, not mixed into latency.
    warm = _post(f"{host}/api/generate", {"model": model, "prompt": "hi", "stream": False}, timeout)
    samples = []
    for i in range(runs):
        prompt = PROMPTS[i % len(PROMPTS)]
        t0 = time.perf_counter()
        out = _post(
            f"{host}/api/generate",
            {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0}},
            timeout,
        )
        wall_ms = (time.perf_counter() - t0) * 1000
        eval_ns = out.get("eval_duration") or 0
        samples.append(
            {
                "wall_ms": round(wall_ms, 1),
                "server_total_ms": round((out.get("total_duration") or 0) / 1e6, 1),
                "prompt_tokens": out.get("prompt_eval_count"),
                "output_tokens": out.get("eval_count"),
                "tokens_per_s": round(out["eval_count"] / (eval_ns / 1e9), 1) if eval_ns and out.get("eval_count") else None,
                "response": (out.get("response") or "").strip()[:40],
            }
        )
    walls = [s["wall_ms"] for s in samples]
    return {
        **base,
        "status": "measured",
        "model": model,
        "runs": runs,
        "warmup_load_ms": round((warm.get("load_duration") or 0) / 1e6, 1),
        "latency_ms_median": round(statistics.median(walls), 1),
        "latency_ms_min": min(walls),
        "latency_ms_max": max(walls),
        "samples": samples,
    }


def write(result: dict, path: Path = REPORT) -> None:
    report = json.loads(path.read_text()) if path.exists() else {}
    report["ollama_probe"] = result
    path.write_text(json.dumps(report, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    p.add_argument("--model", default=os.environ.get("OLLAMA_MODEL"))
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--out", type=Path, default=REPORT)
    args = p.parse_args(argv)
    host = args.host if args.host.startswith("http") else f"http://{args.host}"
    result = probe(host.rstrip("/"), args.model, args.runs)
    write(result, args.out)
    if result["status"] == "measured":
        print(f"measured {result['model']}: median {result['latency_ms_median']} ms over {result['runs']} runs "
              f"(warm-up load {result['warmup_load_ms']} ms). Cost and quality not measured.")
    else:
        print(f"not measured: {result['reason']}")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
