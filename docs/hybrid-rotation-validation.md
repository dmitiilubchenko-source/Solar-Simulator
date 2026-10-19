# Совместный баланс EIH и жёсткого квадруполя: 248–253

17 октября 2026. [Протокол и вывод](hybrid-rotation-protocol.md) записаны до
результатов. Проверены две **синтетические математические модели**, без
переключения рабочего приложения. Все обязательные критерии прошли.
Данные Луны, Rust, начальные условия и силы рабочего профиля прежние.

Главный результат: для суммы order-reduced EIH и Newton Q2 дрейф полных
E/P/J объясняется источниками PN² и PN×Q. Убирать их из диагностики или
называть такой дрейф просто ошибкой интегратора некорректно. Точное решение
выбранного конечного действия сохраняет его E/P/J, но порождает старшие
порядки и **не становится от этого более полной физической моделью ОТО**.

## Что именно проверено

Три тела, массы (.3,.7,.05), одна жёсткая фигура. Два номинальных периода,
129 эпох. G=1, модельные единицы; c=400 — искусственный параметр для
видимости малых источников. Явное SI-подобие M0=1e15 kg, L0=12000 m,
T0=5088.256631 s даёт искусственный c≈943.35 m/s. Это не скорость света
в рабочем Solar и не Солнечная система. Нет календарной эпохи/TDB/SSC-переноса.
Максимальный weak-field параметр на сохранённых состояниях5.571983e-6<1e-4;
оба RHS отклоняют выход из области и совпадающие точки.

Вариант OR: a=aN+aPN+aQ, Sdot=tauQ. Два бюджета вычисляются отдельно:
B(H1 aPN), B(H1 aQ), где H1=∂²L1/∂v². Q torque орбиты сокращается с
обратным моментом spin и второй раз к полному J не добавляется.

Вариант finite-action: a=aN+solve(M0+H1,M0(aPN+aQ)). Его конечный
Lpoint+Newton rotor−UQ автономен, инвариантен относительно переносов и
вращений. Это выбранный постулат с обычным евклидовым rotor, без PN-I,
SO, деформаций или полноценного PN-мультипольного/boost контракта.

Независимость проверок:

- Production DOP853 использует по-блочный контроль x/v/q/S и двух бюджетов;
  Q сила приходит через явный SI-переход из прежнего Newton runtime.
- RK45 reference использует сырую матрицу R и body-Euler Pi. OR point force
  вычисляется отдельными scalar target loops; finite-action acceleration —
  Euler–Lagrange из исходного ordered/triple действия Vines, с complex-step
  производными. Тензорные/кватернионные runtime формулы не импортируются.
- Целые Noether E/P/J проверены отдельно направленными Decimal70/90
  производными с движущейся R. Первая и вторая производные действия,
  SI force bridge и раздельные PN²/PN×Q источники сверены независимо.

## Численные результаты

Значения нормированы на начальные физические масштабы модели; это не метры
ошибки относительно эфемерид. Уточнённый DOP853: rtol3e-12.

| Уточнённый OR | Энергия | Импульс | Полный угловой момент |
| --- | ---: | ---: | ---: |
| Raw относительное изменение | 4.047197e-7 | 2.955778e-8 | 2.195161e-7 |
| Остаток после обоих бюджетов | 1.337370e-14 | 3.609832e-16 | 5.013812e-15 |
| Отдельный PN² интеграл | 8.286484e-10 | 6.140249e-11 | 1.687307e-10 |
| Отдельный PN×Q интеграл | 4.055249e-7 | 2.961681e-8 | 2.195723e-7 |

| Уточнённый finite-action | Энергия | Импульс | Полный угловой момент |
| --- | ---: | ---: | ---: |
| Raw дрейф, без корректирующих бюджетов | 1.321045e-14 | 5.749513e-16 | 5.105253e-15 |

Заранее заданный предел остатков1e-9 соблюдён и на nominal, и на tight,
и на обоих reference уровнях. Для nominal OR max correctedE4.319194e-12,
finite-action4.320188e-12. Не только tightened вариант проходит критерий.

| Проверка траектории/ориентации | OR | Finite-action | Предел |
| --- | ---: | ---: | ---: |
| Production против строгого независимого | 2.929776e-11 | 2.924781e-11 | 3e-7 |
| Два независимых уровня RK45 | 1.883138e-10 | 1.881192e-10 | 3e-8 |
| Production против tighter | 4.779069e-11 | 4.776668e-11 | 3e-8 |
| Raw q norm deviation | 1.858513e-13 | 1.855183e-13 | 1e-8 |
| Reference orthogonality | 9.712952e-12 | 9.709121e-12 | 1e-8 |

