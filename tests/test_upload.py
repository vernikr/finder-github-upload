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
