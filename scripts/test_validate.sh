#!/usr/bin/env bash
# Prove that scripts/validate.py discriminates: every fixture under
# tests/fixtures/valid/ must pass and every fixture under tests/fixtures/invalid/
# must fail. Exits non-zero when any fixture behaves unexpectedly.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
validator="$repo_root/scripts/validate.py"
valid_dir="$repo_root/tests/fixtures/valid"
invalid_dir="$repo_root/tests/fixtures/invalid"

checked=0
failures=0

expect_valid() {
  local fixture="$1"
  checked=$((checked + 1))
  if python3 "$validator" "$fixture" >/dev/null 2>&1; then
    echo "ok: valid fixture accepted: ${fixture#"$repo_root"/}"
  else
    echo "FAIL: valid fixture was rejected: ${fixture#"$repo_root"/}"
    failures=$((failures + 1))
  fi
}

expect_invalid() {
  local fixture="$1"
  checked=$((checked + 1))
  if python3 "$validator" "$fixture" >/dev/null 2>&1; then
    echo "FAIL: invalid fixture was accepted: ${fixture#"$repo_root"/}"
    failures=$((failures + 1))
  else
    echo "ok: invalid fixture rejected: ${fixture#"$repo_root"/}"
  fi
}

if [ -d "$valid_dir" ]; then
  for fixture in "$valid_dir"/*.toml; do
    [ -e "$fixture" ] || continue
    expect_valid "$fixture"
  done
fi

if [ -d "$invalid_dir" ]; then
  for fixture in "$invalid_dir"/*.toml; do
    [ -e "$fixture" ] || continue
    expect_invalid "$fixture"
  done
fi

echo
echo "Checked $checked fixtures, $failures unexpected."

if [ "$failures" -ne 0 ]; then
  exit 1
fi
