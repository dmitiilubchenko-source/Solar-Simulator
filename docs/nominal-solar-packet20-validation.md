# Исходная Солнечная система: год, пакеты 20 часов

2026-10-16T16:29:34+03:00. Этапы215–217, [протокол до расчёта](nominal-solar-packet20-protocol.md),
[полные измерения и контрольные суммы](nominal-solar-packet20-validation.json).

**Три режима прошли прежние критерии.** Actual continuous CLI и GUI target
strict Rust проверены по всем440состояниям. Это квалификация закреплённого
опыта и конкретных путей, а не любых начальных условий или всего runtime.

## Модель, эпохи и независимость

Неизменный [strict checkpoint](solar-sandbox-strict-checkpoint.json):10тел,
SI, SSB, EclipticJ2000, JD2461321.5TDB/DE441. Сохраняются Origin и массы;
GM внешних планет включает спутники. EIH1PN плюс fixedSun/EarthJ2 с реакциями,
без динамического вращения/приливов/PN×J2 сил. Физическое ядро не менялось.
DOP853/rtol3e-14/x_atol1e-3м/v_atol1e-9м/с/per-body/relativeEarth–Moon,
dt3600с. Год31557600с,440эпох,439пакетов:438×20h+6h.

Прежний nominal год на125выходах создавал499границ; это другой контракт.
Новая сетка не добавляет запросов JPL между20hграницами.
Независимый RK45 использует AU/year/EMB+Moon−Earth, отдельные scalarRustEIH
и vectorJ2, не runtime DOP853/силы/coordinate classes.
Три уровня max_step1800/900/450с при rtol1e-13/3e-14/3e-14, atol1e-17.
RHS105194/210392/420776;115.541858с на все три reference.
Начальный roundtrip/oracle snapshot и итоговые SHA прошли.

Последние разности reference: все тела0.087892926м/3.59620346e-8м/с,
Moon−Earth0.000340091м/7.99660285e-10м/с. Первые разности:
все тела0.102607818м/1.93401812e-8м/с, Moon−Earth0.003055241м/8.49944377e-9м/с.
По общей скорости уточнение немонотонно; это сохранено. Чувствительность
не является строгой границей ошибки и не доказывает истинную точность модели.

## Результаты и стоимость

| Режим | Все тела, м | Moon−Earth, м | JPL Moon−Earth, м | Медиана, с | Прошёл |
|---|---:|---:|---:|---:|---|
| legacy_python | 0.121450941 | 0.075260816 | 691.596982 | 21.492345 | Да |
| legacy_rust | 0.136977801 | 0.075091675 | 691.591589 | 12.338370 | Да |
| continuous_rust | 0.067329792 | 0.038344853 | 691.644676 | 2.679864 | Да |

Первые два столбца — максимум по440точкам относительно независимого RK45,
не относительно наблюдений. Численные пороги:каждое тело10м/1e-4м/с,
Moon−Earth0.1м/1e-5м/с. Все позиционные и скоростные критерии прошли.
Результат каждого режима повторён побитно; legacy checkpoint/continue прошёл.
Три чередующихся полных замера включают setup/снимки, исключают аудит/запись;
каждый замер побитно совпал с исходным кандидатом. Внешняя нагрузка и частота
CPU не фиксированы. Медианы не являются обещанием скорости на другом ПК.
Полный процесс reference/candidates/repeats/timings/JPL занял322.609430с.

## JPL и сравнение с прежней сеткой

После свободных траекторий проверены40закреплённых первичных ответов
через SHA и прежний parser; оси/SSB/SI/TDB/Origin/ID совпали.
Только24точно общие эпохи, без интерполяции или изменения траектории.
Максимум по всем телам747.775757м; все тела прошли10км,
Moon−Earth прошла1км. JPL не использовался для подбора параметров.
Прежний continuous на **тех же24эпохах**:691.639740м для Moon−Earth;
новый:691.644676м. Прежний максимум около718.84м на125эпохах остаётся
актуальным; сокращение покрытия до24точек не означает улучшения физики.

На24общих эпохах new-vs-old continuous: все тела0.016716517м,
Moon−Earth0.004958372м; reference-vs-old reference: все0.083987413м,
Moon−Earth0.000295761м. Это диагностика чувствительности сетки/уточнения,
не новый подогнанный gate. Старый continuous год:0.069474м/0.040074м
на125эпохах относительно прежнего reference, стоимость3.233373с;
новый0.067330м/0.038345м на440эпохах,2.679864с. Разные сетки/reference
и внешняя нагрузка не позволяют приписать разность оптимизации или физике.

