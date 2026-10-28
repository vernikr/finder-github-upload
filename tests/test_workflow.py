import pathlib, plistlib, runpy, sys, tempfile, unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]

class WorkflowTests(unittest.TestCase):
    def test_launcher_references_final_not_staging_path(self):
        action={'AMDefaultParameters':{},'AMAccepts':{},'AMProvides':{},'CFBundleVersion':'1','CFBundleIdentifier':'com.apple.RunShellScript','NSPrincipalClass':'RunShellScriptAction'}
        app={'CFBundleVersion':'1','CFBundleShortVersionString':'1'}
        original=pathlib.Path.read_bytes
        def read(path):
            if str(path).endswith('Run Shell Script.action/Contents/Info.plist'): return plistlib.dumps(action)
            if str(path).endswith('Automator.app/Contents/Info.plist'): return plistlib.dumps(app)
            return original(path)
        with tempfile.TemporaryDirectory() as tmp:
            stage=pathlib.Path(tmp)/'stage.workflow'; final=pathlib.Path(tmp)/'GitHub Upload.workflow'
            with patch.object(sys,'argv',['workflow.py',str(stage),str(final)]),patch.object(pathlib.Path,'read_bytes',read):
                runpy.run_path(str(ROOT/'workflow.py'),run_name='__main__')
            doc=plistlib.loads((stage/'Contents/document.wflow').read_bytes())
            command=doc['actions'][0]['action']['ActionParameters']['COMMAND_STRING']
            self.assertIn(str(final),command)
            self.assertNotIn(str(stage),command)
            self.assertIn('"$@"',command)
