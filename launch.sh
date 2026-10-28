#!/bin/bash
set -eu
umask 077
selection=$(/usr/bin/mktemp "${TMPDIR:-/tmp}/github-upload.XXXXXXXX")
printf '%s\0' "$@" > "$selection"
base="$HOME/.local/share/finder-github-upload"
# Safely quote all arguments for the interactive shell launched by Terminal.
command="$(printf '%q' "$base/python") $(printf '%q' "$base/upload.py") --selection-file $(printf '%q' "$selection"); printf '\nНажмите Enter, чтобы закрыть вкладку…'; read -r"
/usr/bin/osascript - "$command" <<'APPLESCRIPT'
on run argv
    tell application "Terminal"
        activate
        do script (item 1 of argv)
    end tell
end run
APPLESCRIPT
