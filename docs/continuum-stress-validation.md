# Komar/current qualification96–98: результаты

[Договор](continuum-stress-contract.md),
[исходный проверенный JSON](continuum-stress-validation.json).
Fresh audit7C/513radialnodes,28ODE jobs,49NPZ,257frozen sources/primary,
7.116826s.18maximum+8minimum+5boolean заранее фиксированных критериев
прошли. ProductionDOP853 rawf/fprime сравнивается с независимой
stress-source Riccati+logf системой: RK45twolevels и tighterDOP853.
Gauss64/128 интегрирует mass flux, exact ordered terms и полный current.
Старые trajectories не использованы; исходные signedzero states/grid
побитово сохранены, source/primary SHA и всеarrays сверены по окончании.

## Численное согласие и чувствительность

| Проверка | Максимальная величина | Фиксированный предел |
|---|---:|---:|
| Komar metric-gradient charge | 3.34e-16 | 1e-11 |
| Komar stress integral / gravitationalM | 3.34e-15 | 1e-11 |
| Gauss mass integral64/128 sensitivity | 3.89e-15 | 1e-11 |
| Production / independent reference I | 3.96e-12 | 1e-8 |
| Production / reference normalized profile | 8.61e-14 | 1e-8 |
| Reference RK45 level sensitivity | 5.22e-10 | 1e-8 |
| RK45 / tighterDOP853 sensitivity | 3.96e-12 | 1e-8 |
| Boundary I / direct matter integral | 7.33e-15 | 1e-9 |
| Gauss current64/128 sensitivity | 8.44e-15 | 1e-9 |
| Independent current integral | 1.06e-14 | 1e-9 |
| Pointwise telescoping identity | 1.34e-15 | 1e-11 |
| Largest individual coefficient Richardson error | 4.67e-5 | 4e-4 |
| c^-4 remainder ratio deviation from16 | 0.225912 | 1.5 |

Numerical agreement7.33e-15 не заменяет reference sensitivity5.22e-10,
не является rigorous error bound и не говорит о physical lunar accuracy.
Regular static mass flux уже включает давление, lapse и proper volume;
он не задаёт отдельную invariant local gravitationalfieldenergy density.
Равенство interiorKomar и m(s) получилось именно для constantε sphere,
не переносится на произвольный density profile.

## Компенсирующаяся пара ошибок

Richardson slopes orderedterms: pressure0.05713907 против2/35,
volume0.28570537 против2/7, lapse0.45709999 против16/35,
frame/profile−0.45709617 против−16/35. Их c^-4 ratios16.0362–16.2259.
Последние два вклада отменяются в integratedfirstPN coefficient.

Wrongpaired removal of lapse/profile тоже даёт first slope0.34284443,
в пределах фиксированного допуска от12/35=0.34285714.
Поэтому лишь проверка первого коэффициента такую ошибку пропускает.
Но measuredsecondcoefficient0.47975563 соответствует wrong151/315,
а правильный numerical0.40408332 — published212/525=0.40380952.
Pairedgap measured0.07567231 против independentlyderived17/225=0.07555556;
finiteC deviation1.1676e-4<2e-3. Wrongsecond gap относительно правильного
coefficient0.0759461>0.01; fullwrongI difference до0.0265411>1e-4.
Так независимые term/profile/secondorder checks обнаруживают paired error,
хотя Newtonlimit и firstPN slope совпали.

Все8wrongcontrols detected: omittedpressure/lapse/volume mass changes
0.286954/0.827316/0.205993; omittedpressure/lapse/profile spin changes
0.0498320/0.239707/0.471538, плюс pairedI и pairedsecond выше.
Они не включаются в физический runtime и не выдаются за valid alternatives.

## Код и проверенные строки

| Задача | Код | Проверка |
|---|---|---|
| Static stress mass and metric boundary | [Komar](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_stress.py:12), [independent metric gradient](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_stress_reference.py:7) | [gradient/flux/mass](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_stress.py:11) |
| Ordered spin terms | [terms](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_stress.py:26), [direct reference](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_stress_reference.py:29) | [pointwise sum](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_stress.py:22) |
| Independent radial profile | [Riccati+logf](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_stress_reference.py:15), [boundary-normalized h](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_stress_reference.py:24) | [regularorigin rejection](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_stress.py:45) |
| Compensating terms and wrongsecond | [coefficients](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_stress_reference.py:34) | [analytic cancellation](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_stress.py:33) |
| Fresh frozen-source audit | [sourceclosure](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_continuum_stress.py:26), [primarySHA](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_continuum_stress.py:39), [audit](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_continuum_stress.py:50) | [allcriteria](C:/Users/Admin/Desktop/Solar-simulator/tests/test_stress_audit.py:16), [source/corruption](C:/Users/Admin/Desktop/Solar-simulator/tests/test_stress_audit.py:27), [freshpaths](C:/Users/Admin/Desktop/Solar-simulator/tests/test_stress_audit.py:39), [offline import](C:/Users/Admin/Desktop/Solar-simulator/tests/test_stress_audit.py:52) |

Targeted helper/reference/audit20passed1.46s. Scientific98 audit без
failedcriteria. Earlierfailed93 остается в отдельном архиве, не переписан.
No new physical inertia tensor or finiteΩ²energy, harmonic/ADMmap,
conservative orbitalPNreaction, physicalMooninit, innercore или tides.