Ошибки всех x/v блоков каждого тела, S и матрицы сохранены в JSON.
Чувствительность самого эталона больше разности production/reference;
это эмпирическая чувствительность, а не строгая верхняя граница ошибки.

Различие **между моделями**, не численная ошибка: максимум нормированных
блоков1.603197e-5; матрицыR1.099732e-5. Абсолютные максимальные различия
положений в модельных единицах длины:6.329892e-6/2.714426e-6/1.350195e-7.
Хорошая энергия finite-action сама по себе не выбирает физически лучший вариант.

## Малые источники и независимые производные

Все6 активных интегральных каналов PN²/PN×Q × E/P/J различимы: выше32eps
и выше10×численного бюджета; намеренное исключение каждого источника
увеличивает соответствующий остаток более чем в10 раз. Это видимость
в усиленной синтетической задаче; прежний ten-body Noether FAILED220
остаётся FAILED, годовой spin/EIH баланс не квалифицирован.

Девять снимков, Decimal70/90, h=1e-6/1e-9/1e-12:
последний h против ожидаемого полного источника — scaled error≤7.523506e-25,
relative active≤8.128920e-18; precision difference≤1.102037e-57.
Пропуск Sdot даёт относительный дефект J около1 по собственному torque scale.
При c→2c источники PN²/PN×Q уменьшаются в16/4 раза на фиксированных состояниях;
это algebraic order control, не измерение физической погрешности модели.

Мосты по9снимкам: полный runtime EIH5.258615e-16 relative;
изолированный PN после вычитания Newton3.000951e-11 (<1e-9);
Q force7.993508e-15/torque8.643966e-16; velocity Hessian1.920817e-16;
point action Euler relation5.574593e-16. Все отдельные пороги соблюдены.

## Неуспехи и исправления сохранены

1. Первый тест249:3failed/13passed0.96s. В независимом momentum1 массив
   создавался вещественным при complex x и real v. NumPy отклонил запись
   комплексного transport term. Исправлен dtype от обоих аргументов;
   формулы/критерии прежние. Исходник и причина сохранены локально.
2. После numerical PASS250 обнаружен неполный domain contract независимого
   RHS: не было явного weak-field guard. Добавлены guard и4отрицательных
   теста до вызова сил/действия. Все8jobs повторены в251; показатели и все9
   decoded arrays250=251 точно. Исходный250 и исполненный исходник сохранены.
3. Грубый directional h=1e-6 не прошёл relative energy threshold1e-7 в8/9
   снимках, в обеих precision. Все исходные флаги/значения сохранены.
   Протокол заранее требует последний h и refinement: h1e-12 прошёл.
   Критерий не ослаблялся, неудобные эпохи не удалялись; увеличение точности
   арифметики без уменьшения h этот FD-остаток не устранило бы.

