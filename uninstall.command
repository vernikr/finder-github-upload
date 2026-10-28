#!/bin/bash
set -eu
rm -rf "$HOME/Library/Services/GitHub Upload.workflow" "$HOME/.local/share/finder-github-upload"
/usr/bin/security delete-generic-password -s finder-github-upload -a vernikr-personal 2>/dev/null || true
/System/Library/CoreServices/pbs -update || true
echo 'Удалено. uv и Python не удалялись.'
