# Architecture

changesrequested (CLI command: `chreq`) reviews a code diff using retrieval over the surrounding repo. It exists to answer one question with numbers: does code-aware chunking make AI code review measurably better, and how do Claude, Gemini and a local ~30B model compare when everything else is held fixed?

## Scope

| In scope | Out of scope |
| --- | --- |
| Python target repos only | Multi-language support |
| AST chunker vs naive chunker | Call-graph or cross-file symbol resolution |
| Vector, BM25, hybrid (RRF) retrieval, optional reranker | Fine-tuning or training any model |
| LangGraph review agent with retry loop and deterministic verifier | GitHub App, webhooks, auto-posting PR comments |
| Adapters for Claude, Gemini and one local ~30B model | IDE plugin or web UI |
| Retrieval eval and review eval with raw results files | LLM-as-judge for core metrics |
| CLI, Docker, CI with a mock-model smoke test | FastAPI server (only if days are left over) |
| Optional trace screenshots (Langfuse or LangSmith) | Integration with auxcord-mcp |

Anything not in the left column needs a ticket before it is built.

## Layers

Four layers (indexing, retrieval, the review agent, the evals) with a thin model layer under the agent. Each layer is testable and swappable without touching the others.

## Repo structure

```text
changesrequested/
├── pyproject.toml             # console script: chreq
├── README.md
├── CLAUDE.md
├── Dockerfile
├── .env.example
├── .github/workflows/ci.yml
├── src/changesrequested/
│   ├── cli.py                 # chreq index | review | eval | report | config check
│   ├── config.py              # loads config.yaml: typed settings and model entries
│   ├── indexing/
│   │   ├── chunkers/ naive.py, ast_python.py
│   │   ├── embed.py           # one fixed embedding model for all studies
│   │   └── store.py           # chunks + metadata in SQLite, vectors in a numpy array
│   ├── retrieval/ bm25.py, vector.py, hybrid.py (RRF), rerank.py
│   ├── models/ base.py (protocol), claude.py, gemini.py, local.py
│   ├── agent/ state.py, nodes.py, graph.py, prompts.py, verifier.py
│   └── evals/ retrieval_eval.py, review_eval.py, matching.py, report.py
├── config.yaml                # settings and models; see below
├── evals/                     # labeled data (committed)
│   ├── retrieval_cases.jsonl
│   └── seeded_bugs/ manifest.jsonl, patches/
├── results/                   # raw JSONL, one line per config x case x run
├── tests/
└── docs/ spec/, hypotheses.md, failure-analysis.md, corpora.md, local-model.md
```

## Stack

Choices are made for clarity over cleverness.

| Part | Choice | Why |
| --- | --- | --- |
| Language | Python 3.11+ | The stdlib `ast` module parses Python with no extra dependency |
| CLI | Typer | Small, typed, generates `--help` |
| Schemas | Pydantic | One definition for state, findings and structured model output |
| Retrieval | `rank_bm25`, numpy cosine search, SQLite metadata | A few thousand chunks do not need a vector database |
| Embeddings | One small local sentence-transformers model | Free to run, identical across every experiment |
| Agent | LangGraph | The retry loop maps onto graph edges |
| Models | Anthropic SDK, Google GenAI SDK, OpenAI-compatible client for the local server | The local model runs behind Ollama or vLLM, which both expose that API |
| Quality | pytest, ruff, GitHub Actions, Docker | CI runs unit tests and a smoke eval against a mock model, so it needs no API keys |

## Configuration

Settings and models live in one file, `config.yaml`, never in code. Adding or changing a model means editing the file. `chreq` reads `./config.yaml`, or the path in the `CHREQ_CONFIG` env var.

```yaml
settings:                        # optional; every field has a default
  context_token_budget: 6000
  max_attempts: 2
  naive_chunk_lines: 60
  naive_chunk_overlap: 10
  results_dir: results
models:
  - name: claude-main
    provider: anthropic          # anthropic | google | ollama | vllm
    model: <model id>
  - name: local-main
    provider: ollama
    model: <model id>
    endpoint: http://localhost:11434/v1
```

Every provider follows the same rule: a set of required fields, and one condition for being available.

| Provider | Required fields | Available when |
| --- | --- | --- |
| `anthropic` | `name`, `model` | `ANTHROPIC_API_KEY` is set |
| `google` | `name`, `model` | `GEMINI_API_KEY` is set |
| `ollama`, `vllm` | `name`, `model`, `endpoint` | `endpoint` is set (no network check) |

- A structurally invalid entry, an unknown provider or a duplicate `name` is an error that names the entry.
- An unavailable entry is skipped with an info log. Loading fails only if no entry is available.
- `chreq review --model <name>` selects one entry. Selecting an unavailable entry is an error that names the missing env var.
- `chreq eval review` loops over every available entry and reports which entries it skipped.
- `chreq config check` validates the file, pings each local endpoint, and prints one status line per entry. It exits 0 when at least one model is usable.
- Each cloud provider reads its key from one fixed env var, the SDK default. `chreq` loads a gitignored `./.env` (template: `.env.example`) into the environment without overriding vars that are already set. `config.yaml` is committed and never contains a key.
- The exact model id and quantization are written into every results line. Do not change an entry's id between runs of the same study.

## Local model

The local model runs on a Mac mini M4 Pro with 24 GB. A ~30B mixture-of-experts model at 4-bit is the target; if it does not fit, use a 3-bit quantization or a smaller model and record why in `docs/local-model.md`. Run indexing first and load the local model afterwards, because the embedding model and the 30B model should not be resident together.
