"""Separate408 read-only auditor: raw artifacts, outcomes, bindings and science scope.
No solver acquisition and no reliance on the executor's ready-made PASS flag.
"""
import collections,hashlib,importlib,importlib.metadata as md,json,math,re,subprocess,sys,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar408-20261111');P=json.loads((W/'plan.json').read_bytes());S=Path(P['candidate_source']);sys.path[:0]=[str(S),str(S/'tests')]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def save(p,d):
    with Path(p).open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
    source=read(W/'source-bindings.json');git=lambda *a:subprocess.check_output(['git','-C',str(S),*a]);assert not git('status','--porcelain');assert git('rev-parse','HEAD').decode().strip()==P['candidate_commit'];assert git('rev-parse','HEAD^{tree}').decode().strip()==P['candidate_tree']
    for n,row in source.items():assert sha(S/n)==row['SHA256'],n
    # Validate against frozen Git tree, not a newly assembled source whitelist.
    tree={n.decode():meta.decode().split()[2] for row in git('ls-tree','-r','-z','HEAD').split(b'\0') if row for meta,n in [row.split(b'\t',1)]};assert tree=={n:row['git_blob'] for n,row in source.items()}
    for n,digest in read(W/'historical-input-bindings.json').items():assert sha(R/n)==digest,n
    for n,digest in read(W/'execution-bindings.json')['source'].items():assert sha(R/n)==digest,n
    from solar_simulator.recipe import runtime_fingerprint
    from scripts.native_audit import require_native
    from scripts.build_portable import candidate_versions,prepare_documents
    from scripts.check_portable import check_document_links
    import solar_simulator,solar_native,numpy,scipy,matplotlib
    require_native();compiled=getattr(solar_native,'solar_native',solar_native);native=Path(compiled.__file__).resolve();assert sha(native)==P['native_SHA256']
    assert Path(sys.prefix).resolve()==Path(P['environment']['prefix']).resolve();assert Path(sys.executable).resolve()==Path(P['test_python']).resolve()
    assert Path(solar_simulator.__file__).resolve().is_relative_to(S/'src');assert native.is_relative_to(Path(sys.prefix));assert candidate_versions(S)[0]=='0.4.0';assert md.version('solar-simulator')==md.version('solar-native')=='0.4.0'
    fp=(json.dumps(runtime_fingerprint('rust'),indent=2)+'\n').encode();assert hashlib.sha256(fp).hexdigest()==P['source_fingerprint'];assert fp==(W/'actual-environment.json').read_bytes();(W/'post-environment.json').write_bytes(fp)
    imports={}
    for n in ['experiment','accuracy','error_control','native_forces','rust_backend','storage','recovery','nbody_rotation','rotation','app','inspection','recipe']:
        module=importlib.import_module('solar_simulator.'+n);assert Path(module.__file__).resolve().is_relative_to(S/'src');imports[n]=module.__file__
    assert all(not any(marker in p for marker in ('preflight-history','audit-history','source-before')) for p in imports.values())
    wheel=Path(P['required_external_inputs'][-1]['source']);assert sha(wheel)==P['environment']['native_wheel_SHA256']
    with zipfile.ZipFile(wheel) as z:
        assert z.testzip() is None;binary=z.read(next(n for n in z.namelist() if n.endswith('.pyd')));assert binary==native.read_bytes();assert 'Version: 0.4.0' in z.read('solar_native-0.4.0.dist-info/METADATA').decode();assert 'Tag: cp314-cp314t-win_amd64' in z.read('solar_native-0.4.0.dist-info/WHEEL').decode()
    pre=read(W/'preflight.json')
    for n,digest in pre['optional_dependency'].items():assert sha(n)==digest
    # Reparse JUnit independently from the census implementation and its status flags.
    cases=list(ET.parse(W/'results/python.xml').getroot().iter('testcase'));expected=read(R/P['inventory'])['nodes'];xml_to_nodes={}
    for node in expected:
        parts=node.split('::');key=('.'.join([parts[0][:-3].replace('/','.'),*parts[1:-1]]),parts[-1]);assert key not in xml_to_nodes;xml_to_nodes[key]=node
    parsed=collections.defaultdict(list)
    for case in cases:
        key=case.get('classname'),case.get('name');assert key in xml_to_nodes,key
        status='ERROR' if case.find('error') is not None else 'FAIL' if case.find('failure') is not None else 'SKIP' if case.find('skipped') is not None else 'PASS';parsed[xml_to_nodes[key]].append(status)
        for part in list(case):assert 'xfail' not in (part.get('type','')+' '+part.get('message','')).lower(),'xfail waiver not allowed'
    assert set(parsed)==set(expected) and len(parsed)==3083
    priority={'PASS':0,'SKIP':1,'FAIL':2,'ERROR':3};actual={n:max(rows,key=priority.get) for n,rows in parsed.items()};counts=dict(collections.Counter(actual.values()));census=read(W/'python-outcomes.json');assert counts==census['counts'] and census['junit_SHA256']==sha(W/'results/python.xml')
    assert {r['nodeid']:r['status'] for r in census['outcomes']}==actual
    full=read(W/'full_stock-completion.json');driver_exit=full['commands'][-1]['exit_code'];assert full['candidate']==P['candidate_commit'] and full['plan_SHA256']==sha(W/'plan.json') and full['junit_SHA256']==sha(W/'results/python.xml')
    assert full['native_rebuilt'] is False
    log=(W/'guard-full-stock/stdout.log').read_text(encoding='utf8');rust_separate=W/'rust_completion-completion.json';rust_records=[]
    if rust_separate.exists():
        rust=read(rust_separate);rust_log=(W/'guard-rust/stdout.log').read_text(encoding='utf8');rust_records=rust['commands'];rust_ok=all(x['exit_code']==0 for x in rust_records) and '19 passed; 0 failed; 0 ignored' in rust_log
    else:
        rust_log=log;rust_ok=driver_exit==0 and '19 passed; 0 failed; 0 ignored' in log
    # GUI callback/state observer independent of final PASS string.
    gui=read(W/'gui/result.json');gui_errors=gui['background_errors'];foreign=gui['foreign_cancellations'];owners={}
    for e in gui['callbacks']:
        key=e['interpreter'],e['after_id']
        if e['event']=='schedule':owners[key]=e['owner']
        elif e['event']=='cancel':assert owners[key]==e['owner']
        else:raise AssertionError(e)
    assert all(not row['after'] for row in gui['destroy'] if row['status']=='CLOSED')
    assert [x['time'] for x in gui['real_completed_packets']]==[1.,2.] and gui['compiled_native_calls']>0
    for key,t in [('stopped',1.),('closed',2.)]:
        checkpoint=gui['checkpoints'][key];assert checkpoint['time']==t;position=checkpoint['bodies'][0]['position'];assert all(abs(x-y)<=1e-12 for x,y in zip(position,[1+2*t,2-t,3+.5*t]))
    assert len(gui['messages'])==1 and '408 controlled write failure' in gui['messages'][0][1]
    layouts=read(W/'408-layout.json');assert len(layouts['rows'])==6;assert {(x['width'],x['height'],x['settings_open']) for x in layouts['rows']}=={(w,h,v) for w,h in [(1180,820),(1024,768),(900,720)] for v in (False,True)}
    assert not layouts['background_errors'] and layouts['state_unchanged'];assert min(x['canvas_height'] for x in layouts['rows'])>170
    for row in layouts['rows']:
        upper=row['upper_label'];title=row['lower_title'];lower=row['lower_label'];assert upper[1]>=title[1]+title[3] and lower[1]>=0
    anomalies=read(W/'stderr-anomalies.json')
    gui_files={'test_app.py','test_app_usability.py','test_app_workflows.py','test_poll_ownership407.py','test_two_q2_gui.py','test_recovery_journey.py','test_controlled_stop.py','test_sandbox_gui.py','test_time_control_gui.py','test_laboratory_rotation_gui.py'}
    groups={label:{n:v for n,v in actual.items() if predicate(n)} for label,predicate in [('GUI',lambda n:'_gui.py::' in n or Path(n.split('::')[0]).name in gui_files),('worker_recovery',lambda n:any(x in n.split('::')[0] for x in ['recovery','controlled_stop','app_workflows','poll_ownership'])),('native',lambda n:any(x in n.split('::')[0] for x in ['test_native','test_numeric_native','test_rust','test_required_native','qualification383_native'])),('storage_compatibility',lambda n:any(x in n.split('::')[0] for x in ['storage','checkpoint','sandbox_branch','branch_commands','parent_gui','schema']))]}
    # Verify unchanged historical inputs and current-model warning directly.
    from historical376_fixture407 import checkout
    from historical033_fixture407v import restore033
    checkout(S,W/'audit-history376');restore033(W/'audit-history033')
    from test_historical_sources407 import assert_version
    assert_version(W/'audit-history033','0.3.3');assert_version(S,'0.4.0')
    from solar_simulator.inspection import TWO_Q2_EXPERIMENTAL_WARNING as warning
    assert 'Solar-Simulator 0.4.0 — кандидат, выпуск не разрешён.' in warning
    for text in ['11/11','10/11','0.244795','10 м — FAIL','Три исторических FAIL380','четыре новых коротких FAIL','NO-GO','не получает допуска402','Универсальные границы ошибки']:
        assert text in warning,text
    plain_paths=re.findall(r'docs/[A-Za-z0-9_.-]+\.md',warning);assert plain_paths and all((S/n).is_file() for n in plain_paths)
    science399=read(R/'docs/q2-scientific-qualification-399.json');science402=read(R/'docs/q2-application-acceptance-402.json');observables=science402['observable_summary'];assert len(science399['jobs'])==58 and len(observables)==11;assert all(x['numerical_gate']=='PASS' for x in observables);assert sum(x['effect_gate']=='PASS' for x in observables)==10
    distance=next(x for x in observables if x['observable']=='distance_AB');assert distance['effect_gate']=='FAIL' and distance['Delta']==10. and abs(distance['minimum_demonstrated_change']-.24479543260761333)<1e-15
    assert 'THREE380_AND_FOUR_NEW_SHORT' in science402['verdicts']['HISTORICAL_SCIENTIFIC_GATE'];assert science402['verdicts']['RELEASE_READINESS']=='NO-GO'
    # Current documentation-only staging includes exact license in real destination.
    out=W/'document-composition';out.mkdir(exist_ok=False);documents=prepare_documents(out);license=out/'runtime/Lib/site-packages/solar_simulator/data/ERFA-LICENSE.txt';license.parent.mkdir(parents=True);license.write_bytes((S/'src/solar_simulator/data/ERFA-LICENSE.txt').read_bytes());links=check_document_links(out)
    assert (out/'docs/releases/v0.4.0.md').is_file() and (out/'docs/releases/v0.4.0.md').read_text(encoding='utf8')==(S/'docs/releases/v0.4.0.md').read_text(encoding='utf8')
    assert not list(out.rglob('*.pyd')) and [p for p in (out/'runtime').rglob('*') if p.is_file()]==[license]
    forbidden={'AGENTS.md','changes.md','development-plan.md','session-handoff.md','session-handoff-archive.md'};assert not any(p.name in forbidden for p in out.rglob('*'))
    # Offline backward compatibility: authenticate original032file bytes via389/407V manifests.
    from solar_simulator.storage import load,to_document,from_document
    from solar_simulator.branch_io import open_experiment
    previous=read(R/'docs/version-migration-407v.json')['compatibility']['historical_files'];legacy=R/'.tools/qualification389';legacy_rows=[]
    for row in previous:
        name=row['name'];path=legacy/name if name.startswith('accepted/') else legacy/'inputs'/name;assert sha(path)==row.get('SHA256',read(R/'docs/compatibility-389-validation.json')['input_binding']['inputs_SHA256'].get(name)),name
        if row.get('expected_rejection'):
            try:load(path)
            except (ValueError,KeyError):legacy_rows.append(dict(name=name,rejected=True));continue
            raise AssertionError('Historical invalid file accepted')
        state,parent=open_experiment(path);document=to_document(state);assert to_document(from_document(document))==document;legacy_rows.append(dict(name=name,roundtrip=True,parent_present=parent is not None))
    save(W/'backward-compatibility-audit.json',legacy_rows)
    # Cumulative receipts are complete even when the command failed; never equate completion with PASS.
    receipts={}
    for p in W.glob('launch-*.json'):
        name=p.stem.removeprefix('launch-')
        if name=='audit':continue  # own supervisor publishes only after auditor exit; final ledger must reconcile it
        f=W/(name+'-resources.json');assert f.is_file(),'Missingresource receipt '+name;record=read(f);assert (W/('guard-'+name)/'supervisor.json').is_file();assert sha(R/'.tools/qualification385/offline_monitor.py')==P['monitor']['SHA256'];receipts[name]=dict(resource_SHA256=sha(f),execution_exit=record['record']['exit_code'],limit_reason=record['record']['limit_reason'])
    # The running auditor receipt is published by supervisor only after this process exits.
    incomplete=[x for x in receipts if receipts[x]['limit_reason']];assert not incomplete,incomplete
    nonpass=[n for n,v in actual.items() if v!='PASS'];source_ok=not nonpass and driver_exit==0 and rust_ok and not gui_errors and not foreign and not anomalies
    group_summary={k:dict(count=len(v),counts=dict(collections.Counter(v.values()))) for k,v in groups.items()}
    save(W/'independent-audit.json',dict(status='AUDIT_COMPLETED',candidate=P['candidate_commit'],tree=P['candidate_tree'],source_fingerprint=P['source_fingerprint'],native_SHA256=P['native_SHA256'],wheel_SHA256=sha(wheel),source_files_checked=len(source),all_source_unchanged=True,imports=imports,versions={n:md.version(n) for n in ['solar-simulator','solar-native','numpy','scipy','matplotlib']},JUnit_counts=counts,raw_XML_cases=len(cases),nodes_checked=3083,duplicate_cases=census['duplicate_cases'],junit_SHA256=sha(W/'results/python.xml'),stock_exit_code=driver_exit,Rust_core19_fmt_success=rust_ok,Rust_commands=rust_records,groups=group_summary,gui_callback_events=len(gui['callbacks']),gui_completed_packets=[1.,2.],compiled_native_calls=gui['compiled_native_calls'],gui_background_errors=gui_errors,gui_foreign_cancellations=foreign,full_test_stderr_anomalies=anomalies,layouts=[{k:r[k] for k in ['width','height','settings_open','canvas_height']} for r in layouts['rows']],historical_raw_unchanged=True,current_runtime_origins_only=True,legacy_files_checked=len(legacy_rows),document_files=len([p for p in out.rglob('*') if p.is_file()]),document_links=links,plain_warning_paths=plain_paths,science_scope=dict(jobs399=58,numerical402='11/11',effects402='10/11',distance_FAIL=distance,historical380_FAIL=3,short402_FAIL=4,fullD1='NO-GO',new_native_not_scientifically_certified=True),resource_receipts=receipts,self_resource_receipt='PENDING_SUPERVISOR_ON_EXIT_MUST_RECONCILE',nonpass_nodes=nonpass,technical_GO=source_ok,release_GO=False,portable_acceptance_executed=False))
    print('INDEPENDENT408AUDIT',counts,'stockexit',driver_exit,'Rust',rust_ok,'technicalGO',source_ok)
if __name__=='__main__':main()
