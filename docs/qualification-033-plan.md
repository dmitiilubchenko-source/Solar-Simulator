# Подготовка квалификации0.3.3: план382

29октября2026. **План, не выполненная квалификация и не разрешение запуска.**
База после отката4dc6320038fe300032d9390cbcb9d9e31f7ddefc; проверочный код после
CI-исправленияbc75156cb01ea2818a6df78fc55582d27f676dc3.
Metadata/native пока0.3.2. [Аудит сохранности](integrity-ci-382.md).

## Переиспользование и необходимые приготовления

Использовать qualify_current_runtime375.py/assess_current_runtime375.py,
current-runtime-375-protocol.json, check_runtime_reliability376.py,
validate_two_q2_380.py, check_project.py --require-native, build_portable.py,
check_portable.py и существующие GUI/storage/recovery/recipe tests.
Не создавать второй solver/framework. Все старые protocol/receipt/NPZ/SHA
остаются immutable; current375 gate новому checkout **отказывает**.

До тяжёлых jobs требуется минимальная параметризация protocol/output paths
в существующих375/376/380 drivers: сейчас имена, часть SHA и выходов закреплены.
Новый явный target сохраняет defaults и exclusive writes. Не править старые
protocol constants ради запуска; проверить параметризацию короткими fault-tests.

## Порядок и GO-критерии

1. **Candidate/environment freeze.** После отдельного согласования подготовить
   отдельный checkout/venv и согласованные Python/Cargo/native версии кандидата.
   Новую native-сборку получить **до** научной квалификации, сохранив нынешнюю.
   Зафиксировать commit, все source/data/dependency/native hashes, ABI/compiler/
   flags, actual IC, SI/frame/epoch/TDB, rtol/atol/error_control/relative_pair,
   эпохи и границы пакетов. Смена bound входа инвалидирует соответствующие jobs.
2. **Newton.** Actual-IC аналитика376, moderate/e=.95 и диагностические e=.99
   peri/apo, прежние49эпох, Python/Rust и same-packet save/resume. Короткие
   N-body reactions/gradients/invariants и независимый3body контроль — через
   действующие tests. До запуска заморозить subset и критерии; у376 нет
   универсального high-e bound. Newton/JPL residual включает отсутствующую
   физику и не является численной ошибкой. d32 остаётся NO-GO.
3. **EIH1PN + fixed Sun/Earth J2.** Те же10тел375, DE441, SSB/Ecliptic J2000,
   JD2461321.5TDB, SI,1год/125эпох/9holdout, Strict/per-body/relative Earth–Moon,
   dt3600s, rtol3e-14, atol x=.001m/v=1e-9m/s, пакеты20/10. Использовать
   прежний независимый EIH/J2 oracle и два reference уровня с новым provenance.
   Criteria из protocol375: per-body/reference <10m/<1e-4m/s, Earth–Moon
   <.1m/<1e-5m/s, reference sensitivity <1m/.1m, model invariants <1e-10.
   Согласованный JPL residual отдельно <10km/тело и <1km Earth–Moon.
   Standard FAIL сохранять. Проверенный JPL cache достаточен; старые arrays —
   regression controls, не новое исполнение. Реально выполнить новые jobs.
4. **Две Q2.** Только total-degree2 Newton M–Q, без Q2–Q2/высших multipoles/
   tides/dissipation/EIH, d>Ra+Rb. Synthetic3802/3body IC,65эпох0..4000s,
   три frozen tolerance levels, Python/Rust, оба q/S/error blocks. Повторить
   independent scalar-I gradients, reactions, E/P/L, covariance, zero-Q,
   norm(q), matrix/body-Pi RK45 с двумя уровнями.
   Прежние criteria380: gradient2e-6/reaction1e-13/angular balance2e-12;
   E/L drift1e-8/Pscale1e-12/qnorm1e-8; fine/reference1e-7/sensitivity1e-8.
   Пакетную и непрерывную сходимость считать отдельно. **Три прежних FAIL
   монотонности не менять**; аналогичный новый FAIL не становится PASS по
   слову «roundoff». До запуска отдельно согласовать допустимый runtime scope
   при таком FAIL. План не ослабляет исходное правило и не подбирает IC/пороги.
