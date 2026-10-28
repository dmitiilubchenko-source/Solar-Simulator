# Dynamic max_step379: результат и инженерное решение

План датирован28 октября2026; завершение29 октября2026.

**NO-GO для внедрения d32.** Peri-start r/v улучшились, но apo-start максимум положения и конечная скорость ухудшились в обоих backend. Production не менялся; другие d не запускались.

Условия: exact IC/G/masses/relative A/B/49epochs/48cold packets/один период376; Newton3D, per-body DOP853, rtol3e-14, atol1e-3m/1e-9m/s. Один заранее выбранный d32, без изменения арифметики или фазы. Это sampled numerical error B−A, не JPL residual.

[Immutable protocol](runtime-step-379-protocol.md), [plan](../scripts/runtime-step-379-plan.json), [machine report](runtime-step-379-validation.json), [compact states/steps/trials](../scripts/validation/runtime-step-379.npz).

## Положение и скорость на одинаковых49 эпохах

Исследования157–160 уже отказали uniform caps и показали немонотонность
dynamic caps; sum/carry кандидаты не прошли весь holdout. Поэтому они не стали
production. Старый опыт e=.95 использовал ContinuousRun/2P/60epochs и иные
atol; его метры не являются baseline этого cold-runtime опыта e=.99. Оттуда
взяты лишь обоснование лёгкого d32 и предостережение от выбора одного успеха.
Подробности сохранены в [отчёте156–164](kepler-phase-validation.md).

| Начало / backend | max r baseline→d32, m | max v baseline→d32, m/s | r ratio | v ratio |
|---|---:|---:|---:|---:|
| high99-peri / python | 39.352175 → 3.7834347 | 0.0055541825 → 0.00053399447 | 0.096143 | 0.0961428 |
| high99-peri / rust | 37.533916 → 2.8937109 | 0.0052975534 → 0.00040842141 | 0.0770959 | 0.0770962 |
| high99-apo / python | 0.027592652 → 0.17821494 | 2.3100188e-06 → 4.9852287e-07 | 6.45878 | 0.215809 |
| high99-apo / rust | 0.025682652 → 0.10324551 | 1.9220371e-06 → 5.0400634e-07 | 4.02005 | 0.262225 |

Для peri-start оба максимума в конце периода (индекс48). Для apo-start максимум скорости около середины периода (индекс24), максимум положения — в конце. Фиксированные окна до результатов: t/P<=.01 или>=.99 для peri; |t/P−.5|<=.01 для apo.

## Перицентр и конец периода

| Начало / backend | peri r, m | peri v, m/s | endpoint r, m | endpoint v, m/s |
|---|---:|---:|---:|---:|
| high99-peri / python | 39.35218 → 3.783435 | 0.005554183 → 0.0005339945 | 39.35218 → 3.783435 | 0.005554183 → 0.0005339945 |
| high99-peri / rust | 37.53392 → 2.893711 | 0.005297553 → 0.0004084214 | 37.53392 → 2.893711 | 0.005297553 → 0.0004084214 |
| high99-apo / python | 0.01637519 → 0.003536885 | 2.310019e-06 → 4.985229e-07 | 0.02759265 → 0.1782149 | 3.288506e-09 → 2.086758e-08 |
| high99-apo / rust | 0.01362415 → 0.003580171 | 1.922037e-06 → 5.040063e-07 | 0.02568265 → 0.1032455 | 3.052771e-09 → 1.209841e-08 |

У apo-start near-peri r/v улучшаются, но конечная позиционная ошибка возрастает в6.46x/4.02x, конечная ошибка скорости — также. Следовательно, локальный выигрыш не гарантирует более точную орбиту на всей заданной сетке. Дополнительные эпохи или новые caps для выбора лучшего результата не добавлялись.

## Инварианты и стоимость

| Начало / backend / режим | max ΔE/|E0| | max ||ΔL||/||L0|| | max ||ΔP||/(M V*) | RHS | accepted/rejected trials | CPU/wall integration, s |
|---|---:|---:|---:|---:|---:|---:|
| high99-peri / python / disabled | 1.2743e-12 | 2.81075e-13 | 3.5607e-18 | 7860 | 629/6 | 0.656250/0.671117 |
| high99-peri / rust / disabled | 1.24078e-12 | 2.17923e-13 | 2.86915e-18 | 7860 | 630/5 | 0.343750/0.418182 |
| high99-apo / python / disabled | 8.94321e-13 | 9.64868e-14 | 1.58604e-18 | 7848 | 629/5 | 0.593750/0.635961 |
| high99-apo / rust / disabled | 8.07782e-13 | 9.68907e-14 | 1.49569e-18 | 7848 | 629/5 | 0.390625/0.430668 |
| high99-peri / python / dynamic32 | 3.77542e-13 | 1.4087e-13 | 1.95449e-18 | 8568 | 694/0 | 0.703125/0.738198 |
| high99-peri / rust / dynamic32 | 1.45426e-13 | 1.40648e-13 | 1.93242e-18 | 8592 | 696/0 | 0.515625/0.554938 |
| high99-apo / python / dynamic32 | 3.89851e-13 | 1.04275e-13 | 1.90927e-18 | 8568 | 694/0 | 0.703125/0.723984 |
| high99-apo / rust / dynamic32 | 2.44055e-13 | 1.19549e-13 | 1.57693e-18 | 8592 | 696/0 | 0.421875/0.452165 |

E/L/P — полные инерциальные величины с исходным COM/drift, как376, не только внутренняя орбита. Нормировки не менялись. Energy drift уменьшился во всех случаях, хотя apo-start position worsens; L/P у apo могут ухудшаться. Это самостоятельные наблюдения, не доказательство r/v точности.

