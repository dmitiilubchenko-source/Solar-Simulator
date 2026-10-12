# Связанное Newton-тело: независимая проверка83–85

Модель и собственные выводы — [договор](bound-body-contract.md).
[Policy](C:/Users/Admin/Desktop/Solar-simulator/scripts/bound-body-policy.json:1)
зафиксирована до jobs; [JSON](bound-body-validation.json) содержит все inputs,
criteria, источники SHA, массивы, jobs и диагностические значения.
Это свободная conservative evolution с внутренними парными силами,
без поддержки орбиты, damping, projection или переноса старых траекторий.

## Данные и протокол

SI/Newton inertial chart, общий t0=0. Synthetic G=0.4 m³/(kg s²),
minimum_distance0.05m. Для equilateral:3mass×2kg, all3links k=4N/m,
rest length3.117691453623979m. Circular radius2m, omega0.8110086478694062s^-1,
ell3.2440345914776247m²/s, kappa²7.857735026918962s^-2>0.
Circular и breathing длительность30.98948611059124s=4rotationperiods,
1025uniformepochs. Breathing initial radius2.12m, radialvelocity0,
тот же ell; состояние не recentre/проектируется во время интегрирования.

Asymmetric4mass (2,3,4,2.5)kg, tetrahedral initialpositions и velocities
заданы вpolicy. Sixlink stiffness=3+i+j N/m, rest length0.97initialdistance,
зафиксирован доjobs и затем не меняется. Начальные COM/P ненулевые:
проверяется линейное движение центра, не принудительное удержание origin.
Длительность12s, та же сетка1025epochs.

DOP853 production rtol1e-11. IndependentCartesian scalarHamiltonian
дифференцируется complex-step, без импорта productionforce/diagnostics.
Breathing отдельно сравнивается с reduced(R,Rdot,phi) equations:
RK45 rtol2e-10/2e-12 и DOP8532e-13. CartesianRK45 breathing2e-12,
asymmetric2e-10/2e-12. atol=rtol/50; maxstepu1/512 у всех.
Точное circular solution не требует ODE и сохраняется отдельным NPZ.

23newlocaltests passed1.17s. Fresh85:9ODEjobs/10NPZ,9.700s,
233sources(231Python+2usedpolicies)/executedcopies frozen.
Policy22maximum/9minimum/5required_true — все36criteria passed.
Report SHA25684e4edfa0d019d5f1af57831a770c1568c83e1967546c3e943682a379ccbf3d5.
Массивы SHA/shapes/finite и bitwiseinitial/grid проверены; sourceguard
междуjobs и по окончании. Минимальная sampled pairdistance1.5223303177m,
все вычисленные RHS отклоняли бы выход за minimum_distance.
Это не строгая гарантия минимального расстояния на всех промежутках времени.

## Численное согласие и чувствительность

| Величина, максимум по заданной сетке | Результат |
|---|---:|
| Force vs independent potential gradient /40N | 2.552e-17 |
| Total force /40N | 2.483e-17 |
| Total torque /(40N×2m) | 2.637e-17 |
| Tensor virial residual /40J | 1.417e-16 |
| Kinetic split residual /40J | 1.318e-16 |
| Energy drift, максимум по3production cases | 1.170e-12J |
| Total angular momentum drift | 5.542e-13kg m²/s |
| COM vs linear motion /2m | 7.892e-15 |
| Circular vs exact position | 8.917e-14m |
| Breathing vs fine reduced position /momentum | 3.866e-11m /1.223e-10kg m/s |
| Reduced levels position /momentum difference | 3.708e-9m /1.160e-8kg m/s |
| Fine reduced vs tighterDOP position /momentum | 3.893e-11m /1.230e-10kg m/s |
| Breathing vs independent Cartesian position | 1.865e-11m |
| Asymmetric vs fine Cartesian position | 5.422e-12m |
| Asymmetric reference levels position /momentum | 4.961e-10m /2.906e-9kg m/s |

Fine/tighter reduced sensitivity сравнима с productionagreement;
agreement не интерпретируется как точность лучше независимого эталона.
Двухуровневое сравнение/rtol/maxstep не дают rigorous trueerrorbound.
Все величины относятся к выбранным synthetic bodies и фиксированным epochs.

## Деформация и проверки намеренно неверных выражений

Breathing radius span0.2377320958m. На пульсацию приходится до4.0665%
internal kinetic energy. При этом S сохраняется, а C(t),Ω(t) меняются.
Шесть controls дали заранее требуемое отличие:

| Намеренно неверная величина | Масштабированное отличие | Заранее минимум |
|---|---:|---:|
| Rigid-only Cdot для breathing | 0.49081 | 0.001 |
| Постоянная C0 вместо C(t) в S=CΩ | 0.26136 | 0.01 |
| Только kinetic energy как conserved total | 0.04716 | 0.01 |
| Пропущенная partner reaction одного link | 0.03797 | 0.01 |
| Пропущенные силы elastic binding | 0.10392 | 0.01 |
| Spring potential energy вместо spring virial | 0.65664 | 0.01 |

Это local/model controls; первые три оцениваются вдоль правильной evolution,
последние силы не интегрировались как отдельные ошибочные траектории.
Две остальные minimumcriteria подтверждают заметную пульсацию и деформацию;
ещё одна проверяет sampled minimum pairdistance. Это не9negativecontrols.

## Ограничения и проверки проекта

Massless instantaneous Hooke links не задают continuum stress tensor,
EOS, давление, внутренние энергетические потоки или материальные параметры.
Newton gravitational potential energy включена, self-energy каждой точки
не определена. Здесь нет полного PN gravitational-field angular momentum,
PN-inertia/multipoles, SSC/tetrad/ADM centre или TDB/TCB qualification.
NewtonTisserand split — instantaneous definition с condition(C)<1e12,
не physicalMoonattitude. Лунные данные, runtime/H57 и strictreceipts не менялись.
Kuiper420/528 ограничения и unexplained121.84″ остаются открытыми.

В этом этапе scientific/unit criteria не провалились и не ослаблялись.
Один отказ доступа к Cambridge поисковой PDF-ссылке сохранён в local source-review;
primary1997 получен через publisherlink. Коэффициенты плохо распознанной
PN-инерции не перенесены в код. Полный check_project:1084Python passed172.68s,
17Rust passed, fmt обоихcrates,1127file/line links. 23новых теста входят в1084;
1061 относится к82. Исходные353statusentries сохранены; runtime/данные/
oldreports/strictreceipts не менялись. Local preservationreceipt:
.tools/rotation83-85/verification.json. Публикация/portable вне задачи.
Finalpreservation passed:466из470baselinefiles unchanged (обновлены4private
docs),137oldJSON/68runtimeRustfiles побайтно сохранены. Все233executedcopies
и10NPZ SHA/shapes/finite/bitwiseinitial/grid повторно проверены. Handoff78строк,
его прежняя версия и archiveprefix сохранены побайтно; private docs ignored.
