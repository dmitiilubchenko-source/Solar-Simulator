"""Close408 resource ledger, SHA envelopes and compact report, not release approval."""
from pathlib import Path
import collections,hashlib,json,subprocess,time
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar408-20261111');P=json.loads((W/'plan.json').read_bytes());a=json.loads((W/'independent-audit.json').read_bytes());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
# Independent closure of the auditor's own receipt, which cannot exist during its execution.
for launch in W.glob('launch-*.json'):
    name=launch.stem.removeprefix('launch-')
    if name=='report2':continue  # own wrapper completion is reconciled by final closure
    r=json.loads((W/(name+'-resources.json')).read_bytes());assert r['record']['limit_reason'] is None
    assert r['record']['exit_code']==0 or (name=='report' and r['record']['exit_code']==1)  # preserved reporting-only self-receipt defect, not an acceptance failure
    assert (W/('guard-'+name)/'supervisor.json').is_file()
resource_rows=[json.loads(p.read_bytes()) for p in W.glob('*-resources.json')]
resources=dict(charged_CPU_seconds=sum(x['charged_CPU_seconds'] for x in resource_rows),charged_active_wall_seconds=sum(x['charged_active_wall_seconds'] for x in resource_rows),worker_CPU_measured=sum(x.get('record',{}).get('worker_CPU_seconds',0) for x in resource_rows),supervisor_CPU_measured=sum(x.get('record',{}).get('parent_supervision_CPU_seconds',0) for x in resource_rows),peak_private_worker_tree_sampled=max(x.get('record',{}).get('peak_private_tree_sampled',0) for x in resource_rows),W_disk_bytes=sum(p.stat().st_size for p in W.rglob('*') if p.is_file()),external_new_source_reserve=P['external_source_reserve'],hard=P['hard'],early=P['early'],limitations='50ms requested polling, real process discovery/memory peaks sampled; not OSquota. Worker plus supervisor charged;10CPU25wall initial allowance not measured. Finalization allowance20CPU45wall will be charged separately in same unchanged budget. Backup separate.')
assert resources['charged_CPU_seconds']+20<1920 and resources['charged_active_wall_seconds']+45<2160
files=[]
# Full authoritative receipts only; temporary pytest fixtures are archived separately after review.
for p in sorted(W.rglob('*')):
    if not p.is_file():continue
    n=p.relative_to(W).as_posix()
    if n.startswith(('temp/','cargo-target/','preflight-history','audit-history','document-composition/','matplotlib/','user-data/')):continue
    files.append(dict(path=n,size=p.stat().st_size,SHA256=sha(p)))
