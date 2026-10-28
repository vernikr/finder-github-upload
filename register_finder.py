"""Enable Finder presentation of the installed workflow, preserving pbs preferences."""
import datetime, os, pathlib, plistlib, subprocess, sys

KEY = '(null) - GitHub Upload - runWorkflowAsService'
SUFFIX = ' - GitHub Upload - runWorkflowAsService'

def update_preferences(data):
    status = data.setdefault('NSServicesStatus', {})
    if not isinstance(status, dict): raise ValueError('Неожиданный формат NSServicesStatus')
    matching = [key for key in status if isinstance(key, str) and key.endswith(SUFFIX)]
    for key in matching or [KEY]:
        entry = status.setdefault(key, {})
        if not isinstance(entry, dict): raise ValueError('Неожиданный формат настроек GitHub Upload')
        modes = entry.setdefault('presentation_modes', {})
        if not isinstance(modes, dict): raise ValueError('Неожиданный формат presentation_modes')
        modes.update(ContextMenu=True, FinderPreview=True, ServicesMenu=True)
    return data

def register(backup_dir):
    result = subprocess.run(['/usr/bin/defaults', 'export', 'pbs', '-'], capture_output=True)
    if result.returncode:
        message = result.stderr.decode(errors='replace')
        if 'does not exist' not in message.lower():
            raise RuntimeError('Не удалось прочитать настройки pbs: ' + message.strip())
        data = {}
        old = plistlib.dumps(data)
    else:
        old = result.stdout
        data = plistlib.loads(old)
        if not isinstance(data, dict): raise ValueError('Неожиданный формат настроек pbs')
    update_preferences(data)
    backup_dir = pathlib.Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = backup_dir/f'pbs-backup-{stamp}.plist'
    fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as f: f.write(old)
    result = subprocess.run(['/usr/bin/defaults', 'import', 'pbs', '-'], input=plistlib.dumps(data), capture_output=True)
    if result.returncode: raise RuntimeError('Не удалось включить контекстное меню: '+result.stderr.decode(errors='replace').strip())
    for flag in ('-flush', '-update'):
        subprocess.run(['/System/Library/CoreServices/pbs', flag], capture_output=True)
    print('Действие включено для контекстного меню Finder. Резервная копия настроек:', backup)
    print('Если действие не видно, в Finder нажмите правой кнопкой на файл → Быстрые действия; при необходимости перезапустите Finder.')

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2: raise ValueError('Укажите каталог для резервной копии')
        register(sys.argv[1])
    except (OSError, ValueError, plistlib.InvalidFileException, RuntimeError) as e:
        print('Не удалось автоматически включить действие для Finder:', e, file=sys.stderr)
        print('Включите GitHub Upload вручную в настройках Быстрых действий или Services.', file=sys.stderr)
        sys.exit(1)
