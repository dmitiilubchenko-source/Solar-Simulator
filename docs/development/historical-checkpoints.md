# Исторические доказательства и запуск checkpoint

Изменение 374, 26 октября 2026. Физические формулы, интеграторы и старые
JSON/NPZ/пороги сохранены. Принятый выпуск остаётся 0.3.2; dev не является
новой квалифицированной поставкой.

## Три разных результата

| Проверка | Что подтверждается | Чего она не разрешает |
|---|---|---|
| Исторические доказательства | Точные объявленные source/data bytes, сохранённые метрики и исходные FAIL | Запуск несовместимого checkpoint или квалификацию текущего runtime |
| Совместимость выполнения | Обязательные текущие зависимости, их SHA на диске и SHA загруженного кода | Заявление годовой точности модели |
| Научная квалификация | Независимые проверки конкретных модели, входов, сетки, длительности и критериев | Перенос точности на другие системы и режимы |

Исторический source resolver в [release_history.py](../../scripts/release_history.py)
не используется в live `verify_sources`/`evolve` и проверках workers.
`verify_checkpoint_history` проверяет старые объявленные зависимости;
он не доказывает полноту старого окружения. Состояние и записанные SHA не
переписываются. Обычное чтение формата также само по себе не разрешает запуск.

## Причины и минимальные изменения

| Группа | Первопричина | Исправление |
|---|---|---|
| A | Исторический вход проверялся как текущий solver | Отдельная проверка исторического происхождения; default выполнения строгий |
| B | В portable-fixtures отсутствовал numeric archive; session знал только UI-список | Полная комплектация архивов и единый список допустимых historical paths |
| C | Старый RK45 cache зависел от сегодняшнего simulation.py и числа изменённых файлов | Историческая проверка source bytes; `current_source_changes` отдельно от научной qualification |
| D | Старый parent проверялся по текущим исходникам, затем требовал live conversion | Историческая проверка parent; чтение закреплённого initial63 без перепривязки SHA |
| E | Существующие годовые receipts привязаны к прежнему runtime | Строгий отказ сохранён; новая квалификация в этот этап не входит |
| F | Тесты старых отчётов требовали буквальные текущие SHA | Историческая проверка только источников; прежние метрики/пороги/неуспехи сохранены |

Для D проверяются pinned SHA checkpoint, raw initial побитно, параметры,
пара/порядок, единицы и solver controls. Текущий `initial_relative` и default
`bound_lunar_initial` сохраняют live-защиту. Исторические варианты включаются
отдельно; `evolve` откажет старому checkpoint до интегрирования.

## Новые обязательные зависимости

В Cartesian canonical `CORE_SOURCES` добавлены `_numbers.py`, `simulation.py`,
`vector3.py`, `coordinates.py`. Relative canonical наследует этот список.
Первый влияет на интерпретацию физических чисел; остальные входят в локальную
цепочку импортов rotation/nbody_rotation. Список содержит 10/12 файлов.
Проверка top-level локальных импортов замыкает эту цепочку. Lazy Newton/native/
profile helpers из других функций nbody_rotation не выполняются canonical solver.
Это не фиксация версий NumPy/SciPy, платформы или всего окружения.

Схемы checkpoint не меняются: source records уже поддерживают эти пути.
Новые checkpoints должны содержать полный текущий список. Старые документы
по-прежнему читаются, но не могут автоматически продолжаться текущим solver.
Fresh-process тест изменяет только `_numbers.py` в отдельной временной копии:
дисковая проверка и проверка загруженных версий отвергают её до solver.
Положительный контроль использует те же неизменённые байты.

## Архивы и переносимость

Старые архивы и SHA сохранены. Новый
[history-before374.zip](../../scripts/validation/history-before374.zip)
содержит 25 точных файлов pre374 (dev240eef4), 53095 байт;
SHA256 `9d55542c89dcb741264adea38f6b060821833edfcbcb4531ca4aa66d1455b7fd`.
Каждый член независимо сверен с сохранённым before-sources snapshot.

Resolver требует допустимый путь внутри root, закреплённый SHA всего архива
и совпадение SHA выбранного члена. Отсутствие live-файла не мешает проверке
точного исторического члена. Отсутствующий несвязанный UI-архив не блокирует
numeric-историю одноимённого файла. Неподходящий архив не даёт ожидаемый SHA;
повреждённый рассматриваемый архив отклоняется. Cargo-переход остаётся
ограниченным прежним manifest и нормализацией CRLF→LF.

Replay-fixtures включают весь набор исторических архивов. Перед намеренной
порчей source/NPZ/метрики/receipt выполняется успешный контроль; затем
проверяется причина отказа, а не произвольный ValueError. Неповреждённые
replay сохраняют 5 baseline FAIL и 10 restart-step FAIL как научные результаты.
RK45 сравнивает все научные поля qualification, а исторический список
изменений отдельно восстанавливает по source inventory того запуска.
Динамическое число файлов текущего дерева не становится новым эталоном.

## Почему E остаётся непройденной

Доказательства 373 ограничены: 10 коротких документов до/после побайтно,
отдельные вращательные траектории и AST вычислительных функций. Это полезно
для отсутствия локальной регрессии, но не воспроизводит все годовые Strict/
qualification-grid/sandbox-limits режимы, backend и переходы состояний.
Нет достаточного независимого доказательства их полной численной
эквивалентности. `check_receipts` сохраняет строгую проверку текущих SHA;
старые архивы не могут сделать `current_qualification_passed=True`.

