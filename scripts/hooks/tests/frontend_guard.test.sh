#!/bin/sh

set -u

root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
guard="$root/scripts/hooks/frontend_guard.sh"
fixtures="$root/scripts/hooks/tests/fixtures"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

check() {
  fixture=$1
  expected_status=$2
  message=${3-}

  if "$guard" < "$fixtures/$fixture" > "$tmp/stdout" 2> "$tmp/stderr"; then
    status=0
  else
    status=$?
  fi
  [ "$status" -eq "$expected_status" ] || {
    printf '%s: expected exit %s, got %s\n' "$fixture" "$expected_status" "$status" >&2
    exit 1
  }
  [ -z "$message" ] || grep -Fq -- "$message" "$tmp/stderr" || {
    printf '%s: missing error message\n' "$fixture" >&2
    exit 1
  }
}

check catch-any.json 2 'Use catch (err: unknown)'
check process-env.json 2 'Use import.meta.env'
check ts-ignore.json 2 'Fix the type error'
check clean.json 0
check non-frontend.json 0
