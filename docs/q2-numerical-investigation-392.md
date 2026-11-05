# Две Q2: численные FAIL и стоимость вычислений — этап 392

5 ноября 2026. **Ограниченный диагностический этап выполнен; установление
единственной первопричины трёх FAIL остаётся UNRESOLVED.** Подтверждённого
дефекта production не найдено. Нельзя объявить расследование всех гипотез
завершённым или объяснить всё исключительно float64.

[Машинный отчёт](q2-numerical-investigation-392.json) содержит все четыре
сравнения, компоненты/тела/эпохи/векторы, reference, counters и профиль.
Исходные [380](two-q2-380.md), [386](two-q2-scope-386.md) и их FAIL неизменны.

## Исходники, данные и вычислительные пути

Dev/origin перед работой `399909c9e6ccfdc1c850845bd357f1dda30a0ff3` был чистым.
Кандидат `fe0f456f2c7ba3a077eac21fc8413937d6e84fac` проверен существующим
verify_freeze: 394 source SHA, actual source activation/prefix/dependency paths,
native `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`,
environment `056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a`.
Python3.14.2t/cp314t, NumPy2.5.1/SciPy1.18.1, OMP/OPENBLAS/MKL=1, остальные
три numerical-env переменные unset. Кандидат/native не менялись.

| Путь | Фактическая реализация и независимость |
|---|---|
| Cold runtime | Experiment.advance → validate_experiment → nbody_rotation.integrate → новый RotationDOP853/SciPy на каждом пакете → decode → raw q/S snapshots |
| Орбита | Входные SI p/v → движущийся COM и relative A/B → Newton point forces Python либо настоящий Rust → сумма Q2 corrections Python → обратное преобразование |
| Вращение | Для каждого тела: principal I → specific Q; q→R, inertial ω=R I⁻¹ Rᵀ S; qdot=(0,ω)⊗q/2, Sdot=τ. Оба backend используют здесь общий Python |
| Continuous control | Тот же integrate/RHS/error norm, один solver/COM frame на4000 s, 65 output epochs; это другой numerical recipe, не другой physical Hamiltonian |
| Историческое измерение | validate_two_q2_380.represented строит R через SciPy Rotation.from_quat(raw q). Затем max нормированных r/v/R/S; raw q в прежний агрегат не входит |
| Независимый reference | RK45, scaled Cartesian/R/body-Pi, scalar principal-I potential/force, иной набор переменных. Общие G/IC/Hamiltonian/binary64/SciPy ограничивают независимость |

Ссылки: [advance](../src/solar_simulator/experiment.py:142),
[Q2 corrections](../src/solar_simulator/nbody_rotation.py:104),
[error norm](../src/solar_simulator/nbody_rotation.py:144),
[integrate](../src/solar_simulator/nbody_rotation.py:171),
[reference](../scripts/two_q2_reference380.py:7),
[старое представление](../scripts/validate_two_q2_380.py:80).
Вращение автономное: reset elapsed time к0 на каждом пакете здесь не означает
смену внешней фазы заданной фигуры. Такие фигуры и EIH этим режимом запрещены.

Модель — Newton total-degree2: все монополи и оба M–Q вклада, обратные силы
и моменты, полные H/P/L модели. Нет Q2–Q2, высших мультиполей, приливов,
диссипации, EIH и контактов. Bounding spheres определяют внешнюю область,
а не точность модели реальных тел. Тензоры I и параметры не подбирались.

SHA всех artifacts manifest380 проверены. Массивы:
`two-q2-380.npz` = `51e7c79d7a36547df92959a8614d9d5804232d39c0ebfe5c4a143ecdd6da696a`,
completion plan = `b93c534e6b38aedc82df70768f1c471963093645f700e20c741ec87fa6fffb13`.
Все исходные23 массива первой попытки совпали dtype/shape/bytes с completion.
Известное отличие assessor SHA после382 снова проверено: исторические байты
0b5ea98c…dec7f0 доступны в Git638ccf0; текущий path-only вариант не выдаётся за
старый файл. Остальные manifest artifacts совпали. В acquisition sources
380/current отличаются app.py, application_profiles.py и driver, а не
вычислительные Q2/rotation/error-control/point-force ядра. Историческая среда
с native032 не названа текущей средой candidate033.

