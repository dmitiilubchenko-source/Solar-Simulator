# IAS15 full-state: девять случаев, этап364

24 октября2026. Basic full-state восстановление прошло18/18вариантов
на девяти прежних actual-IC задачах с двумя epsilon. После каждого из2244
пакетов восстановленное состояние совпало побитно с непрерывным warm IAS15.
Все прежние независимые analytic/E-L-P gates выполнены. Это расширение
исследовательского pilot363; desktop-программа остаётся0.3.1.

## Условия и критерии до опыта

[Протокол364](ias15-full-suite-protocol.md) закреплён до расширенного расчёта.
Использованы неизменные guard/transaction/paired363 и входы/oracle353,
а не новые IC, подобранные под результат. Источники, входы и68файлов
локальной REBOUND5.2.2 проверены по SHA до/после; версии не обновлялись.

Два ньютоновских point mass:
`a_i = G*m_j*(r_j-r_i)/|r_j-r_i|^3`, без других сил. SI, инерциальные3D,
модельное время от0; без softening, вращения, COM shift, столкновений и PN.
Интервал63114866.86220014с, packet_dt631148.6686220014с; прежние82эпохи
для holdout и60для original. Модельные оси и время не являются новым
календарным прогнозом Солнечной системы или сравнением с DE441.

IAS15 basic: epsilon1e-9/1e-11, PRS23, min_dt0, initial dt=packet_dt/200,
exact_finish_time1. Три режима: warm; полный binary restore каждого пакета;
старый physical JSON cold reset каждого пакета. Восстановление не вызывает
синхронизацию/интегрирование и не сбрасывает predictor/compensation поля.

Независимая Decimal100 analytic solution строится из actual binary64 IC;
неопределённость проверенного oracle <1e-6м/<1e-12м/с. Пороги прежние:
max относительного Δr<0.1м, Δv<1e-6м/с, относительные E/L и масштабированный
P drift<1e-10. Сохранение энергии не заменяет позиционную проверку.

## Результаты и оставшиеся отказы

Во всех строках full совпал с warm на пакетах и выходных эпохах.
Ошибки относительно независимой аналитики, метры; cold PASS из двух epsilon:

| Случай | full Δr при1e-9 | full Δr при1e-11 | cold PASS |
|---|---:|---:|---:|
|holdout_circular|0.003357330|0.003355059|2/2|
|holdout_moderate|0.006905549|0.001041432|2/2|
|holdout_original|0.038349077|0.024611350|0/2|
|holdout_permuted|0.026387460|0.023632015|1/2|
|holdout_apocentre|0.005648294|0.023494864|1/2|
|holdout_eccentric_phase|0.002860117|0.001930046|2/2|
|original_0.0|0.002977959|0.003021094|2/2|
|original_0.5|0.002493734|0.002923671|2/2|
|original_0.95|0.048780063|0.019756758|1/2|

Максимумы warm/full: Δr0.04878006332681836м и Δv6.220927669558766e-7м/с
на original_0.95/1e-9; E drift6.097551932957584e-15,
L drift2.972100414730003e-14, P drift2.2189872695083312e-16.
Уменьшение epsilon не всегда уменьшает измеренную глобальную ошибку;
таблица не используется для выбора удобного допуска задним числом.

Cold остался13/18PASS: holdout_original при обоих epsilon,
holdout_permuted/1e-9, holdout_apocentre/1e-11 и original_0.95/1e-9
не прошли старые gates. Cold maxΔr0.2516367285839349м,
maxΔv3.209095625698026e-6м/с. Все warm/cold outputs побитовые353,
список пяти отказов также совпал. Старые353/355FAIL не переписаны.
Full сохраняет прежний warm-результат; сам алгоритм интегрирования
или его непрерывная точность от этого не улучшились.

## Что проверено в сохранении

