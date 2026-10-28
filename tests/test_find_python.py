import os, pathlib, subprocess, tempfile, unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'find-python.sh'

class FindPythonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = pathlib.Path(self.tmp.name)

    def executable(self, name, body):
        path = self.directory / name
        path.write_text('#!/bin/sh\n' + body + '\n')
        path.chmod(0o755)
        return str(path)

    def find(self, uv=''):
        env = dict(os.environ, PATH=str(self.directory), uv=uv)
        return subprocess.run(['/bin/bash', '-c', '. "$1"; find_existing_python', '_', str(SCRIPT)], env=env, text=True, capture_output=True)

    def test_uses_python_313(self):
        expected = self.executable('python3.13', 'exit 0')
        found = self.find()
        self.assertEqual(found.returncode, 0)
        self.assertEqual(found.stdout.strip(), expected)

    def test_rejects_old_python(self):
        self.executable('python3', 'exit 1')
        self.assertNotEqual(self.find().returncode, 0)

    def test_uv_managed_python_no_download(self):
        expected = self.executable('managed-python', 'exit 0')
        uv = self.executable('uv', 'test "$*" = "python find --system --no-python-downloads >=3.12,<4" || exit 4\nprintf "%s\\n" ' + "'" + expected + "'")
        found = self.find(uv)
        self.assertEqual(found.returncode, 0)
        self.assertEqual(found.stdout.strip(), expected)

    def test_falls_back_when_uv_find_fails(self):
        uv = self.executable('uv', 'exit 1')
        expected = self.executable('python3.14', 'exit 0')
        self.assertEqual(self.find(uv).stdout.strip(), expected)
