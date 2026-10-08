# Solar Simulator 0.2

Настольная гравитационная лаборатория на Python и Rust:
взаимное движение N тел в 3D, проекции XY/XZ/YZ, траектории,
диагностика, контакты сфер, отскоки, слияния и контрольные точки.

## Запуск

Открой `Запустить.cmd` или выполни из каталога проекта:

```powershell
.\.venv\Scripts\python.exe -B -m solar_simulator gui
```

Готовую переносимую Windows-сборку можно скачать из
[первого релиза v0.2.0](https://github.com/dmitiilubchenko-source/Solar-Simulator/releases/tag/v0.2.0).
Распакуй ZIP и открой `Solar Simulator.cmd`. В ней собственные Python/Tk
и библиотеки. Локальные результаты сборки находятся в `dist`.

[Полное руководство](docs/user-guide.md) — управление, физические
допущения, сохранение, выбор шага, CLI и сборка.
[Формулы и проверки](docs/physics.md), [Rust](docs/rust.md).
[Матрица точности и измерения скорости ядра](docs/core-validation.md).
[Новый точный режим DOP853 и измеренные ошибки](docs/accuracy-validation.md).
[Солнечная система из JPL DE441](docs/ephemerides.md): сценарий solar-system, закреплённая эпоха 8 октября 2026 TDB.
[Релятивистская модель EIH 1PN](docs/relativity.md): отдельный режим Python/DOP853.
[Отдельные Земля и Луна](docs/moon.md): сценарий solar-system-moon и сравнение с JPL.
[Несферичность Земли J2](docs/oblateness.md): отдельный профиль с фиксированной осью и измеренным влиянием на лунную орбиту.
[Ориентация Земли и лунные J2/C22](docs/orientation.md): профиль earth-moon-q2, заданная ориентация DE441 и учёт её работы, до одного года.
Текущая версия для разработки включает адаптивный расчёт; опубликованный ранее
ZIP 0.2.0 сохраняет прежнее поведение.

## Установка для разработки

Python 3.11 или новее с Tk:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,native]"
.\.venv\Scripts\python.exe -B scripts/build_native.py
.\.venv\Scripts\python.exe -B scripts/check_project.py
```

Python-ядро работает без Rust. Для native-сборки нужен Cargo;
подготовка Windows GNU-инструментов описана в `docs/rust.md`.
На текущем компьютере используется CPython 3.14t; native wheel
привязан к соответствующему ABI. Переносимая сборка включает этот Python.

## Работа через CLI

```powershell
.\.venv\Scripts\python.exe -B -m solar_simulator new sun-earth initial.json --backend rust --integrator verlet
.\.venv\Scripts\python.exe -B -m solar_simulator run initial.json final.json --steps 4000
.\.venv\Scripts\python.exe -B -m solar_simulator inspect final.json
.\.venv\Scripts\python.exe -B -m solar_simulator converge initial.json --steps 4000
```

Сценарии: `sun-earth`, `earth-moon`, `binary-star`, `sun-earth-moon`,
`spheres`, `solar-system`, `solar-system-moon`. Для Солнце–Земля есть `--eccentricity`; физический dt
можно задать через `--dt`. Контактные режимы: `stop`, `bounce`, `merge`.
У астрономических сценариев исходные радиусы нулевые, у `spheres` — 1 м.

## Примеры и выпуск

```powershell
.\.venv\Scripts\python.exe -B examples/sun_earth.py --backend rust --eccentricity 0.6
.\.venv\Scripts\python.exe -B examples/n_body.py --scenario sun-earth-moon --backend rust
.\.venv\Scripts\python.exe -B examples/collisions.py --backend rust
.\.venv\Scripts\python.exe -B scripts/check_app.py
.\.venv\Scripts\python.exe -B scripts/build_portable.py
```

Сборщик создаёт новую папку, ZIP и SHA256 в `dist` с точными версиями
зависимостей и сохранёнными лицензиями. Проверяется изолированный запуск
Python/Tk, нативная физика и приложение. Проверка после распаковки в
другой путь: `python scripts/check_portable.py путь-к-архиву.zip`.

## Модель и ограничения

Все величины в SI. Гравитация точечных масс, Velocity Verlet с фиксированным
шагом или DOP853 с адаптивным шагом и допусками (Python/SciPy, без контактов), попарный алгоритм O(N²). Радиусы используются для контактов;
экранные маркеры имеют условный размер. Отскок гладких сфер сохраняет
импульс и учитывает потери. При слиянии сохраняются масса, импульс,
объём и полный угловой момент, включая пассивный внутренний `spin`.
Скачок разрешённой энергии при смене модели записывается отдельно.

Начальные состояния solar-system и solar-system-moon взяты из JPL; модели точечных тел
не воспроизводит всю физику DE441. Доступен отдельный режим EIH 1PN для слабого поля
и медленных точечных тел без вращения. Нет высших порядков ОТО, приливов, трения, гидродинамики,
разрушения, вращательной динамики и контактных сил для устойчивых или
одновременных контактов. Такие контакты явно отвергаются. Уменьшай dt
при тесных сближениях и проверяй сходимость; графики по снимкам могут
пропускать промежуточные пики. Подробные границы — в руководстве.
