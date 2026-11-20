# Retrieval and Study A

Study A isolates retrieval. It needs no generation model, so it is cheap, fast and deterministic. Hold the embedding model, top-k and token budget fixed, and vary only the chunker and the retriever.

## Storage

- SQLite holds chunk text and metadata: file, symbol, line range.
- A numpy file holds the vectors, searched by cosine similarity.
- One small local embedding model is fixed in config for every experiment.

## Chunkers

**Naive (baseline):** fixed windows of 60 lines with 10 lines of overlap.

**AST chunker** (Python stdlib `ast`):

- One chunk per function, method and class. For a class, the chunk is its header, docstring and method signatures, and each method is its own chunk.
- A module-level chunk holds the docstring and imports.
- Every chunk text starts with a header line giving file path, symbol name and line range, so the embedding sees where the code lives.
- Oversized functions are split on blank lines, with the same header repeated.
- Test linking heuristic: a symbol `foo` in `pkg/a.py` links to tests in `tests/test_a.py` that mention `foo`. The agent uses this to pull related tests.
- Files that fail to parse fall back to the naive chunker.

## Retrievers

Every retriever implements `retrieve(query, k)` and returns chunks with scores.

- BM25 over chunk text.
- Vector search over embeddings.
- Hybrid: reciprocal rank fusion of the BM25 and vector rankings.
- Optional cross-encoder reranker after hybrid retrieval. Off by default. This is the first thing to cut if the schedule slips.

## Configs

| Config | Chunker | Retriever | Question it answers |
| --- | --- | --- | --- |
| A1 | Naive (60 lines, 10 overlap) | Vector | Baseline |
| A2 | AST | Vector | Does code-aware chunking help on its own? |
| A3 | AST | BM25 | Is lexical matching strong for code identifiers? |
| A4 | AST | Hybrid (RRF) | Does combining them beat either alone? |
| A5 | AST | Hybrid + cross-encoder rerank | Is reranking worth its latency? |
| A6 | Naive | Hybrid | Control: is the gain from the chunker or from hybrid retrieval? |

## Metrics

Per config: hit@5, hit@8, MRR, recall of relevant symbols at 8, average tokens per retrieved set, and index build time. Report the 30 held-out cases, and show the 10 tuning cases separately.

## Hypotheses

Write `docs/hypotheses.md` before the first run: one line per config predicting the ranking. The README then reports where the predictions were wrong. A null result, such as AST chunking not beating naive chunking, is a valid finding if the numbers are clean. The commit history must show the hypotheses were committed before the first Study A results.
