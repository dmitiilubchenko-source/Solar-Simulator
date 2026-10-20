# Карта проекта и правила хранения

Актуально на 19 октября 2026. Исходники — в `src` и `rust`; `build`, `dist`
и тестовые распаковки содержат производные копии. Для разработки запускайте
исходный проект через его `.venv`, а не старую portable-сборку.

## Компоненты и точки входа

| Назначение | Основные файлы | Граница ответственности |
| --- | --- | --- |
| Запуск | [README](../README.md), [commands](../src/solar_simulator/commands.py), [cli](../src/solar_simulator/cli.py) | Команды и параметры запуска |
| Модель опыта | [experiment](../src/solar_simulator/experiment.py), [sandbox](../src/solar_simulator/sandbox.py) | Тела, настройки, изменение опыта и расчёт |
| Движение и интегрирование | [motion](../src/solar_simulator/motion.py), [simulation](../src/solar_simulator/simulation.py), [continuous](../src/solar_simulator/continuous.py) | Физический расчёт независимо от Tk |
| Дополнительная физика | [relativity](../src/solar_simulator/relativity.py), [oblateness](../src/solar_simulator/oblateness.py), [nbody_rotation](../src/solar_simulator/nbody_rotation.py), [contacts](../src/solar_simulator/contacts.py) | Поддержка зависит от конкретного режима; наличие модуля не означает совместимость всех эффектов |
| Rust | [solar_core](../rust/solar_core/src/lib.rs), [PyO3](../rust/solar_native/src/lib.rs), [native_forces](../src/solar_simulator/native_forces.py) | Ядро, мост и Python-адаптер |
| Время и сохранение | [time_control](../src/solar_simulator/time_control.py), [storage](../src/solar_simulator/storage.py), [branch_io](../src/solar_simulator/branch_io.py) | Продвижение к цели, checkpoint и bundle с родителем |
| Начальные данные | [ephemerides](../src/solar_simulator/ephemerides.py), [perturbers](../src/solar_simulator/perturbers.py), `src/solar_simulator/data/` | Закреплённые входные данные и их происхождение |
| Представление | [app](../src/solar_simulator/app.py), [orbit_view](../src/solar_simulator/orbit_view.py), [plot_artists](../src/solar_simulator/plot_artists.py) | Tk и отображение состояния |
| Проверки | [check_project](../scripts/check_project.py), `tests/` | Общий прогон и изолированные проверки |

Явный выбор готовых солнечных режимов и распознавание их области:
[solar_profiles](../src/solar_simulator/solar_profiles.py), [руководство](profile-selection.md).
Обязательный аудит native: `check_project.py --require-native` и
[native_audit](../scripts/native_audit.py); обычный режим сохранён.

Управляемая остановка и сохранение последнего завершённого состояния:
[recovery](../src/solar_simulator/recovery.py), [контракт и восстановление](controlled-stop.md).
Recovery-копии находятся вне репозитория, содержат пользовательские опыты
и не относятся к временным сборкам для автоматической очистки.

## Рабочие проверки, исследования и история

- [Рабочий профиль](solar-working-profile.md) и его [JSON](solar-working-profile.json)
  определяют режим и область измерений. Standard и Strict не взаимозаменяемы.
- [Стабилизация runtime](runtime-stabilization.md) описывает текущие исправления
  и сохранённые неуспехи. [Исторический снимок исходников](runtime-sources-before301.zip)
  подтверждает старые source SHA, но не квалифицирует новую сборку.
- [Стоимость расстояний](distance-performance-validation.md): `scripts/profile_distance.py`
  сравнивает прежний контроль и текущий метод, хранит RAWвремена/SHA/годовые кадры.
  Это проверка эквивалентной оптимизации, не новый интегратор/эталон физики.
- `scripts/assess_*.py`, `independent_*.py`, `verify_*.py`, `fetch_*.py` и вспомогательные
  научные модули — стенды и инструменты, а не автоматически исполняемая часть ядра.
  Статус отдельного опыта определяется его протоколом и отчётом в `docs/`.
