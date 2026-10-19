# Свободный лунный ротор: протокол260

17 октября2026, до результатов. Только research, без смены runtime/default,
Rust, IC, GM/I или EIH+dynamic-spin guard. Предыдущие неуспехи сохраняются.

## Модель

Прежние10 тел, SI/SSB/Ecliptic J2000/JD2461321.5 TDB. Взаимные point
Newton+order-reduced EIH1PN, прежние fixed Sun/Earth J2 с реакциями,
один Newton solid-equivalent Moon Q2, связанный с той же I из профиля51.
q body→space, S пространственный, qdot=(0,omega)⊗q/2,
omega=R I⁻¹ Rᵀ S, Sdot=tauQ. Q/реакция/torque из одного потенциала.
Взять из профиля51 только начальные q/S; орбитальные IC из strict seed.
После t0 не брать будущие R/Rdot в RHS. Нет SO/PN-I/SSC/деформаций/приливов.
Это явная приближённая модель, не полная физическая модель Луны.

Основание: [Newton rigid-Q2](conservative-rotation.md),
[первичный GRIT](https://doi.org/10.3847/1538-4357/ac0e97),
[вывод harmonic EIH/rotor](hybrid-rotation-protocol.md),
[Vines, EIH action, стр3](https://fiteoweb.unige.ch/~maggiore/GWVol1/EIHLagrangian.pdf).
Локальный первичный Vines SHA b46e92e61735189459b1732cc29a1330c6480ab1bb2dd13630cebed2de4c4c2f;
формулы прежние, новой теории/сетевого запроса не требуется.

E=EEIH+Trot+Ufixed+UMoon, P=sum pEIH, J=sum x×pEIH+S.
Для OR не требовать константных полных Noether величин без источников:

```text
B(f)=[sum v·f, sum f, sum x×f]
d(E,P,J)/dt = B(H1 aPN)+B(H1(aFixed+aMoon))
             + [0,0,0,0,sum x×(m aFixed)]
```

Moon orbital torque уже сокращён с Sdot. Fixed axes внешние: их torque
остаётся в бюджете полного J; статические Ufixed не совершают внешнюю
работу. Успех глобального баланса не доказывает видимость каждого малого
источника: Noether visibility FAIL219–222 этим опытом не отменяется.

## Численный опыт и критерии до вычисления

32 суток,129 эпох через21600с, без подгонки по будущим данным.
Прямые численные переменные EMB+rho для Earth/Moon, остальные SSB;
явное M0=Sun mass,L0=AU,T0=sqrt(L0³/(GM0)), S масштабирован начальной
нормой. Это смена единиц/линейных переменных, не boost/clock mapping.
В EIH скорости SSB, точная solver rho передаётся для pair расстояния.

- Production DOP853: nominal rtol1e-12/maxstep3600s/xatol1e-3m/vatol1e-9m/s,
  q/Sscaled atol1e-13; tight3e-14/1800s/1e-4m/1e-10m/s/1e-14.
  Контроль худшего блока каждого x/v, отдельные rho/relative-v/q/S/budgets.
- Независимый reference RK45: scalar-target EIH, матрицаR и body-Euler Pi,
  Newton body-frame inertia force; fixed tensor field. Никаких runtime
  quaternion/figure force в RHS эталона. Два уровня rtol1e-12/3e-14,
  maxstep1800/900s, те же SI atols как соответствующие production.
  Worst-block RK45, не общее RMS по состоянию.
- Production nominal/tight: allbody max position<4м, pair<.2м,
  velocity<1e-5м/с, orientation matrix Frobenius<2e-7, relativeS<2e-7.
- Reference nominal/tight: allbody<1м, pair<.05м, velocity<3e-6м/с,
  matrix<1e-7, relativeS<1e-7.
- Production tight/reference tight: allbody<2м, pair<.1м,
  velocity<5e-6м/с, matrix<1e-7, relativeS<1e-7.
  Сохранять по-тельные ошибки и чувствительность самого эталона.
- Raw q norm deviation<1e-8; reference R orthogonality/determinant<1e-8.
- На всех129 эпохах total E/P/J читать отдельно Decimal70; вычитать
  начальные значения до float. Max corrected scaled E/P/J<1e-11.
  В той же диагностике9 эпох сравнить Decimal70/90<1e-30.
  Три отдельных бюджета и raw drift сохранять, не называть floor видимостью.
- На t0 независимый RHS bridge own force/torque<5e-10 и отрицательный
  контроль отсутствия torque/reaction; analytic two-body/Newton limits,
  координатный roundtrip и запрет будущей ориентации в тестах.
- Контрольный strict point+fixed без lunarQ: тот же initial orbit,
  nominal DOP settings, без fit. Отдельно измерить различие моделей.
- Только после свободных расчётов сравнить baseline/free с локальным
  квалифицированным DE441 на129 эпохах; сохранить все ухудшения и max/RMS
  каждого тела/relativeMoon, ориентационные остатки. Цели10км/body,
  1км/pair для этого короткого окна — отдельные статусы, не критерий
  правильности арифметики и не годовая квалификация.
- Внешняя R(t) разрешена только для сравнения ПОСЛЕ propagation.
  DE441 reader uncertainty/различие моделей/численная чувствительность
  не складываются в строгий error bound. Полный год не запускать автоматически.

JSON+полные NPZ, стоимость/nfev/версия библиотек/источники/данные SHA,
сохранение partial и fresh outputs обязательны. Во время jobs код заморожен.
Сначала короткий preflight, затем32суток; при отказе сохранить причину,
порог не ослаблять. Offline publiccopy повтор с запрещённой сетью и
свежим reader receipt. Связанные тесты, рабочий runtime не изменяется.