Следующий отдельный этап должен заранее определить точный профиль, входы,
эпохи/пакеты, backend, допуски и критерии; воспроизвести новую траекторию либо
предоставить достаточное независимое доказательство эквивалентности.
Старые отчёты сохраняются. До этого обязательные отказы E блокируют выпуск;
их нельзя превращать в skip/xfail или называть полную приёмку успешной.

## Проверки

Окончательный `check_project.py --require-native`: **2891 PASS, 3 FAIL,
0 ERROR, 0 skip, 980,30 с**. Полная приёмка НЕ пройдена.

Все три FAIL относятся к `tests/test_sandbox_acceptance.py`: один положительный
контроль текущей квалификации и два однофакторных теста (oblateness.py и
JPL-reference). Непосредственная причина у всех — прежний SHA experiment.py.
Оба отрицательных теста останавливаются на исходном положительном контроле;
проверка их намеренных повреждений остаётся неподтверждённой. Они не заменены
на ожидаемый отказ ради зелёного набора.

| Локальная проверка | Фактический результат |
|---|---|
| Относящийся Python/native набор | 477 PASS, 0 skip, 241,14 с |
| Python CI | 566 PASS, 4 штатных deselect, 18,10 с |
| Rust core и форматирование | 19 PASS, обе fmt PASS |
| Исторический baseline | 49 PASS / 5 исходных научных FAIL, 6786 checkpoint |
| Restart-step | 26 PASS / 10 исходных научных FAIL, 4524 checkpoint |
| Owned session | 18 PASS, 2262 checkpoint |
| Native Newton year replay | Pilot 4/4 и year 4/4, исходные метрики |

После полного прогона 869/869 отпечатков исходников/данных совпали со стартом.
После pytest FAIL полный скрипт не запускает свои последующие Rust/link этапы;
Rust и ссылки проверены отдельно. Это не новая portable-приёмка и не годовая
квалификация текущего solver. Изменений src/rust и численных формул нет.

Самопроверка: source resolver подтверждает bytes, не наличие файла; live
verify/evolve не вызывают его и их тела AST совпадают с pre374. Новый CORE
замыкает локальные top-level imports. Oldcheckpoint отказывает текущему solver,
а новые контрольные состояния проходят обычные restart/codec проверки.
Полнота прежнего окружения и эквивалентность всего годового профиля не доказаны.
Локальные логи находятся в `.tools/history374` и не входят в публичную поставку.
Команды: [выбор проверок](../verification/README.md).


## Изменённые публичные файлы

- scripts: [assess_nominal_jpl.py](../../scripts/assess_nominal_jpl.py), [assess_relative_canonical_checkpoint.py](../../scripts/assess_relative_canonical_checkpoint.py), [assess_rotation_time.py](../../scripts/assess_rotation_time.py), [canonical_checkpoint.py](../../scripts/canonical_checkpoint.py), [newton_year_cache.py](../../scripts/newton_year_cache.py), [release_history.py](../../scripts/release_history.py), [replay_ias15_session.py](../../scripts/replay_ias15_session.py), [replay_native_newton_year.py](../../scripts/replay_native_newton_year.py), [sandbox_checks/README.md](../../scripts/sandbox_checks/README.md), [validation/history-before374.zip](../../scripts/validation/history-before374.zip).
- tests: [test_canonical_checkpoint.py](../../tests/test_canonical_checkpoint.py), [test_canonical_solar.py](../../tests/test_canonical_solar.py), [test_ias15_native_newton_replay.py](../../tests/test_ias15_native_newton_replay.py), [test_ias15_native_session_replay.py](../../tests/test_ias15_native_session_replay.py), [test_ias15_restart_replay.py](../../tests/test_ias15_restart_replay.py), [test_ias15_restart_step_replay.py](../../tests/test_ias15_restart_step_replay.py), [test_ias15_session_replay.py](../../tests/test_ias15_session_replay.py), [test_lunar_initial_boundary.py](../../tests/test_lunar_initial_boundary.py), [test_native_newton_year.py](../../tests/test_native_newton_year.py), [test_native_newton_year_replay.py](../../tests/test_native_newton_year_replay.py), [test_relative_canonical_checkpoint_audit.py](../../tests/test_relative_canonical_checkpoint_audit.py), [test_release_history.py](../../tests/test_release_history.py), [test_release_ui_history.py](../../tests/test_release_ui_history.py), [test_rotation_time_audit.py](../../tests/test_rotation_time_audit.py), [test_sandbox_demo.py](../../tests/test_sandbox_demo.py), [test_sandbox_models.py](../../tests/test_sandbox_models.py), [test_time_control.py](../../tests/test_time_control.py).
- docs: [development/README.md](../../docs/development/README.md), [development/historical-checkpoints.md](../../docs/development/historical-checkpoints.md), [project-inventory.json](../../docs/project-inventory.json), [project-map.md](../../docs/project-map.md), [verification/README.md](../../docs/verification/README.md).


После374 выполнена отдельная [квалификация375](../current-runtime-375-validation.md).
Она даёт новые measured evidence текущему Strict-профилю; прежние отказы374
и исторические отчёты выше сохранены. Это не разрешение через старый архив.