- `scripts/validation/vector3_before331.py` — точные прежние байты геометрии
  для исторического JPL-аудита; фиксированное имя/SHA проверяются отдельно.
  Текущий runtime эту копию не импортирует. Не удалять её как дубликат.
- `scripts/validation/` хранит закреплённые данные и исторические реализации,
  включая непройденный абсолютный эксперимент Койпера. Их нельзя удалять
  как «дубликаты»: тесты и отчёты проверяют конкретные байты.
- `docs/*-protocol.md`, `*-validation.md/json`, ZIP и NPZ — протоколы и результаты.
  Старые результаты сохраняются с областью применимости и исходными отказами.
  Новая дата файла или успешный тест не обновляют научную квалификацию автоматически.
- [Офлайн-данные](offline-data.md) описывают закреплённые источники. Научные кеши
  в `.tools` не относятся к мусору сборки.
- `sandbox.load_experiment` пока остаётся совместимым API чтения ребёнка;
  текущие GUI/CLI используют `branch_io.open_experiment`, сохраняющий родителя.
  Удаление старого API и частных функций требует отдельной проверки вызовов и SHA.

## Реестр, который обновляется вместе с проектом

[project-inventory.json](project-inventory.json) перечисляет файлы компонентов,
публичные документы и данные. [Проверка](../scripts/project_inventory.py) входит
в `scripts/check_project.py` и обнаруживает добавление, удаление и перемещение
файлов внутри этих деревьев. Она не доказывает использование функций,
корректность формул, актуальность текста или SHA научных результатов.
Личные документы, кеши, `target` и сборки в этот реестр не входят.

При изменении структуры или назначения компонента:

1. Обновить соответствующую строку карты и относящийся протокол/руководство.
2. Выполнить `.venv/Scripts/python.exe -X utf8 -B scripts/project_inventory.py --write`.
3. Просмотреть diff реестра и выполнить относящиеся проверки.

При изменении только реализации существующей функции реестр путей не меняется;
описание поведения и результаты проверок обновляются отдельно.
Новый каталог верхнего уровня необходимо явно добавить в проверку реестра.

## Сборки и очистка

Последняя проверенная portable: `SolarSimulator-0.3.0-20261019-223900`.
Папка/ZIP/SHA находятся в dist; [приёмка0.3.0](release-030-validation.md).
Версия подготовлена в dev, перенос в main/tag/Release требует согласования.
ПредыдущиеRC/315/155 сохранены; [RC](candidate-030rc1-validation.md),
[315](recovery-portable-validation.md) и [155](continuous-delivery-validation.md) имеют свои проверки.
`dist/LATEST.txt` — локальный указатель на проверенный артефакт, не команда запуска.
После новой сборки его обновляют только после успешного `check_portable.py`
и проверки SHA. Сам `build_portable.py` не объявляет результат проверенным.

Старые папки, ZIP и распаковки можно удалять после описи, проверки границ путей
и сохранения контрольных сумм, отчётов и отличающихся файлов. Ссылки в старых
отчётах на пути распаковки описывают место исторического запуска: после очистки
оно может отсутствовать. Проверка воспроизводимости выполняется новой распаковкой.
`SolarVerification-*.zip`, научные данные, `.venv`, Rust target и каталоги
публикаций с журналами не удаляются вместе со старыми portable.

[Результат очистки 310](build-cleanup-310.md).


Изменение315: recovery.py также перечисляет локальные копии без разбора опытов;
app открывает их через общий branch_io. commands защищает финальную запись
run-until и использует локальную recovery при отказе записи рядом с output.
build_portable.prepare_documents используется и сборкой, и проверкой реальной
подготовки документов; export_guide переносит все относительные ссылки.
ZIP-документы допускаются только по явному списку четырёх научных архивов.
check_portable проверяет относительные ссылки и полный цикл восстановления
в двух отдельных изолированных процессах. Регрессии: test_recovery_journey.py
и дополнения test_portable_rotation_documents.py. Физика и пакеты прежние.


