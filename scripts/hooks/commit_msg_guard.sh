#!/bin/sh
# Commits must be authored by a human: no AI co-author trailers, no agent identity.
msg_file="$1"

if grep -qiE '^co-authored-by:' "$msg_file"; then
    echo "commit-msg: Co-Authored-By trailers are not allowed." >&2
    exit 1
fi

for ident in "$(git var GIT_AUTHOR_IDENT)" "$(git var GIT_COMMITTER_IDENT)"; do
    if echo "$ident" | grep -qiE 'claude|anthropic'; then
        echo "commit-msg: agent identity is not allowed: $ident" >&2
        exit 1
    fi
done
