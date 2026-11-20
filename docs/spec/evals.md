# Evals: Study B and reproducibility

Every number in the README must be regenerable from files in the repo with one command.

## Study B: model comparison

Study B runs the full review graph on the seeded bugs with the best retrieval config from Study A fixed, and varies only the model. Crossing the studies only at the end gives a handful of data points instead of a grid nobody can interpret.

**Models:** one Claude model, one Gemini model, and one ~30B open model served locally. They are listed in `models.yaml`. Pick the tiers once, before the first run, and do not change them mid-study. Record the exact model id, quantization and date in every results line.

**Held constant:** prompts, graph, retrieved context, temperature (0 or the lowest the provider allows), token budgets, and the 15 bugs plus 5 clean diffs. Run each case 3 times and report the spread.

## Metrics

| Metric | How it is measured | What it shows |
| --- | --- | --- |
| Bug catch rate | A finding in the bug's file within 3 lines of its range counts as a catch. Report as counts, e.g. 11/15 | Core quality |
| Context-dependent catch rate | Same, on the `needs_context: true` bugs only | Whether retrieval plus the model works |
| False-alarm rate | Findings that match no seeded bug and were judged invalid, divided by all findings | Reviewer noise |
| Citation validity | Share of cited files, lines and evidence ids that exist, counted before the verifier drops anything | Hallucinated grounding |
| Schema-failure rate | Outputs failing validation on the first try, and how many the repair attempt saved | Structured-output reliability |
| Graph completion rate | Runs that reach `render` without a fallback flag | Agent robustness |
| Latency | p50 and p95 seconds per review | Practical speed |
| Tokens and cost | Tokens in and out per review, and cost in dollars (zero for local) | Trade-off |

Retrieval metrics (hit@k, MRR, recall) are defined in `retrieval.md`.

## Matching and judging

- Do not use an LLM judge for the headline metrics. Catch rate, citation validity and schema failures are checked by code.
- The only human step is one adjudication pass: label each unmatched finding as valid or invalid, so a real extra bug is not counted as a false alarm. Store the labels in `evals/adjudication.jsonl`.
- If a judged "comment quality" score is added later, never let a model grade its own output, and hand-check a sample of 20.

## Cost control

Rough budget is about 15,000 to 25,000 tokens per review, so about 45 reviews per model is on the order of 0.7 to 1.1 million tokens. This is an estimate, not a measurement. Run 3 cases first, read the token counts in the results file, then proceed. Cache every model response.

## Results format

One JSON line per config, case and run in `results/*.jsonl`.

```json
{"study": "B", "config": "ast-hybrid", "model": "<id>", "quant": null, "case": "b07", "run": 2,
 "caught": true, "findings": 4, "dropped": 1, "schema_fail": false, "repaired": false,
 "tokens_in": 7210, "tokens_out": 880, "latency_s": 14.2, "date": "<YYYY-MM-DD>", "commit": "<git sha>"}
```

## Rules

1. Pin everything: corpus commit hash, package versions, embedding model, model ids and dates. Print them above every results table.
2. Separate tuning from reporting. Tune only on the 10 tuning retrieval cases. Never adjust prompts, eval data or the matcher after looking at held-out results without recording it in the PR.
3. Report counts next to percentages (11/15, not just 73%). With 15 bugs and 3 runs, claim differences only when they are large and consistent, and do not use the word significant.
4. Report negative and null results.
5. `chreq report` renders every README table from `results/` between marker comments, so the README and the data cannot drift apart.
6. CI runs unit tests and a smoke eval with a mock model on 2 cases. Real model runs stay local.
7. Never commit API keys, results that contain private data, or the headline repo's source code.

## Failure analysis

`docs/failure-analysis.md` diagnoses the 5 worst cases across both studies.