5. **Сохранения/source acceptance.** Прежние0/1/2figure, schemas/checkpoints,
   recipe/frame integrity и полный check_project.py --require-native.
   Same-packet save/resume точен в одной frozen среде.8cases/24snapshots
   byte-exact только в их закреплённой среде: при candidate version/native
   fingerprint заранее перечислить metadata-only differences, не игнорировать
   численные состояния и не переписывать baseline. Между средами использовать
   отдельно обоснованные criteria375, не совпадение чужих executable SHA.
6. **GUI/recovery.** Start/pause/stop, write failure/recovery/load/continue/reset,
   отмена без изменения q/S/settings, read-only SI и model-specific report,
   isolated LOCALAPPDATA; demo ограничить200s/4пакетами, не годом.
7. **Реальный portable.** Candidate version/wheel/manifest/SHA/CRC, новый путь
   с пробелами, -I/isolated environment, package resource two-q2-demo380.json,
   настоящий native, отсутствие чужого PYTHONPATH/cache, GUI/recovery probes.
   **Текущий check_portable.py запускает fresh-year и continuous-year**, а не
   только replay: включить их в утверждённый бюджет, не запускать случайно.
   LATEST/main/tag/release — только отдельное решение после приёмки.

## Ресурсы: предварительные оценки, не измерения кандидата

Ориентиры375: current jobs21..69wall s каждый; independent annual reference
125.084s +holdout10.367s. Jobs перекрывались, wall нельзя объявлять CPU.
Полная приёмка375:1065.01s/2902tests. Science380:34.609CPU/30.525wall;
GUI381 финальный2.344CPU s. Новый ABI/compiler/disk могут изменить стоимость.

| Будущая фаза | CPU cap,s | Wall cap,s | Private tree cap | Новые артефакты |
|---|---:|---:|---:|---:|
|Preflight/resource probes|180|360|1GiB|256MiB|
|Newton short qualification|180|360|1GiB|64MiB|
|EIH+J2/reference|1200|1800|2GiB|512MiB|
|Synthetic two-Q2|120|300|1GiB|64MiB|
|Full source/native, включая GUI|2400|2700|3GiB|2GiB|
|Build/isolated portable, включая year probes|1200|1800|2GiB|3GiB|

Общий предварительный потолок5400CPU s/7800wall s,3GiB private tree,
8GiB свободного диска; ожидаемый порядок30..90минwall, не обещание.
Короткий scaling probe и доступные ресурсы проверить до утверждения каждого
тяжёлого job. Если недостаточно — NO-GO/новый план, не поднятие лимита задним
числом. Использовать существующий monitor CPU/wall/private/disk, margins,
partial/final metrics/50ms polling; sampled peaks не считать OS hard quota.

## Свидетельства, блокеры и решение

Новые plan/receipt/NPZ/логи — отдельные имена/exclusive writes, actual backend/
native calls, source/env/reference provenance, эпохи, boundaries, все FAIL и
остановки, SHA до/после. Активный gate для нового receipt согласовать после
реального исполнения; изменение старого CURRENT_RECEIPT_SHA не квалификация.
Project-Archives/Solar-Simulator: независимый readback SHA, иначе CLOUD_UNVERIFIED.

Блокеры тяжёлого старта: candidate commit/version/native не заморожены;
drivers имеют fixed outputs; CPU/RAM новой среды не измерены; packet-monotonicity
scope не согласован. Эти вопросы решить до дорогих вычислений.
**GO** продолжать разработку и короткий preflight. **NO-GO сейчас** годовая/
full release квалификация без отдельного запуска, универсальная scientific
accuracy, main/tag/release. Тяжёлая часть в подготовке382 не выполнялась.

