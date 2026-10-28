import pathlib, plistlib, shlex, uuid
p = pathlib.Path
out = p.home()/'Library/Services/GitHub Upload.workflow/Contents'
out.mkdir(parents=True, exist_ok=True)
action_path = p('/System/Library/Automator/Run Shell Script.action')
info = plistlib.loads((action_path/'Contents/Info.plist').read_bytes())
automator = plistlib.loads(p('/System/Applications/Automator.app/Contents/Info.plist').read_bytes())
launcher = str(p.home()/'.local/share/finder-github-upload/launch.sh')
params = dict(info['AMDefaultParameters'])
params.update(COMMAND_STRING='exec '+shlex.quote(launcher)+' "$@"\n', CheckedForUserDefaultShell=True, inputMethod=1, shell='/bin/bash')
action = {'AMAccepts':info['AMAccepts'], 'AMProvides':info['AMProvides'], 'AMActionVersion':info['CFBundleVersion'], 'CFBundleVersion':info['CFBundleVersion'], 'AMApplication':['Automator'], 'ActionBundlePath':str(action_path), 'ActionName':'Run Shell Script', 'BundleIdentifier':info['CFBundleIdentifier'], 'Class Name':info['NSPrincipalClass'], 'AMParameterProperties':{k:{} for k in info['AMDefaultParameters']}, 'ActionParameters':params, 'CanShowSelectedItemsWhenRun':False, 'CanShowWhenRun':True, 'InputUUID':str(uuid.uuid4()).upper(), 'OutputUUID':str(uuid.uuid4()).upper(), 'UUID':str(uuid.uuid4()).upper(), 'isViewVisible':1, 'nibPath':str(action_path/'Contents/Resources/Base.lproj/main.nib')}
app='/System/Library/CoreServices/Finder.app'
meta={'workflowTypeIdentifier':'com.apple.Automator.servicesMenu', 'inputTypeIdentifier':'com.apple.Automator.fileSystemObject', 'outputTypeIdentifier':'com.apple.Automator.nothing', 'serviceInputTypeIdentifier':'com.apple.Automator.fileSystemObject', 'serviceOutputTypeIdentifier':'com.apple.Automator.nothing', 'applicationBundleID':'com.apple.finder', 'serviceApplicationBundleID':'com.apple.finder', 'applicationPath':app, 'serviceApplicationPath':app, 'applicationPaths':[app], 'applicationBundleIDsByPath':{app:'com.apple.finder'}, 'processesInput':False, 'serviceProcessesInput':False, 'presentationMode':15, 'systemImageName':'NSActionTemplate', 'useAutomaticInputType':False}
doc={'AMApplicationBuild':automator['CFBundleVersion'], 'AMApplicationVersion':automator['CFBundleShortVersionString'], 'AMDocumentVersion':'2', 'actions':[{'action':action,'isViewVisible':1}], 'connectors':{}, 'workflowMetaData':meta}
(out/'document.wflow').write_bytes(plistlib.dumps(doc))
service={'NSMenuItem':{'default':'GitHub Upload'}, 'NSMessage':'runWorkflowAsService', 'NSIconName':'NSActionTemplate', 'NSRequiredContext':{'NSApplicationIdentifier':'com.apple.finder'}, 'NSSendFileTypes':['public.item']}
(out/'Info.plist').write_bytes(plistlib.dumps({'NSServices':[service]}))
print('Установлено:', out.parent)