## Независимый пересчёт: все четыре исхода сохранены

Первым выполнен **только offline audit**: 106 сохранённых массивов, 12 journals
по64 кадра, без solver. Scalar math.fsum reductions и точные Fraction
subtraction/squares + Decimal sqrt не читают готовый PASS как ответ.
Нормировки r/v — max initial pair separation/relative speed данного случая,
S — отдельная начальная норма каждого тела, R — Frobenius norm без SI масштаба.
Для трёх тел масштабы орбиты учитывают все пары, не только A/B.

| Случай | coarse–fine R | standard–fine R | Максимум coarse / standard | Исходный результат |
|---|---:|---:|---|---|
|2 тела Python|4.321053763244028e-15|7.086768132709826e-15|A,4000 s / B,4000 s|FAIL|
|2 тела Rust|7.341808831039677e-15|9.633424121268789e-15|A,3625 s / A,3562.5 s|FAIL|
|3 тела Python|5.625282158101942e-15|6.215018178946092e-15|B,3375 s / B,3937.5 s|FAIL|
|3 тела Rust|1.001853255770063e-14|3.222516758705217e-15|B,4000 s / B,3812.5 s|PASS control|

Во всех четырёх агрегатах доминирует R, но это не метры и не радианы.
Например, standard–fine2/Python имеет максимум в R21 телаB: −4.77396e-15;
2/Rust — R11 телаA: −6.32827e-15; 3/Python — R21 телаB: +4.10783e-15
(полные точные значения/индексы сохранены в JSON). Нельзя сравнивать эти
компоненты с глобальной погрешностью истинной физической траектории.

| Случай | r coarse / standard | v coarse / standard | raw q coarse / standard | S coarse / standard |
|---|---|---|---|---|
|2 Python|1.28849e-15 /1.07290e-15|8.74466e-16 /1.53831e-15|1.72805e-15 /2.59571e-15|9.63506e-16 /1.10903e-15|
|2 Rust|7.61726e-16 /1.26174e-15|1.14062e-15 /2.37084e-15|2.91129e-15 /3.43654e-15|1.03432e-15 /1.25543e-15|
|3 Python|6.71320e-16 /8.92224e-16|1.29070e-15 /1.42395e-15|2.04682e-15 /2.19077e-15|1.20514e-15 /1.67113e-15|
|3 Rust|1.12205e-15 /1.24018e-15|1.92798e-15 /2.05292e-15|3.52152e-15 /1.32402e-15|1.39518e-15 /7.91467e-16|

Это прежние нормированные r/v/S и дополнительная raw-q distance, не SI errors.
Агрегат сравнивает максимумы, которые могут относиться к разным телам/эпохам.
q и −q физически эквивалентны: raw-q нужен для сохранности, но недостаточен
как physical angle. Все прежние 380 criteria оставлены дословно.

## Что показала проверка R/q и SO(3)

Точная рациональная разность сохранённых R с высокоточным извлечением нормы
даёт тот же округлённый binary64 Frobenius результат на проверенных точках.
Следовательно, ошибка sum/sqrt редукции не объясняет смену порядка максимумов.
Отдельно R построена из **точных сохранённых binary64 q**, с нормированием
и Decimal70/100 арифметикой. Все три немонотонности остались:

| Случай | R из q: coarse / standard, Decimal | Physical angle coarse / standard |
|---|---|---|
|2 Python|4.25044e-15 /7.15156e-15|3.00552e-15 /5.05692e-15 rad|
|2 Rust|7.34660e-15 /9.62046e-15|Сохранён в JSON для каждой точки|
|3 Python|5.70048e-15 /6.18457e-15|Сохранён в JSON для каждой точки|
|3 Rust control|9.94417e-15 /3.13540e-15|7.03159e-15 /2.21706e-15 rad|

