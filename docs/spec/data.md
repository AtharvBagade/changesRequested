# Data: corpora, ground truth and seeded bugs

The evals are only credible if the ground truth is hand-labeled, is defined independently of any chunker, and includes bugs that cannot be found without retrieval.

## Corpora

- **Dev corpus:** `auxcord-mcp`, for fast iteration. Never report headline numbers from it.
- **Headline corpus:** one mid-sized open-source Python repo (roughly 5k to 30k lines) that was not written by the project author, pinned to a commit hash. Prefer a less famous repo, since models may have memorized very popular ones.
- Do not vendor the headline repo. Store the commit hash and a fetch script, and record both corpora and their licenses in `docs/corpora.md`.
- Never commit corpus source. Eval data stores only the lines a change touches, with no surrounding context (see `docs/adr/0001-changed-lines-only-from-corpora.md`).

## Retrieval cases

File: `evals/retrieval_cases.jsonl`. 40 cases in total, about 20 diffs and 20 questions about the code. 10 are used for tuning and 30 are held out.

```json
{"id": "r017", "kind": "diff",
 "edits": [{"file": "src/pkg/auth.py", "line": 97, "old": ["        if self.expires_at < now:"], "new": ["        if self.expires_at <= now:"]}],
 "relevant": [{"file": "src/pkg/auth.py", "symbol": "TokenCache.refresh", "lines": [88, 131]}],
 "notes": "why these symbols matter", "split": "heldout"}
```

A `diff` case stores its change as `edits`; the query is the unified diff rebuilt from them at the pinned commit. A `question` case stores a natural-language `query` instead of `edits`.

Each edit replaces the `old` lines starting at `line` with the `new` lines. `old: []` inserts and `new: []` deletes. Only changed lines are stored, never surrounding code, so the repo carries no more of the corpus than the edits themselves.

Relevance is defined by file and line range, never by chunk id. A retrieved chunk is a hit if it overlaps a relevant range. This keeps naive and AST chunkers comparable.

A validator script must check that every relevant range exists at the pinned commit, and that every edit's `old` lines match the pinned commit at `line`.

## Seeded bugs

File: `evals/seeded_bugs/manifest.jsonl`. 15 bugs plus 5 clean diffs.

```json
{"id": "b07", "edits": [{"file": "src/pkg/cache.py", "line": 54, "old": ["    if entry.ttl > now:"], "new": ["    if entry.ttl >= now:"]}],
 "bug_type": "broken-contract",
 "location": {"file": "src/pkg/cache.py", "lines": [52, 58]},
 "needs_context": true, "context_symbols": ["src/pkg/models.py::Entry.is_expired"],
 "description": "hidden ground truth, never shown to the model"}
```

Rules:

- At least 8 of the 15 bugs set `needs_context: true`: the diff looks fine alone and is only wrong given code elsewhere in the repo. Without these, retrieval cannot change the outcome and the model comparison says nothing about chunking.
- Cover a spread of `bug_type` values: off-by-one, missing null check, wrong condition, broken contract with a caller, resource leak.
- The 5 clean diffs are real, harmless changes. They exist to measure false alarms.
- Every bug and clean diff is stored as `edits`, in the same format as retrieval cases, and its patch is rebuilt at the pinned commit. A validator checks that every edit's `old` lines match.
- The `description` field is ground truth and is never placed in a prompt.

## Labeling

Labeling is done by hand by the project author. Budget about half a day for the retrieval cases and half a day for the seeded bugs.
