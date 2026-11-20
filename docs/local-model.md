# Local model

CR-04 spike: can a ~30B mixture-of-experts model at 4-bit answer a 6,000-token review prompt on the project machine, and how fast?

**Answer: yes, with little headroom.** `qwen3-coder:30b` (30.5B MoE, Q4_K_M) answers in about 20 seconds to first token and generates at about 52 tokens/s, but leaves only 8 to 12% of memory free and grew swap slightly on one of four runs. It is the recommended `local-main`. The fallback is `gpt-oss:20b`.

## Setup

| | |
| --- | --- |
| Machine | Mac mini, Apple M4 Pro, 24 GB unified memory, macOS 26.5.1 |
| Server | Ollama 0.40.16 (server; the bundled CLI is 0.32.1 and misses some models in `ollama list`, so the spike uses the HTTP API) |
| Date | 2026-11-20 |
| Prompt | One review prompt built at runtime from structlog at the pinned commit: a one-line diff (`is None` flipped to `is not None` in `processors.py`, line 169) plus surrounding code. About 6,000 tokens; the exact count per model is below, since tokenizers differ. |
| Options | `num_ctx` 8192, temperature 0, `think: false`, JSON schema enforced with `format`, `num_predict` 1024 |
| Isolation | One model loaded at a time, unloaded before and after its run. No embedding model resident. |

Reproduce: `./scripts/fetch_corpora.sh`, then `python scripts/local_model_spike.py [--repeat N] MODEL [MODEL ...]`. Raw results: `results/local_model_spike.jsonl` (rows with a `run` field are the repeat runs).

## Results

Every model ran once. The two candidates then ran 3 more times each, and their rows show the median of those 3 runs with the range in brackets.

| Model | Type | Prompt tokens | First token (s) | Prompt tok/s | Gen tok/s | Memory | Min free | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **`qwen3-coder:30b`** | 30.5B MoE, Q4_K_M | 5,993 | 20.3 (20.3–20.5) | 454 (454–457) | 51.6 (51.5–51.7) | 17.9 GB (17.9–18.0) | 9% (8–9) | Valid JSON, caught (3/3) |
| `qwen3.6:27b-q4_K_M` | 27.8B dense, Q4_K_M | 6,455 | 74.4 | 96 | 9.7 | 16.7 GB | 13% | Valid JSON, caught |
| `qwen3.8:27b-mlx` | 27.8B dense, nvfp4 (MLX) | — | — | — | — | out of memory | 11% | **Failed:** Metal `Insufficient Memory`, runner crashed |
| `gpt-oss:20b` | 20.9B MoE, MXFP4 | 6,027 | 13.4 (13.4–13.4) | 663 (663–663) | 51.6 (51.5–51.6) | 14.5 GB (14.5–14.5) | 36% (35–36) | Valid JSON, caught (3/3) |
| `gemma4:26b-mlx` | nvfp4 (MLX), metadata unclear | 6,966 | 17.1 | 638 | 41.5 | see note | 19% | Valid JSON, caught |
| `gemma4:12b-mlx` | 12.4B, nvfp4 (MLX) | 6,966 | 32.4 | 233 | 39.6 | see note | 33% | Valid JSON, caught |
| `qwen2.5:7b` | 7.6B dense, Q4_K_M | 6,014 | 19.9 | 346 | 44.0 | 4.9 GB | 35% | Valid JSON, caught |

- **First token** is model load plus prompt processing. Load time depends on whether the model file is still in the OS file cache: `qwen3-coder:30b` loaded in 3 s on the single run and about 7 s on every repeat, which accounts for its first-token difference (16.2 s single, 20.3 s median). Prompt and generation speed varied by under 1% across repeats.
- **Memory** is the peak resident size of the llama.cpp runner process. Ollama's `/api/ps` under-reports it badly (2.6 GB for `qwen3-coder:30b`, against 19.1 GB resident), so it is not used. For MLX models the weights live in Metal buffers that do not show up as process memory, so no comparable figure exists; **min free** (lowest system-wide free memory during the run, from `memory_pressure`, idle baseline 91%) is the comparable headroom measure. On `qwen3-coder:30b`'s single run the two agree: 91% to 12% free is about 19 GB, against 19.1 GB resident.
- **Caught** means a finding in `processors.py` within 3 lines of line 169, the Study B matching rule. Every model that ran caught it. This is one easy bug, so it says nothing about review quality; it only shows each model can follow the prompt and return valid structured output.
- `gpt-oss:20b` produced 455 output tokens against 74 to 171 for the others. It appears to reason even with `think: false`, which costs time and tokens on longer reviews.
- **Swap:** the first `qwen3-coder:30b` repeat grew swap by about 370 MB; the other runs of it did not. The `qwen3.8:27b-mlx` failures grew it by 0.9 to 1.3 GB before crashing. No other model grew swap.

## Decision

- **`local-main`: `qwen3-coder:30b`.** It is the spec's target (a ~30B MoE at 4-bit) and is as fast as anything tested because only about 3.3B parameters are active per token. It only just fits: 8 to 12% free at peak across four runs, with a small swap increase on one. Nothing else heavy should run alongside it, and the embedding model must not be resident (indexing runs first, as `architecture.md` says).
- **Fallback: `gpt-oss:20b`.** A 21B MoE at 4-bit with about four times the headroom (36% free), the same generation speed and a faster first token. Use it if `qwen3-coder:30b` starts swapping with the real Study B prompt. Its extra reasoning tokens are the cost.
- **Not used:** the dense 27B models. `qwen3.6:27b` fits but is about 5 times slower to first token and generation (74 s, 9.7 tok/s); `qwen3.8:27b-mlx` runs out of GPU memory at this prompt size.

## Watch in later tickets

- **Context size.** The Study B prompt is a 6,000-token context budget plus the diff and instructions, so it may need `num_ctx` above 8,192. More context means a larger KV cache, and `qwen3-coder:30b` has only 8 to 12% headroom at 8,192. CR-17 must set `num_ctx` explicitly (Ollama's default can silently truncate) and re-check memory at the real prompt size.
- **Swap.** If a run grows swap, timings stop being comparable. Switch to the fallback and record why here.
