# Совместимость389: восемь случаев EXACT, один обязательный контроль не завершён

4 ноября2026. **Полный compatibility gate — NO-GO/незавершён.**
Численное сравнение восьми коротких случаев завершено успешно. Данные и GUI
в проверенной области совместимы. Не исполнен обязательный отрицательный тест:
отказ старой032 новому файлу с двумя Q2 — сработал ранний cumulative CPU-stop.
Сохранён также исходный FAIL тестового worker; он не является дефектом runtime.

[План389](compatibility-389-plan.md),
[машинный отчёт](compatibility-389-validation.json),
[исходный контракт387](compatibility-387-plan.md).

## Версии и обязательные preflight

Исходный devce277f4fea3b079a9a075542579fd9b311f6fd1c.
Accepted main/v0.3.2 cf653c9ca4b60649e70658b002a5e70669411266:
original portable SolarSimulator-0.3.2-20261025-121729, ZIP112312650bytes,
SHA7c578220ec77e792aa9589f32a30352e88277d0d096bff0ad3ca5aae9c014c49.
5979members CRC/SHA повторно проверены против существующей поставки.
Candidate0.3.3 fe0f456f2c7ba3a077eac21fc8413937d6e84fac — отдельный checkout/venv,
не developer runtime с metadata032. Candidate source-bound freeze проверялся
до/после startup и acquisition;13protected historicalSHA unchanged.

| Объект | accepted032 | candidate033 |
|---|---|---|
| NativeSHA256 |0cbc389f139854628f287c04a7cea52c530a18294c2c3a0670faa48bf53c0601|651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091|
| Environment fileSHA256 |4d8838ca01dc6f9f00f74b97c5142bb2dcaa82b8f7ce355192c735bac0b7f335|056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a|
| Canonical fingerprintSHA256 |384bfc30be543d42c9beb1671a63eab9a4f566c9e7487ca07710f96a0aa82f30|302a37b7524bd7443899680b17328ef9a8636773d3fc951b62d017fd842d0464|
| Python/ABI |3.14.2t,cp314t-win_amd64|3.14.2t,cp314t-win_amd64|
| NumPy/SciPy/Matplotlib |2.5.1/1.18.1/3.11.0|2.5.1/1.18.1/3.11.0|

Runtime package/compilednative paths проверены под собственным prefix.
Actual already-loaded NumPy/SciPy BLAS DLL пути и SHA сохранены; обе библиотеки
показали1thread в обоих startup. Profile до NumPy/SciPy: OMP/OPENBLAS/MKL=1,
VECLIB/NUMEXPR/PYTHONHASHSEED unset. Первые3 не очищались worker.
Fingerprint before/after совпал для обоих startup/acquisition; candidate
functional-tail fingerprint также совпал с его предыдущим end fingerprint.
Это общая **текущая** среда сравнения, не повтор исторической unset-среды/ОС.

## IC, реальные траектории и независимый observer

Все input JSON созданы настоящей032 после обоих успешных startup, до первого
advance. `ic-binding.json` фиксирует planSHA/inputSHA; до/после проверены.
Plan.stage387 обозначает исходный selection recipe, не исторические массивы:
эти файлы созданы заново в389. Acquisition audit hook не обнаружил .npz/.npy
access. Никакие старые научные states в расчёт не подставлялись.

SI, Newton G6.67430e-11; original387 masses/IC; Sun–Earth e=.0167.
dt50s, rtol1e-11, atol1e-7m/1e-11m/s, per-body; для singleQ2 originalI/q/S/
boundingradius/q_atol/S_atol и relative(figure,point). Эпохи0/50/100/150s,
три пакета по1шагу. Дополнительно own save/resume из50s с теми же двумя пакетами.
Не менялись solver settings, уравнения, фазы или состав cases.

| Случай | Backend | maxΔr,m | maxΔv,m/s | maxΔE,J | max|ΔP|,kgm/s | max|ΔL|,kgm²/s | Физические bits |
|---|---|---:|---:|---:|---:|---:|---|
|Sun–Earth Verlet|Python|0|0|0|0|0|EXACT|
|Sun–Earth DOP853|Python|0|0|0|0|0|EXACT|
|Sun–Earth–Moon DOP853|Python|0|0|0|0|0|EXACT|
|Один synthetic Q2 DOP853|Python|0|0|0|0|0|EXACT|
|Sun–Earth Verlet|Rust|0|0|0|0|0|EXACT|
|Sun–Earth DOP853|Rust|0|0|0|0|0|EXACT|
|Sun–Earth–Moon DOP853|Rust|0|0|0|0|0|EXACT|
|Один synthetic Q2 DOP853|Rust|0|0|0|0|0|EXACT|

