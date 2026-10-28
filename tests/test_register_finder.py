import copy, plistlib, pathlib, tempfile, unittest
from unittest.mock import patch, Mock
import register_finder as reg

class FinderRegistrationTests(unittest.TestCase):
    def test_preserves_other_preferences_and_shortcuts(self):
        before={'SomethingElse': {'v': 2}, 'NSServicesStatus': {'other': {'x': 3}, reg.KEY: {'key_equivalent':'@x','presentation_modes':{'TouchBar':False,'ContextMenu':False}}}}
        result=reg.update_preferences(copy.deepcopy(before))
        self.assertEqual(result['SomethingElse'],before['SomethingElse'])
        self.assertEqual(result['NSServicesStatus']['other'],{'x':3})
        entry=result['NSServicesStatus'][reg.KEY]
        self.assertEqual(entry['key_equivalent'],'@x')
        self.assertIs(entry['presentation_modes']['TouchBar'],False)
        self.assertIs(entry['presentation_modes']['ContextMenu'],True)
        self.assertIs(entry['presentation_modes']['ServicesMenu'],True)

    def test_existing_custom_identifier(self):
        name='com.example - GitHub Upload - runWorkflowAsService'
        data={'NSServicesStatus':{name:{}}}
        reg.update_preferences(data)
        self.assertNotIn(reg.KEY,data['NSServicesStatus'])
        self.assertTrue(data['NSServicesStatus'][name]['presentation_modes']['ContextMenu'])

    def test_registration_backs_up_and_imports_merged_data(self):
        old=plistlib.dumps({'custom':'untouched'})
        calls=[]
        def fake_run(args, **kwargs):
            calls.append((args,kwargs))
            if args[1] == 'export': return Mock(returncode=0,stdout=old,stderr=b'')
            return Mock(returncode=0,stdout=b'',stderr=b'')
        with tempfile.TemporaryDirectory() as tmp, patch.object(reg.pathlib.Path, 'home', return_value=pathlib.Path(tmp)), patch.object(reg.subprocess,'run',side_effect=fake_run):
            reg.register(pathlib.Path(tmp)/"backup")
            backups=list(pathlib.Path(tmp).rglob('pbs-backup-*.plist'))
            self.assertEqual(len(backups),1)
            self.assertEqual(backups[0].read_bytes(),old)
            updated=plistlib.loads(calls[1][1]['input'])
            self.assertEqual(updated['custom'],'untouched')
            self.assertTrue(updated['NSServicesStatus'][reg.KEY]['presentation_modes']['ContextMenu'])