## Воспроизведение и стоимость

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_hybrid_rotation --output .tools/hybrid-replay
```

Нужен новый путь. Существующий отчёт/каталог отвергается, в том числе failed.
Необходимые входы синтетические и заданы в коде. Первичный PDF проверен
при выводе248, его приватный кеш не является зависимостью запуска.
Автономный child-process из публичной копии с пробелами, без сети/старой.tools,
повторил все показатели и9массивов точно. NumPy/SciPy остались теми же;
новая установка или платформа не квалифицированы.

Последний audit251:46.374213s, все8jobs; OR nominal/tight1.139/2.046s,
reference4.015/6.381s; finite-action nominal/tight1.268/2.265s,
reference11.211/17.497s. Replayprocess47.7075794s. Это одиночные наблюдения,
не сопоставимый performance benchmark и не основание для оптимизации.
Цена эталона включает численное дифференцирование исходного действия.

20новых tests прошли; относящийся набор **133passed10.46s**.
825публичных файлов неизменны во время проверки. Последний полный246:
1819Python/17Rust/fmt, исторический, здесь не повторялся. Нового Cargo/native
build не было. Полные результаты/SHA/параметры/все промежуточные derivative
levels в [JSON](hybrid-rotation-validation.json), trajectories в
`.tools/hybrid248/audit251/` и combined NPZ; источник каждогоjob проверен.

Следующий минимальный шаг — оценить PN×Q и spin-эффекты в реальных SI-масштабах
Солнца–Земли–Луны относительно годового допуска1km для Moon−Earth. Отделить
оценку масштаба от строгой границы глобальной ошибки; затем выбрать нужный
уровень приближений. Не выводить пригодность из усиленного toy c=400.
Рабочий EIH+dynamicrotation guard, неподтверждённый physical I/clock/triad/SSC
mapping, старые Noether и Kuiper420/528 ограничения остаются прежними.
Приливы, 3D, подгонка IC/GM/I и GitHub в этот блок не входят.
Рекомендация: GPT-6.1 Sol High для проверки реальных масштабов и границ вывода.

## Код и проверенные строки

- [hybrid_rotation.Model](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:18)
- [hybrid_rotation.initial](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:34)
- [hybrid_rotation.unpack](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:48)
- [hybrid_rotation.hessian](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:55)
- [hybrid_rotation.mass_solve](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:73)
- [hybrid_rotation.figure_field](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:80)
- [hybrid_rotation.pack](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:91)
- [hybrid_rotation.fields](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:95)
- [hybrid_rotation.rhs](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:110)
- [hybrid_rotation.HybridDOP853](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:118)
- [hybrid_rotation.__post_init__](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:25)
- [hybrid_rotation.__init__](C:/Users/Admin/Desktop/Solar-simulator/scripts/hybrid_rotation.py:120)
- [independent_hybrid_rotation.hat](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_hybrid_rotation.py:11)
- [independent_hybrid_rotation.action](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_hybrid_rotation.py:16)
- [independent_hybrid_rotation.momentum1](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_hybrid_rotation.py:35)
- [independent_hybrid_rotation.derivatives](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_hybrid_rotation.py:49)
- [independent_hybrid_rotation.body_field](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_hybrid_rotation.py:62)
- [independent_hybrid_rotation.pack](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_hybrid_rotation.py:78)
- [independent_hybrid_rotation.rhs](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_hybrid_rotation.py:83)
- [independent_hybrid_rotation.quantities](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_hybrid_rotation.py:120)
- [decimal_hybrid_rotation.matrix](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_hybrid_rotation.py:14)
- [decimal_hybrid_rotation.tensor](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_hybrid_rotation.py:22)
- [decimal_hybrid_rotation.quantities](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_hybrid_rotation.py:28)
- [decimal_hybrid_rotation.snapshot](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_hybrid_rotation.py:38)
- [decimal_hybrid_rotation.precision_agreement](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_hybrid_rotation.py:93)
- [assess_hybrid_rotation.matrices](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:24)
- [assess_hybrid_rotation.reference_state](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:28)
- [assess_hybrid_rotation.error](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:34)
- [assess_hybrid_rotation.norms](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:45)
- [assess_hybrid_rotation.balances](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:51)
- [assess_hybrid_rotation.visibility](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:60)
- [assess_hybrid_rotation.algebra](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:83)
- [assess_hybrid_rotation.qualification](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:108)
- [assess_hybrid_rotation.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:122)
- [assess_hybrid_rotation.main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:227)
- [assess_hybrid_rotation.save](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:152)
- [assess_hybrid_rotation.job](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_hybrid_rotation.py:155)
- [test_hybrid_rotation.test_action_velocity_gradient_and_hessian_are_independently_consistent](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:14)
- [test_hybrid_rotation.test_finite_action_matches_euler_lagrange_and_reduced_residual](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:25)
- [test_hybrid_rotation.test_mass_solve_rejects_indefinite_matrix_without_fallback](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:41)
- [test_hybrid_rotation.test_newton_limit_and_source_reaction_survive_explicit_si_similarity](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:46)
- [test_hybrid_rotation.test_scalar_action_noether_readout_matches_whole_decimal_rotor](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:57)
- [test_hybrid_rotation.test_whole_rotor_directional_identity_has_high_precision_and_order_controls](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:72)
- [test_hybrid_rotation.test_undeclared_decimal_precision_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:82)
- [test_hybrid_rotation.test_budget_error_cannot_be_diluted_by_more_orbits](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:87)
- [test_hybrid_rotation.test_partial_scientific_report_cannot_qualify](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:98)
- [test_hybrid_rotation.test_existing_failure_is_preserved_before_input_loading](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:115)
- [test_hybrid_rotation.test_reference_rejects_unsupported_domain_before_force_or_action](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:126)
- [test_hybrid_rotation.forbidden](C:/Users/Admin/Desktop/Solar-simulator/tests/test_hybrid_rotation.py:131)
