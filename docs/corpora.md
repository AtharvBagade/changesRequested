# Corpora

Both corpora are checked out into `corpora/` (gitignored) by `scripts/fetch_corpora.sh`. The script holds the pinned commits and is the source of truth; this file mirrors it. Neither repo's source is committed here (see [ADR 0001](adr/0001-changed-lines-only-from-corpora.md)).

```sh
./scripts/fetch_corpora.sh
```

## Headline corpus: structlog

| | |
| --- | --- |
| Repo | https://github.com/hynek/structlog |
| Release | `26.1.0` (2026-06-06) |
| Commit | `8174a86a2f14b5bd295eded733ff5fffc12aa173` |
| License | MIT OR Apache-2.0. This project uses it under MIT. |
| Size | 7,274 lines of Python under `src/` |

Every headline number comes from this corpus at this commit.

**Why structlog.** It was the best fit among five measured candidates (structlog, cattrs, boltons, marshmallow, sqlite-utils):

- In the 5k to 30k line range the spec asks for, and not written by the project author.
- Modules depend on each other (processors, config, stdlib integration), so context-dependent seeded bugs are possible. boltons was rejected because its modules are mostly independent.
- 15 of 20 modules have a matching `tests/test_<module>.py`, which suits the AST chunker's test-linking heuristic.
- Plain Python. cattrs has more cross-module coupling, but its core generates code at runtime, which makes bugs hard to seed and label by hand.

**Known risk: memorization.** structlog is public and moderately well known, so the evaluated models may have seen it in training. A model that remembers the original code could spot a seeded bug without retrieval, which would inflate the context-dependent catch rate. This was accepted knowingly. It is measured by CR-35 ([#39](https://github.com/AtharvBagade/changesRequested/issues/39)) before the full Study B runs and reported alongside the results.

## Dev corpus: auxcord-mcp

| | |
| --- | --- |
| Repo | https://github.com/AtharvBagade/auxcord-mcp |
| Commit | `9778b370d5347f164c91959f9b62932d3a8cd9b5` (2026-10-02) |
| License | None yet (the project author's own repo; a license is added in CR-33) |

Used for fast iteration only. Never report headline numbers from it. It is pinned so dev results stay comparable when the repo changes; bump the hash deliberately.

## What may be committed

Eval data stores only the lines a change touches: each edit records the file, the line number, the original lines and the new lines, with no surrounding context. Nothing else from either corpus is committed. Single changed lines are not a substantial portion of structlog, and its MIT license is credited here.

## Changing a pin

Edit the hash in `scripts/fetch_corpora.sh` and in this file in the same PR, then rerun the script. Changing the headline pin invalidates every recipe whose original lines no longer match, so do it only before labeling starts.
