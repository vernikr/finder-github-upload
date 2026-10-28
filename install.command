#!/bin/bash
set -eu
finish() {
  status=$?
  trap - EXIT
  if [ -n "${installer:-}" ]; then rm -f "$installer"; fi
  if [ "$status" -ne 0 ]; then
    printf '\nУстановка завершилась с ошибкой (код %s). Прочитайте сообщение выше.\n' "$status"
  fi
  if [ -t 0 ]; then
    printf '\nНажмите Enter, чтобы закрыть окно… '
    read -r || true
  fi
  exit "$status"
}
trap finish EXIT
cd "$(dirname "$0")"
if [ "$(uname -s)" != Darwin ]; then echo 'Требуется macOS.'; exit 1; fi
base="$HOME/.local/share/finder-github-upload"
mkdir -p "$base"
printf '\nУстановка GitHub Upload.\n'
# Finder may launch Terminal with a minimal PATH; include common macOS locations.
export PATH="$HOME/.local/bin:/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
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
    rm -f "$installer"
    for candidate in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
      if [ -x "$candidate" ]; then uv="$candidate"; break; fi
    done
    if [ -z "$uv" ]; then echo "uv установлен, но его исполняемый файл не найден. Проверьте вывод установщика."; exit 1; fi
  fi
  echo 'Устанавливаем Python 3.12 через uv…'
  "$uv" python install 3.12
  python="$("$uv" python find --system --no-python-downloads 3.12)"
fi
printf 'Используется Python: %s\n' "$python"
"$python" --version
ln -sf "$python" "$base/python"
cp upload.py launch.sh gh_install.py "$base/"
chmod 700 "$base/launch.sh"
"$base/python" workflow.py
"$base/python" register_finder.py || echo "Действие установлено, но может потребоваться включить его в настройках Finder вручную."
printf '\nНастройка доступа к GitHub:\n'
"$base/python" "$base/upload.py" setup
printf '\nГотово. В Finder выделите файлы → правый клик → Быстрые действия → GitHub Upload.\n'
