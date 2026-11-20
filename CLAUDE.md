# changesrequested

changesrequested (CLI: `chreq`) reviews a code diff using retrieval over the surrounding repo. The project answers one question with numbers: does code-aware (AST) chunking make AI code review measurably better than naive chunking, and how do Claude, Gemini and a local ~30B model compare when everything else is held fixed?

The tickets are GitHub issues titled `CR-NN: ...`, grouped into milestones M1 to M5.

## Read first

Each ticket links the spec section it implements. Read that before writing code.

| File | Covers |
| --- | --- |
| `docs/spec/architecture.md` | Scope, out-of-scope list, repo layout, stack, `config.yaml` |
| `docs/spec/data.md` | Corpora, retrieval cases, seeded bugs |
| `docs/spec/retrieval.md` | Chunkers, retrievers, Study A |
| `docs/spec/agent.md` | Model adapters, LangGraph nodes, verifier |
| `docs/spec/evals.md` | Study B, metrics, results format, eval rules |
| `docs/spec/launch.md` | README order, repo settings, profile |

## Commands

These are filled in as the tickets land. Update this section in the same PR that introduces a command.

- Install: `pip install -e .`
- Test: `pytest`
- Lint: `ruff check .`
- Check config: `chreq config check`

## Conventions

- Typed Python 3.11+. Small functions. Choose clarity over cleverness.
- Do not add a dependency or a feature unless a ticket asks for it. Anything outside the ticket's acceptance criteria and the spec's scope table stays out.
- Settings and model choice come from `config.yaml`. Never hard-code a model id in code.
- API keys come from environment variables only, optionally loaded from the gitignored `.env`. Never write a key to any other file, a log or a results line.
- Tests do not call real model APIs. Real-call smoke tests are marked manual.

## Eval rules

- Never change eval data, prompts or the matcher after looking at held-out results without recording the change in the PR description.
- Do not use an LLM as the judge for headline metrics.
- Report counts next to percentages, and report negative results.
- Every number in the README must come from `results/` through `chreq report`.

## Workflow per ticket

1. Read the ticket and the spec section it links. If they conflict, stop and ask.
2. Create a branch named `cr-NN-short-name`.
3. Implement only what the ticket lists, with tests.
4. Run every acceptance command and tick the boxes in the PR description.
5. Open a PR that says `Closes #<issue>`. Update the spec in the same PR if a contract changed.

Work one ticket per session.
