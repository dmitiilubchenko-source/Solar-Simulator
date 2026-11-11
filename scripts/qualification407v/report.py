"""Publish compact407V evidence and the NOT EXECUTED408 plan; no release."""
from pathlib import Path
import json,hashlib,shutil
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar407V-20261111');S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v')
a=json.loads((W/'independent-audit.json').read_bytes());p=json.loads((R/'scripts/qualification407/full408-plan.json').read_bytes());inv=W/'inventory408.json';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p.update(status='PREPARED_NOT_AUTHORIZED_NOT_EXECUTED',candidate_version='0.4.0',candidate_commit=a['candidate_commit'],candidate_tree=a['candidate_tree'],candidate_branch=a['branch'],source_fingerprint=a['source_fingerprint_SHA256'],native_SHA256=a['native_SHA256'],inventory='scripts/qualification407v/inventory408.json',inventory_SHA256=sha(inv),node_count=3083,old_nodes=3073,new_related_nodes=10,environment=dict(interpreter=str(W/'env/Scripts/python.exe'),prefix=str(W/'env'),source=str(S),Python='3.14.2t',numpy='2.5.1',scipy='1.18.1',matplotlib='3.11.0',ABI=a['ABI'],qualified_stage='407V limited version/ABI/short contracts; not full scientific qualification',native_wheel_SHA256=a['wheel_SHA256']),source_temp=dict(source=str(S),TEMP=str(W/'full408-TEMP-MUST-BE-FRESH'),output='NEW ordinary output root, never overwrite407V or399-407; no private ancestor'),preflight=['Verify exact Git HEAD/tree and clean source','Recompute actual fingerprint/native SHA and real -I imports/prefix; no old033binary','Reverify Cargo locked/offline versions; no rebuild/install during acceptance','Recollect full inventory; require all3073 prior+10new nodes with no skip/xfail/deselection','Check exact external376 bundle before collection; old files are data only','Document-only composition including exact license destination; no portable build','Verify all budget and ledger reservations before launch'],scientific_application_release='D1 distanceFAIL;3historic380+4short402FAIL; fullD1/release0.4.0 NO-GO unchanged')
p['required_external_inputs'][0]['source']=str(Path('C:/Users/Admin/Documents/Codex/Solar407-20261110/historical376-inputs.zip'))
p['required_external_inputs'] += [dict(name='immutable033metadata',source='tests/fixtures/metadata033-828c798.zip',size=(S/'tests/fixtures/metadata033-828c798.zip').stat().st_size,SHA256=sha(S/'tests/fixtures/metadata033-828c798.zip'),purpose='Historical383/407 only; do not overlay into live040'),dict(name='native040wheel',source=str(next((W/'wheels').glob('*.whl'))),SHA256=a['wheel_SHA256'],purpose='Exact already built qualified artifact; no oldnative033substitution')]
p['forecast']=dict(CPU_seconds=1580,active_wall_seconds=1150,data_bytes=1572864000,uncertainty='Planning estimate only. Previous406+407forecast1555CPU plus25CPU newtargeted nodes/version preflight; prior monitor overhead included. Full3083 NOT RUN. No new scientific acquisition. Stop if this cannot protect reserves.')
p['phase_reserves']['full_driver_CPU']=1430
p['required_independent_audits']=['Every node outcome incl all FAIL/ERROR/SKIP; compare literal inventory','Current source and native origin/SHA/fingerprint + protected historical snapshots','Actual GUI own/foreign callbacks, settings, data immutability','Model-specific scientific applicability remains separate; do not convert D1 FAIL toPASS','Retained385monitor SHA/cadence/resource ledger and partial receipts','Filtered Project-Archives independent download SHA/size/owner/parent/member integrity']
(R/'scripts/qualification407v/full408-plan.json').write_text(json.dumps(p,indent=2,ensure_ascii=False)+'\n',encoding='utf8',newline='\n');shutil.copyfile(inv,R/'scripts/qualification407v/inventory408.json')
rows=[json.loads(x.read_bytes()) for x in W.glob('*-resources.json')];cpu=sum(x['charged_CPU_seconds'] for x in rows);wall=sum(x['charged_active_wall_seconds'] for x in rows)
resources=dict(charged_CPU_seconds=cpu,charged_active_wall_seconds=wall,peak_private_worker_tree_sampled=max(x.get('record',{}).get('peak_private_tree_sampled',0) for x in rows),W_disk_bytes=sum(x.stat().st_size for x in W.rglob('*') if x.is_file()),external_source_reserve=128*1024**2,hard=json.loads((W/'plan.json').read_bytes())['hard'],early=json.loads((W/'plan.json').read_bytes())['early'],limitations='Retained50ms385 monitor; memory/discovery sampled, not OS quotas. Combined supervisor+worker private checked by hook; peak field is worker only. Initial12CPU/25wall and wrapper1CPU/1wall tail conservative allowances. Finalization still charged separately; backup separate.')
report=dict(stage='407V',date='2026-11-11',base_dev='01aca787bb55f5fe24738bdc7c9ebb7a843c05c2',base_candidate='828c79805f7db4576b474206923285ce0b4541c4',**{k:a[k] for k in ['candidate_commit','candidate_tree','branch','source_fingerprint_SHA256','native_SHA256','wheel_SHA256','ABI','changed_paths','binding','tests','negative_controls','document_files','document_links']},versions=dict(python='0.4.0',core='0.4.0',native='0.4.0'),inventory=dict(node_count=3083,old3073_preserved=True,old3045_plus28_preserved=True,new=10,SHA256=sha(inv)),historical033_fixture=dict(size=3922,SHA256=sha(S/'tests/fixtures/metadata033-828c798.zip'),source_commit='828c79805f7db4576b474206923285ce0b4541c4'),numerical_identity_files=len(a['numerical_files']),compatibility=json.loads((W/'compatibility.json').read_bytes()),resources=resources,scientific_constraints=['A+D1 exact synthetic demo only','Historical402 numerical11/11;effects10/11;distance_AB0.244795m versus10m FAIL','FullD1 application NO-GO','3historic380+4short402 strictconvergenceFAIL retained','No universal error bound or arbitrarytwoQ2 qualification'],failures=['native-build1 missing maturin executable in newprefix, exact existing tool copied; no Rust/source change','setup wrapper output-name collision; exact monitor receipt retained and charged conservatively','compatibility1 wrong diagnostic import; binary controls completed and reused without rerun','audit1 actual new040doc missing399closure: failing regression saved; link now exact public Git399report','doc-failing1 wrong cwd collected wrong scriptsnamespace; corrected cwd reproduces real docFAIL','audit2 omitted known ERFA license destination in document-only harness; exact license copied as normal build would; no production code change'],verdicts=dict(VERSION_CONSISTENCY='PASS',NATIVE_0_4_0='PASS_LIMITED_ABI_BUILD_API',BACKWARD_COMPATIBILITY='PASS_TESTED_SCOPE',NUMERICAL_SOURCE_IDENTITY='PASS',HISTORICAL_PROVENANCE='PASS_TESTED_BOUNDARIES',DOCUMENTATION_COMPOSITION='PASS_STATIC_ONLY',READINESS_FOR_FULL_408='GO_EXACT_CANDIDATE_NOT_EXECUTION_AUTHORIZATION',APPLICATION_D1='NO-GO',RELEASE_READINESS='NO-GO'),cloud=dict(status='CLOUD_UNVERIFIED_PENDING_BACKUP'),unresolved=['Full3083source/native/GUI acceptance408 not executed','Portable build/relocation/acceptance not executed','Old scientific receipts not reissued for newnative SHA','Existing native has no own version symbol; wheel/Cargo/import/hash binding, no new source API'],decision='GO TO FULL SOURCE ACCEPTANCE408 — exact0.4.0 candidate, not release approval.')
(R/'docs/version-migration-407v.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8',newline='\n')
text=f'''#407V — кандидат0.4.0; технический GO к отдельному408

2026-11-11. **UNRELEASED. Выпуск не разрешён.** Принятый main/v0.3.2 остаётся cf653c9.
Полный408, scientific58/22/year и portable build не запускались.

## Точный объект

Отдельная `{a['branch']}` строго основана на828c798, два собственных commit.
Final commit `{a['candidate_commit']}`, tree `{a['candidate_tree']}`.
Actual fingerprint (полный профиль Python/dependencies/native/package, UTF8 indent2+LF):
`{a['source_fingerprint_SHA256']}`. Реальные импорты: отдельный checkout040 и
Documents/Codex/Solar407V-20261111/env; Python3.14.2t, NumPy2.5.1/SciPy1.18.1,
Matplotlib3.11.0; qualified384/407 среды и старые wheels не менялись.

Новый native: cp314-cp314t-win_amd64, SHA256 `{a['native_SHA256']}`;
wheel SHA256 `{a['wheel_SHA256']}`. Rust1.99.0 GNU/PyO3.29.3, maturin1.15.0,
release/locked/offline, отдельный target/output. Native не имеет runtime version
symbol: проверены настоящие Cargo/wheel metadata, loader/API и exact binary.

## Изменения и исторические границы

Шесть metadata файлов меняют только локальные версии на0.4.0; TOML semantic diff
и `cargo metadata --locked --offline` подтвердили неизменность dependency graph.
[build_native](../scripts/build_native.py) в dev исторический; расширенный
[сборщик кандидата](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/{a['candidate_commit']}/scripts/build_native.py)
получил необязательные out/target-dir/locked/offline, старые defaults сохранены.

Все {len(a['numerical_files'])} защищённых src/rust файлов совпали по Git blobs и raw bytes;
единственный runtime delta — release-status фраза inspection.py. AST вне этой
строки, все формулы/настройки/IC/G/Q2/R-reuse/storage/recovery/lifecycle прежние.
Scientific claims предупреждения дословно сохранены. Exact033fixture3922B,
SHA `{report['historical033_fixture']['SHA256']}` взята из828; старые nodeids и
expected032/033 сохранены. Historical383overlay не применяется к live040.
Старые reports/archives/SHA/native651e3466 не изменены.

## Проверки и пределы вывода

- 106 targeted Python/native PASS; 13 compatibility/GUI/history PASS;
  10 version/doc PASS (часть повторяет9из106, это не129уникальных тестов).
- Rust fmt обоих crates PASS; core19PASS,0ignored. Нативный dispatch проверен
  реальными функциями и независимой Newton/EIH аналитикой действующих тестов.
- Сравнение старого и нового native на fixed Newton/EIH force, diagnostics,
  100Verletsteps и коротком existingtwoQ2 контроле побитно совпало в JSON.
  Это малый contract, не новая научная квалификация или universalaccuracy.
- 47 старых inputs/checkpoints/branch файлов проверены по tracked389SHA,
  load/roundtrip либо ожидаемый отказ. Parent/branch только поддерживаемые
  pointmass; dynamicQ2branch остаётся запрещённым. Recovery/CLI/settings и
  короткий двухфигурный GUI проверены существующими тестами.
- Collection:3083nodes, все3073(3045+28) прежних,10новых; removed0.
  Никаких skip/xfail исключений ради версии. Full suite **не запускался**.
- Независимый аудит Git/AST/raw/wheel/member/native/import/JUnit/376closure и
  13negative controls. Missing/corrupt376, metadata substitution обоих направлений,
  force/binary corruption, wrong source/package/native binding отклонены.
- Document-only338files/576relative links PASS; один точный ERFA license asset
  размещён в будущем runtime destination, без исполняемой программы. Новый
  [release candidate page](releases/v0.4.0.md) ссылается на399exactGit, не тащит
  исследовательские инструменты в portable. Старый033page исторический.

Все шесть служебных отказов сохранены в машинном отчёте и raw receipts, включая
настоящий broken399link FAIL до исправления. Второй auditFAIL был ошибкой
статического harness: обычный build размещает ERFAlicense до docs; harness
вначале этого не сделал. После копирования точного license closure проверена.
Не скрывались FAIL и не менялись численные критерии.

## Ресурсы и следующий408

На момент аудита: {cpu:.6f} chargedCPU/{wall:.6f} activewall,
worker sampled private peak {resources['peak_private_worker_tree_sampled']}B,
Wdisk {resources['W_disk_bytes']}B +128MiB external source reserve.
CPU включает supervisor и неудачные попытки; исходный allowance12CPU/25wall
консервативный, не измеренный. Finalization и backup будут добавлены отдельно.
Hard600CPU/1200wall/3GiB/1.5GiB; early480/960/2.7GiB/1.35GiB не увеличивались.
Память и processdiscovery sampled, это не OSquota. Rejected407monitor не использован.

[Новый408plan](../scripts/qualification407v/full408-plan.json) закрепляет exact
candidate/native/prefix/3083inventory/externalinputs/385monitor/reserves/audits.
Proposed hard2400CPU/2700wall/3GiB/2GiB, early1920/2160/2.7GiB/1.8GiB;
forecast1580CPU/1150wall — прогноз, не выполненный полный прогон. Нужен отдельный
запуск после разрешения; full408 не следует автоматически из этого GO.

VERSION_CONSISTENCY/PASS; NATIVE_0_4_0/PASS_LIMITED;
BACKWARD_COMPATIBILITY/PASS_TESTED_SCOPE; NUMERICAL_SOURCE_IDENTITY/PASS;
HISTORICAL_PROVENANCE/PASS_TESTED; DOCUMENTATION_COMPOSITION/PASS_STATIC.
APPLICATION_D1 и RELEASE_READINESS **NO-GO**: historical40211/11 и10/11,
distance_AB0.244795m вместо10mFAIL;3historical380+4short402FAIL сохранены.
Нет допуска arbitrarytwoQ2, гарантии глобальной ошибки или новой точности реальных тел.

Cloud: **CLOUD_UNVERIFIED**, резервирование ещё не завершено; отдельный итог ниже.

**GO TO FULL SOURCE ACCEPTANCE408 — exact0.4.0 candidate, not release approval.**
После отчёта STOP. Main/tag/LATEST/portable032 не затронуты.
'''
(R/'docs/version-migration-407v.md').write_text(text,encoding='utf8',newline='\n')
for n in ('v0.4.0.md','v0.3.3.md'):shutil.copyfile(S/'docs/releases'/n,R/'docs/releases'/n)
print('compact report and proposed408plan prepared')
