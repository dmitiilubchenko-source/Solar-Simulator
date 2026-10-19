# Harmonic EIH и Newton rotor: договор248 и протокол249–251

16 октября2026. До вычисления результатов. Только исследовательская модель;
не новая физическая квалификация Луны или изменение рабочего приложения.
Первичный источник: [Vines, EIH action, Spring2017, стр3](https://fiteoweb.unige.ch/~maggiore/GWVol1/EIHLagrangian.pdf),
прочитан из локального PDF SHA256
`b46e92e61735189459b1732cc29a1330c6480ab1bb2dd13630cebed2de4c4c2f`.
Newton rigid-Q2/инерция и обратный момент — прежний [договор50](conservative-rotation.md).

## Вывод и область применимости

Постулируем конечное автономное действие в одном фиксированном евклидовом
harmonic-подобном модельном базисе, одном времени t:

```text
L = LN(x,v) + L1(x,v) + Trot(R,S) - UQ(x,R)
LN = sum m_i v_i²/2 + sum_(i<j) m_i m_j/r_ij
L1 = sum m_i (v_i²)²/(8c²)
     +sum_(i<j) m_i m_j/(2c²r_ij)
       [3(v_i²+v_j²)-7v_i·v_j-(n_ij·v_i)(n_ij·v_j)]
     -sum_i m_i (sum_(j!=i) m_j/r_ij)²/(2c²)
```

Здесь G=1 в размерностно нормированной модели. Trot в уравнениях ротора
означает обычную кинетическую энергию I/omega; запись через S используется
для состояния/Noether readout, а не как независимая конфигурационная скорость.
Один rotor: Rbody→space, q=(w,x,y,z), пространственный S;
omega=R I^-1 R^T S, Rdot=hat(omega)R, Sdot=tauQ.
Q=(3I-tr(I)identity)/m, UQ=sum m_a m_j n^T Q n/(2d³), с реакцией.
Ни SO, ни PN-I, ни полные PN-мультиполи этим постулатом не вводятся.

Пусть p1=∂L1/∂v, H1=∂p1/∂v, M0=diag(m_i identity), M=M0+H1.
Из point EIH первого порядка:
L1_x-(D_x p1)v = M0 aPN + H1 aN.
Тогда для выбранного конечного действия:

```text
a_exact = aN + solve(M, M0 (aPN+aQ))
a_OR = aN + aPN + aQ
M (a_OR-a_exact) = H1 (aPN+aQ)
p = M0 v+p1
E = E_EIH + Trot+UQ; P=sum p_i; J=sum x_i cross p_i+S
```

Это **точное решение конечного постулата**, не полные уравнения ОТО:
инверсия M порождает старшие порядки, для которых нет всех физических членов.
SPD M проверяется явно, сингулярность/неконечность не маскируется fallback.
Order-reduced сумма тоже имеет ясный договор: удержаны point1PN и NewtonQ,
а смешанные PN×Q и PN² дают остаток. Сохраняемые источники, не новые силы:

```text
b2=H1 aPN, bQ=H1 aQ
B(b)=[sum v_i·b_i, sum b_i, sum x_i cross b_i]
d(E,P,J)/dt = B(b2)+B(bQ)             [OR]
d(E,P,J)/dt = 0                     [finite action exact]
```

Обычный орбитальный Q torque сокращается с Sdot; добавлять его ещё раз
в баланс полного J было бы двойным учётом. Консервативность finite-action
варианта не доказывает его физического превосходства над OR или точность Луны.

## Начальные условия и методы

Синтетические три тела m=(.3,.7,.05), source0. Начальные позиции
(.56,0,0),(-.24,0,0),(3.5,.4,.6). Скорости
(0,.8573214099741123,0),(0,-.3674234614174767,0),(-.06,.5,.08).
Один начальный массовый сдвиг x и v; дальше базис фиксирован.
I=(.002,.0025,.003), boundingradius=.15, q из rotvec(.3,-.2,.4),
omega=(.2,-.3,.9), S=R I R^T omega. Это не ADM данные H57 и не JPL IC.
c=400 — искусственный модельный параметр для видимости PN источников.
Защитная область max(U,v²)/c²<1e-4 и d>boundingradius обязательна.

Нет календарной эпохи, TDB/TCB или физической шкалы точности. Явное SI
подобие для мостов к runtime: M0=1e15kg,L0=12000m,
T0=sqrt(L0³/(G_SI M0)); I0=M0 L0²,S0=M0 L0²/T0.
Это смена единиц, не PN clock/SSC/centre map; физический c в приложении прежний.

Интервал2 номинальных периода по2pi,129 равномерных выходов.
Production OR и finite-action DOP853 rtol1e-10; tighter3e-12;
atol=.01rtol на фиксированных начальных нормах каждого x/v/S, q scale1.
Один spin block и худший по-тельный orbital block, без разбавления ошибки
неактивными координатами. Maxstep=2pi/64, tighter2pi/128.
Для OR интегрируются два отдельных семикомпонентных бюджета PN² и PN×Q;
их scale из начальных физических E/P/J. Нулевые source accumulators получают
эти явно заданные scales, не делятся на нулевое начальное значение.

Независимый reference: matrix R/body Pi, Euler equation, стандартная I-form
MacCullagh сила. Для OR — отдельная scalar-target EIH формула; для finite-action
— Euler–Lagrange force из исходной ordered/triple L, complex-step gradients,
velocity derivative p1 и mass matrix. Runtime q/force/source/Hessian
не импортируются. RK45 rtol3e-12/3e-13,atol=.01rtol тех же scales;
maxstep2pi/128. Reference budgets вычисляются из независимой velocity
производной p1. Сырые q/R не проецируются в сохранённом состоянии.

## Предварительные критерии

- Каждый x/v/S block и R: production/strictreference <3e-7;
  два reference levels и production/tighter <3e-8 в начальных scales.
- Raw q norm и reference R^T R/det ошибки <1e-8.
- Finite-action E/P/J drift и OR исправленные на оба бюджета остатки <1e-9.
  Raw OR drift измеряется, не объявляется нарушением своего усечённого договора.
- Каждый активный source integral E/P/J: сигнал >32eps и >10×суммы
  numerical budget sensitivity и исправленного остатка. Неактивное отмечать явно.
  Пропуск наблюдаемого источника должен дать отклонение >10×исправленного;
  при отказе видимости сохранить FAILED, не уменьшать порог.
- На9 снимках OR (индексы0,16,...128): полная направленная производная E/P/J
  в Decimal70/90 при h=1e-6,1e-9,1e-12. R восстановить в Decimal из raw q,
  а не фиксировать float tensor. Последние derivatives vs аналитические
  источники: scaled<1e-10 и relative active signal<1e-7; precision difference
  <1e-30 в физических scales. Последние два h: scaled change<1e-10.
- Мост SI runtime EIH/Q и scalar point reference: full acceleration <3e-14
  собственной нормы; отдельно PN correction после вычитания N <1e-9;
  Q force/torque <5e-12. H1 against independent p1 derivative <5e-12.
- На тех же9 состояниях c→2c: b2 в16 раз меньше, bQ в4 раза меньше,
  relative mismatch<5e-12. Это algebraic order check, не новый прогноз.
- Контроль без Sdot не должен пройти полный J: максимальный нормированный
  instantaneous дефект >1e-3 относительно собственного torque scale.

Сначала тесты аналитических пределов/реакций/массовой матрицы/Noether формул;
потом замороженные jobs/входы/протокол, SHA до/после, отдельные NPZ и JSON.
Не перезаписывать неуспех. Показывать реальную стоимость и все9×3 канала.
Не менять рабочий guard EIH+dynamicrotation/IC/default/Rust и старые audits.
Полная регрессия2461819Python/17Rust остаётся исторической; новый research
проверяется относящимся набором, без пересчёта старых годовых исследований.
