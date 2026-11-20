"""CR-04 spike: time local Ollama models on one ~6,000-token review prompt.

The prompt is built at runtime from the pinned structlog checkout in corpora/
(run scripts/fetch_corpora.sh first), so no corpus code is committed.

Usage: python scripts/local_model_spike.py [--repeat N] MODEL [MODEL ...]
Writes one JSON line per model and run to results/local_model_spike.jsonl.
Each run loads the model fresh, so repeats measure run-to-run spread.
"""

import argparse
import difflib
import json
import re
import subprocess
import threading
import time
import urllib.request
from datetime import date
from pathlib import Path

OLLAMA = "http://localhost:11434"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "corpora" / "structlog" / "src" / "structlog"
CONTEXT_FILES = ["processors.py", "_config.py", "_base.py", "stdlib.py", "dev.py"]
CONTEXT_CHARS = 24_600  # about 5,800 tokens of code for a Qwen-style tokenizer
NUM_CTX = 8192
OUT = ROOT / "results" / "local_model_spike.jsonl"

SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file": {"type": "string"},
                    "line": {"type": "integer"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                    "claim": {"type": "string"},
                },
                "required": ["file", "line", "severity", "claim"],
            },
        }
    },
    "required": ["findings"],
}


def build_prompt() -> tuple[str, int]:
    """Return the prompt and the 1-based line the seeded change is on."""
    original = (SRC / "processors.py").read_text().splitlines(keepends=True)
    changed = list(original)
    for i, line in enumerate(changed):
        if re.search(r"\bis None\b", line):
            changed[i] = line.replace(" is None", " is not None", 1)
            changed_line = i + 1
            break
    diff = "".join(
        difflib.unified_diff(
            original,
            changed,
            "a/src/structlog/processors.py",
            "b/src/structlog/processors.py",
        )
    )

    context, used = [], 0
    for name in CONTEXT_FILES:
        if used >= CONTEXT_CHARS:
            break
        context.append(f"# file: src/structlog/{name}\n")
        for line in (SRC / name).read_text().splitlines(keepends=True):
            if used + len(line) > CONTEXT_CHARS:
                used = CONTEXT_CHARS
                break
            context.append(line)
            used += len(line)

    prompt = (
        "You are a code reviewer. Review the diff below using the repository "
        "context. Report only real bugs introduced by the diff. Answer with JSON "
        "matching the schema: a list of findings with file, line, severity and "
        "claim.\n\n## Diff\n\n"
        f"{diff}\n## Repository context\n\n{''.join(context)}"
    )
    return prompt, changed_line


def call(path: str, body: dict, timeout: float = 1800) -> dict:
    request = urllib.request.Request(
        f"{OLLAMA}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def swap_used_mb() -> float:
    out = subprocess.run(
        ["sysctl", "-n", "vm.swapusage"], check=False, capture_output=True, text=True
    ).stdout
    match = re.search(r"used = ([\d.]+)M", out)
    return float(match.group(1)) if match else 0.0


def runner_rss_gb() -> float:
    """Resident memory of Ollama's model runner. /api/ps under-reports it.

    llama.cpp models run as llama-server and MLX models as `ollama runner`;
    the `ollama serve` process itself is excluded.
    """
    out = subprocess.run(
        ["ps", "-axo", "rss=,args="], check=False, capture_output=True, text=True
    ).stdout
    rss_kb = 0
    for line in out.splitlines():
        rss, _, args = line.strip().partition(" ")
        if "Ollama.app/Contents/Resources/" in args and not args.endswith(" serve"):
            rss_kb = max(rss_kb, int(rss))
    return rss_kb / 2**20


def free_memory_pct() -> int | None:
    out = subprocess.run(
        ["memory_pressure", "-Q"], check=False, capture_output=True, text=True
    ).stdout
    match = re.search(r"free percentage: (\d+)%", out)
    return int(match.group(1)) if match else None


def run(model: str, prompt: str, changed_line: int) -> dict:
    call("/api/generate", {"model": model, "keep_alive": 0})  # unload if loaded
    swap_start = swap_used_mb()
    samples: dict = {
        "swap_peak_mb": swap_start,
        "rss_peak_gb": 0.0,
        "free_min_pct": free_memory_pct(),
        "runner": None,
    }
    done = threading.Event()

    def sample() -> None:
        while not done.wait(1.0):
            samples["swap_peak_mb"] = max(samples["swap_peak_mb"], swap_used_mb())
            samples["rss_peak_gb"] = max(samples["rss_peak_gb"], runner_rss_gb())
            free = free_memory_pct()
            if free is not None:
                samples["free_min_pct"] = min(samples["free_min_pct"] or 100, free)
            with urllib.request.urlopen(f"{OLLAMA}/api/ps", timeout=10) as r:
                loaded = json.loads(r.read()).get("models", [])
            if loaded:
                samples["runner"] = loaded[0].get("runner")

    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    started = time.monotonic()
    error = None
    try:
        reply = call(
            "/api/generate",
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "format": SCHEMA,
                "options": {"temperature": 0, "num_ctx": NUM_CTX, "num_predict": 1024},
            },
        )
    except (OSError, ValueError) as exc:  # a failed run is a result, not a crash
        reply, error = {}, f"{type(exc).__name__}: {exc}"
    wall = time.monotonic() - started
    done.set()
    thread.join()
    call("/api/generate", {"model": model, "keep_alive": 0})

    # Same rule as the Study B matcher: right file, within 3 lines.
    try:
        found = json.loads(reply.get("response", ""))["findings"]
        valid_json, findings = True, len(found)
        caught = any(
            str(f.get("file", "")).endswith("processors.py")
            and abs(int(f.get("line", 0)) - changed_line) <= 3
            for f in found
        )
    except (ValueError, KeyError, TypeError):
        valid_json, findings, caught = False, None, False

    ns = 1e9
    prompt_s = reply.get("prompt_eval_duration", 0) / ns
    eval_s = reply.get("eval_duration", 0) / ns
    return {
        "model": model,
        "date": date.today().isoformat(),
        "error": error,
        "prompt_tokens": reply.get("prompt_eval_count"),
        "output_tokens": reply.get("eval_count"),
        "load_s": round(reply.get("load_duration", 0) / ns, 1),
        "prompt_tok_per_s": round(reply["prompt_eval_count"] / prompt_s, 1)
        if prompt_s
        else None,
        "gen_tok_per_s": round(reply["eval_count"] / eval_s, 1) if eval_s else None,
        "first_token_s": round((reply.get("load_duration", 0) / ns) + prompt_s, 1),
        "wall_s": round(wall, 1),
        "runner": samples["runner"],
        "runner_rss_peak_gb": round(samples["rss_peak_gb"], 1),
        "free_mem_min_pct": samples["free_min_pct"],
        "swap_start_mb": round(swap_start),
        "swap_peak_mb": round(samples["swap_peak_mb"]),
        "valid_json": valid_json,
        "findings": findings,
        "caught": caught,
    }


def main(models: list[str], repeat: int) -> None:
    prompt, changed_line = build_prompt()
    OUT.parent.mkdir(exist_ok=True)
    for model in models:
        for n in range(1, repeat + 1):
            result = {"run": n, **run(model, prompt, changed_line)}
            print(json.dumps(result), flush=True)
            with OUT.open("a") as f:
                f.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("models", nargs="+")
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    main(args.models, args.repeat)
