#!/bin/bash
# Sourced by the installer. Select an already installed Python before downloading.
# Avoid the Command Line Tools prompt from Apple's /usr/bin/python3 stub.
find_existing_python() {
  local candidate name found
  if [ -n "${uv:-}" ]; then
    found="$("$uv" python find --system --no-python-downloads '>=3.12,<4' 2>/dev/null || true)"
    if [ -n "$found" ] && [ -x "$found" ] && "$found" -c 'import sys; sys.exit(not ((3, 12) <= sys.version_info[:2] < (4, 0)))' >/dev/null 2>&1; then
      printf '%s\n' "$found"
      return 0
    fi
  fi
  for name in python3.15 python3.14 python3.13 python3.12 python3; do
    candidate="$(command -v "$name" || true)"
    [ -n "$candidate" ] || continue
    case "$candidate" in
      /usr/bin/python3*) /usr/bin/xcode-select -p >/dev/null 2>&1 || continue ;;
    esac
    if "$candidate" -c 'import sys; sys.exit(not ((3, 12) <= sys.version_info[:2] < (4, 0)))' >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}
