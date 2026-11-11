"""409 build report and frozen410inputs, preserving the known yeargate blocker."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar409-build-20261111');A=Path('C:/Users/Admin/Documents/Codex/Solar409-20261111');p=json.loads((W/'plan.json').read_bytes());a=json.loads((W/'package-audit.json').read_bytes());c=json.loads((W/'runtime-content-audit.json').read_bytes());cloud=json.loads((A/'cloud-final-closure.json').read_bytes());sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest();root=Path(a['directory'])
# Frozen artifact inputs; no invented successful fresh-year acceptance.
plan=dict(stage=410,status='FROZEN_INPUTS_BLOCKED_VERIFIER_BINDING_NOT_AUTHORIZED_NOT_EXECUTED',runtime_commit=p['base_runtime_commit'],runtime_tree=p['base_runtime_tree'],packaging_commit=a['packaging_commit'],tooling_SHA256=a['tooling_SHA256'],archive=a['archive'],archive_SHA256=a['archive_SHA256'],archive_size=a['archive_size'],archive_member_count=a['member_count'],archive_root=root.name,native_SHA256=p['native_SHA256'],wheel_SHA256=p['wheel_SHA256'],environment='PackagedCPython3.14.2t/NumPy2.5.1/SciPy1.18.1/Matplotlib3.11.0; newrelocationwithspaces,-I,noPYTHONPATH; no qualifiedvenv imports',hard=dict(cpu_seconds=900,wall_seconds=1200,private_bytes=2147483648,disk_bytes=2147483648),early=dict(cpu_seconds=720,wall_seconds=960,private_bytes=1932735283,disk_bytes=1932735283),forecast=dict(CPU_seconds=None,active_wall_seconds=None,reason='409shortsmokes are not a forecast for year/continuous workloads. Must inspect current verifier and prior measured410-equivalentcost before admission; caps not raised automatically.'),mandatory=['Verify originalZIP/allmembers/source/native/ABI/license/privacy','ExtracttoNEWpathwithspaces; noPYTHONPATH/-I actualruntime origins','RealGUI/lifecycle/backend0/1/2Q2/save/load/branch/recovery/oldfiles','SavedJPLreplay AND genuine fresh-year propagation; no cachedNPZreplacement','Mandatorycurrent continuous-year probes; all errors/FAIL/partial preserved','Independent rawoutcome/resource/scientificscopeaudit','Reviewedbackup/independentcloudSHA-size-parent-owner'],known_blockers=[dict(component='verification/recompute_jpl.py',failure='Runtime scientific source changed: src/solar_simulator/experiment.py',evidence_SHA256=sha(W/'year-source-gate-preflight.log'),cause='Historical strictreport pins oldgenerator experiment/application_profiles bytes. Current040source differs. Savedreplay is valid but cannot authorize current solver.',required_resolution='Separate reviewed qualification-only current-source binding mode/protocol before anyyearrun; preserve oldstrictmode, oldreports/SHA/IC/settings/thresholds and require live040allsource/native/environment proof. Negativecontrols for substituted source/native/version/environment. Do not simply replace historicalexpectedSHA or waive freshyear.',not_implemented=True)],preflight_must_stop_if_blocker_unresolved=True,portable_acceptance_pass=False,release_approved=False)
(R/'scripts/qualification409/acceptance410-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf8',newline='\n')
zipmanifest=dict(archive=a['archive'],archive_SHA256=a['archive_SHA256'],archive_size=a['archive_size'],root=root.name,members=a['members']);(R/'scripts/qualification409/zip-members.json').write_text(json.dumps(zipmanifest,indent=2)+'\n',encoding='utf8',newline='\n')
rows=[json.loads(f.read_bytes()) for f in W.glob('*-resources.json')];resource=dict(charged_CPU=sum(x['charged_CPU_seconds'] for x in rows),charged_active_wall=sum(x['charged_active_wall_seconds'] for x in rows),worker_CPU_measured=sum(x.get('record',{}).get('worker_CPU_seconds',0) for x in rows),supervisor_CPU_measured=sum(x.get('record',{}).get('parent_supervision_CPU_seconds',0) for x in rows),sampled_worker_private_peak=max(x.get('record',{}).get('peak_private_tree_sampled',0) for x in rows),new_data_in_W=sum(f.stat().st_size for f in W.rglob('*') if f.is_file()),external_source_reserve=p['external_source_reserve'],hard=p['hard'],early=p['early'],limitations='Sampled, not OSquota; supervisor charged. Includes every failed audit attempt. Initial5CPU10wall allowance conservative. Finalization to be added without capreset; newbackup separate.')
verdicts=dict(CLOUD_408_CLOSURE='PASS_NEW409READBACK_CRC_SHA',SOURCE_IDENTITY='PASS_FROZEN237_RUNTIME_RAWBYTES',NATIVE_WHEEL_REUSE='PASS_EXACT407VWHEEL_NO_REBUILD',PORTABLE_BUILD='PASS_UNRELEASED_CANDIDATE',PACKAGED_RUNTIME_SMOKE='PASS_LIMITED',PACKAGE_CONTENT_INTEGRITY='PASS_ALL6001MEMBERS_AND_RUNTIME_CLOSURE',SCIENTIFIC_SCOPE='PASS_PRESERVED_LIMITATIONS_NOT_NEW_CERTIFICATION',PORTABLE_ACCEPTANCE410='NOT_RUN_BLOCKED_STOCK_FRESH_YEAR_SOURCE_GATE',RELEASE_READINESS='NO-GO')
r=dict(stage=409,date='2026-11-11',dev_start='7f89c39a92ebf8f94948007b2a04a7be10963f03',runtime_commit=p['base_runtime_commit'],runtime_tree=p['base_runtime_tree'],runtime_source_fingerprint=p['source_fingerprint'],packaging_branch=p['packaging_branch'],packaging_commit=a['packaging_commit'],packaging_tooling_SHA256=a['tooling_SHA256'],tooling_changed_paths=['scripts/build_portable.py'],native_SHA256=p['native_SHA256'],native_wheel_SHA256=p['wheel_SHA256'],native_rebuilt=False,archive=a['archive'],archive_SHA256=a['archive_SHA256'],archive_size=a['archive_size'],archive_members=a['member_count'],original_builder_archive=a['initial_builder_archive'],source_package_files=a['package_source_files'],runtime_file_count=c['runtime_file_count'],license_file_count=len(c['license_files']),runtime_roles=c['roles_count'],developer_packages_absent=c['developer_packages_absent'],document_links=a['document_links'],cloud408_closure=cloud,resource_build=resource,packaged_probe=json.loads((W/'independent-smoke2.log').read_text().splitlines()[0]),negative_controls=json.loads((W/'negative-controls.json').read_bytes()),outside_import_negative=True,original_export_refusal_SHA256=sha(W/'original-export-failure.log'),historical_export=dict(role='Savedhistoricalreplay only; originalexporter/verified_sources unchanged. ExactoldsourceDATA restored from pinnedarchives, current040modules imported; advanceforbidden inpreflight, nooldruntime/physics execution',source_fixture_manifest_SHA256=json.loads((W/'build-preflight.json').read_bytes())['historical_manifest_SHA256'],source_snapshots=p['historic_source_substitutions']),failures=[dict(scope='Originalexporter current-source guard',status='Expectedrefusal preserved, not waived',resolution='Separate SHA-bound historical source-data fixture for savedreplay; no changedguards/currentruntimecertification'),dict(scope='Diagnosticpackage-audit firstattempt',cause='Wrongname scenario(two-q2-demo) instead of existing two_q2_demo() factory',resolution='Onlyauditscript corrected; firstFAIL/log/source kept. No rebuild, no packagecodechange'),dict(scope='Contentaudit firsttwoattempts',cause='Independent top-level allowlist omitted declaredERFAsource-license copy and publictests/data/jpl-verification.zip',resolution='Exactalreadydeclaredpublicassets checkedagainstsourceSHA; no blanketwaiver or packagechange. RawFAILs kept')],known_next_blocker=plan['known_blockers'],acceptance410_plan_SHA256=sha(R/'scripts/qualification409/acceptance410-plan.json'),verdicts=verdicts,scientific_facts=dict(equivalence399='28/28historical',numerical402='11/11historical',effects402='10/11historical',distance_AB='0.244795m versus10mFAIL',historical380_FAIL=3,short402_FAIL=4,fullD1='NO-GO',arbitrary_twoQ2_and_real_bodies='NOTQUALIFIED'),new_backup=dict(status='CLOUD_UNVERIFIED_PENDING409BACKUP',portableZIP_is_distinct_from_evidencearchive=True),decision='BUILD/SMOKE/CONTENTS GO; NO-GO TO EXECUTABLE410 UNTIL EXPLICIT CURRENT-YEAR VERIFIER SOURCE-BINDING PREPARATION. NOT RELEASE APPROVAL.')
(R/'docs/portable-build-409.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
text=f'''#409 — cloud408 закрыт; portable0.4.0 собрана, допуск410 заблокирован verifier

2026-11-11. **Сборка/smoke/целостность — GO. Полная410 не выполнена и пока
не допущена: штатный fresh-year verifier отвергает source040 по историческим SHA.**
Выпуск/main/tag/LATEST — NO-GO, принятая032не менялась.
[Машинный отчёт](portable-build-409.json), [инструменты](../scripts/qualification409/README.md),
[frozen inputs/план410](../scripts/qualification409/acceptance410-plan.json),
[все6001ZIPmembers с SHA/CRC](../scripts/qualification409/zip-members.json).

## Cloud closure408

Повторных upload408 не было. Свежие connectorreferences дали независимые HTTPS
скачивания всех3частей,600Bmanifest и582BGitrecoveryrecipe. У каждой части
свой immutable completion/resource receipt. Архив собран **только из этих новых
облачных байтов**, размер44203479B, SHA256f9e56e3ddc3d93b0d29916dd0a7c095e9ea8c8af975f1370a222af31f2bfbadd.
Все1110ZIPmembers CRC/SHA и2982logicalfiles/1109uniquepayloads проверены.
Globalbackupmanifest получил CLOUD_VERIFIED_CHUNKS_SHA256; parent/account/owner-only
проверены заново. Оригинальный408архив/отчёты и прежний CPUUNRESOLVED не менялись.

Первый16MiBreadback занял около202s — согласуется с недостаточностью прежнего100s
timeout при наблюдавшейся сети, но не доказывает одинаковые условия двух запусков.
Новый надзор учитывал child+supervisorCPU. Измеренный30CPU расход первойчасти
потребовал заранее sealedA2 только для остатка:200ms вместо50ms, прочая логика385
побитно прежняя.5synthetic faults(wall/CPU/RAM/disk/interrupt) сохраняют receipts.
Sampling не OSquota;150msдополнительной stoplatency явно учитывается.
Новые409A charged64.375CPU/{cloud['new409_active_wall_charged']:.6f}activewall с
консервативными allowances, внутри120/1800 иearly96/1440. Старый408budget не обнулялся.

## Точная сборка

Runtime exact237f736/tree5cf43fd9…; sourceenvironmentfp{p['source_fingerprint']}.
Новая отдельная branch `{p['packaging_branch']}`, commit `{a['packaging_commit']}`.
Изменён **только scripts/build_portable.py**, ни один runtime/Rust/test/IC/schema/threshold.
Qualified407Venv не переустанавливалась. Native wheel SHA{p['wheel_SHA256']};
.pyd SHA{p['native_SHA256']} reused, компиляция native запрещена wrapper.
Defaultbuilder остаётся прежним; opt-inreuse проверяет version/ABI/wheelSHA/pydSHA,
добавляет offline/noisolationPythonwheel, outputroot и SHA-boundархивныйexportroot.
BUILD-INFO содержит sourcecommit/tree/toolingSHA/nativeSHA/archivalexportrole.

Исходный обязательный JPLexport действительно отказал: исторический strictreport
ожидает другиеexperiment.py/application_profiles.py. FAIL сохранён. Для **экспорта
сохранённых траекторий** создана отдельная read-onlyfixture с точными старыми
байтами изnumeric-before373/laboratory-before381; archive/memberSHA прежние.
Exporter/его sourceguards и отчёты не менялись. Старыеsrc там только данные,
не liveimports; текущие040modules импортируются изqualifiedsource, advance
запрещён в preflight. Это historicalreplay, а не новый годовой scientificPASS040.

ИтоговыйZIP `{Path(a['archive']).name}`, {a['archive_size']}B,
SHA256 `{a['archive_SHA256']}`.6001members, всеCRC/SHA и paths/symlinks/privatefiles
проверены независимо. Исходный builderZIP сохранён отдельно; финальныйZIP
дополняет только generatedCURRENT-STATUS контекстом408/409/непройденной410.
Оригинальные source docs не переписывались, scientificFAIL не скрывались.

## Проверки и наблюдавшиеся отказы

Buildersmokes: реальный packagedPython/Tk/nativephysics иGUI start/close PASS.
Независимые -I probes подтвердили metadata040, actualpackagedorigins/Tcl,
точныйnativeSHA, доступностьtwo_q2_demoresource. Настоящий injection постороннего
пакета отказал поorigincheck. Не запускались fullcheck_portable/relocated/year/continuous.
Полнаяruntimeclosure{c['runtime_file_count']}files сверена сqualifiedCPython,
точными distributions и2wheelcontents; {len(c['license_files'])}licensefiles.
Нетpytest/maturin/setuptools/pip вsitepackages. Publicdocs402/404/license доступны.
ПубличныеverificationZIP иERFAsource-licensecopy являются явными approvedassets,
не случайнымиresearch/privateфайлами.

Negativecontrols: missing/wrongversion/wrongABI/wheelSHA/pydSHA/ambiguouswheels,
unexpectedcompiler/archivalmanifest-or-sourcecorruption/outsideimport; legacydefault
command сохранён без actualcompile. Три аудитных FAIL сохранены: неверныйdemoAPI
в первом smoke и два пропущенных approvedassets в allowlist. Исправлены только
аудитные скрипты, пакет и scientificcriteria не подгонялись; ZIP не пересобирался
ради smokePASS. Initial/finalZIP distinct, оба остаются локально.

## Реальный блокер410

Существующий `verification/recompute_jpl.py` при новом040runtime останавливается
на `Runtime scientific source changed: src/solar_simulator/experiment.py` **до
интегрирования**. Этот отрицательный preflight сохранён. Старыйstrictreport не
переименован и егоSHA не заменены. Перед410нужен отдельный reviewedcurrent-source
binding verifier/protocol, сохраняющий oldstrictmode, IC/settings/criteria и
проверяющий exact040source/native/environment. Нельзя просто убрать проверку,
заменить expectedSHA или подменить mandatoryfresh-year/continuous сохранённымиNPZ.

Plan410фиксирует этотZIP/source/tooling/native и все mandatoryпроверки, но status
BLOCKED_NOT_AUTHORIZED. Caps900CPU1200wall/2GiB2GiB,early720/960/1.8GiB1.8GiB;
прогноз годовых затрат UNRESOLVED: короткийsmoke не даёт такой экстраполяции.
Годовой иcontinuous расчёты здесь не выполнялись, допускне заявлен.

## Наука, ресурсы и дальнейший шаг

Historical39928/28;40211/11numeric,10/11effects,distance0.244795m vs10mFAIL;
3old380+4short402FAIL/fullD1NO-GO сохранены. TwoQ2Newton M-Qdegree-two экспериментален:
нетQ2-Q2/высшихмультиполей/приливов/диссипации/EIH-Q2/universalerrorbound.
Source408и409buildsmoke не сертифицируют реальные тела/произвольные системы.

На момент отчётаBcharged{resource['charged_CPU']:.6f}CPU/{resource['charged_active_wall']:.6f}wall;
CPU supervisor/неудачных попыток включён. Hard300/600/2GiB1GiB,
early240/480/1.8GiB900MiB неизменны, exact385monitor. Finalization дополняется
в том же budget, новыйbackup отдельно. Backup409 пока CLOUD_UNVERIFIED.

Дальше — завершениеbackup409 и отдельно разрешённая подготовка year-source
verifier410. Текущий результат не GO TO EXECUTABLE410 и не releaseapproval. STOP.
'''
(R/'docs/portable-build-409.md').write_text(text,encoding='utf8',newline='\n')
print('409report +frozen410inputs written; blocker explicit')
