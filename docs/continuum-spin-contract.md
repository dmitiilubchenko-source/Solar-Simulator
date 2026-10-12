# Континуальная сфера и slowrotation: договор86–90

Продолжение [bound Newton body83–85](bound-body-contract.md).
Исследовательский предел: статическая сфера постоянной **энергетической**
плотности ε и линейное по angularvelocity вращение идеальной жидкости в GR.
Несжимаемый EOS имеет бесконечную скорость звука; это математический эталон,
не причинная модель вещества и не физическая PN-инерция Луны.

## Входы, определения и источники

| Величина | Определение в этом стенде | Что ещё нужно для Луны |
|---|---|---|
| M kg | Gravitational mass из exterior Schwarzschild | Baryon/rest mass и происхождение параметров |
| R m | Areal radius: площадь сферы4πR² | Harmonic/ADM/PA radius map |
| ρe kg/m³ | ε/c²=3M/(4πR³), constant | Conservedρ* ≠ properrestρ ≠ activeΣ |
| p Pa | Isotropic perfect-fluid pressure; surface p=0 | Elastic stress tensor, EOS и слои |
| Internal energy | Already included in ε; не выделена Π | Thermodynamic rest/internal split и flows |
| t s | Asymptotic Schwarzschild coordinate time | TDB/TCB/localtime qualification |
| Ω rad/s | dφ/dt относительно distant inertial observer | Tisserand/PA/SSC/bodyattitude relation |
| J kg m²/s | Exterior angular momentum linear in Ω | Canonical/harmonic/ADM centre/spin map |
| I kg m² | J/Ω, spherical scalar slowrotation limit | Tensor inertia/multipole/finiteΩ qualification |

