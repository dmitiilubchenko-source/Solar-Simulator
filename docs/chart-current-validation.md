# Coordinate current/tensor audit105–107

[Договор](chart-current-contract.md),[проверенный JSON](chart-current-validation.json).
Suppliedcurrent instantaneous snapshots, fixedstaticmetric/time/origin,
не self-consistent fluidmodel ине physical PNlunar inertia.
3C=.02/.15/.3,12freshradialIVP jobs,18NPZ,271source/policy/primarycopies,
3.119373s.17maximum+7minimum+5boolean fixedcriteria passed.
Для каждой C две3Dсетки5760/25600points; независимые angularintegrals
аналитические, radialGauss64/128 сindependentRiccati/logF profile.
Production/refsourceSHA, signedzero/raw/grid иallarrays свереныafterjobs.
Нетreuse старыхharmonictrajectories илиruntimechanges.

## Числа и чувствительность

| Проверка | Максимальнаяrelativeвеличина | Предел |
|---|---:|---:|
| Currentmass analytic reference | 9.90e-15 | 1e-10 |
| Areal/harmonic firstmoment | 1.46e-14 / 1.57e-14 | 1e-9 / 1e-8 |
| Areal/harmonic secondmoment | 1.92e-14 / 1.78e-14 | 1e-9 / 1e-8 |
| Axialcharge analytic reference | 1.67e-14 | 1e-9 |
| Quadraticparticlekinetic measure reference | 2.39e-14 | 1e-9 |
| 3Dpointgridlevels sensitivity | 8.98e-15 | 1e-8 |
| AnalyticradialGausslevels sensitivity | 2.15e-14 | 1e-9 |
| RadialreferenceRK45levels sensitivity | 4.92e-12 | 1e-8 |
| RK45/tighterDOP853 moment sensitivity | 4.35e-15 | 1e-8 |
| Cotangentpointwise workpairing | 1.34e-16 | 1e-11 |
| Axialcharge andkineticmeasure coordinatepullback | 1.91e-16 / 1.99e-16 | 1e-11 |
| Metricmatrix pullback | 2.76e-16 | 1e-11 |
| Currentdensity/volume pointmasspullback | 5.48e-17 | 1e-11 |
| EuclideanC/STF moment analytic reference | 5.63e-14 | 1e-8 |

Sampledpositivecurrentshape minimum0.316939>0.1,
sampledJacobian minimum0.579193>0.05. Numericalagreement1e-14 не
заменяет radialreference sensitivity4.92e-12 ине являетсяtrueaccuracybound.
Grid-dependent moment convergence здесь проверяетcoordinate/current model,
не измереннуюлуннуюструктуру илиphysicalEOS/stress.

Fivewrongcontrols обнаружены: forwardmomentum Ap вместоA^-Tp даёт
workpairingrelativeerror0.267196; Euclideanp=mV даётaxialerror0.754811;
positionAx вместоλx меняетtensor на0.794254; centre-affine approximation
scale²D ошибается на0.209814; density treatedas scalar меняетmass на0.659160.
Это explicitnegativecontrols; они не реализованы в runtime.

## Проверенные строки

| Задача | Код | Проверка |
|---|---|---|
| Nonlinearposition/vector/covector/metric | [snapshot](C:/Users/Admin/Desktop/Solar-simulator/scripts/chart_current.py:30) | [independentcomplexJacobian andpairings](C:/Users/Admin/Desktop/Solar-simulator/tests/test_chart_current.py:13) |
| Currentdensityweight | [pullback](C:/Users/Admin/Desktop/Solar-simulator/scripts/chart_current.py:20) | [inverseJacobian density](C:/Users/Admin/Desktop/Solar-simulator/tests/test_chart_current.py:34) |
| Rawcoordinate D/C/STF | [snapshot](C:/Users/Admin/Desktop/Solar-simulator/scripts/chart_current.py:30) | [affinelimit/no recentre](C:/Users/Admin/Desktop/Solar-simulator/tests/test_chart_current.py:27) |
| Independentanalyticangular/radial oracles | [analytic](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_current_reference.py:26) | [angularintegrals](C:/Users/Admin/Desktop/Solar-simulator/tests/test_current_reference.py:6) |
| Freshsourcefrozen3Daudit | [audit](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_chart_current.py:56) | [allcriteria](C:/Users/Admin/Desktop/Solar-simulator/tests/test_current_audit.py:15), [corruption](C:/Users/Admin/Desktop/Solar-simulator/tests/test_current_audit.py:25), [offlineimport](C:/Users/Admin/Desktop/Solar-simulator/tests/test_current_audit.py:39) |

Targeted17passed1.44s. First105testfixture gaveboth irregularorigin and
ill-conditioned differential, so earliercentre guardcorrectly fired.
Original1failed/9passed/source/log retained `.tools/rotation100-109/test105-failure`.
Fixturenowisolates illconditioning atnoncentre nodes; no production/tolerance
change. Theseproofs do notcertify temporal E/J conservation, physicalPNfluid
tensor, gravitationalfieldspin/ADM/SSC, fullLunar initialization or tides.
