#!/bin/sh

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')

case "$file_path" in
  */frontend/src/*.ts|*/frontend/tests/*.ts)
    content=$(printf '%s' "$input" | jq -r '.tool_input.content // .tool_input.new_string // empty')
    errors=''
    if printf '%s\n' "$content" | grep -qE 'catch[[:space:]]*\(.*:[[:space:]]*any\)'; then
      errors='Use catch (err: unknown), not catch (err: any).\n'
    fi
    if printf '%s\n' "$content" | grep -q 'process\.env'; then
      errors="${errors}Use import.meta.env, not process.env.\n"
    fi
    if printf '%s\n' "$content" | grep -q '// @ts-ignore'; then
      errors="${errors}Fix the type error instead of using @ts-ignore.\n"
    fi
    if [ -n "$errors" ]; then
      printf '%b' "$errors" >&2
      exit 2
    fi
    ;;
esac
