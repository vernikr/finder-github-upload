#!/bin/bash
set -eu
installer=''
work=''
old_moved=0
final="$HOME/Library/Services/GitHub Upload.workflow"
finish() {
  status=$?
  trap - EXIT
  if [ "$old_moved" = 1 ] && [ ! -e "$final" ] && [ -n "$work" ] && [ -e "$work/previous.workflow" ]; then
    mv "$work/previous.workflow" "$final" || { echo 'Не удалось восстановить прежнее действие; оно находится в:' "$work/previous.workflow"; work=''; }
  fi
  if [ -n "$installer" ]; then rm -f "$installer"; fi
  if [ -n "$work" ]; then rm -rf "$work"; fi
  if [ "$status" -ne 0 ]; then
    printf '\nУстановка завершилась с ошибкой (код %s). Прочитайте сообщение выше.\n' "$status"
  fi
  if [ -t 0 ]; then printf '\nНажмите Enter, чтобы закрыть окно… '; read -r || true; fi
  exit "$status"
}
trap finish EXIT
cd "$(dirname "$0")"
if [ "$(uname -s)" != Darwin ]; then echo 'Требуется macOS.'; exit 1; fi
printf '\nУстановка GitHub Upload.\n'
export PATH="$HOME/.local/bin:/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
. ./find-python.sh
uv="$(command -v uv || true)"
if [ -z "$uv" ] && [ -x "$HOME/.cargo/bin/uv" ]; then uv="$HOME/.cargo/bin/uv"; fi
python="$(find_existing_python || true)"
if [ -z "$python" ]; then
  if [ -z "$uv" ]; then
    echo 'Подходящий Python не найден. Устанавливаем uv официальным установщиком astral.sh…'
    installer="$(/usr/bin/mktemp)"
    /usr/bin/curl -LsSf https://astral.sh/uv/install.sh -o "$installer"
    /bin/sh "$installer"
    rm -f "$installer"; installer=''
    for candidate in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
      if [ -x "$candidate" ]; then uv="$candidate"; break; fi
    done
    if [ -z "$uv" ]; then echo 'uv установлен, но исполняемый файл не найден.'; exit 1; fi
  fi
  echo 'Устанавливаем Python 3.12 через uv…'
  "$uv" python install 3.12
  python="$("$uv" python find --system --no-python-downloads 3.12)"
fi
printf 'Используется Python: %s\n' "$python"
"$python" --version
mkdir -p "$HOME/Library/Services"
umask 077
work="$(/usr/bin/mktemp -d "$HOME/Library/Services/.github-upload-install.XXXXXXXX")"
staged="$work/GitHub Upload.workflow"
"$python" workflow.py "$staged" "$final"
base="$staged/Contents/Resources"
mkdir -p "$base"
ln -s "$python" "$base/python"
cp upload.py launch.sh terminal.sh gh_install.py uninstall.command "$base/"
chmod 700 "$base/launch.sh" "$base/terminal.sh" "$base/uninstall.command"
# Preserve a locally downloaded gh and the pbs backups from the prior installation.
for previous in "$final/Contents/Resources" "$HOME/.local/share/finder-github-upload"; do
  if [ ! -e "$base/gh" ] && [ -x "$previous/gh" ]; then cp -p "$previous/gh" "$base/gh"; fi
  for backup in "$previous"/pbs-backup-*.plist; do
    [ -f "$backup" ] || continue
    cp -p "$backup" "$base/"
  done
done
printf '\nНастройка доступа к GitHub:\n'
"$base/python" "$base/upload.py" setup
# Prepare everything first. Rename the old and new bundles on the same filesystem.
# The EXIT trap restores the old bundle if the second rename fails.
if [ -e "$final" ]; then mv "$final" "$work/previous.workflow"; old_moved=1; fi
mv "$staged" "$final"
old_moved=0
base="$final/Contents/Resources"
"$base/python" register_finder.py "$base" || echo 'Действие установлено, но может потребоваться включить его в настройках Finder вручную.'
# Remove only files created by earlier versions, leaving unrelated files alone.
legacy="$HOME/.local/share/finder-github-upload"
if [ -d "$legacy" ]; then
  rm -f "$legacy/python" "$legacy/upload.py" "$legacy/launch.sh" "$legacy/terminal.sh" "$legacy/gh_install.py" "$legacy/gh" "$legacy/auth.json" "$legacy"/pbs-backup-*.plist
  if [ -d "$legacy/__pycache__" ]; then
    rm -f "$legacy/__pycache__"/upload.*.pyc "$legacy/__pycache__"/gh_install.*.pyc
    rmdir "$legacy/__pycache__" 2>/dev/null || true
  fi
  rmdir "$legacy" 2>/dev/null || true
fi
printf '\nГотово! Выделите файлы в Finder → Быстрые действия → GitHub Upload.\n'
printf 'Скачанный ZIP и распакованную папку установщика теперь можно удалить.\n'
printf 'Установленное действие: %s\n' "$final"
