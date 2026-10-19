# Переносимая рабочая сборка108–109

12 октября2026. Пакет100–109 завершён: новые научные стенды100–107
проверены отдельно; приложение продолжает использовать прежнюю проверенную
физику. Изменения108–109 исправляют состав сборки и добавляют готовый
сценарий уже реализованного ньютоновского вращения Луны.

## Готовый результат

[ZIP, 105626218байт](C:/Users/Admin/Desktop/Solar-simulator/dist/SolarSimulator-0.2.0-20261012-212738.zip)
и [SHA256](C:/Users/Admin/Desktop/Solar-simulator/dist/SolarSimulator-0.2.0-20261012-212738.zip.sha256).
SHA256: `2b97b2cb1acda3b5a9067dbf480ef3c569fe677a030d7d8990980a832e1470a3`.
Версия пакета0.2.0; timestamp различает эту новую проверенную сборку.
Распаковать ZIP и запустить `Solar Simulator.cmd` либо `Moon Rotation.cmd`.
Второй запуск открывает готовый Newton/DOP853/per-body Earth–Moon сценарий
с динамической ориентацией Луны и обратными силами/моментами.
Полная PN-модель вращения, внутреннее ядро и приливы пока не включены.

## Исправленный пропуск упаковки

Исходный сборщик включал актуальный USER-GUIDE, но не копировал
`nbody-rotation.md`, на который руководство ссылалось. Готового dynamic-Q2
сценария тоже не было. Теперь переносится публичная цепочка документов
и JSON-политик вращения/новых стендов:80файлов. Ссылки на личные рабочие
документы остаются простыми подписями; содержимое личных файлов не читается
и не переносится. Новые исследовательские скрипты, private primarycache и архивные NPZ
остаются в рабочем проекте, не становятся зависимостями приложения.

Добавлены `scenarios/solar-system-moon-newton-dynamic-q2.json`, отдельный
launcher, CURRENT-STATUS и сведения о сценарии в BUILD-INFO. JSONschema10,
q/S/инерция/происхождение/допуски сохраняются существующим storage API.
Физические модули src, Rust и исходные астрономические данные не изменялись.

## Фактические проверки

- Итоговый `check_project.py`:1243Python-теста за150.05s,17Rust,
  cargofmt обоих crates; прошли.61newtests включены в1243.
- Проверки публичной documentclosure и запрета внешнего файла:2passed0.25s.
- CLI создал новый NewtonMoon scenario; checkpoint сохранил rotations
  точно, продолжение/reset прошли. Реальный скрытый Tk GUI продвинул опыт.
- Свежие project/native wheels и отдельный CPython3.14t runtime собраны;
  native/Tk/приложение проверены непосредственно в новой папкеdist.
- ZIP распакован в новый каталог `.tools/portable relocated 20261012-212912`;
  `python -I`, PATH ограничен Windows, PYTHONHOME/PYTHONPATH/TCL/TK overrides
  удалены. Python/Rust/Numpy/SciPy/Matplotlib и Tcl загрузились из runtime.
- Relocated probe прошёл старые сценарии, контакты, EIH/Q2, MPC-fitting,
  новый NewtonMoon scenario и его checkpoint/restart; isolated=1.
- Дополнительный настоящий Tk/Laboratory GUI из распакованной папки
  продвинул dynamicMoon scenario; isolated=1, runtimeprefix локальный.
- ZIP CRC и SHA совпали; bytes всех runtime `.py` и data `.json/.txt`
  соответствуют рабочим исходникам.284относительные ссылки документов
  в архиве разрешаются. AGENTS/личные документы/.tools/.venv не попали вZIP.
- Предыдущий проверенный ZIP от11октября оставлен; его SHA повторно проверен.

Полные локальные логи и receipts: `.tools/rotation100-109`.
Научные результаты: [harmonicmap](harmonic-sphere-validation.md) и
[coordinate current/tensors](chart-current-validation.md). Их sourcecopies
соответствуют фактически выполненным расчётам; позднее изменены только
build/checkportable scripts. Старые отчёты не переписаны под новые SHA.

## Код и ограничения

[Сборка](C:/Users/Admin/Desktop/Solar-simulator/scripts/build_portable.py:65),
[relocation check](C:/Users/Admin/Desktop/Solar-simulator/scripts/check_portable.py:11),
[проверки документарной границы](C:/Users/Admin/Desktop/Solar-simulator/tests/test_portable_rotation_documents.py:8).
Лунный профиль — прежняя mean-solid rigid-аппроксимация, не mantle/core
или квалифицированная PN-инерция. Кольцо420 не прошло геометрический
критерий;528 прошло собственные численные проверки, но KBO/SB441 остатки
выросли. Численное согласие не объявляется истинной физической точностью.
Никакой GitHub-публикации или релиза в этом пакете не выполнялось.