Rawq/S каждого вращающегося состояния также EXACT; все4эпохи сохранены.
16own same-packet restarts подтвердили и значения, и binary64 bits.
Checkpoint documents/settings/initial data совпали отдельно от environmentmetadata.
Independent observer использует math.dist/fsum/Newton+MacCullagh E/P/L из387,
без Solar numerical evaluator. Все значения E/P/L на каждой эпохе в machine/raw
report; их совпадение/дрейф не является оценкой глобальной орбитной ошибки.

Native execution подтверждён profile events без подмены numerical functions:
в каждой версии RustVerlet5actualevolve calls; RustDOP RHS/point_acceleration
337/337,397/397,280/280. PythonVerlet5step; PythonDOP337/397/280RHS и0nativecalls.
Счётчики включают три основных и два resume пакета, не внутренние accepted steps.

## A/C: данные и действия пользователя

| Проверка | Фактический результат |
|---|---|
|Legacy schemas1–9 и singleQ2schema10|PASS: original032inputs читаются033; по8продвинутых old checkpoints загруженыcandidate|
|Own same-packet save/load/resume|16/16bits EXACT|
|Branch/parent/recovery|PASS на point-mass случае в обеих средах; вращающиеся ветки существующим контрактом не поддерживаются|
|Original recipe/manifest/frames|Целостность PASS; cross-version strictreplay корректно отказал до нового интегрирования|
|ActualTk Start/pause/load/save/recovery|PASS в обеих средах, поодному50sGUIпакету; selector dialogs mocked|
|Cancel/corrupt/unsupported schema|PASS: явный отказ/отмена без изменения опыта|
|Неподходящий native|PASS известных missing-entrypoint/noncompiled-negative probes; actualbinarySHA отдельно preflightguard|
|Old032 load newtwo-Q2 file|**NOT EXECUTED**, CPU-stop до входа теста. Статического ожидаемого отказа недостаточно для PASS|

Не заявляется universal ABI-native SHA enforcement пользовательским runtime.
Новые файлы с двумя Q2 не интегрировались; файл сохранён только для negative test.

## Различия и сохранённые FAIL/STOP

Environment fingerprints отличаются по application_version/package_files/native,
что соответствует разным исходникам/версии/бинарникам. Python/dependencies/platform/
численная env части совпали. Это не доказательство эквивалентности всех native APIs.

Исходный candidate worker после завершения всех8cases передал `Trajectory` в
`replay_trajectory`, ожидающий directory path. Сохранён TypeError/traceback/exit1,
progress snapshots и fingerprints. Это ошибка тестового draft, не productionbug.
Точный reproducer повторён без интегрирования; `old.directory` вместо объекта
даёт ожидаемый ValueError несовместимости recipe, destination не создаётся.
Исправлена только отдельная functional-tail проба; initialworkerFAIL не переписан.
Она закончила недостающие candidate GUI/native/old-data/recovery checks.
Ни один из8scientificcases не пересчитывался. Futurefixedworker сохранён отдельно.

Первый проход израсходовал158.359375CPU. Прежний operational early160/binding
сохранён. Отдельный remaining-plan заранее выделил часть **оставшихся21.640625s
исходного user180CPU бюджета** на только незавершённый tail, с cumulativeearly176.
Это не новый180sbudget и не изменение научных критериев/900MiBguard.
Следующий old-two процесс остановлен cumulativeCPU guard; обычные runtime jobs
после STOP не повторялись. Выполнена лишь обязательная offline редукция готовых
states под исходным180sceiling, с отдельным binding. Полный C не превращён вPASS.

## Проверки, ресурсы и решение

14guard/observer tests PASS/0FAIL/0skip. Независимое повторное чтение всех64primary
states и16resume snapshots подтвердило одинаковые времена/настройки/bits и
фактический backend. InputSHA сохраняется, raw-source/native/environment bindings
и все failure logs включены в `.tools/qualification389`; outputs не перезаписывались.
Controlled cumulative **176.78125CPU s/138.70493active wall s**,6766315bytes до
документов/архива. Сохранённый self sampled peak237203456bytes(226.2148MiB),
external worker219570176bytes,supervisorpeakcommit37908480bytes. Sampling10/50ms,
retainedCPUhandles, no OS hardquota. Метаданные/документы/Git/network/backup отдельно.

**A PASS в указанной области; B PASS только8короткихcases; C PARTIAL.**
**NO-GO полному compatibility gate/выпуску033:** остаётся ровно один обязательный
контроль old032 two-Q2 load rejection. Следующий узкий этап может использовать
уже сохранённый two-q2.json и states без повторения8орбит; нужен отдельный бюджет.
Production/runtimepatch не обоснован, Newton384/annual385 не пересчитывались.
Кандидат/main/tag/LATEST/375–388science/триFAIL380 не менялись. Также остаются
ownerpolicy/B_app386, fullrelease source/native/desktop и настоящаяportable033
acceptance. Успех восьми опытов не универсальная физическая аттестация.
После389STOP. Следующий этап: закрыть единственный negativecheck без новых орбит.
Модель: GPT-6.1 Sol High.
