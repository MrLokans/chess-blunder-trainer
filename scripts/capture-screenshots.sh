#!/usr/bin/env bash
# Capture 2x Retina desktop UI overviews for LLM visual review.
# Usage: ./scripts/capture-screenshots.sh [base-url]

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
base_url="${1:-http://localhost:8000}"
base_url="${base_url%/}"
output_dir="$project_root/screenshots/$(date +%Y%m%d-%H%M%S)"
session="blunder-tutor-screenshots-$$"
pages=(profile dashboard traps starred profiles management import settings)
paths=(/ /dashboard /traps /starred /profiles /management /import /settings)

cleanup() {
    agent-browser --session "$session" close >/dev/null 2>&1 || true
}
trap cleanup EXIT

command -v agent-browser >/dev/null || {
    echo "Error: agent-browser is required." >&2
    exit 1
}
curl --fail --silent --show-error --max-time 3 "$base_url" >/dev/null || {
    echo "Error: App is not reachable at $base_url" >&2
    exit 1
}

mkdir -p "$output_dir"
agent-browser --session "$session" open about:blank >/dev/null
agent-browser --session "$session" set viewport 1440 1080 2 >/dev/null

for index in "${!pages[@]}"; do
    page="${pages[index]}"
    agent-browser --session "$session" open "$base_url${paths[index]}" >/dev/null
    agent-browser --session "$session" wait --load networkidle >/dev/null
    agent-browser --session "$session" screenshot "$output_dir/page-$page.png" >/dev/null
    echo "Captured $output_dir/page-$page.png"
done