После согласования знака единичных q chord=||qa−qb||=2sin(θ/4), откуда
θ=4asin(chord/2). Так вычислены малые углы без вычитания trace около3.
Для SO(3) ||Ra−Rb||F=2sqrt(2)sin(θ/2); оба независимых представления сверены.
Это угол **между сохранёнными состояниями**, не установленная global error.
Decimal70/100 здесь согласовались после округления результатов к binary64.
Симметрия q/−q и масштабирование проверены отдельно exact Fraction/Decimal.

Обычный trace/acos observer на этих данных иногда даёт0, иногда до2.98e-8 rad
при отличиях сохранённых q порядка1e-15. **Он непригоден для этого масштаба**,
но не использовался в старом FAIL gate и не является обнаруженным дефектом
production. Ошибка построения сохранённого SciPy R из q до~7.3e-16 по F
заметна для таких контрастов, однако не является их единственной причиной:
inequality сохраняется при сравнении самих нормированных q.

## Reference: важное ограничение интерпретации, не причина старого gate

В coarse–fine / standard–fine вообще нет RK45 reference. Поэтому H5 не может
быть вычислительной причиной **этой** немонотонности. Он нужен для другого
вопроса — абсолютной ошибки относительно решения усечённых уравнений.

Межуровневая разность R reference ≈6.25568e-11 /6.77849e-11 для2/3тел;
у fine RK45 max ||RᵀR−1||F ≈1.21481e-12 /1.30997e-12, polar defect
≈6.07511e-13 /6.55207e-13. Он не разрешает утверждение об абсолютной
ориентационной ошибке1e-15. Это indicators, не строгие верхние границы ошибки.
Polar projection выполнена только offline для оценки дефекта: raw R не
исправлялись, старые error metrics не заменялись углами/новыми PASS.

## Разрешённый малый эксперимент после offline audit

Offline исключил единственную причину в norm/ref, но не различил H1/H2/H3.
До интегрирования сохранены immutable plan и supplement: exact старые IC,
G/модель/SI/65epochs0..4000 s, **только standard level** (rtol1e-11,
x_atol1e-8 m, v_atol1e-12 m/s, исходные spin tolerances), оба backend и
PASS control3/Rust. Нет перебора фаз/допусков/шагов.

Выполнены4 cold trajectories с64 пакетами62.5 s и2 continuous Python control.
Для observer — plain/observed первый пакет2/Python и2/Rust; затем сравнение
30 полных массивов новых6 trajectories со старыми по **dtype/shape/bytes**.
Все совпали. Четыре midpoint t=2000 s save/load и продолжения исходными32
пакетами дали прежние конечные документы. Midpoint physical numbers независимо
проверены побайтно; конечные поля конечны/ненулевые, численное равенство здесь
не скрывает signed-zero различие. Кандидат/source/environment проверены до/после.

Observer — отдельный subclass, вызывающий исходные constructor/step/error norm
один раз и возвращающий исходный результат. RHS/native wrappers считают реальные
вызовы. Коэффициенты DOP853, силы, q/S и состояния solver не редактировались.
В контрольном наборе не обнаружено изменения численной траектории observer.
Это ограниченная проверка невмешательства, а не утверждение для всех программ.

| Case/backend/recipe, standard | RHS | Native | Accepted / rejected attempts | max estimator norm |
|---|---:|---:|---:|---:|
|2 Python cold|4352|0|320 /0|9.55209e-5|
|2 Rust cold|4352|4352|320 /0|1.96024e-4|
|3 Python cold|4328|0|318 /0|1.23624e-4|
|3 Rust cold, PASS control|4352|4352|320 /0|2.44806e-4|
|2 Python continuous|443|0|30 /0|0.984521|
|3 Python continuous|467|0|30 /2|1.50873 (включая rejected)|

Accepted — успешные вызовы _step_impl. Attempts/rejections согласованы двумя
свидетельствами: отдельными возвращёнными error norms и nfev_delta/12 внутри
step; проверен установленный SciPy rk.py (12 stages/attempt). Dense-output RHS
снаружи step в rejected counts не включён. Нет выдуманного публичного счётчика.
Всего primary RHS18294/native8704; smokes, suffixes и fixed-RHS benchmark
учитываются отдельно. Исторические380 production RHS counters не записывались:
числа392 относятся к новому наблюдению, хотя states совпали точно.

