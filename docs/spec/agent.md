# Review agent and model layer

The agent is a LangGraph graph with one retry loop and a deterministic verifier. Only grading, query rewriting and analysis call a model, so most of the graph is testable without one.

## Model adapters

Every model call goes through one protocol:

```text
ModelAdapter.generate_structured(prompt, schema) -> validated object + usage + latency
```

- Adapters: Claude (Anthropic SDK), Gemini (Google GenAI SDK), local (OpenAI-compatible endpoint).
- Which adapter and model id to use comes from `models.yaml`. See `architecture.md`.
- Responses are cached on disk, keyed by a hash of the prompt and model entry, so reruns are free.
- Schema failures are reported in the result, never raised, so they can be counted.
- Prompts and the graph are identical across models. A per-model prompt tweak is recorded as a finding, never applied silently.

## State

A Pydantic model passed between nodes: `diff`, `index_id`, `queries`, `chunks`, `attempts`, `sufficient`, `findings`, `dropped_findings`, `errors`, and `usage` (tokens in and out, latency per node).

## Nodes

| # | Node | Uses a model? | What it does |
| --- | --- | --- | --- |
| 1 | `parse_diff` | No | Extract files, hunks and changed symbols with `ast` |
| 2 | `build_queries` | No | One query per changed symbol: name, signature and docstring |
| 3 | `retrieve` | No | Hybrid retrieval per query, deduplicate, cap at a 6,000-token context budget, add linked tests |
| 4 | `grade_context` | Yes | Structured output: is the context enough, and what is missing? |
| 5 | `rewrite_query` | Yes | Turn the missing-information list into new queries, then back to `retrieve` |
| 6 | `analyze` | Yes | Produce findings with file, line, severity, claim, evidence chunk ids and a suggested test |
| 7 | `verify` | No | Drop any finding whose file, line or evidence id is not in the diff or retrieved chunks, and log what was dropped |
| 8 | `render` | No | Markdown or JSON report |

## Edges and failure handling

- `grade_context` goes to `analyze` when the context is sufficient or `attempts` has reached 2. Otherwise it goes to `rewrite_query`, which loops back to `retrieve`.
- If `analyze` returns output that fails schema validation, run one repair attempt that shows the validation error. If that also fails, return an empty result with a flag set. Count both events.
- The verifier is deterministic. It turns "does the model hallucinate citations" into a number without a second model to trust. The README may call this node `receipts`.

## Traces

Write a JSONL trace per run: node, input hash, output, tokens, latency. A Langfuse or LangSmith screenshot of one run is optional for the README.
