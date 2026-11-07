# Q2-398B: Rust preflight завершён, scientific399 пока NO-GO

2026-11-07. [Машинные результаты](q2-qualification-preflight-398b.json).
Это продолжение398, в локальном журнале изменение399. **Полная научная серия399
не запускалась.** Sealed GO plan не создан, release0.3.3 NO-GO, A+D1 не утверждена.

## Проверенные источники и область результата

Исходный dev/origin `91a9abb4ca59cc0d9b62de932029c6d69bcc2ba2`, деревья чистые.
Baseline `fe0f456f2c7ba3a077eac21fc8413937d6e84fac` и кандидат
`f723a2162b4e115378959e244f428529be2d4516` неизменны. Native SHA256
`651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`.
Использована прежняя read-only среда384: Python3.14.2t, NumPy2.5.1, SciPy1.18.1,
OMP/OPENBLAS/MKL=1. Canonical imports, commit/tree, actual native/environment
сверены до и после каждой Rust-cohort; полные fingerprints остаются прежними395.

[58job contract](../scripts/q2-qualification398-plan.json), IC/G/SI, эпохи,
reference397, saved380NPZ и критерии не менялись. Сохранённые12Python probes,
два короткихRK45 и прежний computational ledger398 не перезаписаны и не повторены.
Три исторических strict-convergence FAIL независимо пересчитаны из saved evidence.

## Все missing Rust prefixes

Для каждого source выполнены two-bodies/three-bodies standard и one-Q2 legacy394,
cold+continuous, ровно первые3 исходные эпохи:0/62.5/125s либо0/50/100s.
Это **12коротких probes**, не12полных scientificjobs.

|Контраст baseline/candidate внутри Rust|Raw r/v/q/S|Checkpoint journal SHA|RHS/native на source|
|---|---|---|---|
|two-bodies cold|exact|exact|136/136|
|two-bodies continuous|exact|exact|68/68|
|three-bodies cold|exact|exact|136/136|
|three-bodies continuous|exact|exact|68/68|
|one-Q2 cold|exact|exact|112/112|
|one-Q2 continuous|exact|exact|71/71|

Всего1182наблюдаемых RHS/native dispatch, solver calls2дляcold/1дляcontinuous.
SO3различия0. Сравнение Python/Rust побитно не требовалось и не объявляется.
SHA `initial.json`, `result.json`, `complete.json` привязаны к своему source и
ресурсным измерениям, поэтому их равенство между sources не требуется.

Независимые E/P/L сверены с runtime; повторная редукция saved arrays совпала.
Максимальные короткие дрейфы Rust: E9.695360185280904e-15,
L5.337155307329417e-16, P4.911172556212484e-17, rawqnorm2.886579864025407e-15.
Ошибки относительно соответствующих сохранённых short references и разность
двух уровней reference приведены отдельно в JSON. Reference-level gap не является
rigorous error bound. Эти цифры не квалифицируют4000s, реальную Землю–Луну или JPL.

## Совместимость свидетельств398

Body-ID observer и continuous-t0 regression проверены текущими targeted tests.
Новый Rust использует тот же неизменённый `q2_execution398.py` и отдельный binding.
Старый v1cold результат остаётся со своим прежним tool binding: исправлениеt0
касалось continuous recording, а cold advance/IC/raw values сохранились.
Его допустимо использовать в сравнении коротких raw результатов; нельзя
переименовывать его в scientific399 или приписывать ему новый tool SHA.
Старый failed continuous raw не был записан до исключения и остаётся недоступным.

## Controller: доказанный дефект и минимальное исправление

Минимальный failing test подтвердил: старый controller принимал completed
attempt envelope и число guard-каталогов без исходного `supervisor.json`.
Это недостаточная проверка resource provenance при resume, не дефект физики.

[attempt_history](../scripts/run_q2_qualification399.py) теперь сверяет исходную
guard-запись с inline receipt, последовательность номеров, finite nonnegative
счётчики, накопленные CPU/wall без возврата бюджета и отсутствие partial.
`load_monitor` выделен только для проверки границы controller/supervisor;
production путь и SHA-bound monitor прежние, команды из JSON не выполняются.
Частичная публикация controller также требует отдельного recovery-решения.

Проверки: неверные plan/source/environment/job/tool SHA, чужой owner, изменённый
или отсутствующий guard/result, partial, повторная запись, запрет интегрирования
при resume завершённого SHA-verified job. Старый failing test/log сохранены.
Сквозной synthetic test использовал настоящий385monitor и настоящие маленькие
дочерние процессы: остановка между2подтверждёнными cohorts, resume, прежний
порядок5фаз и7подтверждённых guard records, без уменьшения consumed resources.
**Только worker command заменён доверенным harmless test hook.** Scientific
worker и полная оценка58реальных jobs этим тестом не аттестованы.
Отдельный настоящий CLI subprocess отказал unadmitted plan до загрузки runtime.

Локально **30PASS/1явно deselected**: новый controller suite и execution398,
кроме неизменённого дорогого full58 synthetic evaluator. Этот evaluator уже
прошёл CI исходного текущего HEAD42376428071; его файлы здесь не менялись.
Полный current-revision CI выполняется отдельно после push. Это software checks,
не scientific qualification. Нового локального full-suite PASS не заявляем.

## Ресурсы398B и ошибки подготовки

Измеренные5guardedattempts: **14.921875CPU s /13.184024active wall s**, включая
исходный ожидаемый failing test. Worker private peak247054336B, RSS149463040B,
supervisor peak37441536B; пики не синхронные, 50ms sampling не ловит любой spike.