Cold solver начинает каждый раз с h≈0.0406–0.0602 s, затем выбирает новую
сетку; continuous начинает один раз с h≈0.049 s. Старые continuous contrasts
сходятся:2body9.35266e-10→1.19796e-11,3body9.41591e-10→1.01899e-11 по R.
Их большие coarse/fine различия не делают continuous автоматически точнее
cold. Заменять пакеты ради скорости без отдельной оценки точности нельзя.

Все64 перехода каждого cold случая сохраняют raw q/S точно; нет скрытого
обнуления spin или нормирования q на границе. Norm(q) drift на входах пакетов порядка
6.7e-16–1.3e-15. Повторённые COM/relative encode/decode дают roundtrip до
1.82e-12–3.64e-12 m и~4.4e-16 m/s. Это измерение арифметики координатного
преобразования, не физический импульс и не доказанный вклад в каждый FAIL.
Исходные65эпох — только границы пакетов; внутренние состояния отсутствовали.
Новая trace снимает это информационное ограничение для standard subset, но
не изолирует controller reset, recentering, truncation и roundoff друг от друга.

## H1–H5 и первопричины

| Гипотеза | Проверяемый признак / результат | Чего не хватает для причинного вывода |
|---|---|---|
|H1 implementation|Неверные force/torque gradients, reaction, I/R frame или повреждение q/S. На22 saved-state проверках (IC и исторические максимумы, standard/fine, включая повторные IC) прежние gradient2e-6/reaction1e-13/angular2e-12 PASS. Covariance и zero-Q/free spin tests PASS; save/resume exact|Это не22 независимые системы. Конечная выборка не доказывает отсутствие всех ошибок. Подтверждённого reproducer production bug нет|
|H2 cold/reset|Реально новый solver/COM/mesh каждый пакет,318–320 против30accepted steps. q/S границы exact, coordinate roundtrip ненулевой, применение recipe воспроизводимо|Контроль cold fixed-frame не отделён от warm/fixed-frame; индивидуальный вклад reset/packing в три FAIL **UNRESOLVED**|
|H3 arithmetic|Сами сохранённые нормированные q расходятся на несколько e-15; высокоточный observer не меняет исходы|Нет high-precision интегрирования/локального IVP из exact incoming state. Ошибка усечения и накопление roundoff не разделены. Исключительно float64 не доказано|
|H4 metric|Exact saved-R norm и Decimal q→R сохраняют все3FAIL. Нестабильность trace/acos отдельно показана|H4 не объясняет три FAIL единолично. max по разным телам/эпохам — характеристика старого критерия, не найденная ошибка его реализации|
|H5 reference|Reference не входит в старую inequality; разрешения RK45 недостаточно для абсолютного1e-15 вывода|H5 исключён как computational cause gate, но absolute error при таком масштабе **не установлен**|

Для **каждого** из2/Python,2/Rust,3/Python unique root cause остаётся
UNRESOLVED. Установлено: это не просто ошибка Frobenius reduction, внешнего
reference или потеря raw q/S при checkpoint. Сочетание холодного численного
пути и малых arithmetic/method differences совместимо с данными; доли причин
не измерены. Строгая монотонность между двумя решениями относительно fine
не является математической гарантией адаптивного метода в binary64.
Это объясняет ограниченность вывода из gate, но не переименовывает его FAIL.

## Производительность: измерено, а не оптимизировано

Сначала прочитаны старые CPU и доступные reference RHS receipts. Production
RHS в380 отсутствовал, поэтому только после offline выполнен frozen benchmark:
первый RHS state каждого case/backend, warmup3 +3 batches×200 +cProfile200.
Всего803 fixed evaluations на вариант; Rust фактически803 native calls,
Python0. Это фиксированное состояние, не выбор удачной ошибки/траектории.