## Фактические CLI и Tk

Actual CLI packet_steps20:4400CSVстрок/440состояний, все uint64 bitexact
с continuousRust; всеJD/порядок/массы/work/Settings/Origin иoutputSHA проверены.
Actual Tk Laboratory: JSON_load, batch20, _start_target, реальные worker
futures, _poll, _record, _draw;440состояний bitexact с legacyRust,
финальный JSON/time/Settings/Origin сохранены. CLI experimental-флаги прежние.
CLI elapsed2.060251с, GUI17.607135с, полныйIOпроцесс24.183024с:
это отдельные единичные наблюдения, не сравнение производительности GUI/CLI.
Окно скрыто, ручнойpoll, filechooser stub, modalerrorsraise; физика неmock.
Отзывчивость видимого окна и реальная перерисовка mainloop не измерены.
Загрузка continuous final.json начинает новый контроллер; buffers не сохранены.

## Проверки, воспроизведение и ограничения

42проверки численного контракта прошли за0.96с;38IO/GUI/continuous проверок
за12.74с.18новых параметризованных случаев; это две конкретные команды
в JSON, не полный набор всех тестов. Отказов215/216нет; исходные неуспехи
standard139 и других исследований не переписаны. Все source/input/actual
oracleDLL/native.pyd/SciPy привязаны к SHA и неизменны до конца расчёта.

Из корня проекта с проверенным venv:

```text
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_nominal_solar_packets --output .tools/nominal-repeat/annual --raw-cache .tools/qualification144/jpl-batches
.venv/Scripts/python.exe -X utf8 -B -m scripts.verify_nominal_solar_packets audit --annual-receipt .tools/nominal-repeat/annual.json --output .tools/nominal-repeat/io
```

Использовать новый путь; не переписывать исходный аудит. Для первой команды
нужны40исходных JPLответов с заданными SHA: локальный путь выше либо `raw`
из [публичного JPL-комплекта](../tests/data/jpl-verification.zip), распакованного
без изменения байтов. Требуются проверенные SciPy/native и Rust compiler
для oracle; это не автономная проверка с одним Python без зависимостей.
Исходные траектории/логи/выходы сохранены локально .tools/nominal215.

Нет гарантии между снимками, для standard, ordinaryplayback, иныхbatch,
пользовательских масс/тел/сближений/горизонтов. Нет интегрированных годовых
Noether21sources десяти тел, полнойОТО или истинной точности понаблюдениям.
Койпер экспериментальный и не включён. Нового portableZIP/релиза/push нет.
Текущий [паспорт профиля](solar-working-profile.md) обновлён по этому результату.

## Проверенные определения

- [versions](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_nominal_solar_packets.py:30)
- [shared_epochs](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_nominal_solar_packets.py:36)
- [scope_qualified](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_nominal_solar_packets.py:49)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_nominal_solar_packets.py:55)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_nominal_solar_packets.py:198)
- [calendar_snapshots](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_nominal_solar_packets.py:20)
- [verified_receipt](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_nominal_solar_packets.py:45)
- [gui_worker](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_nominal_solar_packets.py:61)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_nominal_solar_packets.py:129)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_nominal_solar_packets.py:216)
- [test_force_backend_variants_preserve_nominal_calendar_and_initial_experiment](C:/Users/Admin/Desktop/Solar-simulator/tests/test_nominal_solar_packets.py:13)
- [test_only_exact_24_common_epochs_are_selected_without_adding_outputs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_nominal_solar_packets.py:25)
- [test_io_or_jpl_success_cannot_replace_failed_numerical_reference_or_mode](C:/Users/Admin/Desktop/Solar-simulator/tests/test_nominal_solar_packets.py:41)
- [test_existing_failure_archive_is_preserved_before_loading_any_inputs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_nominal_solar_packets.py:52)
- [test_all_nominal_csv_epochs_and_metadata_are_checked](C:/Users/Admin/Desktop/Solar-simulator/tests/test_nominal_solar_io.py:17)
- [test_nominal_receipt_rejects_untrusted_sources_or_missing_calendar](C:/Users/Admin/Desktop/Solar-simulator/tests/test_nominal_solar_io.py:41)
- [test_previous_operational_evidence_is_preserved_before_receipt_reads](C:/Users/Admin/Desktop/Solar-simulator/tests/test_nominal_solar_io.py:56)
