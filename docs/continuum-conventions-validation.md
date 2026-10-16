# Проверка определений массы, координат и частоты92–95

[Договор и собственный вывод](continuum-conventions-contract.md),
[проверенный JSON](continuum-conventions-validation.json).
Fresh audit:7 compactnesses0.008/0.002/0.0005/0.02/0.1/0.25/0.3;
513radialnodes,35IVP jobs,56NPZ,250code/policy/primary copies,
8.647574s. Это структура статической сферы по радиусу, не temporal orbit.
19maximum+6minimum+5boolean критериев заданы доjobs и пройдены.
Policy SHA и bytes находятся в report/source copies; inputs/initial/grid,
все сохранённые arrays и code/primary closure сверены после расчёта.
Старые Hartle trajectories не использовались, runtime не изменялся.

## Что численно проверено

| Проверка | Максимальный результат | Фиксированный предел |
|---|---:|---:|
| Proper-energy mass, independent Gauss | 7.33e-15 | 1e-11 |
| Gauss64/128 sensitivity proper mass | 8.66e-15 | 1e-11 |
| Closed radius / independent log-ODE | 1.46e-11 | 1e-8 |
| Two RK45 levels, radius sensitivity | 9.4447e-9 | 1e-8 |
| RK45 / tighterDOP853 radius | 1.46e-11 | 1e-8 |
| Rational inverse / numerical IVP inverse | 1.36e-11 | 1e-10 |
| Spatial metric/volume pullback | 8.89e-16 | 1e-11 |
| Isotropic exterior surface match | 4.45e-16 | 1e-11 |
| Baryon mass in two coordinate charts | 8.38e-12 | 1e-8 |
| Baryon quadrature level sensitivity | 5.85e-12 | 1e-8 |
| Baryon mass, coordinate IVP sensitivity | 3.62e-9 | 1e-8 |
| Fresh Hartle/Riccati I agreement | 5.56e-16 | 1e-8 |
| Local coframe speed/clock | 4.34e-16 relative | 1e-11 |
| Same J from local response×rate | 3.62e-16 relative | 1e-11 |

Coarse RK45 sensitivity около границы критерия; это опубликованный результат,
не основание ослаблять критерий или объявлять tighter agreement истинной
погрешностью. Метрики оценивают numerical consistency в заданном benchmark.
Даже agreement5.56e-16 не квалифицирует physical lunar inertia/accuracy.
Барионные профили — явно заданные tracers, без thermodynamic/EOS certification.

Richardson first-order slopes: distant0.3428483, proper-energy0.1028556,
isotropic1.1427763, surface-static−0.05713915, surface-ZAMO0.2628482.
Соответствующие аналитические значения12/35,18/175,8/7,−2/35,46/175.
Максимальное slope deviation8.0821e-5<2e-4; c^-4 remainder ratios
16.0274–16.1941, fixed16±1. Proper mass quadratic-series остаток c^-6:
ratios64.1379–64.5568, fixed64±1; slope0.5999865 против3/5.
Proper-energy deficit Newton coefficient0.6003216 против0.6;
без EOS он не называется полной binding energy.

Six wrong controls detected: Euclidean volume difference0.278663,
areal-as-isotropic radius0.333772, coordinate density as scalar5.21867,
omitted lapse1.22874relative, omitted shift1.42513relative,
unchanged inertia slope after convention switch0.799919.
Это намеренно неверные варианты, не alternative physical models.

## Неудачный тест и исправление

Первый targeted93:3failed/26passed1.17s. Test перепутал radius metric
identity: использовал (x/s)x'=1/u вместо x'/(x/s)=1/u.
Независимый regular log-ODE помог выявить ошибку в самом критерии теста.
Исправление следует непосредственно из dx/x=ds/(su); tolerance не ослаблен,
production map не менялся. Firstfailed log/source/test/failure receipt
сохранены `.tools/rotation92-95/test93-failure`.
После исправления29tests0.49s; c reference tests32total0.65s;
все новые helper/reference/audit regressions38passed1.68s.
Clean-source child import работает без privateprimarycache; freshaudit
без cache явно отклоняется до созданияoutputs. Existing corruptedprimary
отклоняется по заранее pinnedSHA, а не принимается как новый источник.

## Проверенные строки кода и тестов

| Задача | Код | Проверка |
|---|---|---|
| Interior isotropic map/regular derivative | [geometry](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_conventions.py:15), [inverse](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_conventions.py:30) | [independent ODE and metric](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_conventions.py:22) |
| Proper volume/energy | [hypergeometric volume](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_conventions.py:44) | [independent quadrature](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_conventions.py:15) |
| Explicit baryon density and three mass measures | [integrands](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_conventions.py:52) | [no guessed rest density](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_conventions.py:40), [invalid input](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_conventions.py:65) |
| Static/ZAMO rates and same exterior J | [rates](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_conventions.py:78), [responses](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_conventions.py:107) | [signed/zero rate](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_conventions.py:51), [slowdomain](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_conventions.py:79) |
| Numerical inverse coordinate quadrature | [reference](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_conventions_reference.py:35) | [independent mass](C:/Users/Admin/Desktop/Solar-simulator/tests/test_conventions_reference.py:7) |
| Orthonormal coframe | [tetrad](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_conventions_reference.py:45) | [clock/speed](C:/Users/Admin/Desktop/Solar-simulator/tests/test_conventions_reference.py:19) |
| Convention-dependent analytic slopes | [series](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_conventions_reference.py:56) | [derived first derivatives](C:/Users/Admin/Desktop/Solar-simulator/tests/test_conventions_reference.py:25) |
| Source/primary/result guard | [code guard](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_continuum_conventions.py:26), [primary SHA](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_continuum_conventions.py:39), [audit](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_continuum_conventions.py:50) | [allcriteria](C:/Users/Admin/Desktop/Solar-simulator/tests/test_conventions_audit.py:17), [corruption](C:/Users/Admin/Desktop/Solar-simulator/tests/test_conventions_audit.py:28), [freshpaths](C:/Users/Admin/Desktop/Solar-simulator/tests/test_conventions_audit.py:35), [offline import](C:/Users/Admin/Desktop/Solar-simulator/tests/test_conventions_audit.py:49) |

Ограничения неизменны: no harmonic/ADM map, no PN tensor/multipoles/field
qualification, no finiteΩ² energy/shape/mass, no physical Moon init/tides.
