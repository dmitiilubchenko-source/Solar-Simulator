# Надёжность рабочего Solar DOP853: этап376

28 октября2026. База Solar dev83899827c70104299a4e5311d44b870017af8f62,
Research dev0b82e0531151e3f0d52f75f380c905638a3d4ddc; оба дерева чистые до работ.
**Изолированного дефекта физического ядра не найдено.** Добавлены воспроизводимый
headless-набор и проверки packet/file/process continuation. Формулы, интеграторы,
source runtime, native binary, сохранения, версия0.3.2 и исторические evidence
не менялись. Ошибки e=.99 измерены именно у Solar, не перенесены из IAS15.
0.3.2 уже принята вmain; этот этап не выпускает новую portable/версию.

## Реальный путь вычисления

`application_profiles / CLI → Experiment → advance → evolve_accurate → SciPy`
`→ Python Newton/EIH либо Rust point_acceleration → Python figures → Body`.
Ветки с динамическим вращением и контактами выбираются до обычной accuracy.

| Путь | Интегратор и силы | Область/ограничения |
|---|---|---|
| [experiment.advance L142](../src/solar_simulator/experiment.py#L142), [accuracy L17](../src/solar_simulator/accuracy.py#L17) | SciPy DOP853; по умолчанию [PerBodyDOP853 L20](../src/solar_simulator/error_control.py#L20); сохранён global-rms для прежних настроек | Newton или point EIH1PN; fixed J2/prescribed Q2 с обратными ускорениями и учётом работы заданной ориентации. Точки, без контактов |
| [native_forces.prepare L5](../src/solar_simulator/native_forces.py#L5), [PyO3 L188](../rust/solar_native/src/lib.rs#L188), [core force L29](../rust/solar_core/src/relativity.rs#L29) | Rust вычисляет Newton/EIH point accelerations, включая выделенную относительную пару; интегрирует всё ещё SciPy | Фигуры остаются Python. Нет fallback Rust force в Python; отсутствующий/stale native вызывает отказ |
| [rust_backend.evolve L11](../src/solar_simulator/rust_backend.py#L11), [core evolve L85](../rust/solar_core/src/lib.rs#L85) | Рабочий фиксированный Velocity Verlet, Python либо Rust/PyO3/JSON-мост | Newton; отдельные контакты/отскоки/слияния сфер. Нельзя считать его Rust DOP853 |
| [nbody_rotation L142](../src/solar_simulator/nbody_rotation.py#L142) | SciPy RotationDOP853, Newton+одна динамическая фигура Q2, ориентация/угловой момент/обратные моменты | Отдельная ветка Experiment; без EIH, заданных фигур, контактных радиусов/passive spin; собственный контроль ошибки |
| [ContinuousRun L31](../src/solar_simulator/continuous.py#L31) | Тот же SciPy DOP853 с сохранённым в памяти solver; Rust forces/per-body, Newton/EIH, допустимые заданные фигуры | Явно экспериментальный отдельный CLI, SciPy1.18.1; не обычный advance, без контактов/dynamic rotation. Controller buffers не сериализуются |
| [solar_adaptive](../rust/solar_adaptive/README.md) | Исследовательский Rust DOP853; generic ODE и поставляемый NewtonRun | Не подключён к Experiment/PyO3 runtime. В Newton adapter light_speed=None; исходные численные FAIL сохранены |
| [IAS15 reference](../scripts/ias15_reference.py#L47), [EIH research](../scripts/ias15_eih.py#L21) | Только исследовательские адаптеры REBOUND: Newton и отдельный полный native EIH callback | Не backend приложения. Начальный analytic adapter ограничен двумя Newton точками; EIH adapter явно без фигур/вращений/контактов. Solar-Research e=.99 изучал Newton два тела |

Обычный advance каждый раз создаёт новый solve_ivp на локальном [0,duration]
в движущемся COM frame; optional relative pair уменьшает масштаб внутренней
координаты. dt*steps задаёт границу пакета, не внутренний шаг DOP853.
Имена тел не входят в формулу, кроме явного выбора пары/figure через настройки.
rtol/atol — локальный контроль, не глобальный допуск; нижний rtol3e-14.
Проверено и потенциальное ложное «нулевое уточнение»: compare_tolerances
явно отказывает, если на floor получаются менее трёх разных rtol.

Текущая [квалификация375](current-runtime-375-validation.md) относится к
конкретным10 телам, эпохе/оси/модели EIH+J2, Strict/packet recipe и native/env.
Её JPL остатки не являются ошибками относительно двухтельного решения.

## Переносимость наблюдений Solar-Research

Локально прочитаны mechanism99-offline-report и all8/audit-summary с проверкой
их manifest SHA. Приватные research raw, исходники и массивы сюда не копировались.
Таблица оценивает методологическую применимость; не присваивает IAS15 FAIL Solar.

| Результат Research | Применимость к Solar | Что уже есть | Доказанный дефект? | Дополнительная проверка | Приоритет |
|---|---|---|---|---|---|
| Ненулевая clock component accepted IAS15 edges | Только общий вопрос арифметики времени; локальные часы SciPy/packet API другие | time_control._interval отклоняет недостижимые границы; tests/test_time_control.py | Нет. Наш первый отказ — ошибка sampling grid, защита runtime уже работала | Регистрировать requested/actual durations; при необходимости отдельный bounded trace SciPy, не переносить IAS decomposition | P1/часть выполнена |
| Крупный propagated incoming error | Начальное состояние каждого нового solve_ivp уже содержит накопленный численный остаток | Current375: same-packet file continuation; tests/test_accuracy.py | Нет. Это математическое свойство propagation, не причина конкретной ошибки | Same-packet bitwise file/process continuation, выполнено здесь | P1 |
| Уменьшение IAS15 epsilon не обязано улучшать global max | Методологическая осторожность применима к rtol; EPS и rtol не эквивалентны | assess_accuracy, compare_tolerances, независимые375 Strict20/Strict10 | Нет | Сопоставить rtol Solar с собственной аналитикой; выполнены16 пар | P1 |
| Endpoint PASS не ограничивает промежуточные ошибки | Любой sampled observer, включая Solar |125 годовых epochs,9 holdout; отдельные high-e continuous audits | Нет обещания continuous bound в текущем контракте | Заранее плотнее поставить packet snapshots около обоих перицентров; выполнено, но49 точек не bound | P1 |
| CE/CD, cold reset и адаптивная история меняют результат | Нельзя переносить рецепты IAS15. Обычный DOP853 reset происходит на каждом advance | Обычный checkpoint хранит физическое состояние/настройки; continuous — другой контракт | Нет доказанной потери состояния | Сравнить одинаковые recipe и отдельно другую пакетизацию; выполнено | P1 |
| Force/update roundoff residuals не измеряют global причинный вклад | Требуется проверить именно Solar Newton/EIH и его арифметику | test_native_forces: независимый scalar EIH, Python, pair override; старые kepler force/roundoff/holdout audits | Нет | Не внедрять carry/sumprod/max_step по IAS15 данным. Изолированный контраст нужен только под конкретную гипотезу Solar | P2 |
| Resource monitor потерял метрики на KeyboardInterrupt | Относилось к исследовательскому monitor, не доказательство ошибки product recovery | controlled-stop/run-until/recovery и отдельные product tests | Не выявлен новый product дефект | Не переносить исследовательскую инфраструктуру в runtime; для этого набора reused local guard | P2 |

## Заранее фиксированный набор и сохранённые неуспехи

[Исходный план](../scripts/runtime-reliability-376-protocol.json) SHA163da489…
и [его exact source](../scripts/validation/runtime376-before-grid.py.txt) сохранены.
Первый проход:0 complete jobs,4 аналитических reference; target на четвёртой
границе первого case был на1ULP недостижим. previous=31557.43343110007s,
target=315574.3343110007s, dt=284016.90087990067s;
previous+dt=315574.33431100077s, разница5.820766091346741e-11s.
advance_towards отклоняет это до solver; проверено отрицательным тестом.
Это недостаток нового стенда, не исправление физики и не замаскированный FAIL.

[Планv2](../scripts/runtime-reliability-376-protocol-v2.json)
SHAfa3bda4d8d32df11a2cc2f83a6df4ed187dd4d9e6ec163c602c6e6cc509c117e
создан до нового запуска. Все49 точек сохранены: правило nearest2^-20s
даёт точную двоичную решётку; на этом горизонте менее2^45 ticks, разности и
суммы представимы точно. Сдвиг каждой requested epoch ≤2^-21s, не подгонялся
по ошибкам. Requested/actual/hex записаны. Оригинальный FAIL не переписан.

Сценарии: e=.5/.95 с начальным E=0; e=.99 с E=0 иpi. Повторно использован
holdout_fixture, наклонная плоскость, COM offset/drift; IC сохранены binary64.
Newton точечные массы в SI, отсчёт времени0. Один номинальный период,
конец приведён к объявленной двоичной решётке. Нет JPL/PN/figures/contact.
G и массы фиксированы как реальные исходные binary64 значения.
Главный эталон: exact subtraction исходных IC и exact(G)*(exact(mA)+exact(mB)),
аналитический Decimal f/g70/100, без production RHS или solve_ivp.
Максимальное различие уровней <4.85e-60m/<9.38e-65m/s — арифметическое
согласие эталона, не физическая точность симуляции.

32 grid jobs:4 IC×Python/Rust×rtol1e-13/3e-14×absolute/relative variables.
Здесь названия standard/strict обозначают только rtol, а не полную солнечную
EIH+J2 квалификацию. Atol1e-3m/1e-9m/s, per-body. Ещё4 high99 strict-relative
single-packet controls. В8 strict-relative grid jobs — file/save/load и тот же
suffix. Measurement epochs являются границами пакетов, это часть численного recipe.
Бюджет180CPU/360active wall s,1GiB private,64MiB артефактов задан до запуска.

## Измерения

Все36 jobs complete; умеренный case проходит прежние100m/1e-3m/s/energy1e-10
во всех8 вариантах. Для high-e новые runtime accuracy gates не назначались.
Ниже strict-relative subset; все абсолютные/standard/контрольные варианты
доступны в [JSON](runtime-reliability-376-validation.json) и
[исходных массивах](../scripts/validation/runtime-reliability-376.npz).

| e / начало | backend | max r,m | max v,m/s | max relative energy drift |
|---|---|---:|---:|---:|
|.5 / peri|Python|0.135418|6.11805e-8|2.67474e-14|
|.5 / peri|Rust|0.137642|6.22281e-8|2.85462e-14|
|.95 / peri|Python|3.67831|4.69068e-5|2.54737e-13|
|.95 / peri|Rust|3.94335|5.02864e-5|2.68874e-13|
|.99 / peri|Python|39.3522|5.55418e-3|1.27430e-12|
|.99 / peri|Rust|37.5339|5.29755e-3|1.24078e-12|
|.99 / apo|Python|0.0275927|2.31002e-6|8.94321e-13|
|.99 / apo|Rust|0.0256827|1.92204e-6|8.07782e-13|

По всем8 grid вариантам диапазоны r/v: .5 —0.1024..0.2110m/
4.615e-8..9.529e-8m/s; .95 —2.990..9.870m/3.813e-5..1.259e-4m/s;
.99-peri —31.50..108.07m/4.446e-3..1.525e-2m/s;
.99-apo —0.02568..0.99412m/9.229e-7..4.398e-6m/s.
Все16 matched rtol-пар улучшились при строгом допуске. Это ограниченное
свидетельство чувствительности/сходимости, не универсальный порядок или bound.
Relative coordinates не обязаны давать лучший результат в любом двухтельном case.

В high99-peri r/v maxima этой сетки достигаются в конце периода; high99-apo
velocity maximum — около0.5P, position maximum — в конце. Низкий drift E
не ограничивает фазовую/позиционную ошибку: именно это наблюдается здесь.
Утверждать, что причиной является только фаза, roundoff или reset, пока нельзя.

Сравнение **одинаковой конечной эпохи**, не максимумов разных сеток:
high99-peri Python grid39.3522m/0.00555418m/s против onepacket37.2464m/
0.00525697m/s; Rust37.5339m/0.00529755m/s против33.3858m/0.00471208m/s.
High99-apo endpoint r Python0.02759m против0.04244m, Rust0.02568m против0.13126m.
Следовательно, packetization влияет на численный путь; onepacket не универсально
лучше. Это не ошибка save/load:8 same-packet suffix совпали точно по документам.
Ещё2 Python/native проверки сделали то же продолжение в новом процессе точно.
Адаптивные буферы не сериализовались и новые рецепты IAS15 не применялись.

## Независимая проверка, стоимость и ограничения

[Fraction observer L38](../scripts/assess_runtime_reliability376.py#L38) независимо
пересчитал r/v/E/L/P из1576 raw state observations; не доверяет flags PASS.
Точные Fraction kinetic/momenta +Decimal120 distance сверены с Decimal130
основным observer на всех эпохах. Отдельные тесты портят metric и массив при
прежних успешных flags и требуют отказа. Оба reader разделяют Newton physics,
IC/G и сохранённый аналитический эталон; это не два независимых IVP solver.
COM identities вычисляются обоими, но tiny cancellation floors120/130 не
сравниваются побитно. Первоначальный новый unit fixture также сохранил FAIL:
нормированная скорость с SI G давала unbound energy; исправлен до protocol run.

Два измерительных attempts вместе с надзором:53.875CPU s,46.9234active wall s;
peak sampled private tree133300224bytes (~127.13MiB). Для завершённого attempt
worker29.4531CPU s и supervision6.640625s. Последовательные одиночные timings
не являются стабильным benchmark backend. Финальные проверки/pytest отдельно:
130PASS/11.09s с обязательным настоящим native, безskip;4 convergence PASS/0.99s;
19 Rust core PASS, обе cargo fmt PASS. Большая повторная годовая квалификация,
полная desktop/portable приёмка и REBOUND integrations не запускались.
Старые375 positive/source/accepted032 guards входят в относящийся набор и PASS.
Новые12 обычных регрессий включены в desktop CI selection;2 source-bound
evidence tests оставлены отдельно от portable контрактов.
Python CI subset:566PASS/4 штатныхdeselected/9.76s; это отдельная проверка,
не полная новая source/desktop/ZIP приёмка. Дубликаты между наборами не суммируются.

Повторить на этом source/native/environment, с новым output:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_runtime_reliability376 verify
.venv/Scripts/python.exe -X utf8 -B -m scripts.check_runtime_reliability376 run --output .tools/runtime376-new/data
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_runtime_reliability.py tests/test_runtime_reliability_evidence.py -p scripts.native_audit
```

Другая версия/бинарник требует нового явного source/environment plan; текущие
SHA нельзя подменять ради воспроизведения. Эти данные не меняют JPL-критерии375
и не квалифицируют другой CPU/OS/native, continuous режим или все sandbox IC.

Источники: [SciPy1.18.1 DOP853 и controller](https://raw.githubusercontent.com/scipy/scipy/v1.18.1/scipy/integrate/_ivp/rk.py),
[Orekit elliptic Cartesian f/g](https://raw.githubusercontent.com/CS-SI/Orekit/develop/src/main/java/org/orekit/orbits/KeplerianMotionCartesianUtility.java),
[NASA PROP2B](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/FORTRAN/spicelib/prop2b.html).
Последний описывает central/massless постановку; наша относительная задача
двух конечных масс имеет mu=G*(mA+mB), не G*mA. Чужой solver не исполнялся.

## Классификация и три направления разработки

| Категория | Вывод |
|---|---|
|1. Дефект runtime реализации|Не изолирован. Нет основания менять ядро или открывать ветку физического исправления |
|2. Численное ограничение|Измерена конечная точность текущего DOP853/float64/config у high-e; её нельзя заменить малым локальным rtol или energy drift |
|3. Измерительный стенд/документация|Исходная grid не была representable; unit fixture смешивал нормирование/SI; оба FAIL сохранены. В docs/README также устарел принятый номер0.3.1 — исправлен на фактическую0.3.2 |
|4. Физическая модель|Newton isolated two-body не реальная Солнечная система. Этот audit не измерял недостающие эффекты или новые JPL остатки |
|5. Гипотезы|Причинные вклады force/update roundoff, adaptive history, packet reset и phase пока не разделены. Совпадение backends не доказывает отсутствие общей ошибки |

| Направление | Минимальный следующий шаг и польза | Сложность/риск | Критерий завершения |
|---|---|---|---|
|Научная достоверность — P1|Отдельно объявить4 short high99 controls (оба начала/оба backend) с неизменными IC/output epochs и чувствительностью к internal max_step; переиспользовать existing kepler step audit, адаптируя именно cold runtime. Уточнить механизм перед изменением production |Средняя; более мелкий шаг может усилить roundoff. Не внедрять cap/carry автоматически |Все исходные outputs сохранены, проверен independent reference/holdout, показаны r/v/E/L/P и RHS/CPU до/после; эффект воспроизводится на обеих фазах либо признан неуниверсальным |
|Вычисления и восстановление — P1|Закрепить recipe как обязательную часть объяснения replay/resume; выполнить failure/interrupt/atomic-save сценарии для обычного GUI/CLI по существующим recovery tests и уточнить поддерживаемые native/env перед0.3.3 |Низкая/средняя; нельзя молча дробить пакеты или переносить чужой qualification SHA |Последняя committed boundary сохраняется после injected failure; same-recipe/new-process результат точен; изменённая пакетизация явно другая; native/env qualification не ослаблена |
|Пользовательская полезность — P2|Дать понятный headless/CLI отчёт модели, численного recipe и области проверенной точности, используя существующие diagnostics/recipe; отдельно показывать numerical sensitivity и JPL residual |Низкая/средняя; риск ложной универсальной оценки «точности» |Исходный Solar preset, изменённая масса и high-e пример показывают корректные units/model/пакеты и статус sampled/unqualified; никакой автоматической гарантии по одному rtol |

Оптимизация, новая физика, новый интегратор, научная статья и расширение
Research не выполнялись. Сначала нужна диагностика конкретной причины,
потом небольшой failing regression и отдельная ветка исправления. Версии,
main/теги и portable этим этапом не меняются.
