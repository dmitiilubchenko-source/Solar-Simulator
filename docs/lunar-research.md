# Расчёт закреплённого начального вращения Луны

Изменение70, 11 октября2026. Доступна отдельная команда: от pinned x/v и
R/Rdot до совместной инверсии p/S, Earth–Moon Jacobi состояния, интегрирования,
сохранения и продолжения. Модель остаётся conditional-research;
[физическая квалификация](lunar-source-qualification.md) не пройдена.
Рабочий GUI Newton/schema10 не меняется. Это самостоятельный исследовательский
расчёт H57, а не полный PN extended-body или модель приливов.

## Договор

В envelope schema1 сохраняются strict initialreceipt68 и strict relative
checkpoint63. При создании/загрузке/эволюции pinned источник строится заново:
проверяются начальное состояние побитово, I/mass/c, порядок всех десяти тел,
пара Earth3/Moon4, epoch/frame/units, трактовка harmonic x/v и q/S, SHA кода
и исходных данных. `physical_mapping_certified` всегда boolean false.
Raw current q/S/p/X/r не нормируются, не перебустируются и не переинициализируются.
Новые численные controls допускаются явно через `integration`, проверяются
строго и сохраняются; не меняют physicalmodel/initialreceipt.

В отличие от receipt68 envelope содержит интегрируемое состояние. Старые
Cartesian/Jacobi/runtime loaders не принимают весь envelope как свой формат.
Вложенный generic checkpoint можно читать старым researchloader, но тогда
строгая дополнительная связь с initialreceipt обеспечивается только этим API.
Checksum обнаруживает изменение, не удостоверяет автора или историю решения.
Currentstate проверяется по области/типам/геометрии; его принадлежность траектории
не доказывается checksum. Её отдельно проверяют restart и научный аудит71.

Источники проверяются до и после расчёта относительно загруженных модулей.
Возобновление заново выбирает адаптивные шаги: file/state roundtrip побитовый,
но вся resumedtrajectory не обязана совпадать побитово с непрерывной.
Futureorientation/ephemerides в эволюцию не поступают. Остальные тела —
нулевые pointspin. Кольцо и астероиды в данном стенде отсутствуют.

## Запуск из корня проекта

Каждый output должен быть новым путём. Здесь используются имена-примеры;
фактический часовой smoke сохранён в локальной `.tools/rotation69-71`.

```powershell
.venv/Scripts/python.exe -X utf8 -B scripts/run_lunar_research.py init initial.json --purpose conditional-research
.venv/Scripts/python.exe -X utf8 -B scripts/run_lunar_research.py run initial.json final.json --duration-seconds 86400 --samples 33 --trajectory trajectory.npz
.venv/Scripts/python.exe -X utf8 -B scripts/run_lunar_research.py run final.json resumed.json --duration-seconds 86400 --samples 33
.venv/Scripts/python.exe -X utf8 -B scripts/run_lunar_research.py export resumed.json velocity.json
```

Duration — дополнительные секунды SI-similarity/TDB-as-input-coordinate-time.
NPZ хранит точную модельную сетку, raw state и SHA начальной/final записей;
его научное повторное использование требует отдельной проверки grid/state/
representation/source hashes. Velocityexport содержит полную dx/dt из H,
прямую относительную скорость и пространственную скорость ориентации,
не подменяет скорость на p/m и не является import/checkpoint.
Запись эксклюзивная, сохранённые файлы не перезаписываются. Несколько output
не являются одной атомарной транзакцией при сбое диска; целостность каждого
checkpoint проверяет loader. Перед run существующие/совпадающие outputs
отклоняются до расчёта.

## Проверки и код

22новых теста внутри78related passed21.84s. Реальная команда init/run/export
прошла, час/17эпох, без будущих таблиц. Отдельный процесс продолжил половину
часового теста: initial/metadata и первый/последний raw state сохранены побитово;
разность с uninterrupted ниже предварительного1м. Это smoke, не32day аудит.

- [Источник и начальное построение](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_research.py:44),
  [численные controls](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_research.py:60),
  [связь receipt/checkpoint](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_research.py:88).
- [Создание](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_research.py:104),
  [strict envelope](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_research.py:120),
  [эволюция](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_research.py:140),
  [export](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_research.py:146),
  [команда](C:/Users/Admin/Desktop/Solar-simulator/scripts/run_lunar_research.py:16).
- [Побитовый source/file](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research.py:29),
  [семантические подмены](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research.py:43),
  [schema/controls](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research.py:64),
  [source guard](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research.py:79),
  [запрет futureorientation](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research.py:86),
  [process restart](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research.py:96),
  [сохранность outputs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research.py:121).

В71 устранён пропуск spin_initial.py в source manifest receipt68, от которого
зависит и данный API. Исходный часовой smoke70 сохранён как исторический;
новая версия его strict sourcehash отклоняет. Создавайте новое initial,
не заменяйте provenance старого файла. Формулы и rawinitial не изменились.
