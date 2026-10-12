# Локальные события и свободное SR-облако: договор79–82

Модельные проверки расширяют [метрический pointspin](metric-spin-contract.md).
Ни один из новых инструментов не назначает PN-инерцию Луны или не меняет
runtime/H57/strictreceipts/DE441. Все входы SI и относятся к явно выбранным
координатам/времени. Глобальная и локальная эпохи задаются отдельно.

## Leading локальная карта событий

[Soffel et al.2003, Appendix IAU B1.3, p35](https://arxiv.org/pdf/astro-ph/0303376)
даёт координатное преобразование; здесь реализована только часть c^-2.
Пусть z(t),v,a,j — движение центра; r=x−z(t), U — внешний скалярный
потенциал на центре, Udot — его materialderivative. Заданные B/Bdot
определяют дополнительную SO(3) gauge. Кинематически невращающаяся
исходная карта соответствует B=I. Формулы стенда:

T=Tcentre−v·r/c²,
X=B F, F=r+[v(v·r)/2+U r+r(a·r)−a r²/2]/c²,
dTcentre/dt=1−(v²/2+U)/c².

Нужны все четыре блока ∂tT,gradT,∂tX,∂xX. При фиксированном x,
dr/dt=−v; ∂tT=centre_rate−a·r/c²+v²/c², gradT=−v/c².
Для материальной globalvelocity vg: dT/dt=∂tT+gradT·vg,
dX/dT=(∂tX+∂xX vg)/(dT/dt).
Inverse velocity решает (∂xX−outer(vlocal,gradT))vg=
vlocal ∂tT−∂tX. Пространственного поворота/центрального clockrate недостаточно.

Jet содержит явные jerk и Udot: без них невозможно правильно вычислить
производную пространственной карты в ускоряющейся системе.
from_sources вычисляет Udot=∂tU+v·gradU для внешних monopoles75.
Self-field исключён. Область: U/c²≤1e-3, |vcentre|²/c²≤1e-3,
|a||r|/c²≤1e-3; materialglobaltrajectory subluminal и dT/dt>0.
Данные не recentre/нормируются/проецируются автоматически.

Стенд не реализует c^-4 time transformation, TDB→TCB, абсолютный offset,
surfaceclock, полный ADM/multipole map или динамически вычисленную B.
Jacobian d(cT,X)/d(ct,x) безразмерен. Его ct/time-space block относительно
exactLorentz может иметь leading c^-3 remainder из-за множителя c.
Поэтому c^-4 audit сравнивает clockrate/time/position/spatialJac/velocity
с указанными физическими единицами отдельно, не общий4Dnorm.

## Exact свободное облако

Это замкнутая модель массивных свободных частиц в Minkowski(-+++), x0=ct.
В localT=0 явно задан restframe: sumspatialP=0 и energycentroid=0.
Позиции/скорости не корректируются для выполнения этих условий.
Частицы имеют En=mγn c², pn=mγn un, Xn(T)=Xn0+un T.
После начального снимка они расширяются, а не остаются жёстким телом.

Rotationless activeLorentz boost с velocityV переводит restingorigin
в движущийся со скоростью+V. Для среза общего globalt каждый Tn получается
отдельно: Tn=[t/γV−V·Xn0/c²]/[1+V·un/c²].
Суммы P4=Σpn4 и Jµν=Σ(xµpν−xνpµ) сравниваются с преобразованными
resttensors. Энергия и angularmomentum conserved, но conservationalone
не подтверждает одновременность: individualfreeparticle Jµν постоянно
вдоль всей worldline. Неверный commonslice нужно проверять событиями.

[Costa/Natário, arXiv1410.6443v2, §2 (1)–(4)](https://arxiv.org/pdf/1410.6443)
определяет momentum/angularmomentum и наблюдательский centroid через
energy-momentum. Для этой дискретной модели на общем globalt:
ZE=ΣEn xn/ΣEn; covariantcentreZ=Vt. Из tensorboost следуют
ZE−Z=V×Srest/Erest,
angularSaboutZ=Sparallel+γV Sperp,
angularSaboutZE=Sparallel+Sperp/γV.
AboutZ выполняется Sµν Pν=0; aboutZE временные компоненты angular2form
нулевые. Это два разных SSC; energycentroid не объявляется ADM-centre.

Spin4 получается из Pauli-Lubanski contraction
Sµ=εµνρσ Pν Jρσ/(2Mc), ε0123=+1, как convention
[DJS2008, §II и (6)–(10)](https://arxiv.org/html/0711.1048v2).
Этот intrinsicvector не зависит от выбора origin. Его covariantspatial
компоненты и positive-root H отдельно дают Euclideanspin.
Для rotationless boost restcloud этот S равен Srest; spatialdual angular
2form в lab не является тем же covariantspatial vector. H не SO3.

## Newton moments и kinetic snapshot

На одном заданном localT=0 с rest-mass weights: D=ΣmXXT,
C=tr(D)I−D, M=D−tr(D)I/3=−STF(C). Positive-semidefiniteD — необходимая
реализуемость второго момента положительной плотности. В данной convention
Q2potential=−3G mpoint n·M·n/(2r³), как в local_multipole72.
Это диагностическая проверка общего Newtondensity; независимые effective
C/M модели72 намеренно остаются феноменологическими и не изменяются.

При affineimage A X: D'=ADAT и C'=tr(D')I−D'. ACA^T не является общим
правилом Euclidean-inertia при неортогональном A; аналогично STF не
коммутирует с таким A. Это алгебра данного распределения restmasses,
не универсальное правило преобразования PN-gravitational multipoles.

Для начальных скоростей un=Ω×Xn exactkineticJ=Σmγ X×u,
NewtonJ=CΩ, leadingkineticcorrection=Σ(m|u|²/2c²) X×u.
Сумма нелинейна по Ω; это не новая постоянная PN-инерция.
Bindingenergy/centripetalstresses/selfgravity отсутствуют. Модель нельзя
использовать как физическое описание вращающейся Луны.

## Код и независимые проверки: проверенные строки

| Задача | Код | Проверки |
|---|---|---|
| Explicit jet/source derivatives | [Jet](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_event_map.py:22), [from_sources](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_event_map.py:60) | [centreclock/translation](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_event_map.py:53) |
| Four-block event Jacobian | [event](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_event_map.py:86) | [complex-step/chainrule](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_event_map.py:34) |
| Velocity/inverse | [velocity](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_event_map.py:115), [inverse](C:/Users/Admin/Desktop/Solar-simulator/scripts/local_event_map.py:127) | [same independent check](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_event_map.py:34) |
| Lorentz boost | [boost](C:/Users/Admin/Desktop/Solar-simulator/scripts/sr_cloud.py:23) | [metric/inverse](C:/Users/Admin/Desktop/Solar-simulator/tests/test_sr_cloud.py:16) |
| Common-global-t slice | [snapshot](C:/Users/Admin/Desktop/Solar-simulator/scripts/sr_cloud.py:76) | [exact simultaneity/centroids](C:/Users/Admin/Desktop/Solar-simulator/tests/test_sr_cloud.py:25) |
| Charges/centres/spin4 | [charges](C:/Users/Admin/Desktop/Solar-simulator/scripts/sr_cloud.py:91), [spinvector](C:/Users/Admin/Desktop/Solar-simulator/scripts/sr_cloud.py:118) | [SSC/root](C:/Users/Admin/Desktop/Solar-simulator/tests/test_sr_cloud.py:25), [conservation](C:/Users/Admin/Desktop/Solar-simulator/tests/test_sr_cloud.py:57) |
| D/C/M compatibility | [mass_moments](C:/Users/Admin/Desktop/Solar-simulator/scripts/density_moments.py:21), [density_pair](C:/Users/Admin/Desktop/Solar-simulator/scripts/density_moments.py:35) | [particle potential](C:/Users/Admin/Desktop/Solar-simulator/tests/test_density_moments.py:8), [affineimage](C:/Users/Admin/Desktop/Solar-simulator/tests/test_density_moments.py:19) |
| Kinetic spin-limit | [rotation_snapshot_spin](C:/Users/Admin/Desktop/Solar-simulator/scripts/density_moments.py:55) | [directparticle/multipleΩ](C:/Users/Admin/Desktop/Solar-simulator/tests/test_density_moments.py:31) |
| Independent free Hamiltonian | [scalar](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_sr_reference.py:9), [complexgradient](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_sr_reference.py:13) | [gradient/order](C:/Users/Admin/Desktop/Solar-simulator/tests/test_boundary_cloud_audit.py:14) |
| Freshaudit/freeze | [audit](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_boundary_cloud.py:79) | [policy/importclosure](C:/Users/Admin/Desktop/Solar-simulator/tests/test_boundary_cloud_audit.py:39), [nooverwrite](C:/Users/Admin/Desktop/Solar-simulator/tests/test_boundary_cloud_audit.py:55) |

[Результаты и существенные ограничения](boundary-cloud-validation.md).
