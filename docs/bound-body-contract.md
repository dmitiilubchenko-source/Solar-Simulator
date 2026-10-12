# Связанное деформируемое тело: договор83–85

Продолжение [кинематических модельных задач79–82](extended-boundary-contract.md).
Следующий стенд вводит внутренние силы связи и собственную Newton-гравитацию.
Это исследовательская модель конечного числа частиц, не модель недр Луны,
не континуальная упругость и не PN-расширение runtime/H57.

## Что проверено в первичных публикациях

[Kopeikin/Vlasov2004, §10.1, (10.1.1)–(10.1.3), pp88–89 PDF](https://arxiv.org/pdf/gr-qc/0403068)
определяет bare spin через материальный тензор и псевдотензор поля в выбранных
локальных координатах. В развёрнутом выражении присутствуют кинетический вклад,
внутренняя энергия, напряжения, собственные скалярный и векторные потенциалы,
внешние multipoles и gauge terms. §10.2,(10.2.6) отдельно переопределяет spin.
Отсюда следует ограничение прошлого kinetic-only snapshot: он не определяет
полный PN-спин или измеренную PN-инерцию связанного тела.

[Klioner1997, §3,(8)–(15), pp386–387](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/699A54C26B8F92BC4E97518AD66E7C32/S0252921100046844a.pdf/on-the-problem-of-post-newtonian-rotational-motion.pdf)
задаёт разложение spin на остаток внутренних движений и inertia×angularvelocity.
Tisserand-like axes зануляют остаток; principal-inertia axes задаются другим
условием. Определение PN-инерции включает stress и self-gravity integrals.
OCR формулы(10) недостаточен для надёжного переноса её коэффициентов в код:
никакие её PN-коэффициенты здесь не реализуются.

[Xu/Tao/Wu2003, вводная часть и(1)–(3)](https://arxiv.org/pdf/gr-qc/0306015)
подтверждает Newton C/M identity и rigid-density limit. Их дальнейшая PN
quasirigidity требует отдельного constitutive assumption; этот стенд его
не принимает. Newton identity сама по себе не становится общей PN identity.

Consensus search/fetch Klioner1997 работает; доступ к PDF через одну поисковую
ссылку Cambridge отказал, другая ссылка издателя дала полный текст. Тесты
не зависят от сети. Исходные ссылки/прочитанные места локально в .tools.

## Выбранная модель и собственный вывод

SI: массы m_i>0 kg, позиции x_i m, canonical p_i=m_i v_i kg m/s.
Время t s — единственное Newton coordinate time с явно заданным t0=0;
декартов инерциальный chart, начальные origin/velocity задаются входом.
Это не TDB/TCB, не SSC и не relativistic local frame. Постоянная G≥0
задаётся явно, допускается синтетическая для модельных задач.

H=Σp_i²/(2m_i)+Σ_(i<j)[−G m_i m_j/r_ij]
  +Σ_links k_ij(r_ij−l_ij)²/2.

Связь — massless central Hooke link с заданными k>0 N/m и l>0 m,
один неориентированный link на пару. Гравитация действует между всеми парами.
Собственная гравитационная энергия каждой точки не включена; точки не
заменяют плотность континуального тела. Массы фиксированы, нет damping,
collision/softening/constraints/hidden support; явный minimum_distance
отклоняет неподдерживаемое сближение без изменения силы.

Для q=x_j−x_i, r=|q|, f=G m_i m_j/r²+k(r−l), где k=0 у пары без link:
F_i+=f q/r, F_j−=f q/r; xdot=p/m, pdot=F.
Попарная реакция и центральность дают ΣF=0 и Σx×F=0.
Энергия H, total P=Σp, total J=Σx×p сохраняются.
COM z=Σmx/Σm движется с P/Σm; origin не recentre в ODE.

Относительно диагностического COM: r_i=x_i−z, u_i=v_i−P/Σm,
D=Σm r rᵀ, C=tr(D)I−D, M=STF(D), S=Σm r×u.
Это Newton моменты той же дискретной массы, а не PN gravity moments.
W=Σr_i F_iᵀ=−Σ_pairs (f/r)q qᵀ — integrated pair virial,
не уникальный локальный continuum stress tensor.
При Kint=Σm u²/2 и A=Σm u uᵀ:
Dddot/2=A+W, Iddot=4Kint+2tr(W), I=tr(D).
Gravity traceW equals gravitational potential energy; spring contribution
−Σk(r−l)r отличается от spring potential energy. Их нельзя смешивать.

## Newton rotation/deformation split

При positive-definite C: Ω=C^-1 S, residual_i=u_i−Ω×r_i.
Σm r×residual=0; Kint=(Ω·CΩ)/2+Σm residual²/2.
Это instantaneous Newton Tisserand condition/least-squares rotation.
Не вычисляет PN-инерцию, не назначает principal axes или body attitude.
При singular C направление вращения не уникально — функция явно отказывает,
не применяет pseudoinverse. Данные/моменты не проецируются.
Для численной уникальности также требуется condition(C)<1e12; это ограничение
helperfunction, не измеренный параметр вещества или PN-физики.

Cdot=Σm[2(r·u)I−u rᵀ−r uᵀ]. Для rigid velocity residual=0,
Cdot=hat(Ω)C−C hat(Ω). Для деформирующегося тела эта rigid formula
в общем неверна, даже при сохранении S. Фиксированный C0 не заменяет C(t).

## Независимый equilateral limit

Три равные массы m, одинаковые links(k,l); радиус R от COM,
pair distance sqrt(3)R. Initial equilateral coordinates и одинаковые
radial/tangential velocities сохраняют этот симметричный subspace.
Specific angular momentum ell=R² phidot постоянно; total S_z=3m ell.
V(R)=−sqrt(3)Gm²/R+3k(sqrt(3)R−l)²/2.
Rddot=ell²/R³−Gm/(sqrt(3)R²)−3k(R−l/sqrt(3))/m,
phidot=ell/R². Reduced H=3m(Rdot²+ell²/R²)/2+V(R).

Circular frequency at Rc:
omega_c²=Gm/(sqrt(3)Rc³)+3k(1−l/(sqrt(3)Rc))/m>0.
Radial stability requires kappa²=3omega_c²−2Gm/(sqrt(3)Rc³)+3k/m>0.
Circular exact solution, breathing reduced ODE и независимый Cartesian
Hamiltonian gradient проверяют разные свойства одной модели.
Это наши Newton выводы из явно заданного H, не формулы PN-публикаций.

Численные критерии записаны до fresh audit85. Сходимость и sampled
сохранение H/J не доказывают физическую точность Moon или устойчивость
произвольного link graph на произвольном времени.

## Реализация и проверенные строки

| Задача | Код | Независимая проверка |
|---|---|---|
| Defensive SI parameters/domain | [Parameters](C:/Users/Admin/Desktop/Solar-simulator/scripts/bound_body.py:26) | [invalid inputs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body.py:92), [singular/overflow](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body.py:96) |
| Central pair potential/force/reaction | [fields](C:/Users/Admin/Desktop/Solar-simulator/scripts/bound_body.py:60), [rhs](C:/Users/Admin/Desktop/Solar-simulator/scripts/bound_body.py:87) | [scalar-H gradient](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body.py:17), [symmetries/no edits](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body.py:30) |
| E/P/J/COM and tensor virial | [diagnostics](C:/Users/Admin/Desktop/Solar-simulator/scripts/bound_body.py:97) | [virial/elastic distinction](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body.py:50) |
| Newton rotation/deformation split | [rotation_split](C:/Users/Admin/Desktop/Solar-simulator/scripts/bound_body.py:128) | [least-squares/kinetic split](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body.py:63), [rigid circular limit](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body.py:75) |
| Independent Cartesian Hamiltonian | [scalar](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_bound_reference.py:9), [gradient](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_bound_reference.py:23) | [units/off-origin COM](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body_audit.py:35) |
| Equilateral radial reduction | [radial_rhs](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_bound_reference.py:35), [reconstruction](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_bound_reference.py:41) | [off-circular analytic force/energy](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body_audit.py:15) |
| Fresh inputs/source/arrays/report | [models](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_bound_body.py:36), [audit](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_bound_body.py:67) | [all criteria](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body_audit.py:46), [source guard](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body_audit.py:57), [fresh paths](C:/Users/Admin/Desktop/Solar-simulator/tests/test_bound_body_audit.py:68) |

[Зафиксированные результаты и ограничения](bound-body-validation.md).