[Hartle1967, ApJ1501005, DOI10.1086/149400](https://articles.adsabs.harvard.edu/pdf/1967ApJ...150.1005H)
проверен визуально по оригинальному PDF: p1012(25–29),p1014(38–43),
p1015(46–49). Это radial structure ODE, не эволюция орбиты во времени.
[Reina2015/2016, (12–16),(23–27)](https://arxiv.org/pdf/1503.07835)
проверяет surface matching и homogeneous background. Его second-order
surface-mass correction(22) здесь **не** реализована; при constantε surface
jump её нельзя забывать в будущем полном расчёте порядкаΩ².
[Chan/Chan/Leung2015,(2.4–2.10),(3.11)](https://arxiv.org/pdf/1411.7141)
даёт независимое опубликованное compactness expansion I/(MR²).

[Kopeikin/Vlasov2004, (9.2.1–3),(9.3.10),(10.1.3)](https://arxiv.org/pdf/gr-qc/0403068)
использован для выявления недостающих continuum inputs, не переноса их
bare-spin коэффициентов в новый chart. Их gauge/ρ*/centre definitions
не объявляются теми же, что Schwarzschild areal-radius benchmark.
Формулу KlionerPN-inertia из плохого OCR по-прежнему не реализуем.

## Static background, SI

C=GM/(Rc²), s=r/R. Domain benchmark1e-12≤C≤0.3,0≤s≤1;
физический pressure singular limit C=4/9 остаётся вне области helper.
u=sqrt(1−2Cs²), A=sqrt(1−2C), N=(3A−u)/2.
Metric ds²=−N²c²dt²+dr²/u²+r²dΩ_sphere².
m(r)=M s³; p/(ρe c²)=(u−A)/(3A−u).
Для малых C numerator вычисляется равнозначно без потери разности:
p/(ρe c²)=C(1−s²)/[(u+A)N]. Никакого epsilon/softening.

Newton limit при той же leading M/R:
ρ=3M/(4πR³), U=GM(3−s²)/(2R)>0,
pN=ρGM(1−s²)/(2R), radialg=−GM s/R²,
I_N=2MR²/5, gravitationalenergy W_N=−3GM²/(5R),
∫pN dV=GM²/(5R), W_N+3∫pN dV=0.
Conserved baryonic mass в GR этим leadingNewtonM не определяется.

## Linear rotation and exterior matching

j=u/N, f=barω/barω_c, barω=Ω−ω_frame, f(0)=1,f'(0)=0.
Производные по s; L=j'/j=−2Cs/u²−Cs/(uN).
(s⁴j f')'+4s³j' f=0,
f''=−(4/s+L)f'−4L f/s.
При s=0 используем regular-limit f''(0)=−4 L'(0)f(0)/5,
L'(0)=−C[2+1/N(0)]. Этот точный предел не hidden cutoff.

Boundary Ω/barω_c=f(1)+f'(1)/3,
J/barω_c=c²R³ f'(1)/(6G),
a=I/(MR²)=f'(1)/[6C(f(1)+f'(1)/3)].
Normalized fΩ=barω/Ω; exterior fΩ(s)=1−2C a/s³, s≥1.
SI charges helper требует Ω²R³/(GM)≤1e-2; это область slowrotation
benchmark, не доказанная оценка пропущенной Ω² ошибки.
Continuity of fΩ and derivative вs=1 проверяется явно.
Hartle(49): a=−2/(3C)∫_0^1 s³j' fΩ ds.

## Independent pressure/Riccati reference and analytic order

Из staticEinstein equations L=−3Cs(1+p/(ρe c²))/(1−2Cs²).
Это независимое stress-source вычисление без productionmetric derivatives.
z=s f'/f решает z'=−z(z+3)/s−L(z+4), z(0)=0,z'(0)=0.
Его boundary a=z(1)/[2C(3+z(1))]; различны переменные и вычисление L.
RK45 двух уровней + tighterDOP853 сравниваются с rawproduction f/f'.
Referenceprofile z(s) проверяет всю radial structure, не только endpoint.

Наш order-by-order вывод из ODE при f(0)=1:
L=−3Cs−(3s/2+9s³/2)C²+O(C³),
f=1+(6s²/5)C+(3s²/5+99s⁴/70)C²+O(C³),
Ω/barω_c=1+2C+(301/70)C²+O(C³),
a=2/5+(12/35)C+O(C²).
Последний коэффициент отдельно совпадает с Chan(3.11), где следующий
равен212/525. FirstPN остаток должен быть O(C²)=O(c^-4) при fixedM/R,
а quadraticcompactness остаток O(C³). Не fit coefficients по новымjobs.

No-pressure reference — намеренно неверный контроль L=−3Cs/(1−2Cs²):
сохраняет Newton limit, но даёт slope2/7 вместо12/35. Это не alternativeEOS.
Newton constantI, omission Ω boundary matching и assumptionbarω=Ω
также дают контролируемые ошибки. Инерция ещё не добавляется к runtime.

Этот benchmark не учитывает finiteΩ² shape/mass correction/rotationenergy,
нет time-orbit PNreaction Hamiltonian, multipole tensors, tides или lunarinit.
Консервативный NewtonE/J из85 не становится общим PN-инвариантом.
Критерии radialjobs и compactness limits зафиксированы до audit89.

## Проверенные функции и тесты

| Задача | Код | Проверка |
|---|---|---|
| SI/background parameters | [Sphere](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_sphere.py:28) | [bad scales](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_sphere.py:55), [domain](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_sphere.py:60) |
| Metric/pressure/TOV/surface | [background](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_sphere.py:61) | [complex derivative/TOV](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_sphere.py:10), [stable smallC](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_sphere.py:27) |
| Newton pressure/field/virial | [profile](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_sphere.py:74), [integrals](C:/Users/Admin/Desktop/Solar-simulator/scripts/continuum_sphere.py:85) | [volume integrals](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuum_sphere.py:37) |
| Raw f/fprime radial ODE | [rhs](C:/Users/Admin/Desktop/Solar-simulator/scripts/fluid_spin.py:12) | [regularcentre/stress-source](C:/Users/Admin/Desktop/Solar-simulator/tests/test_fluid_spin.py:9), [independentC expansion](C:/Users/Admin/Desktop/Solar-simulator/tests/test_fluid_spin.py:21) |
| Exterior/charges/slowdomain | [boundary](C:/Users/Admin/Desktop/Solar-simulator/scripts/fluid_spin.py:27), [charges](C:/Users/Admin/Desktop/Solar-simulator/scripts/fluid_spin.py:37), [exterior](C:/Users/Admin/Desktop/Solar-simulator/scripts/fluid_spin.py:53) | [SI matching](C:/Users/Admin/Desktop/Solar-simulator/tests/test_fluid_spin.py:30), [finiteΩ domain](C:/Users/Admin/Desktop/Solar-simulator/tests/test_fluid_spin.py:54) |
| Pressure-Riccati/TOV reference | [Riccati](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_fluid_reference.py:21), [TOV](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_fluid_reference.py:34) | [independent TOV derivative](C:/Users/Admin/Desktop/Solar-simulator/tests/test_fluid_spin_audit.py:26) |
| Published inertia coefficients | [series](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_fluid_reference.py:39) | [polynomialODE](C:/Users/Admin/Desktop/Solar-simulator/tests/test_fluid_spin.py:21) |
| Matter-current integral | [integrand](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_fluid_reference.py:55) | [Newtonlimit](C:/Users/Admin/Desktop/Solar-simulator/tests/test_fluid_spin_audit.py:18) |
| Source/primary lifecycle | [codeguard](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_fluid_spin.py:25), [primaryguard](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_fluid_spin.py:38), [audit](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_fluid_spin.py:52) | [allcriteria](C:/Users/Admin/Desktop/Solar-simulator/tests/test_fluid_spin_audit.py:34), [primarychanges](C:/Users/Admin/Desktop/Solar-simulator/tests/test_fluid_spin_audit.py:45), [freshpaths](C:/Users/Admin/Desktop/Solar-simulator/tests/test_fluid_spin_audit.py:58), [cleanofflineimport](C:/Users/Admin/Desktop/Solar-simulator/tests/test_fluid_spin_audit.py:68) |

Импорт использует только code/policy sourceclosure. Fullscientificaudit требует
localprimarycache доjobs и сверяет primarySHA междуjobs/поокончании; offline
импорт не даёт разрешения на непроверенный scientificreport.
[Числа, отказы, исправление90 и ограничения](continuum-spin-validation.md).
