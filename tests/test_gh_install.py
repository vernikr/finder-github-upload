import hashlib, io, json, pathlib, tempfile, unittest, zipfile
from unittest.mock import patch
import gh_install

class GhInstallTests(unittest.TestCase):
    def test_download_checksum_and_extract(self):
        z = io.BytesIO()
        with zipfile.ZipFile(z, 'w') as archive:
            archive.writestr('gh_2.0_macOS_arm64/bin/gh', b'executable')
        payload=z.getvalue(); name='gh_2.0_macOS_arm64.zip'; sums='gh_2.0_checksums.txt'
        release={'tag_name':'v2.0','assets':[{'name':name,'browser_download_url':'zip'},{'name':sums,'browser_download_url':'sums'}]}
        responses={gh_install.RELEASE:json.dumps(release).encode(), 'zip':payload, 'sums':(hashlib.sha256(payload).hexdigest()+'  '+name+'\n').encode()}
        with tempfile.TemporaryDirectory() as d, patch.object(gh_install.shutil,'which',return_value=None), patch.object(gh_install.platform,'machine',return_value='arm64'), patch.object(gh_install,'get',side_effect=lambda url: responses[url]):
            result=pathlib.Path(gh_install.find_or_install(d))
            self.assertEqual(result.read_bytes(), b'executable')
            self.assertTrue(result.stat().st_mode & 0o100)
            responses['zip']=b'tampered'
            result.unlink()
            with self.assertRaisesRegex(RuntimeError, 'Контрольная сумма'):
                gh_install.find_or_install(d)