RHS вырос на9.0–9.5%, CPU ratios1.07–1.50. Это один замер с одинаковой instrumentation и IO в обоих вариантах, не устойчивый benchmark. nfev включает2 начальных RHS +12 на попытку +3 dense stages на каждый endpoint. Rejection counts получены через неизменный error norm и сверены с SciPy-ветвлением norm>=1, не из выдуманного внутреннего счётчика.

## Независимость и интерпретация

- Все4 disabled arrays byte-for-byte совпали с376 до первого capped job. Отключённый subclass также совпал с оригиналом в синтетическом preflight по y/t/nfev и наследует те же коэффициенты.
- Decimal f/g70/100 повторил все сохранённые reference values376. Другой mpmath orbital-basis evaluator80/110 проверил98epochs: максимальный gap с Decimal <4e-90m/<8e-95m/s, precision convergence <8e-64m/<8e-70m/s. Эти цифры описывают согласованность аналитики, не точность DOP853 или реальных планет.
- Fraction/Decimal120 пересчитал r/v/E/L/P всех392states; метрики, maxima indices, peri/endpoint проверены, готовые PASS flags не использовались. Весь step/trial trace и nfev проверены независимо, включая полное сохранение48packet boundaries.
- Cap действительно действует на внутренних шагах: около157s minimum и440607s maximum по текущему относительному состоянию. В SciPy менялся только max_step; force/coefficient/norm/controller formulas не менялись.
- Post-hoc trace localization (не causal test): initial-proposal cap binds286–288 раз, из них156–157 в заданном peri window и130–132 вне него. Terminal boundary clipping отделено по local clock/ULP; простой proposed>cap сам по себе не означает изменения terminal step.
- Меняется адаптивная сетка; следовательно меняются truncation/roundoff history и входная ошибка последующих cold packets. Их единственные вклады этим контрастом не изолированы. Нельзя объявлять причиной только перицентр, roundoff или reset.
- Нет повторной capped-траектории в новом процессе: измерение каждого cap-case однократное. Артефакты и offline metrics воспроизводимы, baseline integration воспроизведён; универсальная reproducibility cap-mode не аттестована.

## Ресурсы и ограничения измерения

Основной worker + независимый observer + надзор:21.3125CPU s,19.0411active wall s при120/300. Самый высокий sampled worker private126193664bytes (~120.35MiB), parent private на завершении20377600bytes (~19.43MiB). 50ms sampling может пропустить короткий memory spike; stop не является OS CPU quota. Использованы ранние110CPU/280wall/900MiB/56MiB thresholds.

Private peak каждого case отдельно не измерялся: общий sampled peak не выдаётся за восемь индивидуальных значений. Сохранены per-case CPU/wall/RHS и step/trial arrays. Ради одной детализации памяти новые орбиты не повторяли. Полный рабочий каталог при завершенииguard3.22MB, compact public arrays399139bytes; raw journals/source snapshot остаются локально.

Эта стоимость относится к guarded scientific workers/observer/supervision; подготовка, regression tests и форматирование отчёта отдельно. Никаких новых физических моделей, IAS15, scientific matrix, JPL/year runs или manuscript.

## Решение и следующий полезный шаг

Оба peri-start дают однонаправленный выигрыш в Python/Rust, но необходимый заранее заданный screen выполнен только2/4: apo-start положение и endpoint скорость хуже. **Внедрение NO-GO; перебор d завершён на единственном заданном значении.** Меньший drift E не отменяет отказ.

Если к cap когда-либо вернутся по новой практической причине, обязательны заранее заданные другие IC/фазы/горизонты, многотельный/EIH профиль, повторяемость/lifecycle, поддерживаемые SciPy/native среды и проверка по плотной независимой сетке. Это условия возможного внедрения, не автоматически открытая программа исследований.

Следующий непосредственно полезный шаг — показать уже готовую диагностику377–378 в существующем интерфейсе одной read-only командой/кнопкой: модель, допуски, проверенная запись и честный статус совместимости, без повторного расчёта. Затем готовить кандидата0.3.3 с нужной desktop/native/portable приёмкой. Новую физику и cap автоматически не добавлять.

## SHA и программные проверки

Plan SHA256 `5a9997c7ac80fc8e2d98823637ec1979201e9aa70bf63c11283f9ba48001704a`; arrays SHA256 `ea924c201d8eec744a575dea6bc605051790e19fa2a57c360225599437c8118b`. Полные execution/source/input SHA, версии и ресурсы — в plan/JSON. Base941eda3; Python3.14.2 free-threaded, SciPy1.18.1/NumPy2.5.1; observer Python3.14.2/mpmath1.4.1. Native0.3.2 SHA `0cbc389f139854628f287c04a7cea52c530a18294c2c3a0670faa48bf53c0601` прежний.

До science:44preflight testsPASS,10guard fault testsPASS, independent oracle self-test2epochs/3negative controlsPASS. После science:59related/native regression PASS/6.53s,0skip; PythonCI626PASS/4прежнихdeselect/33.01s; наборы пересекаются. Проверены46relative navigation targets и1402existingfile/line links. Исторические evidence/пороги376 и production source не изменены.

Плотные NumPy step/trial buffers после загрузки (байты, **не private peak процесса**):

| Начало/backend | baseline bytes | d32 bytes | дополнительный buffer |
|---|---:|---:|---:|
| high99-peri__python__strict__relative | 85736 | 94384 | 8648 |
| high99-peri__rust__strict__relative | 85840 | 94656 | 8816 |
| high99-apo__python__strict__relative | 85704 | 94384 | 8680 |
| high99-apo__rust__strict__relative | 85704 | 94656 | 8952 |
