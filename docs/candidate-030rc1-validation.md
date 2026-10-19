# Приёмка кандидата 0.3.0rc1

Кандидат в dev, не принятый стабильный выпуск. Main и v0.2.0 сохранены.
Python/native metadata:0.3.0rc1, Cargo:0.3.0-rc.1. Область — поставка
существующих функций, без изменения физических формул и критериев.
[Предварительно заданная область и аналитика](candidate-030rc1.md).

## До и после

Раньше native-wheel выбирался по mtime. Теперь версии Python, двух Cargo
манифестов и отдельного native pyproject согласуются до создания каталога;
выбор требует ровно одного совместимого wheel нужной версии/ABI. Более новый
старый wheel игнорируется, отсутствие/неоднозначность отклоняются явно.
Отдельный реальный отказ подготовки выявил, что Maturin использовал оставшийся
номер0.2.0 из native pyproject при Cargo0.3.0-rc.1. Метаданные согласованы,
и отрицательная проверка исключает повторение этой ошибки.

Старый ZIP315 не содержал316–319. Кандидат добавляет их поставку и приёмку
в двух независимых изолированных процессах, с дополнительными CLI-процессами:
GUI edit units→branch→record→cooperative close/recovery→restart/continue→
playback/comparison/export→recipe/replay полного/остановленного префикса PyRust.
Сами численные пакеты и физическое ядро не менялись. Spin/mass сравниваются
точно, компоненты баллистики и Δr/Δv — по заранее заданным выражениям,
abs1e-10 и rel0. Просмотр запрещает solver; исходные байты записей неизменны.

## Локальные проверки и обнаруженные отказы

Первый прогон новых тестов:3PASS/1FAIL за7.99с. В служебном probe Vector3
сравнивался по идентичности объектов, а не компонентам. Файл сохранения
содержал правильные значения; исправлен probe, не ядро и не критерий.
Повтор:4PASS42.95с. После расширения проверки native pyproject и перехода
на согласованные установленные кандидаты:13PASS48.41с вместе с документами.

Первый install без build-isolation не нашёл setuptools.build_meta в .venv.
Повторена обычная изолированная установка build-зависимостей; runtime-зависимости
не обновлялись. pip check — без нарушений. Native/core пересобраны;
старые архивы, рецепты и научные отчёты с номером0.2.0 не переписаны.

## Проверенные места реализации

- [build_portable.py:candidate_versions](C:/Users/Admin/Desktop/Solar-simulator/scripts/build_portable.py:29)
- [build_portable.py:select_native_wheel](C:/Users/Admin/Desktop/Solar-simulator/scripts/build_portable.py:41)
- [build_portable.py:build](C:/Users/Admin/Desktop/Solar-simulator/scripts/build_portable.py:93)
- [check_portable.py:check_recording_workflows](C:/Users/Admin/Desktop/Solar-simulator/scripts/check_portable.py:316)
- [portable_workflows.py:create](C:/Users/Admin/Desktop/Solar-simulator/scripts/portable_workflows.py:29)
- [portable_workflows.py:restore](C:/Users/Admin/Desktop/Solar-simulator/scripts/portable_workflows.py:112)
- [portable_workflows.py:vector](C:/Users/Admin/Desktop/Solar-simulator/scripts/portable_workflows.py:19)
- [test_portable_candidate.py:test_artifact_selection_ignores_newer_wrong_version_and_wrong_abi](C:/Users/Admin/Desktop/Solar-simulator/tests/test_portable_candidate.py:21)
- [test_portable_candidate.py:test_missing_or_ambiguous_candidate_is_an_explicit_error](C:/Users/Admin/Desktop/Solar-simulator/tests/test_portable_candidate.py:29)
- [test_portable_candidate.py:test_paired_metadata_accepts_normalized_candidate_and_rejects_stale_component](C:/Users/Admin/Desktop/Solar-simulator/tests/test_portable_candidate.py:40)
- [test_portable_candidate.py:test_new_workflows_across_real_isolated_processes](C:/Users/Admin/Desktop/Solar-simulator/tests/test_portable_candidate.py:54)

## Статус

Полная native-приёмка кандидата прошла:2147Python за693.94с,19Rust,
обе fmt, без пропусков; полный wall702.35с. Source/data/native/core.exe
SHA неизменны. Реестр914путей,3086file:lineссылок. Отдельная проверка настоящего
ZIP после свежей распаковки тоже прошла; LATEST обновлён только после PASS/SHA.
Архив315 проверен по прежнему SHA256;315/155 сохранены.

