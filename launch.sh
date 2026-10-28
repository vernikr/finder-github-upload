#!/bin/bash
set -eu
umask 077
job=$(/usr/bin/mktemp -d "${TMPDIR:-/tmp}/github-upload.XXXXXXXX")
selection="$job/selection"
finished="$job/finished"
printf '%s\0' "$@" > "$selection"
base="$(cd "$(dirname "$0")" && pwd -P)"
# Quote arbitrary path names for Terminal's configured login shell.
command="exec /bin/bash $(printf '%q' "$base/terminal.sh") $(printf '%q' "$selection") $(printf '%q' "$finished")"
# Keep a controller alive in the background so only the window we opened closes;
# stdout/stderr are detached from Automator. Never close a window containing other tabs.
/usr/bin/osascript - "$command" "$job" "$finished" > /dev/null 2>&1 <<'APPLESCRIPT' &
on run argv
    set commandText to item 1 of argv
    set jobPath to item 2 of argv
    set donePath to item 3 of argv
    set cleanupJob to false
    try
        tell application "Terminal"
            activate
            set uploadTab to do script commandText
            set uploadTTY to ""
            repeat 30 times
                set uploadTTY to tty of uploadTab
                if uploadTTY is not missing value and uploadTTY is not "" then exit repeat
                delay 0.1
            end repeat
            if uploadTTY is missing value or uploadTTY is "" then error "Terminal did not provide a TTY"
        end tell
        set targetID to missing value
        tell application "Terminal"
            repeat with w in windows
                if (tty of tabs of w) contains uploadTTY then
                    set targetID to id of w
                    exit repeat
                end if
            end repeat
        end tell
        if targetID is missing value then error "Upload window not found"
        repeat 172800 times
            delay 0.5
            set finishedFlag to do shell script "/bin/test -f " & quoted form of donePath & " && /bin/echo yes || /bin/echo no"
            tell application "Terminal"
                if not (exists window id targetID) then
                    set cleanupJob to true
                    exit repeat
                end if
                if finishedFlag is "yes" then
                    set targetWindow to window id targetID
                    if (count of tabs of targetWindow) is 1 then
                        repeat 20 times
                            if not (busy of tab 1 of targetWindow) then exit repeat
                            delay 0.1
                        end repeat
                        set currentTTY to tty of tab 1 of targetWindow
                        if (currentTTY is uploadTTY or currentTTY is missing value or currentTTY is "") and not (busy of tab 1 of targetWindow) then close targetWindow saving no
                    end if
                    set cleanupJob to true
                    exit repeat
                end if
            end tell
        end repeat
    end try
    if cleanupJob then do shell script "/bin/rm -rf " & quoted form of jobPath
end run
APPLESCRIPT