Первый launcher ошибочно использовал developer venv без `psutil` и отказал до
импорта monitor, без научных вызовов. Точное CPU этого отказа **UNMEASURED**.
Удержан резерв1CPU/1wall; номинальная сумма15.921875CPU/14.184024wall ниже
early16/45. Резерв не выдаётся за измеренный верхний предел. Это ограничение
строгой суммарной resource аттестации сохранено явно. Новых численных запусков
после финального аудита нет, cap20/60/512MiB/32MiB не повышался.

## Почему backup398 стоил318CPU

Сохранённый receipt: worker288.234375CPU, supervisor30.15625CPU,
total318.390625CPU/303.889058wall. Из них287.625CPU принадлежит основному
Python backup процессу; точного профиля по операциям нет — **UNRESOLVED**.

Это широкий filtered prepare183записей/391471909B выбранных файлов, включая
11999291Bновую broad-delta и251639034Bбазу, а не compression225441Bstage ZIP.
178записей уже cloud-verified и ещё одна verified по chunks.
Source-level анализ подтвердил: scientific scan сначала читает/проверяет/hashes
весь выбранный cache, затем решает, что изменилось; delta verification повторно
читает base и payload; configured archives hashes/review предшествуют reuse
cloud evidence. Эти операции и50ms filesystem supervision не бесплатны.
Точную долю scan/hash/secret scan/decompression/ZIP/I/O восстановить нельзя.

На этом ПК добавлена явная reviewed `filtered_prepare_files` очередь только для
`prepare --project Solar-Simulator`: новые данные проходят прежние SHA/review/
cloud-readback, неизменённые395bundle и398raw используются по verified manifest.
Ежедневный запуск без project-фильтра сохраняет прежний полный обход; старые
156источников и originals не удалены. Три synthetic backup tests проверили
узкую очередь, прежний daily scope и отказ повреждённого SHA. Замер нового
реального prepare и cloud verification фиксируется отдельно при завершении.
При source SHA mismatch старый backup API записывает FAILED, но его общий
exit code может остаться0; поэтому readiness проверяем по manifest, не exit code.
Этот отдельный существующий дефект return code здесь не изменён.

## Реалистичный проект399, не утверждённый бюджет

Оценка wholejobCPU масштабирует измеренный prefix по4000/prefix horizon.
Применены1.5worker margin,+3CPUstartup/attestation,50%supervisor reserve,+5CPU.
Переход standard→coarse/fine и full horizon пока экстраполируется, не измерен.
Wall учитывает measured jobwall, запас и supervision. Это инженерные ориентиры.

|Независимая группа|Jobs|CPU s с резервами|Wall s с резервами|
|---|---:|---:|---:|
|baseline Python, включая2reference|16|102.312|123.996|
|baseline Rust|14|82.625|99.662|
|candidate Python|14|90.781|106.662|
|candidate Rust|14|80.656|97.547|

Итого~356.375CPU/~427.87wall и~37.55MB scientific output. **Финальный full-grid
evaluator и backup/network добавляются отдельно; их полный timing не измерен.**
Ни381CPU из398, ни356CPU здесь не являются подтверждённым бюджетом всей серии.
Измерены single samples, 15.625ms CPU quantization и variation startup; доверительный
интервал не оценён. Предварительное предложение —180CPU/360wall на группу,
early144/288,1GiB/128MiB,early900MiB/112MiB; **не разрешение владельца**.

Текущий controller намеренно сохраняет старый global144CPU/288wall policy и
all-cohort loop. Независимые группы с новым бюджетом им пока не допускаются.
Следующий необходимый небольшой шаг: явная source-bound group admission с
регрессионными tests и отдельная оценка full-grid offline evaluator; без новых
орбит и повторения завершённых probes. После этого согласовать общий бюджет.

При будущем выполнении: отдельные immutable каталоги групп, fixed source/backend/
58IDs/IC/эпохи/SHA; после каждой группы узкий archive+manifest+cloud readback.
Независимый merge обязан проверить все58уникальных jobs. После выключения ПК —
сначала проверить manifest/guard receipts/file SHA; partial не продолжать и не
перезаписывать, consumed budget не обнулять. Cold/continuous рецепты не заменять.

## Решение

**GO в проверенной области:** короткие Rust source contrasts и tested controller
components. **NO-GO scientific399:** не утверждён и не реализован независимый
group budget, неизвестен full-grid evaluator cost и остаётся оговорка раннего
resource accounting. Sealed GO plan не создан. Main/tags/LATEST/portable032,
physics/integrators/R-reuse и оба frozen candidate не менялись. После отчёта STOP.

## Завершение сохранения и CI

Code commit`0d32c36f500a7cd4cb17bbedad4700344241c226`, CI42381484916:
Python+desktop-native success, adaptive-research configured skip. Включён
новый controller suite и прежний full58 synthetic evaluator; это software CI.
Новая reviewed очередь prepare:1.046875CPU/2.500304wall; archive creation
0.3125CPU/0.284310wall. Пять отдельно измеренных backup legs (3synthetictests,
archive,prepare,дваcloudreadbacks):2.234375CPU/5.38715wall.
Connector/server CPU, часть transfer latency, Git/CI/edit не измерены.
Нельзя называть это ускорением318CPU того же алгоритма: scope теперь только
новые115rawmembers, с reuse прежних verified dependencies. Dailyfullscan прежний.
Archive178983B и внешний manifest8877B independently downloaded, size/SHA256/
parent проверены: CLOUD_VERIFIED_SHA256. Личные документы и конфигурация
других проектов не выгружены. Научная серия399 по-прежнему NO-GO.