Одиночные времена тестов — цена проверки, не ускорение интегрирования.
Баллистика проверяет единицы/время/доставку; точность гравитационного решения
так не измеряется. Подробные ограничения recipe сохраняются, старый recipe
при несовпадении версии/окружения отклоняется, а не переписывается.


## Проверенная portable

`SolarSimulator-0.3.0rc1-20261019-212011.zip` — 112366338байт.
SHA256: `86e53c4435c1566fd70b6005e77461bc47a13644f2aff1d451421fa2f15fe2a9`.

Сборка 43.37с; полная ZIP-приёмка 212.70с.
Это одиночные замеры разных стадий, не benchmark производительности симулятора.
Сборка выполнялась с отдельным LOCALAPPDATA, заданным контроллером приёмки;
в проверке ZIP собственные изолированные PATH/imports/Tcl/LOCALAPPDATA.
Standalone builder пока полагается на переданный LOCALAPPDATA для своего
smoke GUI; автоматическую изоляцию внутри сборщика стоит закрепить перед final.

Свежая распаковка с пробелами/новые процессы:574относительные ссылки,
78py/json/txt файлов runtime побайтно совпали с исходниками,4публичных научных
ZIP побайтно совпали, native pyd совпал с проверенным установленным binary.
Личные документы/.tools исключены. Установленные версии Python-пакетов
сверены с BUILD-INFO; настоящий native и библиотеки находятся внутри runtime.

Прежние GUI/recovery/save/load/parent/target/CLI CSV/финальная ошибка записи
прошли; новые PyRust editor/relative units/record/close/restart/playback/
comparison/export/audit/replay полного и остановленного префикса прошли.
Сохранены точные spin/mass/parent/checkpoints и исходные байты записей;
просмотр не запускал solver. Все CLI replay сравнивали полные кадры и их число.

## Новый годовой расчёт внутри распакованного runtime

10тел, SI, SSB/EclipticJ2000, JD2461321.5TDB/DE441, Strict Rust DOP853:
dt3600с,rtol3e-14,xatol1e-3м,vatol1e-9м/с, per-body/relative Earth–Moon,
EIH1PN+fixed Sun/Earth J2 с реакцией. GM гигантов — системные барицентры.
Длительность31557600с,125сохранённых эпох/499пакетов, время свежего solver
14.895с. Параметры/эпохи/системы и первичные40ответов
проверены по закреплённым SHA при экспорте/повторе; нового сетевого JPL-запроса нет.

| Тело | Максимальный остаток JPL, м | Максимальный остаток скорости, м/с |
|---|---:|---:|
| Sun | 218.804816 | 1.37822718e-05 |
| Mercury | 207.691441 | 2.67644374e-05 |
| Venus | 257.467671 | 2.33010071e-05 |
| Earth | 174.549540 | 4.14231002e-05 |
| Moon | 747.755283 | 0.00196633897 |
| Mars | 571.340787 | 4.37239113e-05 |
| Jupiter | 273.266260 | 1.88702416e-05 |
| Saturn | 31.079503 | 1.91131306e-06 |
| Uranus | 17.165371 | 1.08236891e-06 |
| Neptune | 64.701300 | 4.11352077e-06 |

Moon−Earth: 718.824785м /
0.00197761124м/с. Все старые цели10км/1км прошли.
Отличие свежих x/v от прежних сохранённых на этой же125-эпоховой сетке —
точно0 для каждого тела и пары. Это сохранение поведения, не повышение
физической точности. 125/440-эпоховые максимумы разных сеток не сопоставляются
как улучшение. RK45-независимость принадлежит прежнему аудиту141, здесь
выполнен новый production-расчёт и повтор старого проверенного сравнения.
Сохранён старый численный FAIL Standard-профиля; Strict не сертифицирует
другие IC/горизонт/пакеты или непрерывную ошибку между сохранёнными эпохами.

Continuous-регрессии воспроизведены, general_release_passed остаётся false.
Noether/PN×J2/PN-spin и экспериментальные Kuiper420/528 ограничения прежние;
новой физической квалификации вращения и полных консервативных балансов нет.

0.3.0rc1 прошёл описанную приёмку. Это локальный кандидат для демонстрации,
а не опубликованный0.3.0. Main/старый v0.2.0 не изменялись; стабильный номер
и его окончательная поставка требуют отдельной подготовки и проверки,
а перенос в main — согласования с пользователем.
