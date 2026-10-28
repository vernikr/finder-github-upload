import os, pathlib, shutil, subprocess, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home=pathlib.Path(self.tmp.name)/'home'; self.home.mkdir()
        self.source=pathlib.Path(self.tmp.name)/'download'; self.source.mkdir()
        for filename in ('install.command','find-python.sh','workflow.py','upload.py','launch.sh','terminal.sh','gh_install.py','register_finder.py','uninstall.command'):
            shutil.copy2(ROOT/filename,self.source/filename)
        binpath=self.home/'.local/bin';binpath.mkdir(parents=True)
        uname=binpath/'uname';uname.write_text('#!/bin/sh\necho Darwin\n');uname.chmod(0o755)
        python=binpath/'python3.13'
        python.write_text('''#!/bin/sh
case "$1" in
 -c) exit 0 ;;
 --version) echo 'Python 3.13 mock'; exit 0 ;;
 workflow.py) mkdir -p "$2/Contents"; printf mock > "$2/Contents/document.wflow"; exit 0 ;;
 */upload.py) if [ "${FAIL_SETUP:-}" = 1 ]; then exit 1; fi; exit 0 ;;
 register_finder.py) exit 0 ;;
 *) echo unexpected >&2; exit 1 ;;
esac
''');python.chmod(0o755)
        self.final=self.home/'Library/Services/GitHub Upload.workflow'
        self.final.mkdir(parents=True)
        (self.final/'old-marker').write_text('old')

    def run_install(self, fail=False):
        env={**os.environ,'HOME':str(self.home),'PATH':str(self.home/'.local/bin')+':/usr/bin:/bin','FAIL_SETUP':'1' if fail else ''}
        return subprocess.run(['/bin/bash',str(self.source/'install.command')],cwd=self.source,env=env,text=True,capture_output=True,timeout=15)

    def test_failed_setup_preserves_old_workflow(self):
        p=self.run_install(fail=True)
        self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertEqual((self.final/'old-marker').read_text(),'old')
        self.assertEqual(list(self.final.parent.glob('.github-upload-install.*')),[])

    def test_failed_swap_restores_old_workflow(self):
        wrapper=self.home/'.local/bin/mv'
        wrapper.write_text('''#!/bin/sh
case "$1" in */.github-upload-install.*/GitHub\ Upload.workflow) exit 1 ;; esac
exec /bin/mv "$@"
''')
        wrapper.chmod(0o755)
        p=self.run_install()
        self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertEqual((self.final/'old-marker').read_text(),'old')
        self.assertEqual(list(self.final.parent.glob('.github-upload-install.*')),[])

    def test_new_bundle_does_not_depend_on_download_folder(self):
        p=self.run_install()
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn('можно удалить',p.stdout)
        self.assertFalse((self.final/'old-marker').exists())
        base=self.final/'Contents/Resources'
        self.assertTrue((base/'terminal.sh').is_file())
        self.assertTrue((base/'uninstall.command').is_file())
        self.assertFalse((base/'tests').exists())
        shutil.rmtree(self.source)
        self.assertTrue((base/'upload.py').exists())
        self.assertTrue((base/'python').resolve().exists())
        self.assertEqual(list(self.final.parent.glob('.github-upload-install.*')),[])
