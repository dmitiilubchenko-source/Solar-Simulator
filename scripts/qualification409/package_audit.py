"""Final409ZIP/content/smoke audit; no full relocated or year integration."""
import hashlib,json,os,shutil,stat,subprocess,sys,zipfile
from pathlib import Path,PurePosixPath,PureWindowsPath
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar409-build-20261111');P=json.loads((W/'plan.json').read_bytes());B=json.loads((W/'build-completion.json').read_bytes());folder=Path(B['output']);runtime=folder/'runtime';S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();original=folder.with_name(folder.name+'.zip');before=sha(original)
context='''\n## Контекст кандидата409 (не разрешение выпуска)\n\nИсторическая страница docs/releases/v0.4.0.md сохранена из exact237f736 до408.\nПозднейшая техническая source/native/GUI acceptance408:3083PythonPASS/core19PASS\nтолько exact237f736/newnative040/qualifiedenv. Portable acceptance410 НЕ выполнена.\nНовый native SHAa2b7e07573720a269efc712ee4fb74dcc747d24a4967d72d4c3d812158b3399b\nвзят из wheel407V без пересборки; это не новая научная квалификация.\nA+D1:11/11numerical,10/11effects;distance_AB0.244795м вместо10мFAIL;fullD1NO-GO,\n3historical380+4short402FAIL сохранены. TwoQ2—экспериментальная Newton M-Q модель,\nнет Q2-Q2/высшихмультиполей/приливов/диссипации/EIHQ2/универсальной ошибки.\nJPL Verification воспроизводит только исторические сохранённые траектории.\nPhysics Verification/fresh-year перед410требует отдельной source-binding проверки:\nстарый verifier не должен автоматически считать новый runtime историческим.\nMain/tag/LATEST/release не изменены; готовность к пользовательскому выпуску NO-GO.\n'''
assert (folder/'CURRENT-STATUS.md').read_bytes().endswith(context.encode()),'Reuse exact already appended context; no doubleappend'
# Preserve the initial builderZIP; finalZIP additionally includes generated context.
final=folder.with_name(folder.name+'-409.zip')
assert sha(final)=='74247a863bd1c445ecfa736e1a0df60db43ad541cb34d7df5de909410781f3bd','Preserve and verify completed ZIP; no rebuild/repack'
private={'AGENTS.md','changes.md','development-plan.md','learning-log.md','project-review.md','project-context.md','session-handoff.md','session-handoff-archive.md','.env'};members=[]
with zipfile.ZipFile(final) as z:
 assert z.testzip() is None;seen=set()
 for item in z.infolist():
  n=PurePosixPath(item.filename);win=PureWindowsPath(item.filename);assert not n.is_absolute() and not win.drive and '..' not in n.parts and item.filename not in seen;seen.add(item.filename)
  assert not stat.S_ISLNK(item.external_attr>>16) and not any(x in n.parts for x in private|{'.tools','.venv','__pycache__','node_modules'})
  raw=z.read(item);relative=n.relative_to(folder.name).as_posix();assert len(raw)==item.file_size and hashlib.sha256(raw).hexdigest()==sha(folder/relative)
  members.append(dict(path=relative,size=item.file_size,SHA256=hashlib.sha256(raw).hexdigest(),CRC32=f'{item.CRC:08x}'))
actualpackage=runtime/'Lib/site-packages/solar_simulator';expected={p.relative_to(S/'src/solar_simulator').as_posix():sha(p) for p in (S/'src/solar_simulator').rglob('*') if p.is_file() and p.suffix in ('.py','.json','.txt') and '__pycache__' not in p.parts};actual={p.relative_to(actualpackage).as_posix():sha(p) for p in actualpackage.rglob('*') if p.is_file() and p.suffix in ('.py','.json','.txt') and '__pycache__' not in p.parts};assert actual==expected
native=next((runtime/'Lib/site-packages/solar_native').glob('*.pyd'));assert sha(native)==P['native_SHA256'];assert sha(P['wheel'])==P['wheel_SHA256']
from importlib import metadata
sys.path.insert(0,str(Path(P['packaging_root'])));from scripts.build_portable import dependency_closure
for dist in dependency_closure().values():
 root=Path(dist.locate_file('')).resolve()
 for entry in dist.files or []:
  source=Path(dist.locate_file(entry)).resolve()
  if not source.is_relative_to(root) or not source.is_file() or '__pycache__' in source.parts or source.suffix=='.pyc':continue
  target=runtime/'Lib/site-packages'/source.relative_to(root);assert target.is_file() and sha(target)==sha(source),str(entry)