evidence=dict(stage=408,candidate=P['candidate_commit'],tree=P['candidate_tree'],source_fingerprint=P['source_fingerprint'],native_SHA256=P['native_SHA256'],wheel_SHA256=P['environment']['native_wheel_SHA256'],interpreter=P['test_python'],prefix=P['environment']['prefix'],original_inventory_SHA256=P['inventory_SHA256'],plan_SHA256=sha(W/'plan.json'),all_source_bindings='source-bindings.json',files=files,executor_source_SHA256={str(p.relative_to(R)):sha(p) for p in (R/'scripts/qualification408').glob('*.py')},status='COMPLETE_STOCK_AND_INDEPENDENT_AUDIT; NOT_RELEASE_APPROVAL',self_audit_supervisor_reconciled=True,excluded_here='Temporary fixtures and recoveries covered by reviewed backup manifest; no claim that excluded cache/dependency/Git copies were cloud uploaded')
(W/'evidence-manifest.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf8',newline='\n');(R/'scripts/qualification408/evidence-manifest.json').write_bytes((W/'evidence-manifest.json').read_bytes())
(W/'resource-ledger-before-finalization.json').write_text(json.dumps(resources,indent=2)+'\n')
verdicts=dict(SOURCE_ACCEPTANCE='PASS_EXACT040_ENV_ONLY',RUST_NATIVE_ACCEPTANCE='PASS_CORE19_FMT_ABI_NATIVE145_RELATED_TESTS',GUI_DESKTOP_ACCEPTANCE='PASS_TESTED_ENV',WORKER_RECOVERY_ACCEPTANCE='PASS_TESTED_PATHS',BACKWARD_COMPATIBILITY='PASS_TESTED_SCOPE',DOCUMENTATION_COMPOSITION='PASS_STATIC_ONLY',SCIENTIFIC_EVIDENCE_SCOPE='PASS_HISTORICAL_SCOPE_PRESERVED_NOT_NEW_NATIVE_SCIENTIFIC_CERTIFICATION',APPLICATION_D1='NO-GO_DISTANCE_EFFECT_FAIL',PORTABLE_READINESS='NOT_BUILT_NOT_ACCEPTED_SEPARATE_PLANNING_ONLY',RELEASE_READINESS='NO-GO_NO_OWNER_RELEASE_APPROVAL_PORTABLE_NOT_ACCEPTED_D1_UNMET')
assert a['technical_GO'] and a['JUnit_counts']=={'PASS':3083}
report=dict(stage=408,date='2026-11-11',candidate=P['candidate_commit'],tree=P['candidate_tree'],candidate_branch=P['candidate_branch'],dev_start=P['dev_start'],source_fingerprint=P['source_fingerprint'],native_SHA256=P['native_SHA256'],wheel_SHA256=P['environment']['native_wheel_SHA256'],ABI=P['environment']['ABI'],actual_python=P['test_python'],prefix=P['environment']['prefix'],versions=a['versions'],original_inventory_SHA256=P['inventory_SHA256'],inventory=dict(total=3083,old3045=3045,new407=28,new407V=10,removed=0,unknown=0,duplicates=a['duplicate_cases']),Python=dict(PASS=3083,FAIL=0,ERROR=0,SKIP=0,stock_exit_code=0,junit_SHA256=a['junit_SHA256'],pytest_wall_seconds=722.57),Rust=dict(core_PASS=19,FAIL=0,ignored=0,core_fmt='PASS',native_fmt='PASS',locked_offline_metadata='PASS',native_rebuilt=False,scope='Actual stock408cargo fmt/core tests; PyO3 exact407Vartifact, not rebuilt'),groups=a['groups'],GUI=dict(real_event_loop=True,layouts=a['layouts'],callback_events=a['gui_callback_events'],background_errors=a['gui_background_errors'],foreign_cancellations=a['gui_foreign_cancellations'],genuine_ballistic_packets=a['gui_completed_packets'],compiled_native_RHS_calls=a['compiled_native_calls'],expected_recovery_write_failure='Injected once then successful retry; no lost committed state',full_stderr_anomalies=a['full_test_stderr_anomalies']),compatibility=dict(legacy_files=47,scope='SHA-bound historical032files/checkpoints/branch inputs via389/407V plus full ordinary regression set; not all formats of all versions',dynamic_rotation_branch='Unsupported unchanged',strict_recipes='Mismatch may reject; never weakened'),documentation=dict(files=338,relative_links=576,stock_file_line_links=1402,static_only=True,ERFA_license_destination='runtime/Lib/site-packages/solar_simulator/data/ERFA-LICENSE.txt',source='exact candidate only',no_portable_build=True),historical_scope=a['science_scope'],failures=[dict(scope='Reporting harness only',phase='report',cause='Attempted to read its own resource receipt before supervisor could publish it',preserved='guard-report/stdout.log + report-resources.json + report-attempt1.py',resolution='Exclude only currently running report2; final closure must reconcile every receipt incl preserved exit1. No candidate/test/science change or full suite rerun')],unresolved=['New native040 has no automatic scientific qualification from033receipts','FullD1 distance_AB effect remainsFAIL;3historical380+4short402convergenceFAIL retained','Portable build/relocated acceptance not authorized/not executed','Release not approved; no main/tag/LATEST changes'],resources=resources,independent_audit=dict(SHA256=sha(W/'independent-audit.json'),source_files_checked=a['source_files_checked'],all3083outcomes_reparsed=True,executor_PASS_flag_not_used_as_sole_proof=True,self_supervisor_reconciled=True,external_review=False),evidence_manifest_SHA256=sha(W/'evidence-manifest.json'),verdicts=verdicts,cloud=dict(status='CLOUD_UNVERIFIED_PENDING_REVIEW_AND_DOWNLOAD'),decision='TECHNICAL SOURCE/NATIVE/GUI GO — exact Solar-Simulator 0.4.0 candidate, verified environment only.',next_step='Plan a separate portable build/relocation acceptance and owner decision on disclosed experimentalQ2scope; no build/release now')
(R/'docs/release-source-acceptance-408.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
text=f'''#408 — полная source/native/GUI приёмка кандидата0.4.0

2026-11-11. **TECHNICAL SOURCE/NATIVE/GUI GO — exact Solar-Simulator 0.4.0 candidate, verified environment only.**
Это не разрешение выпуска. Main/v0.3.2, теги, LATEST, старые portable и evidence399–407V не менялись.
[Машинный отчёт](release-source-acceptance-408.json), [исполнители](../scripts/qualification408/README.md),
[новый immutable plan](../scripts/qualification408/plan.json),
[полный source-bound manifest](../scripts/qualification408/evidence-manifest.json).

## Точный объект и метод

Dev перед работой: `{P['dev_start']}`. Кандидат `{P['candidate_commit']}`,
ветка `{P['candidate_branch']}`, tree `{P['candidate_tree']}`. Worktree чистый;
все Git blobs и raw SHA проверены до/после. Проверялся отдельный checkout, не dev.
Actual source/environment fingerprint `{P['source_fingerprint']}`.
Native040 SHA `{P['native_SHA256']}`; wheel SHA `{P['environment']['native_wheel_SHA256']}`,
ABIcp314-cp314t-win_amd64. Реальные imports — source040 и exact407Venv;
Python3.14.2t/NumPy2.5.1/SciPy1.18.1/Matplotlib3.11.0,
Rust1.99.0GNU/PyO3.29.3. Установок/подмены зависимостей и PyO3 rebuild не было.
Только standalone core tests компилировались из исходников кандидата.

Штатный `scripts/check_project.py --require-native` исполнен **один раз**.
Флаги только reporting: verbose/summary/JUnit; PYTEST selection/config/assertions
не менялись. Новые временные output находятся вне приватных source ancestors.
Junit путь POSIX, отдельный TEMP; nested tests используют разные temp roots.

## Фактические результаты

| Область | Результат |
|---|---|
| Python полный набор |3083PASS /0FAIL /0ERROR /0SKIP; stock exit0|
| Inventory |3045+28+10=3083; удалённых/неизвестных узлов0|
| Rust |fmt core/native PASS;19corePASS,0failed/ignored, настоящий408результат|
| Native-related tests |145PASS по заранее существующим именам файлов; часть проверяет Pythonfacade, не145независимых физических аттестаций|
| GUI-related tests |53PASS; реальный Tk/Matplotlib event loop по существующим сценариям|
| Worker/recovery-related |26PASS плюс отдельный live journey; группы могут пересекаться|
| Storage/compatibility-related |71PASS и47старых SHA-boundфайлов load/roundtrip/expectedreject|
| Документы |338files/576relative links;1402stockfile-line links; static only|

Pytest занял722.57wall-секунды. Exit0 штатного driver включает его собственные
inventory/docs/native preflight, полный pytest, Rustfmt/coretests и links.
Отдельный Rust replay не потребовался. Full suite не повторялся ради PASS.
Все3083outcomes независимо перепарсены из XML; tracebacks отсутствуют, поскольку
нет FAIL/ERROR. RawJUnit/stdout/stderr/exit/timestamps и SHA receipts сохранены.

## GUI, callback ownership и восстановление

Дополнительный функциональный journey переиспользует существующий406контракт:
два настоящих однотельных DOP853пакета к1s/2s с nativeforces, аналитическая
баллистическая проверка, pause/switchbackend/stop/writefailure/retry/save/load/
activeWMclose, неизменность исходного файла и двухQ2q/S при read-only load/save.
Затвор Event действует до вычисления и не подменяет результат solver.
Зафиксированы77callback events,178реальных native RHS calls,0Tclbackgrounderrors,
0foreign cancellations. Destroy leaves no owned callbacks. Статусы и числа
независимо сверены по raw событиям/состояниям, не только по PASS строке.
ДвухQ2орбита заново не интегрировалась в дополнительном journey.

| Окно | Canvas закрытые / открытые настройки, px |
|---|---:|
|1180×820|511 /407|
|1024×768|347 /243|
|900×720|295 /191|

Во всех6случаях canvas строго >170px, labels не пересекаются/не обрезаны,
состояние опыта неизменно. Full штатный layout test дополнительно проверяет
controls/footer clipping. Правильный worker-error контракт407/ownerpoll остался;
не возвращалось требование роста общего количества таймеров.

## История, совместимость и научные границы

External376bundle706900B SHA2326775712ab071ec6354b01f529ba2749c22bbee773e5f26948c11408cc38d5
и immutable033metadata3922B SHAa1fe4cbdf213a6d97652a7d8e2108f584a1c0066ab8fcc5adb96bbc951b5c970
проверены доpytest и независимым аудитором. Missing/corrupt/substitution controls
в полном наборе проходят. Historical artifacts используются как данные;
currentlive modules имеют только source040origins и новый nativeSHA.
Никаких ослаблений strict recipe/source/version gates. Старые пользовательские
состояния проверены в ограниченной области; dynamicQ2branch по-прежнему
не поддерживается, source-bound рецепты вправе отказать в другом окружении.

Historical399fixed58 и28/28equivalence остаются прежними, не новыми408сериями.
Historical402:11/11numericalPASS,10/11effects. distance_AB0.24479543260761333m
вместо10m — **FAIL**; fullD1 **NO-GO**. Три исторических FAIL380 и четыре коротких
FAIL402 сохранены. Никакой universalerrorbound/аттестации реальных тел/
arbitrarytwoQ2нет. Native040не получает научную сертификацию из033receipts.
Это внутренний независимый audit кода/данных, не внешняя научная рецензия.

## Ресурсы и завершение

На момент аудита charged{resources['charged_CPU_seconds']:.6f}CPU/{resources['charged_active_wall_seconds']:.6f}activewall,
измеренные worker{resources['worker_CPU_measured']:.6f}/supervisor{resources['supervisor_CPU_measured']:.6f}CPU.
Sampledworkerprivate peak{resources['peak_private_worker_tree_sampled']}B;
Wdisk{resources['W_disk_bytes']}B+64MiBreserve для новых файлов внеW.
Hard2400CPU/2700wall/3GiB/2GiB;early1920/2160/2.7GiB/1.8GiB неизменны.
Использован exact385monitor SHAfe0f4e83a5b1473a23404e813f3f98693fac8099181d936ca5980e3e1f80a508,
прежний50msrequested cadence; sampling/process discovery могут пропускать пики,
это не OSquota. Ledger cumulative, supervisorCPU включён, receipt аудитора
после его выхода отдельно согласован. Initial10CPU/25wall — консервативный allowance,
не измерение; finalization20CPU/45wall добавляется отдельно в тот же budget.

SOURCE/RUST_NATIVE/GUI_DESKTOP/WORKER_RECOVERY/BACKWARD_COMPATIBILITY — PASS
только в измеренной области. DOCUMENTATION_COMPOSITION — PASSstatic.
SCIENTIFIC_EVIDENCE_SCOPE — сохранён, не новый научный допуск.
APPLICATION_D1 — NO-GO; PORTABLE_READINESS — NOTBUILT/NOTACCEPTED;
RELEASE_READINESS — NO-GO. Нет runtime/test/source fixes и повторных полных запусков. Первый report-only helper пытался прочитать собственный ещё не опубликованный resource receipt; этот FAIL/traceback сохранён и учтён. Исправлен только порядок закрытия отчёта, не результат acceptance; финальная closure сверяет оба report receipts.
Cloud пока **CLOUD_UNVERIFIED**, independentreadback ещё впереди.

Дальше допускается только отдельное планирование portable0.4.0 и приёмки
перенесённой сборки, с решением владельца о явно экспериментальном Q2 scope.
Здесь portable/build/release/main/tag/LATEST не выполняются. После отчёта STOP.
'''
(R/'docs/release-source-acceptance-408.md').write_text(text,encoding='utf8',newline='\n');print('408report and evidence manifest written; no release')
