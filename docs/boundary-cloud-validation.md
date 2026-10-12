# Freshaudit локальных событий и SR-облака79–82

[Договор и проверенные строки](extended-boundary-contract.md).
[Policy доjobs](C:/Users/Admin/Desktop/Solar-simulator/scripts/boundary-cloud-policy.json:1).
[JSONreport](boundary-cloud-validation.json), SHA256
c1b4089093fe12750ede988cd3a91cb9ba5f717269f9499723fdadac875160f8.

## Стенд и статус

6свободных частиц,3symmetrypairs:2/3/4kg eachpair;
positivepositions(1200,300,-200),(-900,1100,400),(400,-600,1400)m,
opposites; initial Ω=(.15,−.2,.3)rad/s, V=(300,−400,500)m/s.
Synthetic c=50000/100000/200000m/s; никакой астрономической интерпретации.
10s,257равномерных epochs. Для сравнения x/2000m, p/10000kgm/s.
Restcloud задан в localT=0, globalt0 particles имеют разные localtimes.

Аналитические общие globalt snapshots сравнены с independentHamiltonian
H=Σsqrt(m²c4+c²p²), complex-step ∂H/∂p и свободной динамикой p'=0.
RK45 rtol1e-11/2e-13 и DOP8532e-13; atol=rtol/50,maxu step1/64.
Запуск0.339s,3ODEjobs; эта простая линейная траектория не требует долгого
расчёта и не является новым многолетним gravity/DE441 аудитом.
20maximum/7minimum/5boolcriteria passed.37новых unitchecks79–82 passed1.12s.

228sources (226Python+2usedpolicies), исполненные копии и5NPZ SHA сохранены
в.tools/rotation82; shape/finite/rawinitial/grid reverified.
Транзитивно используемые metric-spin-policy и integrate_raw_initial78
включены явно; прошлые successful/failedreports не переиспользованы.
Rawepoch0 сохраняется непосредственно; никакого SO3/spin projection.
Python/NumPy/SciPy версии записаны, binarydependencies не SHA-прикреплены.

## Числа

| Проверка | Результат | Предел |
|---|---:|---:|
| Lorentzmetric defect | 3.511e-16 | 1e-12 |
| Common-global-time cΔt/lengthscale | 8.731e-14 | 1e-11 |
| TotalP covariance | 0 | 1e-11 |
| TotalJ covariance relative | 2.243e-13 | 1e-9 |
| Energy/J drift | 0 / 2.308e-13 | 1e-11 / 1e-9 |
| Individual massshell relative | 3.391e-16 | 1e-11 |
| Covariant/lab SSC scaled | 1.561e-13 / 2.026e-13 | 1e-11 |
| Centroidformula/2000m | 1.216e-15 | 1e-11 |
| Spin4 covariance / Euclideanspin relative | 2.371e-15 / 2.378e-15 | 1e-9 |
| Reference x/2000m / p/10000kgm/s | 8.006e-15 / 0 | 1e-9 / 1e-11 |
| Referencelevel x/2000m sensitivity | 1.776e-15 | 1e-9 |
| DOP vs RKreference x/2000m | 1.421e-14 | 1e-9 |
| Newton density-pair / affineimage identity | 0 / 8.738e-17 | 1e-11 |

Positionagreement1.601e-11m, referencelevel sensitivity3.553e-12m,
DOP difference2.843e-11m — numericalcomparisons этой простой траектории.
Tighter/methoddifference может оказаться больше agreement при float64;
это не строгая true-error оценка и не физическая точность Луны.

Remainderclock/time/position/spatialJac/velocity и kineticspin при doublingc
уменьшается в15.99996–16.00235раз. Criterion15.9–16.1 пройден.
Сходимость показывает порядок усечения именно этих величин при fixedinput,
а не completeness PN-модели протяжённого тела.

## Отрицательные контроли

| Намеренный дефект | Значение | Заданный minimum |
|---|---:|---:|
| CommonlocalT вместо commonglobalt: errorcΔt/2000m | 0.010701 | 1e-4 |
| Та же ошибка: positions/2000m | 0.00015436 | 1e-5 |
| Игнорировать centroidshift/2000m | 8.027e-6 | 1e-6 |
| Metricroot как SO3: Gramdefect | 0.00020000 | 1e-5 |
| Newton CΩ как exact kineticspin | 5.201e-5 | 1e-6 |
| Наивное ACA^T как inertiaimage | 0.00014947 | 1e-6 |
| OmittedgradT в velocity | 0.00022398 | 1e-6 |

Все обнаружены. FreeJ conservation не является негативным контролем
одновременности: каждый freeparticle Jtensor инвариантен вдоль worldline.
Поэтому ошибки среза проверяются общим временем событий и позициями.

## Сохранённый отказ и область действия

Первый subset79/80:22passed/1failed. Тест ошибочно требовал localtime
spread>1ms; реальная геометрия давала0.84959984ms. Никакой физический закон
не требует этого порога. Его заменили independentidentity ΔT=−V·ΔX/c²
при commonglobalt с исходным relative1e-11. Отказ сохранён в
.tools/rotation79-82/test80-failure.json до началаfresh82; policy82 неизменна.
Centre-shift test отдельно tightened1e-9→1e-11 и прошёл.

ExactfreeSRcloud не жёсткое тело: начальное Ω задаёт лишь velocities.
Нет binding/centripetalstresses/selfgravity/pressure/internalenergy модели.
Kineticspin c^-2 correction нельзя объявить полной lunarPNinertia.
Newton C/M compatibility не обязывает generalPNmoments иметь тот же вид.
Leadingevent карта ещё не даёт полный harmonic→ADM/SSC/multipole boundary,
взаимодействующую extendedbodyPN динамику или time-scale qualification.
Физический lunarinitialspin не изменён. Приливы остаются следующим
физическим направлением после conservativeextendedbodyqualification.

Полный check_project:1061Python passed169.55s (включая37новых),17Rust,
fmt обоихcrates passed,1103file/line links.340oldstatusentries/main сохранены;
runtime/data/receipts/oldreports unchanged. Finalverification локально в
.tools/rotation79-82; publication/portable вне задачи.
Финальная сверка passed:453из457baselinefiles unchanged, обновлены только
4private docs;135старыхJSON и68runtime/Rustfiles сохранены. Все228sourcecopies
и5NPZ повторно проверены по SHA/shape/finite/rawinitial/grid; handoff75строк,
старый handoff и archiveprefix сохранены побайтно.
