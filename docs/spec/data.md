# Data: corpora, ground truth and seeded bugs

The evals are only credible if the ground truth is hand-labeled, is defined independently of any chunker, and includes bugs that cannot be found without retrieval.

## Corpora

- **Dev corpus:** `auxcord-mcp`, for fast iteration. Never report headline numbers from it.
- **Headline corpus:** one mid-sized open-source Python repo (roughly 5k to 30k lines) that was not written by the project author, pinned to a commit hash. Prefer a less famous repo, since models may have memorized very popular ones.
- Do not vendor the headline repo. Store the commit hash and a fetch script, and check its license before committing any snippets. Record all of this in `docs/corpora.md`.

## Retrieval cases

File: `evals/retrieval_cases.jsonl`. 40 cases in total, about 20 diffs and 20 questions about the code. 10 are used for tuning and 30 are held out.

```json
{"id": "r017", "kind": "diff", "query": "<unified diff text or a natural-language question>",
 "relevant": [{"file": "src/pkg/auth.py", "symbol": "TokenCache.refresh", "lines": [88, 131]}],
 "notes": "why these symbols matter", "split": "heldout"}
```

Relevance is defined by file and line range, never by chunk id. A retrieved chunk is a hit if it overlaps a relevant range. This keeps naive and AST chunkers comparable.

A validator script must check that every relevant range exists at the pinned commit.

## Seeded bugs

File: `evals/seeded_bugs/manifest.jsonl`. 15 bugs plus 5 clean diffs.

```json
{"id": "b07", "patch": "patches/b07.diff", "bug_type": "broken-contract",
 "location": {"file": "src/pkg/cache.py", "lines": [52, 58]},
 "needs_context": true, "context_symbols": ["src/pkg/models.py::Entry.is_expired"],
 "description": "hidden ground truth, never shown to the model"}
```

Rules:

- At least 8 of the 15 bugs set `needs_context: true`: the diff looks fine alone and is only wrong given code elsewhere in the repo. Without these, retrieval cannot change the outcome and the model comparison says nothing about chunking.
- Cover a spread of `bug_type` values: off-by-one, missing null check, wrong condition, broken contract with a caller, resource leak.
- The 5 clean diffs are real, harmless changes. They exist to measure false alarms.
- Every patch must apply cleanly at the pinned commit. A validator checks this.
- The `description` field is ground truth and is never placed in a prompt.

## Labeling

Labeling is done by hand by the project author. Budget about half a day for the retrieval cases and half a day for the seeded bugs.
