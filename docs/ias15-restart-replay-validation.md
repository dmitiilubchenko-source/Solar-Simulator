# Независимое повторение результатов восстановления IAS15

22 октября2026,354. [Валидатор](../scripts/replay_ias15_restart.py) заново
вычисляет все actual-IC метрики353, cold−warm и restarted-oracle диагностику
из [публичного NPZ](ias15-restart-samples.npz) и
[receipt](ias15-restart-validation.json). REBOUND не импортируется и не
исполняется; нет обращения к raw/.tools/сети и пересчёта самих траекторий.

Подтверждены все9случаев/54варианта,324массива и6786physicalcheckpoints.
JSON SHA/биты/masses/time/origin, точные границы и принадлежность выходов
пакетным снимкам проверены. Повторены relative E/L/P, specificorbitalenergy,
поэпоховые ошибки и все сохранённые максимумы. Метаданные счётчиков и времени
проверяются на согласованность; новые measurements из этих файлов не создаются.
Повторы/C force-counter квалифицировались в353, здесь C не выполняется.

Результат faithful replay: **49PASS/5FAIL**, all_checks_passed=false.
Успех целостности не выдаётся за прохождение научного gate.
В частности, намеренная подмена агрегата наtrue отвергается.

[8тестов](../tests/test_ias15_restart_replay.py) PASS5.27с/0skip: копия всех
публичных входов в другом корне без.tools, повреждение источника/NPZ,
partialreceipt, ложныйaggregate/метрика и порча внутреннихphysicalданных
даже после обновления внешнегоNPZ SHA. Подмена state/JSON не скрывается
согласованным обновлением только хеша архива.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.replay_ias15_restart
.venv/Scripts/python.exe -X utf8 -B -m pytest -q tests/test_ias15_restart_replay.py
```

В другом корне использовать `--root <копия проекта>` с закреплёнными
источниками, receipt и архивами. Для вычисления метрик нужна совместимая
Python/NumPy-среда; это не автономный исполняемый файл и не portable-продукт.
Источник SHA не заменяется ради PASS. Старые353код/данные не изменялись.
Runtime/интегратор/допуски/версия/ZIP/main прежние.
