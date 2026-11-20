#!/usr/bin/env bash
# Check the eval corpora out into corpora/ (gitignored) at their pinned commits.
# This list is the source of truth for the pins; docs/corpora.md mirrors it.
set -euo pipefail

CORPORA=(
  "structlog https://github.com/hynek/structlog.git 8174a86a2f14b5bd295eded733ff5fffc12aa173"
  "auxcord-mcp https://github.com/AtharvBagade/auxcord-mcp.git 9778b370d5347f164c91959f9b62932d3a8cd9b5"
)

root="$(cd "$(dirname "$0")/.." && pwd)/corpora"
mkdir -p "$root"

for entry in "${CORPORA[@]}"; do
  read -r name url sha <<<"$entry"
  dir="$root/$name"
  if [ ! -d "$dir/.git" ]; then
    git init -q "$dir"
    git -C "$dir" remote add origin "$url"
  fi
  git -C "$dir" fetch -q --depth 1 origin "$sha"
  git -C "$dir" checkout -q --detach FETCH_HEAD
  actual="$(git -C "$dir" rev-parse HEAD)"
  if [ "$actual" != "$sha" ]; then
    echo "error: $name is at $actual, expected $sha" >&2
    exit 1
  fi
  echo "$name: $sha"
done
