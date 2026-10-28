import os, pathlib, subprocess, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class TerminalRunnerTests(unittest.TestCase):
    def test_clears_noise_and_finishes_after_enter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)
            base=root/'.local/share/finder-github-upload'
            base.mkdir(parents=True)
            python=base/'python'
            python.write_text('#!/bin/sh\nprintf "Файлов: 2\\n"\n')
            python.chmod(0o700)
            selection=root/'selection'; selection.write_bytes(b'/tmp/test\0')
            finished=root/'finished'
            p=subprocess.run(['/bin/bash',str(ROOT/'terminal.sh'),str(selection),str(finished)],input='\n',text=True,capture_output=True,env={**os.environ,'HOME':str(root)},timeout=5)
            self.assertEqual(p.returncode,0)
            self.assertTrue(p.stdout.startswith('\x1b[2J\x1b[HФайлов: 2'))
            self.assertTrue(finished.exists())
            self.assertIn('Нажмите Enter',p.stdout)

    def test_upload_error_does_not_skip_enter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);base=root/'.local/share/finder-github-upload';base.mkdir(parents=True)
            python=base/'python';python.write_text('#!/bin/sh\necho failure >&2\nexit 1\n');python.chmod(0o700)
            finished=root/'done'
            p=subprocess.run(['/bin/bash',str(ROOT/'terminal.sh'),str(root/'selection'),str(finished)],input='\n',text=True,capture_output=True,env={**os.environ,'HOME':str(root)},timeout=5)
            self.assertIn('failure',p.stderr)
            self.assertIn('Нажмите Enter',p.stdout)
            self.assertTrue(finished.exists())
