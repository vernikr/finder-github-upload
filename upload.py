#!/usr/bin/env python3
"""Finder GitHub Upload: one atomic commit per selection."""
import base64, datetime, getpass, json, os, pathlib, secrets, subprocess, sys, urllib.error, urllib.parse, urllib.request
import gh_install

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

def app_dir():
    return pathlib.Path.home() / '.local/share/finder-github-upload'

def gh_env():
    env = os.environ.copy()
    for key in ('GH_TOKEN', 'GITHUB_TOKEN', 'GH_HOST'):
        env.pop(key, None)
    return env

def gh_token(gh):
    try:
        p = subprocess.run([gh, 'auth', 'token', '--hostname', 'github.com'], text=True, capture_output=True, env=gh_env())
    except OSError as e:
        raise UploadError(f'Не удалось запустить GitHub CLI: {e}. Повторите установку.') from None
    if p.returncode or not p.stdout.strip():
        raise UploadError('GitHub CLI не авторизован. Запустите установщик снова и войдите через браузер.')
    return p.stdout.strip()

def token_get():
    config = app_dir() / 'auth.json'
    if config.exists():
        try:
            auth = json.loads(config.read_text())
            if auth.get('method') == 'gh': return gh_token(auth['gh'])
            if auth.get('method') != 'pat': raise UploadError('Неизвестный способ авторизации. Повторите установку.')
        except (ValueError, KeyError) as e:
            raise UploadError(f'Ошибка настроек авторизации: {e}. Повторите установку.') from None
    # Also supports installations made before browser login was introduced.
    p = subprocess.run(['/usr/bin/security', 'find-generic-password', '-s', SERVICE, '-a', OWNER, '-w'], text=True, capture_output=True)
    if p.returncode: raise UploadError('Токен не найден в Keychain. Запустите install.command и настройте вход.')
    return p.stdout.rstrip('\n')

def save_auth(settings):
    target = app_dir() / 'auth.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    fd, name = tempfile.mkstemp(prefix='.auth-', dir=target.parent)
    try:
        with os.fdopen(fd, 'w') as f: json.dump(settings, f)
        os.replace(name, target)
    finally:
        if os.path.exists(name): os.unlink(name)

def choose(title, options):
    """Use arrow keys on a terminal; fall back to a numbered prompt otherwise."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print('\n' + title)
        for i, option in enumerate(options, 1): print(f'  {i}. {option}')
        while True:
            value = input('Номер [1]: ').strip()
            if not value: return 0
            if value.isdigit() and 1 <= int(value) <= len(options): return int(value) - 1
            print('Введите номер из списка.')
    import select, termios, tty
    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    selected = 0
    color = sys.stdout.isatty() and os.environ.get('TERM', '') != 'dumb' and 'NO_COLOR' not in os.environ
    bold = '\x1b[1m' if color else ''
    cyan = '\x1b[1;36m' if color else ''
    reset = '\x1b[0m' if color else ''
    print('\n' + bold + title + reset + ' (↑/↓, Enter)')
    def render():
        for i, label in enumerate(options):
            highlighted = cyan + '❯ ' + label + reset if i == selected else '  ' + label
            print('\r\x1b[2K' + highlighted)
        sys.stdout.flush()
    try:
        tty.setcbreak(fd)
        render()
        while True:
            key = os.read(fd, 1)
            if not key: raise EOFError('Поток ввода закрыт')
            if key in (b'\r', b'\n'):
                return selected
            if key == b'\x1b':
                sequence = b''
                for _ in range(2):
                    if not select.select([fd], [], [], 0.1)[0]: break
                    sequence += os.read(fd, 1)
                if sequence in (b'[A', b'OA'): selected = (selected - 1) % len(options)
                elif sequence in (b'[B', b'OB'): selected = (selected + 1) % len(options)
                else: continue
                sys.stdout.write(f'\x1b[{len(options)}A')
                render()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)
        print()

def setup():
    choice = choose('Выберите способ входа', ['Через браузер с GitHub CLI (рекомендуется)', 'Ввести персональный токен (PAT)'])
    if choice == 0:
        try:
            gh = gh_install.find_or_install(app_dir())
        except (OSError, RuntimeError, ValueError, KeyError, urllib.error.URLError) as e:
            raise UploadError(f'Не удалось установить GitHub CLI: {e}') from None
        gh = str(pathlib.Path(gh).resolve())
        try:
            token = gh_token(gh)
            use_existing = choose('GitHub CLI уже авторизован', ['Использовать текущую учётную запись', 'Войти в другую учётную запись']) == 0
        except UploadError:
            token = None
            use_existing = False
        if not use_existing:
            print('GitHub покажет одноразовый код. Откройте страницу в браузере и подтвердите доступ.', flush=True)
            p = subprocess.run([gh, 'auth', 'login', '--hostname', 'github.com', '--web', '--git-protocol', 'https'], env=gh_env())
            if p.returncode: raise UploadError('Вход через GitHub CLI не завершён.')
            token = gh_token(gh)
        settings = {'method': 'gh', 'gh': gh}
    elif choice == 1:
        print('Создайте fine-grained PAT с доступом к uploads и Contents: Read and write.')
        token = getpass.getpass('Вставьте токен (ввод не отображается): ').strip()
        if not token: raise UploadError('Пустой токен.')
        settings = {'method': 'pat'}
    else:
        raise UploadError('Неизвестный способ входа.')
    repo = api(token, 'GET', '')
    if not repo.get('permissions', {}).get('push'): raise UploadError('Токен не имеет права записи в uploads.')
    if repo.get('size') == 0:
        try:
            api(token, 'GET', '/git/ref/heads/' + urllib.parse.quote(repo['default_branch'], safe='/'))
        except UploadError as e:
            if 'HTTP 404' not in str(e) and 'HTTP 409' not in str(e): raise
            print('Репозиторий пуст. Автоматически создаём первый коммит с README.md…')
            api(token, 'PUT', '/contents/README.md', {'message': 'Initialize uploads repository', 'content': base64.b64encode(b'# Uploads\n\nFiles uploaded from Finder.\n').decode('ascii')})
            print('Первый коммит создан.')
    if settings['method'] == 'pat':
        # The security command receives the password briefly as an argument.
        p = subprocess.run(['/usr/bin/security', 'add-generic-password', '-U', '-s', SERVICE, '-a', OWNER, '-w', token], capture_output=True, text=True)
        if p.returncode: raise UploadError('Не удалось сохранить токен в Keychain: ' + p.stderr.strip())
    save_auth(settings)
    print('Доступ к репозиторию проверен и настройка сохранена.')

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
    print(f'Файлов: {len(items)}. Содержимое загружается в {OWNER}/{REPO}.', flush=True)
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
        subprocess.run(['/usr/bin/osascript', '-e', 'on run argv\ndisplay dialog ("Ссылка скопирована в буфер:\n" & item 1 of argv) buttons {"OK"} default button "OK" with title "GitHub Upload"\nend run', url], check=False, stdout=subprocess.DEVNULL)
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
    except KeyboardInterrupt:
        print('\nОтменено пользователем.', file=sys.stderr)
        sys.exit(130)
    except (UploadError, OSError, KeyError, ValueError, EOFError) as e:
        print('\nОшибка: ' + str(e), file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__': main()
