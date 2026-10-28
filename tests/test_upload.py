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
