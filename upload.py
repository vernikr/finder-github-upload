#!/usr/bin/env python3
"""Finder GitHub Upload: one atomic commit per selection."""
import base64, datetime, getpass, json, os, pathlib, secrets, subprocess, sys, urllib.error, urllib.parse, urllib.request

OWNER = 'vernikr-personal'
REPO = 'uploads'
SERVICE = 'finder-github-upload'
LIMIT = 50 * 1024 * 1024
API = f'https://api.github.com/repos/{OWNER}/{REPO}'

class UploadError(Exception): pass

def api(token, method, path, data=None):
    raw = None if data is None else json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(API + path, data=raw, method=method, headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json', 'User-Agent': 'finder-github-upload'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        try: message = json.load(e).get('message', '')
        except Exception: message = ''
        raise UploadError(f'GitHub HTTP {e.code}: {message}') from None
    except urllib.error.URLError as e: raise UploadError(f'Сетевая ошибка: {e.reason}') from None

def token_get():
    p = subprocess.run(['/usr/bin/security', 'find-generic-password', '-s', SERVICE, '-a', OWNER, '-w'], text=True, capture_output=True)
    if p.returncode: raise UploadError('Токен не найден в Keychain. Запустите install.command и настройте токен.')
    return p.stdout.rstrip('\n')

def setup():
    print('Создайте fine-grained PAT с доступом к репозиторию uploads и Contents: Read and write.')
    token = getpass.getpass('Вставьте токен (ввод не отображается): ').strip()
    if not token: raise UploadError('Пустой токен.')
    repo = api(token, 'GET', '')
    if not repo.get('permissions', {}).get('push'): raise UploadError('Токен не имеет права записи в uploads.')
    if repo.get('size') == 0:
        try:
            api(token, 'GET', '/git/ref/heads/' + urllib.parse.quote(repo['default_branch'], safe='/'))
        except UploadError as e:
            if 'HTTP 404' not in str(e) and 'HTTP 409' not in str(e): raise
            print('Репозиторий пуст: для работы GitHub API нужно создать первый коммит с README.md.')
            if input('Создать README.md в корне uploads? [y/N] ').strip().lower() not in ('y', 'yes', 'д', 'да'):
                raise UploadError('Инициализация отменена. Создайте первый коммит вручную и повторите установку.')
            api(token, 'PUT', '/contents/README.md', {'message': 'Initialize uploads repository', 'content': base64.b64encode(b'# Uploads\n\nFiles uploaded from Finder.\n').decode('ascii')})
            print('Первый коммит создан.')
    # The security command receives the password briefly as an argument.
    p = subprocess.run(['/usr/bin/security', 'add-generic-password', '-U', '-s', SERVICE, '-a', OWNER, '-w', token], capture_output=True, text=True)
    if p.returncode: raise UploadError('Не удалось сохранить токен в Keychain: ' + p.stderr.strip())
    print('Токен проверен и сохранён в Связке ключей.')

def collect(paths):
    selected = []
    for name in paths:
        p = pathlib.Path(name)
        if p.is_symlink(): raise UploadError(f'Символические ссылки не поддерживаются: {p}')
        if not p.exists(): raise UploadError(f'Не найдено: {p}')
        if not p.is_file() and not p.is_dir(): raise UploadError(f'Необычный тип файла: {p}')
        selected.append(p)
    if not selected: raise UploadError('Не выбраны файлы.')
    parents = {str(p.parent.resolve()) for p in selected}
    if len(parents) != 1: raise UploadError('Выберите объекты из одной папки Finder.')
    items = []
    def visit(p, relative):
        if p.is_symlink(): raise UploadError(f'Символические ссылки не поддерживаются: {p}')
        if p.is_dir():
            for child in sorted(p.iterdir(), key=lambda x: x.name): visit(child, relative / child.name)
        elif p.is_file():
            if p.stat().st_size > LIMIT: raise UploadError(f'Файл больше 50 МиБ: {p}')
            items.append((p, relative.as_posix()))
        else: raise UploadError(f'Необычный тип файла: {p}')
    for p in selected: visit(p, pathlib.PurePosixPath(p.name))
    names = [name for _, name in items]
    if len(set(names)) != len(names): raise UploadError('Повторяющиеся пути в выделении.')
    if not items: raise UploadError('Нет файлов: Git не сохраняет пустые папки.')
    return items

def run(paths):
    items = collect(paths)
    token = token_get()
    repo = api(token, 'GET', '')
    branch = repo['default_branch']
    refpath = '/git/ref/heads/' + urllib.parse.quote(branch, safe='/')
    folder = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d_%H-%M-%S') + '-' + secrets.token_hex(4)
    print(f'Папка: {folder}\nФайлов: {len(items)}. Содержимое загружается в {OWNER}/{REPO}.', flush=True)
    entries = []
    for i, (path, rel) in enumerate(items, 1):
        data = path.read_bytes()
        if len(data) > LIMIT: raise UploadError(f'Файл стал больше 50 МиБ: {path}')
        blob = api(token, 'POST', '/git/blobs', {'content': base64.b64encode(data).decode('ascii'), 'encoding': 'base64'})
        entries.append({'path': folder + '/' + rel, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']})
        print(f'\r[{i}/{len(items)}] {i*100//len(items):3}%  {rel}', flush=True)
    # Reference update is non-forced; on concurrent changes retry with new parent/tree.
    for attempt in range(3):
        parent = api(token, 'GET', refpath)['object']['sha']
        base = api(token, 'GET', '/git/commits/' + parent)['tree']['sha']
        tree = api(token, 'POST', '/git/trees', {'base_tree': base, 'tree': entries})
        commit = api(token, 'POST', '/git/commits', {'message': 'Upload ' + folder, 'tree': tree['sha'], 'parents': [parent]})
        try:
            api(token, 'PATCH', '/git/refs/heads/' + urllib.parse.quote(branch, safe='/'), {'sha': commit['sha'], 'force': False})
            break
        except UploadError as e:
            if attempt == 2 or not any(f'HTTP {x}' in str(e) for x in (409, 422)): raise
            print('Ветка изменилась, повторяем публикацию…', flush=True)
    url = f'https://github.com/{OWNER}/{REPO}/tree/{urllib.parse.quote(branch, safe="")}/{urllib.parse.quote(folder)}'
    print('\nГотово: ' + url, flush=True)
    try:
        subprocess.run(['/usr/bin/pbcopy'], input=url.encode(), check=True)
        subprocess.run(['/usr/bin/osascript', '-e', 'on run argv\ndisplay dialog ("Ссылка скопирована в буфер:\n" & item 1 of argv) buttons {"OK"} default button "OK" with title "GitHub Upload"\nend run', url], check=False)
    except OSError: print('Не удалось скопировать ссылку; скопируйте её из строки выше.')

def main():
    try:
        if sys.argv[1:] == ['setup']: setup()
        elif len(sys.argv) == 3 and sys.argv[1] == '--selection-file':
            name = sys.argv[2]
            try: paths = [os.fsdecode(x) for x in pathlib.Path(name).read_bytes().split(b'\0') if x]
            finally: pathlib.Path(name).unlink(missing_ok=True)
            run(paths)
        else: run(sys.argv[1:])
    except (UploadError, OSError, KeyError, ValueError) as e:
        print('\nОшибка: ' + str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__': main()
