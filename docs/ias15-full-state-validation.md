# IAS15: ограниченный full-state pilot363

Полное binary-восстановление после каждого пакета сохранило численный результат
непрерывного IAS15 на одном заранее выбранном случае `holdout_circular`, с двумя
epsilon. Это исследование сохранения состояния, не новый backend Solar.
Критерии заданы до опыта в [протоколе](ias15-full-state-protocol.md).

## Модель и независимая проверка

Два взаимно притягивающихся Newton point mass, SI, инерциальные трёхмерные
координаты, модельное время от0, без softening/PN/вращения/COM shift. Использованы
точные исходные binary64 IC, массы и независимая Decimal actual-IC аналитика
из353 через `load_cases`; приближённая круговая орбита не заменялась точным кругом.
Интервал63114866.86220014с, packet_dt631148.6686220014с,82выходные эпохи,
131пакет. Это модельная задача, не календарный прогноз DE441/JPL.
Рецепт IAS15: REBOUND5.2.2, basic gravity, PRS23, min_dt0, начальный
dt=packet_dt/200, epsilon1e-9/1e-11, exact_finish_time1.

Старые пороги без изменений: относительное положение <0.1м, скорость <1e-6м/с,
относительные дрейфы E/L и масштабированный дрейф P <1e-10.

| epsilon | warm/full: max Δr, м | warm/full: max Δv, м/с | physical cold: max Δr, м |
|---|---:|---:|---:|
|1e-9|0.003357329786242536|6.588253455129325e-10|0.008132502634329304|
|1e-11|0.003355059343388938|6.558643422188722e-10|0.008132502634329304|

Для warm/full max E drift5.716454937147802e-16, L drift≤1.1338906213339337e-14,
P drift2.2189872695083312e-16. Все старые gates здесь прошли также у cold;
его max Δv1.5908601118081708e-9м/с. Warm и cold побитно совпали с сохранёнными
контролями353; full совпал с warm. Это не исправляет пять старых cold FAIL
на других задачах353/355 и не устанавливает универсальную точность IAS15.

## Что действительно восстановлено

262 committed restore:131×2epsilon. На каждой границе сопоставлены позиции,
скорости, ускорения, массы, G, время, dt/dt_last_done, steps_done, модельные flags
и все17записанных IAS15 fields.13буферов имеют согласованную длину: single6double,
dp7 по42double; фактический `N_allocated=6` проверен в C-state до/после restore.
Между независимо созданными warm/full исключён только неиспользуемый этим
детерминированным basic-моделированием начальный rand_seed; внутри restore
он также обязан сохраниться побитно. CPU walltime и адреса указателей
не участвуют в численной идентичности. Никакие поля не сбрасываются вручную.

Каждый snapshot — новый полный поток общего C-writer, не append/delta chain.
После чистого Python preflight вызываются отдельно archive-create и sim-init
`with_messages`; используется snapshot0 без synchronize/getSimulation/integrate
при чтении. Оба сырых C mask равны0 на всех262принятых восстановлениях.
Python warnings также проверены. C archive handle освобождается ровно одним
владельцем в finally; Python Simulation сохраняет обычное владение своей памятью.
Байты остаются живыми до закрытия memory stream.

Guard создаётся из собственного свежего basic-контроллера, не из входного
sidecar. Проверяет библиотечные68SHA, версию/build header, ABI/layout, origin,
порядок двух позиционных identities/массы, physical JSON, epoch, список/порядок/
длины embedded fields, неизменность модели, конечность чисел и запрет user pointers.
При отказе integration/export/load остаётся предыдущий immutable committed
physical/binary snapshot, новые пакеты после failed latch запрещены.

По56отрицательных проверок для каждого epsilon: неверные provenance/version/
ABI/library/identity/SHA/time/mass; изменения G/N/t/callback flag; отсутствие и
укорочение каждого13буферов; duplicate field; все10C callback slots, включая
pre_timestep_modifications; bits4/128/2048 в каждой C-фазе и RuntimeWarning.
Повреждённые данные не передавались C. Предварительные buffer guards используют
синтетический Python payload, который никогда не загружается C. Warning bits
инъецированы после корректных C-вызовов: это проверка отказа wrapper, не
утверждение, что принятый архив сам вызвал такие предупреждения.

## Стоимость и воспроизведение

Поток до первого шага2875байт; каждый committed полный поток5697байт.
Один qualified paired run, секунды на131пакет:

|epsilon|warm integration|full integration|capture+preflight|read+strict validation|
|---|---:|---:|---:|---:|
|1e-9|0.004723|0.005139|0.065905|0.268784|
|1e-11|0.004502|0.004750|0.064400|0.272015|

Чтение включает повторный export/сравнение. Это единичные инструментированные
измерения; отдельная запись доказательств на диск вне этих интервалов.
Они показывают стоимость строгого Python wrapper, не ускорение метода.
Остальные предварительные прогоны и их raw timings сохранены в.tools/full363;
статистического performance benchmark не проводилось.

Первый guards-only запуск отказал до орбиты: публичный REBOUND setter не
принимает `None` для снятия callback. Исправлена очистка только собственного
тестового C-pointer slot. Первый receipt/исходники сохранены в `guards-first*`.
Затем guards прошли; последующие draft/qualified прогоны дали одинаковые
орбитальные outputs. Самопроверка усилила restore-сравнение rand_seed;
ранние draft outputs/source ZIP сохранены отдельно, старые научные отчёты
не переписывались. Финальный источник и результат закреплены отдельным run.

Публичные [receipt](ias15-full-state-validation.json) и
[28массивов](ias15-full-state-samples.npz):528warm/full streams+physical JSON,
epochs/states/actual-IC oracle и cold-контроль. NPZ SHA256:
`ed3703b0a13a9deb1d95453bcc4b1e981f43f81ed1bb6f1930e7541b0e4c1ae3`.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.replay_ias15_full_state
.venv/Scripts/python.exe -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_ias15_full_state.py
```

Offline replay повторяет аналитику/инварианты, bindings, physical/binary поля,
warm/full и прежние353контроли без REBOUND и без C-load/интегрирования.
Для нового live опыта требуется прежняя локальная pinned библиотека:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_ias15_full_state --library .tools/ias15165/dependency --output .tools/full363/another-new-run.json
```

Это доверенный собственный snapshot, тот же build/64-bit ABI/процесс, ровно
два unnamed point mass. Не формат безопасного чтения произвольных чужих файлов,
не переносимый Solar checkpoint, не испытание нового процесса или callback.
GPL-3.0-or-later REBOUND не встроен в продукт; upstream code/binary не вендорены.
Лицензия/adoption, Rust, runtime,0.3.1 portable и main/теги остаются вне этапа.

Primary source — закреплённый sdist и [source-аудит362](ias15-archive-source-validation.md).
Официальные исходники:
[IAS15 state](https://github.com/hannorein/rebound/blob/5.2.2/src/integrator_ias15.h),
[binary writer/reader](https://github.com/hannorein/rebound/blob/5.2.2/src/binarydata.c),
[archive lifetime](https://github.com/hannorein/rebound/blob/5.2.2/src/simulationarchive.c).
Следующий отдельный этап — все9прежних задач с теми же gates; native callback
и новый процесс требуют отдельных проверок. Только один круговой pilot принят.
