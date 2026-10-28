import pathlib, tempfile, unittest, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import upload

class SelectionTests(unittest.TestCase):
    def test_nested_and_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp); d=root/'папка'; d.mkdir(); (d/'.hidden').write_text('a'); (d/'hello.txt').write_text('b')
            self.assertEqual([x[1] for x in upload.collect([str(d)])], ['папка/.hidden', 'папка/hello.txt'])
    def test_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp); (root/'a').write_text('x'); (root/'link').symlink_to(root/'a')
            with self.assertRaises(upload.UploadError): upload.collect([str(root/'link')])
    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(upload.UploadError): upload.collect([tmp])
    def test_single_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=pathlib.Path(tmp); (r/'a').mkdir(); (r/'b').mkdir(); (r/'a'/'x').touch(); (r/'b'/'y').touch()
            with self.assertRaises(upload.UploadError): upload.collect([str(r/'a'/'x'), str(r/'b'/'y')])
if __name__=='__main__': unittest.main()

class GitTests(unittest.TestCase):
    def test_one_commit_with_paths(self):
        from unittest.mock import patch
        calls=[]
        def fake_api(token, method, path, data=None):
            calls.append((method,path,data))
            if path == '': return {'default_branch':'main'}
            if path.startswith('/git/ref/heads/'): return {'object':{'sha':'parent'}}
            if path == '/git/commits/parent': return {'tree':{'sha':'base'}}
            if path == '/git/blobs': return {'sha':'blob'}
            if path == '/git/trees': return {'sha':'tree'}
            if method == 'POST' and path == '/git/commits': return {'sha':'commit'}
            if method == 'PATCH': return {}
            raise AssertionError((method,path))
        with tempfile.TemporaryDirectory() as tmp:
            d=pathlib.Path(tmp)/'dir'; d.mkdir(); (d/'a.txt').write_text('hello')
            with patch.object(upload,'api',side_effect=fake_api), patch.object(upload,'token_get',return_value='test'), patch.object(upload.subprocess,'run'):
                upload.run([str(d)])
        tree = next(data for method,path,data in calls if path == '/git/trees')
        self.assertEqual(tree['base_tree'],'base')
        self.assertTrue(tree['tree'][0]['path'].endswith('/dir/a.txt'))
        self.assertEqual(sum(method=='PATCH' for method,path,data in calls), 1)

class AuthTests(unittest.TestCase):
    def test_browser_setup_saves_method_not_token(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(upload, 'app_dir', return_value=pathlib.Path(temp)), \
                 patch.object(upload.gh_install, 'find_or_install', return_value='/usr/local/bin/gh'), \
                 patch.object(upload, 'gh_token', return_value='secret-token'), \
                 patch.object(upload, 'api', return_value={'permissions': {'push': True}, 'size': 1}), \
                 patch('builtins.input', side_effect=['1', '']):
                upload.setup()
            config = (pathlib.Path(temp) / 'auth.json').read_text()
            self.assertNotIn('secret-token', config)
            self.assertEqual(upload.json.loads(config)['method'], 'gh')

    def test_gh_missing_is_readable_error(self):
        from unittest.mock import patch
        with patch.object(upload.subprocess, 'run', side_effect=FileNotFoundError('missing')):
            with self.assertRaises(upload.UploadError): upload.gh_token('/missing/gh')

    def test_no_config_uses_old_keychain(self):
        from unittest.mock import patch, Mock
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(upload, 'app_dir', return_value=pathlib.Path(temp)), \
                 patch.object(upload.subprocess, 'run', return_value=Mock(returncode=0, stdout='old-token\n')):
                self.assertEqual(upload.token_get(), 'old-token')

class InitializationTests(unittest.TestCase):
    def test_empty_repo_initialized_without_question(self):
        from unittest.mock import patch
        calls = []
        def fake_api(token, method, path, data=None):
            calls.append((method,path))
            if path == '': return {'permissions': {'push': True}, 'size': 0, 'default_branch': 'main'}
            if method == 'GET': raise upload.UploadError('GitHub HTTP 409: Git Repository is empty.')
            if method == 'PUT': return {}
            raise AssertionError((method,path))
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(upload, 'app_dir', return_value=pathlib.Path(tmp)), \
                 patch.object(upload.gh_install, 'find_or_install', return_value='/usr/local/bin/gh'), \
                 patch.object(upload, 'gh_token', return_value='t'), \
                 patch.object(upload, 'api', side_effect=fake_api), \
                 patch('builtins.input', side_effect=['1', '']):
                upload.setup()
        self.assertIn(('PUT', '/contents/README.md'), calls)

    def test_nonempty_repo_is_not_initialized(self):
        from unittest.mock import patch
        calls=[]
        def fake_api(token,method,path,data=None):
            calls.append((method,path))
            return {'permissions':{'push':True}, 'size': 5}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(upload, 'app_dir', return_value=pathlib.Path(tmp)), \
                 patch.object(upload.gh_install, 'find_or_install', return_value='/usr/local/bin/gh'), \
                 patch.object(upload, 'gh_token', return_value='t'), \
                 patch.object(upload, 'api', side_effect=fake_api), \
                 patch('builtins.input', side_effect=['1','']): upload.setup()
        self.assertEqual(calls,[('GET','')])

class BundledGhTests(unittest.TestCase):
    def test_gh_is_recorded_relocatably(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp:
            base=pathlib.Path(temp)
            with patch.object(upload, 'app_dir', return_value=base), \
                 patch.object(upload.gh_install, 'find_or_install', return_value=str(base/'gh')), \
                 patch.object(upload, 'gh_token', return_value='secret'), \
                 patch.object(upload, 'api', return_value={'permissions':{'push':True}, 'size': 1}), \
                 patch('builtins.input', side_effect=['1','']): upload.setup()
            auth=upload.json.loads((base/'auth.json').read_text())
            self.assertEqual(auth['gh'], ':bundled:')
            with patch.object(upload, 'app_dir', return_value=base), patch.object(upload, 'gh_token', return_value='t') as token:
                self.assertEqual(upload.token_get(),'t')
                token.assert_called_once_with(str(base/'gh'))
