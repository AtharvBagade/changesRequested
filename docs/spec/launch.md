# README and GitHub launch

A reviewer decides in about 30 seconds, so the top of the README and the repo page do most of the work.

## README order

1. Name, the tagline "The reviewer nobody wants, now with citations and eval scores", and badges for CI, license and Python version
2. A demo GIF of `chreq review` on a real diff
3. The question the project answers, in two sentences
4. Results: the Study A table and the Study B table, each with pinned versions above it
5. How it works: the architecture diagram and the agent graph
6. Quickstart: three commands, plus the Docker version
7. Reproduce the results: `chreq eval ...` and `chreq report`
8. Limitations and what to do next
9. Links to `docs/failure-analysis.md` and `docs/hypotheses.md`

## Repo settings

- Description: one line with the question and "RAG, LangGraph, evals"
- Topics: `code-review`, `rag`, `langgraph`, `evals`, `llm`, `ai-agents`, `python`
- MIT license, `.env.example`, and a `.gitignore` covering keys, caches and local indexes
- CI badge, Docker image builds, v0.1.0 release with notes
- Issues enabled, no stray branches, meaningful commit messages

## Profile

- Pin `changesrequested` first, then `auxcord-mcp`, then `ndjson-cli`. Unpin `skills` or give it a README.
- Rewrite the bio to name the role and stack.
- Create the profile README repo (a repo named exactly like the GitHub username).
- Fix the `auxcord-mcp` clone URL, add its license and publish its v0.1.0 release.
- Post on LinkedIn with the most surprising number from the evals.

## Be ready to defend

Why that chunk size, why RRF, why a deterministic verifier, how ground truth was labeled, what the local model got wrong and why, and what would change with another week.
