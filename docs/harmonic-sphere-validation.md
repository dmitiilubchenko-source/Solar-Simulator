# Гармоническая карта100–104: результаты независимого аудита

[Уравнения и explicit gauge choice](harmonic-sphere-contract.md),
[проверенный JSON](harmonic-sphere-validation.json).
Current104 уточняет исходный неуспешный IVP reference, не меняет модель,
policy tolerances или criteria. Static constant-energy-density sphere,
selected smooth harmonic Cartesian chart; не ADM/SSC/Lunar initial mapping.

## Протокол и результаты

8C:0.008/0.002/0.0005/0.02/0.1/0.25/0.3/0.0001;513radialnodes,
32freshIVP jobs,48NPZ,263executedcode/policy/primary copies,7.660272s.
20maximum+5minimum+5boolean criteria fixed доfirstaudit иunchangedinrefinement.
Production rawF/Fprime DOP853; independent shiftedRiccati/logF RK45twolevels
иtighterDOP853. PositiveGauss32/64 exteriorbasis independentof128-termseries.
Raw signedzero initial/grid andallarrays bitwiseverified; source/primarySHA
иcopies rechecked. No reuseofoldharmonic trajectories.

| Проверка | Максимальный результат | Предел |
|---|---:|---:|
| Exteriorbasis/independentintegral scaled | 2.85e-14 | 1e-11 |
| Gauss32/64 basis scaled sensitivity | 6.40e-14 | 1e-11 |
| Vacuumoperator scaled residual | 5.33e-15 | 1e-11 |
| Independentradius profile difference | 2.04e-14 | 1e-8 |
| Independentderivative profile difference | 3.05e-13 | 1e-8 |
| RK45 referencelevels sensitivity | 2.76e-10 | 1e-8 |
| RK45/tighterDOP853 sensitivity | 3.05e-13 | 1e-8 |
| Matching scale/residualgauge agreement | 2.67e-15 / 5.41e-15 | 1e-8 |
| Currentdensityweight relative difference | 3.53e-13 | 1e-8 |
| Pointwise volume/current pullback | 6.67e-16 | 1e-11 |
| Independentharmonicoperator residual/C | 6.67e-12 | 1e-8 |
| Surface value/firstderivative | 2.23e-16 | 1e-11 |
| Surface metric/current measure | 8.89e-16 | 1e-11 |
| Surface metricfirstderivative | 3.11e-15 | 1e-10 |
| Matrixconditioning maximum | 4.822069 | 1e8 |
| Sampledminimum radial/tangentJacobian | 0.579193 | >0.05 |

Origin metric isotropy defect0. Publishedfirstorderremainders c^-4 ratios
16.0222–16.0895; quadraticremainders c^-6 ratios64.1275–64.5179,
withinfixed16±1 /64±2. SmallC residualgauge coefficient deviation from
−4/35 is6.351e-5<0.002. Tailbounds are analytic series truncation bounds;
they exclude float64 summation error, so are not total numerical error bounds.

Wrongcontrols detected: zeroresidualgauge derivativejump0.0655525,
isotropicmap substitutedintoharmonicoperator0.0711513,
arealmap substitutedintoharmonicoperator1.5, growingexterior usedatorigin0.3.
They are not alternate valid implementations of the chosen global chart.
No physicalDarmoiscondition falsely imposed: smoothderivative continuity is
an explicit coordinate choice, while other chart choices are possible.

## Исходный отказ и устранение причины

First104 failed atC=.02 tighterDOP853 nearorigin, after15completedjobs/21NPZ.
Full originalcode/policy/arrays/error retained `.tools/rotation104`;
firstlog `.tools/rotation100-109/audit104.log`. Solver warnings and failure
were not suppressed or treated as convergence. Diagnosis samples: constant
floating residual−2.7756e-17 in K(s)−5w dividedbys; this breaks O(s)
regular scaling belowabout1e-8 and eventually forces pathological steps.

Let w0=C[6−1/N0]/5 andδ=w−w0. Exact algebra yields
(K(s)−K0)/s²=12C²/u²−C²(3A−1−u)/[(1+u)uNN0].
Then δ'=s(K−K0)/s²−5δ/s−s(w0+δ)(w0+δ+a/s),δ0=0.
This removesconstant subtraction without cutoff, epsilon,projection,
solverfallback or relaxed tolerance. OriginalRiccati variable and equations
remain in99contract as the analytic derivation; currentcode storesδ/logF.
Newregression verifies regularscaledsource at1e-4…1e-14. Corrected42targeted
tests passed1.92s; fresh32jobs/48NPZ completed withall30criteria passed.
Currentwork `.tools/rotation104-r2`; firstfailure is separate andimmutable.

Agreement2e-14 does not replace referencelevel sensitivity2.76e-10,
and neither qualifies physical lunar accuracy. Benchmarkdomain1e-4≤C≤0.3
excludes Moon compactness; incompressible EOS remains acausal.

## Код и проверенные строки

| Задача | Код | Проверка |
|---|---|---|
| Regular rawinterior | [rhs](C:/Users/Admin/Desktop/Solar-simulator/scripts/harmonic_sphere.py:20) | [independentoperator](C:/Users/Admin/Desktop/Solar-simulator/tests/test_harmonic_sphere.py:8) |
| Stablevacuum/analytic tails | [series](C:/Users/Admin/Desktop/Solar-simulator/scripts/harmonic_sphere.py:44), [tailbounds](C:/Users/Admin/Desktop/Solar-simulator/scripts/harmonic_sphere.py:60) | [quadrature/operator](C:/Users/Admin/Desktop/Solar-simulator/tests/test_harmonic_sphere.py:27) |
| Globalmatching/metric/currentweight | [match](C:/Users/Admin/Desktop/Solar-simulator/scripts/harmonic_sphere.py:90), [interior](C:/Users/Admin/Desktop/Solar-simulator/scripts/harmonic_sphere.py:104), [exterior](C:/Users/Admin/Desktop/Solar-simulator/scripts/harmonic_sphere.py:126) | [surface/origin](C:/Users/Admin/Desktop/Solar-simulator/tests/test_harmonic_matching.py:9), [residualgauge](C:/Users/Admin/Desktop/Solar-simulator/tests/test_harmonic_matching.py:24) |
| Shiftedindependentreference | [Riccati](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_harmonic_reference.py:16), [integralbasis](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_harmonic_reference.py:30) | [profile](C:/Users/Admin/Desktop/Solar-simulator/tests/test_harmonic_reference.py:9), [tinycentre](C:/Users/Admin/Desktop/Solar-simulator/tests/test_harmonic_reference.py:43) |
| Frozenaudit | [audit](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_harmonic_sphere.py:53) | [allcriteria](C:/Users/Admin/Desktop/Solar-simulator/tests/test_harmonic_audit.py:15), [corruption](C:/Users/Admin/Desktop/Solar-simulator/tests/test_harmonic_audit.py:25), [offlineimport](C:/Users/Admin/Desktop/Solar-simulator/tests/test_harmonic_audit.py:45) |

Full PN tensor/stress/multipoles, extendedbody conservativeHamiltonian E/J,
ADM/SSC/Lunar initialmapping иtides остаются отдельными будущими задачами.
