# Solar Simulator 0.2

Настольная лаборатория ньютоновской гравитации на Python и Rust:
взаимное движение N тел в 3D, проекции XY/XZ/YZ, траектории,
диагностика, контакты сфер, отскоки, слияния и контрольные точки.

## Запуск

Открой `Запустить.cmd` или выполни из каталога проекта:

```powershell
.\.venv\Scripts\python.exe -B -m solar_simulator gui
```

Готовая переносимая Windows-сборка находится в `dist`: распакуй ZIP
и открой `Solar Simulator.cmd`. В ней собственные Python/Tk и библиотеки.

[Полное руководство](docs/user-guide.md) — управление, физические
допущения, сохранение, выбор шага, CLI и сборка.
[Формулы и проверки](docs/physics.md), [Rust](docs/rust.md).

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
.\.venv\Scripts\python.exe -B -m solar_simulator new sun-earth initial.json --backend rust
.\.venv\Scripts\python.exe -B -m solar_simulator run initial.json final.json --steps 4000
.\.venv\Scripts\python.exe -B -m solar_simulator inspect final.json
.\.venv\Scripts\python.exe -B -m solar_simulator converge initial.json --steps 4000
```

Сценарии: `sun-earth`, `earth-moon`, `binary-star`, `sun-earth-moon`,
`spheres`. Для Солнце–Земля есть `--eccentricity`; физический dt
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
шагом, попарный алгоритм O(N²). Радиусы используются для контактов;
экранные маркеры имеют условный размер. Отскок гладких сфер сохраняет
импульс и учитывает потери. При слиянии сохраняются масса, импульс,
объём и полный угловой момент, включая пассивный внутренний `spin`.
Скачок разрешённой энергии при смене модели записывается отдельно.

Нет реальных эфемерид, относительности, приливов, трения, гидродинамики,
разрушения, вращательной динамики и контактных сил для устойчивых или
одновременных контактов. Такие контакты явно отвергаются. Уменьшай dt
при тесных сближениях и проверяй сходимость; графики по снимкам могут
пропускать промежуточные пики. Подробные границы — в руководстве.
