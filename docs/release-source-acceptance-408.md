#408 — полная source/native/GUI приёмка кандидата0.4.0

2026-11-11. **TECHNICAL SOURCE/NATIVE/GUI GO — exact Solar-Simulator 0.4.0 candidate, verified environment only.**
Это не разрешение выпуска. Main/v0.3.2, теги, LATEST, старые portable и evidence399–407V не менялись.
[Машинный отчёт](release-source-acceptance-408.json), [исполнители](../scripts/qualification408/README.md),
[новый immutable plan](../scripts/qualification408/plan.json),
[полный source-bound manifest](../scripts/qualification408/evidence-manifest.json).

## Точный объект и метод

Dev перед работой: `ce79016a9430308faee8368d4d47ba7fb8883043`. Кандидат `237f73612c3c159acf92b32a15cf0289958fd921`,
ветка `codex/candidate-0.4.0-version-407v`, tree `5cf43fd9c5bb7d0d80a427d8a6d11ec8b81cb8e9`. Worktree чистый;
все Git blobs и raw SHA проверены до/после. Проверялся отдельный checkout, не dev.
Actual source/environment fingerprint `f84294862fac710dedd03bdf854b537e541aa5c955f90938832e9b72840d2083`.
Native040 SHA `a2b7e07573720a269efc712ee4fb74dcc747d24a4967d72d4c3d812158b3399b`; wheel SHA `5c2db314218484f5cb8b436de4479d5ecb069b56a5bd621eaa6e5cd5c70a5adb`,
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

На момент аудита charged1359.515625CPU/795.094862activewall,
измеренные worker745.156250/supervisor596.812500CPU.
Sampledworkerprivate peak1004916736B;
Wdisk1150728916B+64MiBreserve для новых файлов внеW.
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

Final closure: 1385.921875chargedCPU/844.457832activewall; включает finalization allowance20CPU/45wall (не измерение). Все supervisor/completion receipts закрыты, в том числе сохранённый report-only exit1 и исправленный report2exit0. [Полная closure](../scripts/qualification408/final-closure.json). Primary tests/runtime failures0.

## Резервирование: CLOUD_UNVERIFIED

Локальный reviewed deduplicated archive44203479B, SHA256
`f9e56e3ddc3d93b0d29916dd0a7c095e9ea8c8af975f1370a222af31f2bfbadd`:
2982logicalfiles/1109unique payloads/1110ZIPmembers. Локальные CRC/SHA проверены.
Восемь intentionally corrupt/unsafe test fixtures не загружены; точные пути/SHA/
причины в JSON и EXCLUDED-ORIGINALS.json внутри архива. Оригиналы сохранены.
Остальные10646exclusions включают Cargo/cache/Git-recoverable/staticstaging и
private-named/compiled-test fixtures; они не объявляются cloud-backed.

Три части16MiB/16MiB/10649047B,600Btransportmanifest и582BGitrecoveryrecipe
загружены в существующий приватный Solar-Simulator parent. Fresh metadata
подтвердила размер/parent/owner-only; **это не подтверждение содержимого**.
Первый independentverify-cloud download превысил100s; subprocess остановлен,
stale lock15428 снят только после проверки отсутствия PID. Новых prepare,
повторных загрузок или попыток сверх бюджета не было. Последующая CRC-проверка
облачных байтов не запускалась. Backup остановлен до900wallcaps; архивирование
24.796875CPU/25.144116wall measured, прочие CPU/tool costs не полностью измерены.
Операционный backupbudget120CPU/900wall/1GiB/512MiB отдельный; не увеличивался.

[Точные ID/SHA и инструкция продолжения](../scripts/qualification408/backup-pending.json)
позволяют продолжить только readback с отдельной оценкой бюджета. Сначала использовать
существующие IDs, а не загружать дубликаты. Source acceptance повторять не требуется.
Никакие secret/context/SQLite/env/cache не загружались;399–407Vархивы не тронуты;
404использовать только вместе с прежним append-only erratum.
Технический результат408 остаётся GO; облачное резервирование **не завершено**.
CIa26b77b run43079691834SUCCESS — только devsubsets, не замена full408.
