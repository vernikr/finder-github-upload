#!/bin/bash
set -eu
final="$HOME/Library/Services/GitHub Upload.workflow"
legacy="$HOME/.local/share/finder-github-upload"
rm -rf "$final"
if [ -d "$legacy" ]; then
  rm -f "$legacy/python" "$legacy/upload.py" "$legacy/launch.sh" "$legacy/terminal.sh" "$legacy/gh_install.py" "$legacy/gh" "$legacy/auth.json" "$legacy"/pbs-backup-*.plist
  rmdir "$legacy" 2>/dev/null || true
fi
/usr/bin/security delete-generic-password -s finder-github-upload -a vernikr-personal 2>/dev/null || true
/System/Library/CoreServices/pbs -update || true
echo 'Удалено. uv, Python и общая авторизация GitHub CLI не удалялись.'
