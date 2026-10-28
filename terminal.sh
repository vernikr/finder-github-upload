#!/bin/bash
# Runs in a newly opened Terminal window. No change to the user's Terminal profile.
set -u
selection=$1
finished=$2
base="$(cd "$(dirname "$0")" && pwd -P)"
# Clear only this window's visible screen; don't erase the user's scrollback.
printf '\033[2J\033[H'
PYTHONDONTWRITEBYTECODE=1 "$base/python" -u "$base/upload.py" --selection-file "$selection"
printf '\nНажмите Enter, чтобы закрыть окно… '
IFS= read -r || true
: > "$finished"
