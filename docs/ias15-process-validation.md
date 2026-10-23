# IAS15: восстановление и продолжение в новом процессе365

24 октября2026. Все36новых worker-процессов восстановили полный snapshot
и продолжили расчёт побитно относительно frozen FULL364. Проверены3336
последующих пакетов и3372записи состояния, включая36точек загрузки.
Это проверка restart/lifecycle исследовательского IAS15; продукт остаётся0.3.1.

## Протокол, модель и независимая проверка

[Протокол365](ias15-process-protocol.md) задан до орбитальных результатов.
Те же9actual-IC задач353/364, два epsilon1e-9/1e-11. Newton two point mass,
SI, inertial3D, modelt0=0; без PN/softening/вращения/COM shift/callback.
Старые masses/IC, packet_dt631148.6686220014с, интервал63114866.86220014с,
epochs82/60; basic gravity, PRS23/min_dt0/exact_finish_time1.

Для каждого варианта запущены два новых процесса с snapshot:

| Точка | Index holdout/original | Модельное время, с |
|---|---:|---:|
|первый committed пакет|1/1|3155.743343110007|
|первая граница >=T/2|66/57|31557433.43110007|

Каждый worker загружает один snapshot и непрерывно интегрирует оставшиеся
прежние packet endpoints доT; повторных restore/reset внутри suffix нет.
Сохранённые поля сравниваются с FULL364, который уже сверён с warm.
Так проверяется и исходный rand_seed. На каждой новой границе совпали17
IAS15fields, actual N_allocated6, x/v/a/masses, G, dt/dt_last_done,
steps_done и остальные сериализуемые fields. Исключены walltime и адреса
указателей. C restore использует неизменный guard363, два raw C mask=0,
без warnings, synchronize/getSimulation или интегрирования при чтении.

На выходных эпохах собран прежний warm-prefix плюс новый continued suffix.
Независимые Decimal actual-IC analytic/E-L-P metrics повторены для всей
составной траектории и отдельно для suffix. Все36вариантов прошли старые
пороги: Δr<0.1м, Δv<1e-6м/с, относительные E/L и масштабированный P drift<1e-10.
Максимумы в обеих проверках: Δr0.04878006332681836м,
Δv6.220927669558766e-7м/с, E6.097551932957584e-15,
L2.972100414730003e-14, P2.2189872695083312e-16.
Это ошибки на фиксированных выходных эпохах, не граница ошибки во все времена.
Oracle и его прежняя неопределённость <1e-6м/<1e-12м/с не менялись.

## Новый процесс и отказы

Supervisor запускает тот же Python executable через subprocess, передаёт
только JSON metadata/hash; C/Python simulation object не передаётся.
Worker сам читает выбранные bytes из SHA-pinned public NPZ364 и строит
свежий guard из исходных IC. Версия, ABI,68librarySHA, origin, массы/порядок,
epoch, physical/binary SHA и file-binding inventory проверяются до C-reader.
В каждом worker до этого отсутствовал импорт REBOUND; library5.2.2
загружена явно из прежнего локального research dependency, без установки.

Нечисленная stdlib-проба до орбит выявила Windows venv redirector:
Popen.pid принадлежит launcher, а interpreter worker имеет другой PID и
ppid=launcherPID. Протокол до опыта уточнён для direct S→W либо Windows
S→L→W. Supervisor знает S/L по Popen, через stdin передаёт launch metadata,
worker связывает их с фактическими pid/ppid, request SHA и уникальным launch_id.
Все36положительных запусков использовали проверенную Windows цепочку S→L→W.
Это не fork с переданной памятью и не произвольное послабление PID-проверки.

Четыре дополнительных реальных worker получили неверные outer SHA, ABI,
binary SHA и source SHA. Все завершились с отказом до C restore; input,
stdout/stderr, worker-start/result сохранены. Подмена ABI/binary metadata
сверяется с frozen snapshot, а не принимается из самого запроса на доверии.
Повреждённые данные C-reader не получал. Пять старых coldFAIL353/355/364
сохранены в исходных отчётах; cold reset в365 не выполнялся.

Raw candidate bin/sidecar записываются в новые файлы; committed marker
появляется только после точного сравнения payloads. Ошибка записи или
сравнения оставляет прежний committed snapshot и candidate для диагностики.
Unit-тесты проверили этот порядок, nonzero exit/timeout с сохранением logs,
stale pid/ppid/nonce/mask/import results, выход binding за root, неверные
metadata/schema и изменение каждого17IAS15payload в canonical SHA.

Первый pytest collection отказал: fixture была названа reserved именем
request. До орбит имя исправлено; first-test-source.py/first-pytest.log
сохранены.tools/process365. После исправления48тестов прошли; после
учёта launcher и real-child теста прошли50предварительных проверок.
В реальном орбитальном run новых отказов не было; численные gates не менялись.

## Стоимость и воспроизводимость

Один инструментированный run; секунды, суммарно36положительных workers:

| Участок | Секунды |
|---|---:|
|launch-to-exit wall|66.0549692|
|restore с проверками|0.1302505|
|integration3336пакетов|0.1848617|
|capture + preflight|2.1277019|
|запись + сравнение + подпись payloads|9.0750313|

Весь supervisor цикл до финальной NPZ упаковки76.9960990с, включая четыре
negative workers, source checks и аналитику. Launch включает startup/imports,
чтение старых данных и работу worker; строки не складываются в независимые
части одной суммы. Это не performance benchmark и не ускорение интегратора.

[Receipt](ias15-process-validation.json) и [108массивов](ias15-process-samples.npz):
indices, новые physical states и canonical field SHA для каждого job.
NPZ479613байт, SHA256
`105fad3035d811c2c6a5f26fcfc50206e23c82bf2acef2e738f80eb945946ca2`.
Canonical SHA включает build header и все поля кроме clocks/addresses,
использует бинарные payloads с lengths/names; rand_seed не исключён.
Предыдущие raw FULL364 buffers повторно не публикуются. Все новые raw
streams/sidecars/commit markers, requests и logs остаются локально
в.tools/process365/process-first-workers; source ZIP/report/NPZ также сохранены.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.replay_ias15_process
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_ias15_process.py
```

Offline replay проверяет источники/входы/запросы/identity цепочки,36jobs,
3372physical states и signatures относительно frozen364, затем независимо
повторяет composite/suffix metrics. Он не загружает REBOUND, не выполняет
новый C-restore/интегрирование и не читает raw локальные worker streams.
Новый live run требует той же отдельно установленной pinned библиотеки:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_ias15_process --library .tools/ias15165/dependency --output .tools/process365/another-new-run.json
```

Проверен этот Windows/Python/build/ABI и две фиксированные точки для каждой
задачи. Другой PC/OS/ABI, произвольная restore boundary и native callbacks
этим не приняты. Primary writer/reader/ownership — [source-аудит362](ias15-archive-source-validation.md).
Runtime, физические данные, зависимости приложения, portable0.3.1/main/теги
не менялись. Лицензия/adoption/Rust integrator/продуктовый состав0.3.2 ещё
требуют отдельного решения; точность относительно JPL этим не улучшалась.
