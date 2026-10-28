#!/bin/bash
set -eu
cd "$(dirname "$0")"
if [ "$(uname -s)" != Darwin ]; then echo 'Требуется macOS.'; exit 1; fi
base="$HOME/.local/share/finder-github-upload"
mkdir -p "$base"
printf '\nУстановка GitHub Upload. Интернет потребуется для загрузки uv и Python.\n'
uv="$(command -v uv || true)"
if [ -z "$uv" ] && [ -x "$HOME/.local/bin/uv" ]; then uv="$HOME/.local/bin/uv"; fi
if [ -z "$uv" ]; then
  echo 'Устанавливаем uv официальным установщиком astral.sh…'
  installer="$(/usr/bin/mktemp)"
  trap 'rm -f "$installer"' EXIT
  /usr/bin/curl -LsSf https://astral.sh/uv/install.sh -o "$installer"
  /bin/sh "$installer"
  rm -f "$installer"
  trap - EXIT
  for candidate in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
    if [ -x "$candidate" ]; then uv="$candidate"; break; fi
  done
  if [ -z "$uv" ]; then echo "uv установлен, но его исполняемый файл не найден. Проверьте вывод установщика."; exit 1; fi
fi
"$uv" python install 3.12
python="$("$uv" python find 3.12)"
ln -sf "$python" "$base/python"
cp upload.py launch.sh "$base/"
chmod 700 "$base/launch.sh"
"$base/python" workflow.py
/System/Library/CoreServices/pbs -update || true
printf '\nНастройка доступа к GitHub:\n'
"$base/python" "$base/upload.py" setup
printf '\nГотово. В Finder выделите файлы → правый клик → Быстрые действия → GitHub Upload.\n'
read -r -p 'Нажмите Enter для выхода…' || true