2244full restore,4524архивных warm/full snapshot с начальными состояниями,
252массива. На каждой границе и внутри C-load проверены17IAS15fields,
длины13буферов/фактический N_allocated6, x/v/a/masses, G, время,
dt/dt_last_done, steps_done и остальные сериализуемые модельные fields.
Walltime/pointer addresses исключены; rand_seed сохраняется внутри restore,
его независимые начальные значения исключаются только между контролями.

У каждого принятого orbital restore два raw C mask=0. До каждой траектории
выполнены56guard checks, всего1008: provenance/version/ABI/library, массы/
порядок/время, SHA/framing/model, missing/short каждого буфера, duplicate field,
все10callbackslots, инъецированные warning bits4/128/2048 в обе C-фазы и
RuntimeWarning. Повреждённые payloads не передавались небезопасному C-reader.
Инъекции warnings — проверка отказа wrapper, не предупреждения принятых данных.

Отдельный unit-тест инъецировал serialization exception на каждом из18
синтетических вариантов: остальные попытки продолжились, source ZIP/NPZ/
JSON и18last-committed markers сохранились, aggregate completed0/full gateFalse.
Это тест оркестрации без C и без орбиты, не научные данные.
Реальные расширенные прогоны завершились без новых исключений.

## Стоимость, артефакты, воспроизведение

Raw полный поток:2875байт до первого шага,5697байт на committed границе.
Qualified run, суммарно на18вариантов, секунды:

| Измеренная часть | Секунды |
|---|---:|
|warm integration|0.1301415|
|full integration|0.1400593|
|capture + preflight|1.7859454|
|read + strict re-export validation|7.5325147|
|весь цикл до финального NPZ packaging|25.9866687|

Последняя строка включает запись пакетов, guards, cold/analytic checks и
проверку bindings. Read уже включает строгую проверку через повторный export.
Это инструментированные единичные измерения; wrapper/сохранение дороже
самого интегрирования. Performance benchmark и оптимизация не проводились.
Предварительный run занял29.4825795с до packaging; все54орбитальных output
массива warm/full/cold побитовые между первым и qualified run.

Первый run/source ZIP/все packet files оставлены в.tools/full364/suite-first*.
После него усилена проверка отчёта/размеров/стоимости и добавлен тест
исключений оркестрации; финальный run имеет отдельные новые source bindings
и артефакты suite-qualified*. Никакие старые receipt не исправлялись ради PASS.

Публичные [receipt](ias15-full-suite-validation.json) и
[252массива](ias15-full-suite-samples.npz), NPZ18296282байта,
SHA256 `cd6e03644b649cb390f2bea5361e9b480e7d3bf309bbc82f95ebf3aec4965155`.
Хранят все warm/full streams и physical JSON, cold checkpoints, epochs,
states и actual-IC oracle. Это экспериментальные доказательства, не готовый
поддерживаемый формат сохранения пользовательских опытов.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.replay_ias15_full_suite
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_ias15_full_suite.py
```

Offline replay проверяет source/input/array SHA, все cases/epsilon/массивы,
модель/physical/binary поля, аналитику/инварианты, размер и сохранённые cold
FAIL без REBOUND, C-load и нового интегрирования. В обычной Python CI идут
двадцать быстрых negative/unit checks; полный252-array replay выполняется
целевым тестом и включён в adaptive research suite.

Новый live опыт с прежней отдельно установленной pinned библиотекой:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_ias15_full_suite --library .tools/ias15165/dependency --output .tools/full364/another-new-run.json
```

Primary writer/reader/lifetime и ограничения описаны в
[source-аудите362](ias15-archive-source-validation.md) и [pilot363](ias15-full-state-validation.md).
Новая версия REBOUND не загружалась, upstream code/binary не вендорены.
Результат относится к двум point mass, заданным IC/эпохам, trusted same-build
64-bit ABI/process/basic без callbacks. Новому процессу, native силам,
другому компьютеру/ABI и общей модели песочницы нужна отдельная проверка.
Лицензия/adoption, standalone Rust integrator и версия0.3.2 не приняты;
runtime/данные/допуски/portable0.3.1/main/теги сохранены.