# Extra exact-origin/version/native/Tk/scenario smoke, no orbit integration.
code="""import json,pathlib,sys,tkinter,importlib.metadata as md,solar_simulator,solar_native,numpy,scipy,matplotlib
root=pathlib.Path(sys.executable).resolve().parent
for m in [solar_simulator,solar_native,numpy,scipy,matplotlib]:
 assert pathlib.Path(m.__file__).resolve().is_relative_to(root),'portable origin mismatch'
assert md.version('solar-simulator')==md.version('solar-native')=='0.4.0'
from solar_simulator.inspection import TWO_Q2_EXPERIMENTAL_WARNING as warning
assert '0.244795' in warning and 'NO-GO' in warning and '11/11' in warning
from solar_simulator import scenario_catalog
from solar_simulator.application_profiles import two_q2_demo
state=two_q2_demo();assert len(state.rotations)==2
window=tkinter.Tk();window.withdraw();assert pathlib.Path(window.tk.call('info','library')).is_relative_to(root);window.destroy()
print(json.dumps(dict(prefix=sys.prefix,source=solar_simulator.__file__,native=getattr(solar_native,'solar_native',solar_native).__file__,version=md.version('solar-simulator'),twoQ2=True)))
"""
env=os.environ.copy()
for n in ['PYTHONPATH','PYTHONHOME','TCL_LIBRARY','TK_LIBRARY']:env.pop(n,None)
env['LOCALAPPDATA']=str(W/'smoke-user');env['MPLCONFIGDIR']=str(W/'smoke-matplotlib')
p=subprocess.run([str(runtime/'python.exe'),'-I','-X','utf8','-B','-c',code],cwd=folder,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE);(W/'independent-smoke2.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode()
# A real outsider package injection must fail the same origin predicate.
external=W/'external-site';shutil.copytree(S/'src/solar_simulator',external/'solar_simulator',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
negative="import sys;sys.path.insert(0,"+repr(str(external))+");"+code
p=subprocess.run([str(runtime/'python.exe'),'-I','-X','utf8','-B','-c',negative],cwd=folder,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE);(W/'outside-import-negative.log').write_bytes(p.stdout+p.stderr);assert p.returncode!=0 and b'portable origin mismatch' in p.stderr
# Show the existing410year gate explicitly, without allowing any integration.
year="import sys;sys.path.insert(0,'verification');import recompute_jpl;recompute_jpl.recompute('verification')"
p=subprocess.run([str(runtime/'python.exe'),'-I','-X','utf8','-B','-c',year],cwd=folder,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE);(W/'year-source-gate-preflight.log').write_bytes(p.stdout+p.stderr);assert p.returncode!=0 and b'Runtime scientific source changed: src/solar_simulator/experiment.py' in p.stderr
# Real docs and licenses, not BUILD-INFO alone.
from scripts.check_portable import check_document_links
links=check_document_links(folder);assert (folder/'docs/q2-application-acceptance-402.md').is_file() and (folder/'docs/q2-gui-lifecycle-fix-404.md').is_file() and (actualpackage/'data/ERFA-LICENSE.txt').is_file()
assert sha(original)==before and all(sha(Path(P['packaging_root'])/n)==digest for n,digest in json.loads((W/'build-preflight.json').read_bytes())['runtime_files'].items())
result=dict(status='PASS_BUILD_ZIP_SMOKE_NOT_FULL_ACCEPTANCE',candidate=P['base_runtime_commit'],packaging_commit=B['packaging_commit'],tooling_SHA256=B['tooling_SHA256'],native_SHA256=P['native_SHA256'],wheel_SHA256=P['wheel_SHA256'],directory=str(folder),archive=str(final),archive_size=final.stat().st_size,archive_SHA256=sha(final),initial_builder_archive=dict(path=str(original),SHA256=before,retained_unchanged=True),member_count=len(members),members=members,package_source_files=len(expected),package_identity=True,dependency_identity=True,document_links=links,origin_negative_rejected=True,native_rebuilt=False,smoke='Packaged-I real imports, metadata,Tk,2Q2resource +originalbuilder realGUI/native smokes',year_source_gate='BLOCKED_HISTORICAL_EXPERIMENT_SOURCE_SHA_BEFORE_ANY_INTEGRATION; must be addressed before410, not waived',release_ready=False)
(W/'package-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');final.with_suffix('.zip.sha256').write_text(result['archive_SHA256']+'  '+final.name+'\n',encoding='ascii');print('PACKAGE_AUDIT',result['archive_size'],result['archive_SHA256'],len(members))