Режим316: [trajectory](../src/solar_simulator/trajectory.py) связывает прежние
пакеты с полными атомарными checkpoint/SHA и индексом, не содержит формул сил.
[playback](../src/solar_simulator/playback.py) управляет курсором сохранённых кадров;
[trajectory_view](../src/solar_simulator/trajectory_view.py) показывает их без solver.
App использует прежний единственный worker и явную метку задания записи;
старый путь вычисления опыта сохранён. [Контракт и проверка](trajectory-recording.md),
регрессии test_trajectory.py/test_trajectory_gui.py. Папки solar-trajectory-* —
пользовательские данные, игнорируются Git, не являются сборками для очистки.

Режим317: [comparison](../src/solar_simulator/comparison.py) проверяет точный
parent-якорь и общие сохранённые эпохи, вычисляет Δr/Δv в SI и экспортирует
отчёт без solver/интерполяции. [comparison_view](../src/solar_simulator/comparison_view.py)
показывает наложение выбранного тела, разности и курсор общих эпох.
App/commands только открывают режим. [Контракт](trajectory-comparison.md);
test_comparison.py — независимая кинематика/время/состав/экспорт,
test_comparison_gui.py — реальный Tk/геометрия графиков/сохранность входов.

Редактор318: [input_units](../src/solar_simulator/input_units.py) выполняет явные
преобразования входа в SI, [body_fields](../src/solar_simulator/body_fields.py)
общий для edit/add, хранит неизменённый SI и снимок опоры. App по-прежнему
создаёт branch и сохраняет его до смены опыта. [Единицы и проверки](body-editor-units.md);
test_input_units.py — известные коэффициенты/предел float,
test_body_units_gui.py — реальный ввод/roundtrip/ошибки/parent/продолжение PyRust.

Происхождение319: [recipe](../src/solar_simulator/recipe.py) получает fingerprints
установленных файлов, связывает sidecar с прежним manifest и повторяет
опубликованные пакеты через прежний record_trajectory. Функций сил в нём нет.
Trajectory автоматически пишет рецепт; commands добавляет check/replay,
viewer — read-only проверку. [Контракт/проверки](recording-recipe.md),
test_recipe.py/test_recipe_gui.py: свежие процессы, полный кадр, отрицательные
контроли/ошибки/стабильность/legacy. Старые форматы и reader сохранены.


[Правила выпусков](release-workflow.md) описывают dev/main, неизменяемые теги,
момент обновления версии и проверяемые условия переноса готового выпуска.
Текущая цель0.3.0 не заменяет опубликованный v0.2.0; исходный checkpoint main
сохранён без отката. Версия пакета меняется при подготовке кандидата, до его приёмки.


Кандидат324: [область0.3.0rc1](candidate-030rc1.md) и
[результат приёмки](candidate-030rc1-validation.md). build_portable сверяет
Python/Cargo/native-pyproject версии и выбирает wheel по версии/ABI,
не поmtime. check_portable вызывает portable_workflows.py в двух
изолированных процессах: GUI units/branch/record/close/restart/view/compare
и отдельный CLI audit/replay PyRust. test_portable_candidate.py проверяет
отрицательные варианты выбора wheel/метаданных и реальный probe на исходниках;
последний не подменяет отдельную приёмку ZIP. Формулы физики не менялись.


Версия325: [состав0.3.0](releases/v0.3.0.md), [результатприёмки](release-030-validation.md).
Build run_build_smokes сам выделяет временный профиль внеZIP, очищает внешние
Python/Tcl настройки и изолирует font/recovery-файлы; общий профиль для двух
процессов удаляется только в собственном проверенном tools-каталоге.
Успех/ошибка/сохранность caller-профиля проверены реальными дочерними процессами
в test_portable_candidate.py; окончательная проверка поставки выполняется отдельно.
Документ выпуска выбирается по текущей версии pyproject, не по старому RC.
