#407V — кандидат0.4.0; технический GO к отдельному408

2026-11-11. **UNRELEASED. Выпуск не разрешён.** Принятый main/v0.3.2 остаётся cf653c9.
Полный408, scientific58/22/year и portable build не запускались.

## Точный объект

Отдельная `codex/candidate-0.4.0-version-407v` строго основана на828c798, два собственных commit.
Final commit `237f73612c3c159acf92b32a15cf0289958fd921`, tree `5cf43fd9c5bb7d0d80a427d8a6d11ec8b81cb8e9`.
Actual fingerprint (полный профиль Python/dependencies/native/package, UTF8 indent2+LF):
`f84294862fac710dedd03bdf854b537e541aa5c955f90938832e9b72840d2083`. Реальные импорты: отдельный checkout040 и
Documents/Codex/Solar407V-20261111/env; Python3.14.2t, NumPy2.5.1/SciPy1.18.1,
Matplotlib3.11.0; qualified384/407 среды и старые wheels не менялись.

Новый native: cp314-cp314t-win_amd64, SHA256 `a2b7e07573720a269efc712ee4fb74dcc747d24a4967d72d4c3d812158b3399b`;
wheel SHA256 `5c2db314218484f5cb8b436de4479d5ecb069b56a5bd621eaa6e5cd5c70a5adb`. Rust1.99.0 GNU/PyO3.29.3, maturin1.15.0,
release/locked/offline, отдельный target/output. Native не имеет runtime version
symbol: проверены настоящие Cargo/wheel metadata, loader/API и exact binary.

## Изменения и исторические границы

Шесть metadata файлов меняют только локальные версии на0.4.0; TOML semantic diff
и `cargo metadata --locked --offline` подтвердили неизменность dependency graph.
[build_native](../scripts/build_native.py) в dev исторический; расширенный
[сборщик кандидата](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/237f73612c3c159acf92b32a15cf0289958fd921/scripts/build_native.py)
получил необязательные out/target-dir/locked/offline, старые defaults сохранены.

Все 103 защищённых src/rust файлов совпали по Git blobs и raw bytes;
единственный runtime delta — release-status фраза inspection.py. AST вне этой
строки, все формулы/настройки/IC/G/Q2/R-reuse/storage/recovery/lifecycle прежние.
Scientific claims предупреждения дословно сохранены. Exact033fixture3922B,
SHA `a1fe4cbdf213a6d97652a7d8e2108f584a1c0066ab8fcc5adb96bbc951b5c970` взята из828; старые nodeids и
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

На момент аудита: 283.484375 chargedCPU/175.104515 activewall,
worker sampled private peak 844398592B,
Wdisk 513267516B +128MiB external source reserve.
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

Итог основного407V: charged 315.281250CPU/239.999718activewall, включая finalization allowance25CPU/60wall (консервативный bound, не измерение). Из них worker 140.968750CPU, supervisor 123.656250CPU измерены. Wdisk513279399B+128MiBsource reserve; внутри прежних caps.
