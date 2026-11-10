# Блокеры source acceptance407: GO к отдельной полной408

10 ноября2026, Europe/Moscow. **Все73исходных отказа406 получили PASS после
исправления причин и targeted повторов.** Это поэтапный результат, не новый
полный прогон и не разрешение выпуска. Полные3073теста в407 не запускались.
Application D1/release0.3.3 остаются NO-GO.

[Машинный отчёт](q2-release-blockers-407.json) содержит каждый исходный nodeid,
старый статус, SHA исходного traceback, новый результат и SHA его JUnit receipt.
[Инструменты](../scripts/qualification407/README.md) и
[предварительный план408](../scripts/qualification407/full408-plan.json) отделены
от замороженного кандидата.408 здесь не исполняется.

## Проверенный кандидат

Dev перед работой: `41164b76b0b3f4c4b9c46d0cddec2b0e807a5297`.
Новая отдельная ветка `codex/candidate-0.3.3-blockers-407` строго от
`8fe01304e502f55e879addb0a4b6f3e062832e37`, без слияния всего dev.

| Привязка | Значение |
|---|---|
| Frozen commit407 | `828c79805f7db4576b474206923285ce0b4541c4` |
| Tree | `b858d380b86ac702e85e20ff4acfe0b1efef66ab` |
| Actual source fingerprint | `29bb46f8e37f0e92e635bfc292739ca53d0c742d218726c44bb97d6d87fe051c` |
| Прежний native0.3.3 SHA256 | `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091` |

Фактические `-I` imports/prefix проверены: source нового checkout, отдельная
test venv с побитными копиями qualified384dependencies. Python3.14.2t,
NumPy2.5.1/SciPy1.18.1/Matplotlib3.11.0/TclTk8.6.15, native ABI/реальный dispatch.
Pip/install/PyO3 rebuild отсутствуют. Optional REBOUND — только прежняя
SHA-bound тестовая зависимость, не runtime integrator. Численные modules,
Rust, native, IC, G, допуски и R-reuse относительно405 побитно неизменны.
В package fingerprint отличается только `control_row.py`.

## Причины406 и фактическое закрытие

| Исходная группа | Старые FAIL / ERROR | Результат407 |
|---|---:|---|
| responsive_layout | 1 / 0 | PASS:167→191px, порог >170 прежний |
| legacy_poll_count_assertion | 1 / 0 | PASS: один собственный poll, replacement/scheduled/error/close/foreign controls |
| historical_control_row_binding | 51 / 0 | 49PASS в полном targeted73; ещё2после замыкания376fixture |
| historical375_cargo_fixture | 0 / 10 | Все10PASS, setup завершён; assertions действительно выполнены |
| historical032_cargo_metadata | 4 / 0 | Все4PASS в явном accepted032checkout; current033 отдельно |
| private_ancestor_setup | 6 / 0 | Все6PASS; нормальные source/TEMP roots, privacy filter не ослаблен |
| **Всего** | **63 / 10** | **73PASS по полному mapping,0оставшихся исходных отказов** |

Первый завершённый targeted73-прогон дал70PASS/3FAIL. Он сохранён неизменным.
Три поздних барьера устранены отдельно: два376source/dependency failures и
отсутствующий `docs/releases/v0.3.3.md` в document preparation. Финальные
66соседних тестов прошли на032c36e; после последней tests-only правки владения
poll ещё2теста прошли на828c798. Длинные исторические51повторно не исполнялись:
их replay/numerical implementation и inputs не менялись, diff проверен.
Такая комбинация receipts не называется полным source acceptance нового commit.

### Layout и poll

Исходные два GUI FAIL воспроизведены на405. Сохранён настоящий client-window
скриншот900×720 **с раскрытыми настройками в момент167px**, а также координаты
каждого widget, requested/actual sizes, scaling1.3333 и bounding boxes подписей.
В отличие от снимков406, это действительно состояние отказа.

