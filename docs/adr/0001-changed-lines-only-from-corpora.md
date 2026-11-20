# Eval data stores only changed lines from the corpora

Seeded bugs and diff-type retrieval cases would naturally be committed as unified diffs, but a diff carries the corpus's surrounding code as context. We decided not to commit corpus source, so each change is stored as a recipe: file, line number, the original lines and the new lines, with zero context. The full diff is rebuilt from the pinned checkout at runtime (equivalent to a zero-context hunk that `git apply --unidiff-zero` accepts). The stored original lines double as the integrity check, since a recipe whose original lines no longer match the pinned commit fails validation.

## Considered options

- **Commit full diffs under structlog's MIT license, with its license file.** Simplest, but puts surrounding corpus code in the repo.
- **Recipes with a hash of the original lines and a minimal find/replace fragment.** No corpus text at all, but a short fragment such as `>` can match several places in a line, and reviewing a bug means running a script.
- **Keep eval data outside the repo.** Breaks the rule that every number is regenerable from the repo.

## Consequences

- The tooling that builds diffs and validates recipes is part of CR-11 and CR-22.
- Changing the headline corpus pin after labeling invalidates recipes whose original lines moved, so the pin is fixed before labeling starts.
