"""Find GitHub CLI or install its official macOS zip in the app directory."""
import hashlib, json, os, pathlib, platform, shutil, tempfile, urllib.request, zipfile

RELEASE = 'https://api.github.com/repos/cli/cli/releases/latest'

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'finder-github-upload', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()

def find_or_install(base):
    existing = shutil.which('gh')
    if existing:
        return existing
    local = pathlib.Path(base) / 'gh'
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    arch = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'amd64', 'AMD64': 'amd64'}.get(platform.machine())
    if not arch:
        raise RuntimeError('Неизвестная архитектура Mac: ' + platform.machine())
    print('GitHub CLI не найден. Скачиваем официальный релиз в папку приложения…', flush=True)
    data = json.loads(get(RELEASE))
    version = data['tag_name'].removeprefix('v')
    assets = {x['name']: x['browser_download_url'] for x in data['assets']}
    zipname = f'gh_{version}_macOS_{arch}.zip'
    sumsname = f'gh_{version}_checksums.txt'
    if zipname not in assets or sumsname not in assets:
        raise RuntimeError('GitHub CLI: нет подходящего архива или контрольных сумм.')
    checksums = get(assets[sumsname]).decode('utf-8')
    checksum = next((line.split()[0] for line in checksums.splitlines() if len(line.split()) == 2 and line.split()[1].lstrip('*') == zipname), None)
    if not checksum:
        raise RuntimeError('Не найдена контрольная сумма архива GitHub CLI.')
    payload = get(assets[zipname])
    if hashlib.sha256(payload).hexdigest().lower() != checksum.lower():
        raise RuntimeError('Контрольная сумма GitHub CLI не совпадает; загрузка отменена.')
    import io
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        matches = [n for n in archive.namelist() if n.endswith('/bin/gh') and not n.startswith('/') and '..' not in n.split('/')]
        if len(matches) != 1:
            raise RuntimeError('Неожиданное содержимое архива GitHub CLI.')
        binary = archive.read(matches[0])
    local.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.gh-', dir=local.parent)
    try:
        with os.fdopen(fd, 'wb') as f: f.write(binary)
        os.chmod(tmp, 0o700)
        os.replace(tmp, local)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return str(local)