| IC/backend | Median RHS wall,µs (range) | cProfile inclusive Q2 corrections | R constructions / constant Q per RHS |
|---|---|---|---|
|2 Python|338.43 (326.47–356.75)|61.3%|4 /2|
|2 Rust|330.86 (313.28–331.07)|64.2%|4 /2|
|3 Python|344.15 (340.31–346.43)|60.5%|4 /2|
|3 Rust|323.34 (315.47–363.26)|63.8%|4 /2|

CPU median во всех200-call batches312.5µs, но Windows process_time квантован:
такая выборка не измеряет улучшение на доли процента. cProfile увеличивает
время (~0.12 s/200 вместо~0.06–0.07 s); его shares не равны точным долям
неинструментированной программы. Вложенные inclusive times нельзя суммировать.
Надёжного вывода о выигрыше Rust на N=2/3 по этим шумным ranges нет.
Rust ускоряет здесь только point forces; Q2/R/ω остаются в Python.

Подтверждена повторная работа: на каждый RHS для двух фигур R вычисляется
четыре раза (поле и ω), хотя текущих q всего два; constant inertia-derived Q
строится дважды. cProfile R share11.5–11.8%, Q3.3–3.5%. Исходники показывают
новые arrays при этих вызовах. Полный allocation profile/пиковое число
аллокаций/tracemalloc и долговременные утечки **не измерялись**.
Наблюдаемые cold primary CPU1.59–1.69 s включают observer/dispatch/snapshot,
не равны чистой стоимости solver. Continuous0.156–0.188 s — иной recipe.

| Предложение, не патч | Возможная польза / минимальная область | Риск и повторные проверки |
|---|---|---|
|Один и тот же R для field и ω внутри одного RHS|Убрать2 из4 одинаковых R constructions. Оптимистический Amdahl потолок по профилю~1.06× RHS|Сохранить normalize/finite checks и порядок оставшихся операций, array layout; проверить exact RHS и trajectories 0/1/2Q2, gradient/invariants/resume, новое source-bound Q2 доказательство|
|Подготовить constant Q/I once per integrate|Убрать2 построения constant Q/RHS; вместе с R optimistic~1.10×, не измеренное ускорение|Readonly arrays, обновление только с валидными parameters, не менять quadrupole arithmetic/контракт. Затрагивает одну и две фигуры; отдельная квалификация|
|Persistent/warm solver|Меньше RHS и стартов; Python4352→443 и4328→467 на одном horizon|Это изменение numerical recipe, не безопасная локальная оптимизация. Меняет сетку/packing/точность и controller/checkpoint lifecycle; **NO-GO автоматическому внедрению**|

Скоростной патч не реализован, after-измерений нет. Нельзя обещать эти проценты
как результат. Constant Q означает **body-frame** tensor: инерциальный R Q Rᵀ
обязан обновляться вместе с ориентацией, его кешировать между RHS нельзя.
Нельзя суммировать gain с native без нового профиля. Удалять валидацию,
снижать точность, добавлять threads/GPU или переносить весь Q2 в Rust ради этого
малого кейса не предлагается. Ничего из этого не исправляет FAIL380 само по себе.

## Проверки, неуспехи, ресурсы и воспроизведение

Новые tests проверяют resolved tiny angle, q/−q, rational scaling, точную норму,
per-body/S scaling, pinned-data replay всех4исходов и отказ при плохом SHA.
Прежние potential gradients/covariance/zero-Q tests повторены при настоящем
кандидате. Финальные результаты и SHA приведены в JSON.

Сохранены диагностические FAIL: ошибочный local import relative_coordinates
исправлен на coordinates; затем1FAIL/8PASS нового unit test с невозможным
exact-zero ожиданием после Decimal70 scaling. Сам исторический критерий не
меняли. Тест теперь отдельно требует exact q/−q и доказывает scale invariance
через rational outer-products; finite Decimal остаток ограничен1e-67, исходя
из70digits и числа операций, а не по380ошибке. Это observer arithmetic test,
не новый физический бюджет. Старые логи и executed source сохранены.

Позднее добавлен standalone saved-data CLI; точные ранние байты helper
восстановлены и проверены по **ранее сохранённому** acquisition SHA,
AST всех metric functions совпал. Binding/результаты не переписаны.
Смена только новых tools после завершения workers не изменила кандидат.