В [ControlRow._layout](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/828c79805f7db4576b474206923285ce0b4541c4/src/solar_simulator/control_row.py#L32)
изменены ровно три вертикальные константы: внутренний padding3→2px и gap6→4px.
Ширины controls, minimum window, состояние настроек и footer не скрывались.
Lifecycle/cancellation методы и остальной runtime не менялись; AST и точный
трёхзаменный byte diff проверены независимо.

| Окно | Canvas: настройки закрыты / открыты, px |
|---|---:|
|1180×820|511 /407|
|1024×768|347 /243|
|900×720|295 /191|

Старый layout test прошёл без изменения170px. Проверены clipping controls,
footer/details, отсутствие пересечения проверяемых подписей и обрезанного
нижнего xlabel, resize и неизменность полного документа опыта.

[Worker-error сценарий и oracle](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/828c79805f7db4576b474206923285ce0b4541c4/tests/test_app_workflows.py#L76)
сохраняют startup rejection, pending Future, два прежних сообщения об ошибках
и последующее продолжение. Oracle проверяет Tcl-command owner и единственный
poll, замену ID и удаление старого. Scheduled callback реально выполняется;
после close owned callbacks отсутствуют, foreign host timer остаётся.
Negative controls ловят duplicate, missing poll и необработанный worker error.
Самопроверка дополнительно воспроизвела ошибку oracle с **чужим одноимённым
`_poll`**; после фильтра по владельцу этот контроль проходит. Production poll
не менялся. Это новый сохранённый failing test, не ослабление контракта.

### Historical closure и граница runtime

[read_sources](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/828c79805f7db4576b474206923285ce0b4541c4/scripts/historical_sources407.py#L13)
аутентифицирует весь8-member snapshot и pinned manifest до выдачи байтов.
Старый ControlRow получен непосредственно изe9 при SHA0dbf30d3…;
current405/407 никогда не выдаётся за него. Остальные7файлов375 получены из
точных сохранённых accepted032raw bytes с исходными SHA, дополнительно сверены
с Git object identity. При восстановлении LF/CRLF не преобразуются.

Historical032Cargo tests используют явно обозначенную032fixture; validator
`historical_sha` не ослаблен, candidate metadata остаётся0.3.3. Проверены подмены
metadata в обе стороны. Negative tests отклоняют current405/407 внутри old
snapshot, byte/commit/member/manifest повреждения, missing artifacts, попытку
записать old metadata в live source. Strict current-source guards отказывают
при изменении force source, tolerance code, IC и compiled-native artifact.
Old-source audit по-прежнему не разрешает исполнение текущего solver.

Поздняя376fixture потребовала двух дополнительных точных Git-source files
из08d60d9 и трёх исходных dependency artifacts. Все ожидаемые SHA уже находились
в неизменном протоколе376. [Изолированная fixture](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/828c79805f7db4576b474206923285ce0b4541c4/tests/historical376_fixture407.py#L13)
копирует только аутентифицированную source closure; старые binary/SciPy bytes
используются как данные, **не импортируются и не исполняются**. Реальный runtime
по-прежнему использует qualified native0.3.3. Current-mode validator остаётся
привязан к live source и отрицательный контроль проходит.

Forensic bundle `historical376-inputs.zip`:706900B, SHA256
`2326775712ab071ec6354b01f529ba2749c22bbee773e5f26948c11408cc38d5`.
Он не входит в обычный Git и обязателен для будущих historical376tests:
`SOLAR_HISTORICAL376_BUNDLE` задаётся явно. Missing/corrupt bundle даёт FAIL,
не skip или подстановку нынешнего native. Это3артефакта, не backup окружения.

### Документы и пути

Source и TEMP находятся в обычных изолированных каталогах без `.tools` ancestor;
реальные imports, TEMP/TMP и pytest paths зафиксированы. JUnit использует POSIX
paths. Производственный privacy filter не изменён. Старые privacy-negative tests
и проверки unsafe/unlisted archives сохраняются и проходят.

В кандидат включены точные утверждённые402/404Markdown+JSON и их необходимая
публичная link/read-only dependency closure:17файлов около0.87MB, не весь dev.
Manifest происхождения находится в candidate `docs/q2-document-composition-407.json`.
Исторический unresolved GUI текст402 сохранён и читается вместе с404.
Все plain paths из runtime warning существуют, scientific FAIL не сокращались.

Document-only preparation проходит. Для будущего экспорта developer links из
этих двух отчётов становятся ссылками на точный публичный41164b7; исполняемые
research tools не попадают в пакет. Текст и ограничения отчётов сохраняются.
Страница0.3.3 явно называется **кандидатом, не выпущенной версией**.
Portable build и relocated acceptance здесь не выполнялись.

## Коммиты и независимая проверка

| Commit | Назначение / затронутые проверки |
|---|---|
|c9bc3e7|Три geometry constants; прежний layout test и шесть actual layouts|
|7d892ec|Poll ownership/error/recovery contract и hostile controls|
|243a337|Exact e9/032 snapshot, historical mapping и375fixture|
|bae34d1|Явные032metadata fixtures и source/metadata corruption tests|
|069148b|Замкнутая376fixture с внешними pinned forensic inputs|
|0da97d1|Публичные документы/статический export; восстановление incidental test EOL|
|032c36e|Карта/inventory/scope и strict current-source negative controls|
|828c798|Tests-only исправление owner oracle для foreign callback с тем же именем|

Полные diff SHA/paths и список tests по каждой группе доступны в JSON/сохранённых
Git commits; exact patch outputs также сохранены в raw407. Силы и integrators
не затрагивались. Старые399–406report/source/receipt SHA сверены и неизменны.

В [новом inventory](../scripts/qualification407/inventory407.json)3073nodes:
3045→3045identity mapping, удалённых0, новых28. Новые:14history controls,
1poll,2docs,2forensic-input controls,5перенесённых402observer и4scope404tests.
Collection прошла; code/config SHA закреплены. Не запускались2972старыхPASS
заново без причины: выполнены связанные соседи, включая66последнихPASS.

## Надзор и ресурсный учёт

Prototype disk scanner дал на статических данных1.0→0.09375CPU за4сканирования
одного environment и совпадение byte counts. Synthetic guards прошли, но первый
реальный targeted запуск встретил Windows transient-directory PermissionError;
повтор ошибки в finally потерял resource receipt. **Prototype NO-GO.** Он отключён
в stage guard; сохранены код, лог и failed attempt. Старые406receipts не менялись.

Продолжение использовало прежний точный monitor385. Отдельно прошли его CPU,
wall,RAM,disk,interrupt/termination/owned-child-cleanup controls; checkpoint
сохраняется. Выполнены actual-preflight AST controls для missing/partial receipts,
учёта failed work, prior CPU/wall и отсутствия reset при resume.

У406средний цикл852samples/568.46wall — около0.667s, хотя sleep50ms.
Disk scanning измеренно дорог;100tree discoveries заняли0.546875CPU,
100memory/CPU queries ниже разрешения process clock. В407полный targeted73:
worker143.578125CPU, supervisor131.5CPU; 66neighbors:47.75/43.140625CPU.
Безопасное ускорение реального надзора пока не квалифицировано.

Общий charged ledger: **647.265625CPU /329.0637618active wall**.
Из CPU:560.265625process telemetry,5tail allowances,2initial allowance,
**80conservative upper bound потерянной попытки**, не измеренное потребление.
Основание последнего: внешний tool наблюдал3.184021wall,16logical CPU;
использована верхняя граница16×5wall. Бюджет не обнулён и не повышен.

Recorded worker-private peak447508480B; memory peak потерянной попытки неизвестен.
Combined supervisor+worker threshold проверялся, отдельный combined peak не
сохранён. Disk tree контролируется вместе с512MiB внешнего source reserve;
точный recorded peak приведён в JSON. Hard900CPU/1200wall/3GiB/2GiB и
early720/960/2.7GiB/1.8GiB сохранены. Sparse samples — не OS quota.
Monitor costs включены и выделены по фазам; backup отдельно. Git/editor/cloud/
remote CI CPU не измерялись. Ephemeral pytest fixtures могут ротироваться самим
pytest; immutable logs/XML/snapshots и forensic inputs сохранены отдельно.

## Решение и408

Targeted layout/poll/history/metadata/path/composition/regression и numerical
source identity — PASS. **FULL_SOURCE_ACCEPTANCE: NOT_RUN.**
Fixed58source equivalence28/28, D1numerical11/11, effects10/11 с distanceFAIL,
3historic380+4short402convergenceFAIL и fullD1/releaseNO-GO остаются историческими
фактами, не переаттестованы техническими тестами.

Допустимо: **GO TO FRESH FULL SOURCE ACCEPTANCE408 — candidate407 frozen;
not full acceptance and not release approval.** Proposed408:hard2400CPU/2700wall/
3GiB/2GiB,early1920/2160/2.7GiB/1.8GiB,forecast около1555CPU/1100wall с прежним
монитором и явным резервом. Расчёт включает измеренные276.19CPU восстановленных
historical checks. Нужен новый source-bound execution plan/preflight и отдельное
разрешение; незавершённые/непомещающиеся группы должны останавливаться с partial.

## Сохранение

Кандидат407 опубликован в отдельной ветке; dev получает только tooling/report.
Main/tags/LATEST/portable0.3.2 и прежние кандидаты не менялись; release не создаётся.
Новый407backup пока **CLOUD_UNVERIFIED**: упаковка/загрузка/readback pending.
Архивы399–406 не перезаписываются и не выгружаются заново. Для404по-прежнему
обязателен прежний manifest erratum.11исключённых fixtures406 не объявляются
облачно сохранёнными. Личный контекст — отдельный приватный Git. После отчёта STOP.