Короткий воспроизводимый offline пересчёт из Git, без native/solver:

Код: [scalar/exact norm](../scripts/q2_saved_metrics392.py:14),
[resolved quaternion comparison](../scripts/q2_saved_metrics392.py:32),
[pinned replay](../scripts/q2_saved_metrics392.py:85),
[tiny-angle test](../tests/test_q2_saved_metrics392.py:8),
[tamper rejection test](../tests/test_q2_saved_metrics392.py:63).

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.q2_saved_metrics392 --output .tools/q2-replay-392.json
```

Output должен быть новым; исторические input SHA проверяются до NPZ loading,
allow_pickle=False, никаких команд из input не выполняется. Полные traces,
immutable plan/supplement, initial/raw/failure files, profiles и ресурсы
сохраняются отдельно в reviewed Project-Archives с manifest/readback SHA.

Общий бюджет неизменен:120CPU/300active wall/1GiB/64MiB; early90/240/900MiB/48MiB.
Все контролируемые попытки, включая FAIL, worker и целый supervisor process CPU
суммируются. RSS и Windows private(commit/PrivateUsage) записываются отдельно;
память supervisor+worker контролируется совместно. Sampling50ms, retained
Windows final CPU handles; это не hard OS quota и возможны короткие пики.
Показатели на закрытии и ограничения измерения — в machine report.
На закрытии controlled jobs: **35.546875 CPU s /33.037231 active wall s**,
включая неуспехи и supervisor. Worker private peak153141248B (~146.05MiB),
RSS peak151089152B; OS supervisor peak commit37453824B. Консервативная сумма
раздельных private peaks190595072B (~181.77MiB), не синхронный физический пик.
Ресурсных STOP нет. 6698530B/71файл в рабочем каталоге до финальных заметок/
архива; **пик числа файлов не инструментирован**, конечное число за пик не выдаётся.
Внешний supervisor venv launcher/последний record-tail CPU отдельно не пойман;
приведённые цифры не полный CPU всего чата/подготовки. Sampling caveats сохранены.
Финальные targeted tests **13PASS/0FAIL/0skip**, 1420 file/line links,
1299 inventory paths, standalone CLI и historical/source checks PASS.
Чтение/редактирование, Git/CI и обязательный backup prepare/upload отдельно.
Full check_project, Newton384, годовой EIH/JPL и portable build не запускались.

## Решение следующему этапу

**NO-GO production fix/оптимизации/ослаблению gate в392:** изолированного
дефекта, который можно корректно исправить, нет. **GO к обсуждению** одного
узкого causal contrast, если необходимо количественно объяснить FAIL:
fixed-frame cold на прежнем standard IC против уже сохранённого cold/continuous,
либо независимый high-precision локальный accepted-edge IVP из exact saved
incoming state. До исполнения нужны отдельные source/metrics/ресурсный preflight;
не новая полная матрица и не перебор более удачных rtol.

Это должно разделить recentering/reset и локальный method/roundoff вклад;
нынешний набор их не разделяет. Если для продукта достаточно честно сохранить
ограничение strict monotonicity, следующий полезный engineering шаг — отдельно
согласованный небольшой R-reuse prototype с before/after точностью и временем.
Он не объявляется исправлением научного FAIL.

При будущем изменении Q2/rotation integration: повторить one-/two-Q2 gradients,
free/zeroQ, covariance, rawq/S persistence/GUI и относящуюся scientific Q2
квалификацию. Newton point-only и EIH+fixedJ2 численные пути этим не меняются,
но их неприкосновенность доказать diff/SHA и regression tests. Изменение
общих coordinates/error-control/native затронет также Newton384/annual385 и
потребует отдельного решения о научной квалификации. Новый fingerprint обязателен;
старые receipts нельзя переименовывать или переписывать.

Все три FAIL380 сохранены. A+D1 из391 остаётся предложением; release033
**NO-GO**, main/tag/LATEST/candidate/portable032 неизменны. После отчёта STOP.
Рекомендуемая модель следующего узкого этапа: GPT-6.1 Sol High.
