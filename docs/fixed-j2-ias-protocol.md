# FixedJ2: контракт сил и балансов для исследовательского IAS15

Протокол184,15октября2026, до trajectoryresults. Только существующая
Newton/EIH point + ньютоновская fixedJ2, без новой физики/default/runtime.

## Силы и область проверки

SI,c=299792458м/с,G Solar; модельные IC,t0=0, без эфемерид/эпохи TDB.
IAS15 REBOUND5.2.2 gravitynone,velocityflag1,PRS23,min_dt0,
epsilon1e-9/1e-11,initialdt=dt/200,exact_finish_time1.
Полная сила nativepoint(Newton либо order-reducedEIH)+existingaxisJ2.
Для каждой пары figure/point есть противоположная сила на источнике;
если обе фигуры, суммируются обе figure/point, без quadrupole/quadrupole.
Поддерживаются только FixedJ2, вне R; prescribedaxes/spin/contacts отвергать.
Callbackexceptionlatch/stop/rethrow, никакого Newtonfallback при ошибке.
Прежние исследовательские адаптеры/исходники/сборка не редактируются.

Независимая энергия figure/point:
V2=Gm_i m_j (rᵀQr)/(2r⁵),Q=J2R²(3ssᵀ−I),r=r_j−r_i.
Сила из тензорного градиента, не runtimeaxisexpression; reaction учитывается.
До динамики: complex-step ∇V2, аналитические экватор/полюс, два источника,
перенос/поворот/разворотоси, реакция/torque, insideR и unsupportedguards.
Отдельную J2поправку сравнивать отдельно от основной pointсилы.
Порог относительной силовой/потенциальной/torque сверки5e-13.
Для нулевого torque нормировка — расстояние пары×сумма норм figureforce,
а не нулевая норма torque; размерный масштаб, без epsilon в силе.
Отрицательный snapshotконтроль без source-reaction должен дать дисбаланс
>1e-3 от суммы норм правильных figureforce, сохранить его показатели.

## Корректные балансы

Newtonfixedaxes: E_N+V2 и P сохраняются, dJ/dt=τQ=Σr×m aQ.
Для единственной оси сохраняется её проекция J; полный J меняться может.

EIHдиагностика из L=L_N+L_PN: H_PN=∂²L_PN/∂v∂v,
a=a_N+a_PN+aQ. Для order-reducedEIH остаток Euler–Lagrange равен
H_PN(a_PN+aQ). Отдельно интегрируются PN² и смешанный PN×Q источники:
R2=H_PN a_PN, Rmix=H_PN aQ.
S_E=Σv·R, S_P=ΣR, S_J=Σr×R, плюс NewtonτQ в S_J.
Следовательно сравниваются Δ(E_EIH+V2),ΔP_EIH,ΔJ_EIH с интегралами
этих источников. Это bookkeeping усечённых уравнений, **не добавление
2PN/PN×J2 сил** и не увеличение физической точности модели.

H_PN b для тела i:
m_i[½v_i² b_i+v_i(v_i·b_i)]/c² +
Σ(j≠i)Gm_i m_j[6b_i−7b_j−n_ij(n_ij·b_j)]/(2r_ij c²).
До динамики сверить с независимой Decimal70 mixedfinite разностью
скалярного опубликованного L_PN; относительная норма <1e-10.
Сами NoetherE/P/J — из независимогоscalarEIHaction/complexstep;
runtime diagnostics не используются для их формирования.

## Три заранее заданные модельные задачи

a=1e8м,e=.2,μ/(ac²)=1e-6,массы(.8,.2)μ/G,
начало в перицентре r=a(1−e), v=√[μ(1+e)/r],
наклонная касательная(0,.8,.6),осьрадиуса(1,0,0),COMoffset=(3a,−2a,a),
COMdrift=(20000,−10000,5000)м/с. Имена Alpha/Beta, произвольные тела.
Три задачи: Newtonоднафигура,Newtonдвефигуры,EIHдвефигуры.
Фигура Alpha:J2=.005,R=a/5,s=(0,0,1);
Beta:J2=−.003,R=a/7,s=(.6,0,.8). Только figure/point,без mixedforces.
Два номинальных периода P=2π√(a³/μ),61равномерная выходная эпоха.
dt=P/100,packet20,точныеобщиеграницы; DOP853/native/per-body/rtol3e-14,
atol1e-7м/1e-13м/с, и оба заранее выбранных epsilonIAS15.

Независимый RK45 в безразмерных a,√(a³/μ),Mtotal, с tensorJ2 и независимым
matrixEIH. Расширенные ODE одновременно интегрируют три раздельных
источника: τQ,PN²,PN×Q. Уровни maxP/200,/400,/800,
rtol1e-13/3e-14/3e-14,atol состояния и нормированных бюджетов1e-17.
Последние уровни: <0.01м/<1e-5м/с по всем телам, различия бюджетов
<1e-10 в масштабах |E0|,Σm|v0|,|J0|.
Кандидаты: <0.1м/<1e-4м/с; остатки всех скорректированных балансов<1e-9.
Ограничение: балансы кандидата используют независимый референсный интеграл
источников на сходящейся referenceтраектории; не отдельную integration
callbackbudget внутри IAS/DOP. Сначала требуется согласие координат.

Ожидаемые негативные Newtonконтроли: rawpointEбезV2 и полныйJбезτQ
должны меняться >1e-6 в указанных масштабах; это не ошибка интегратора.
Единственная ось: Δ(J·s)/|J0|<1e-9. Для mixedEIH показать отдельно
PN²/PN×Q интегралы и rawотклонения, не требовать их обнуления.

## Воспроизводимость и цена

Фиксировать input/source/library/actualnativepyd SHA до/после, rawNPZ/JSON,
общиепакеты, exactIC, repeatbitexact, все отказы без смены порогов.
Стоимость: прогрев+3чередующихся fulltrajectories включая physicalcallback,
setup/выгрузку61состояния, без reference/diagnostics/диска/SHA.
steps_done не acceptedcount/RHS. Не переносить коэффициенты других задач.
Это не10bodyгод/EIH+J2/JPLqualification и не доказательство rotatingbody
физики; противоположные моменты вращения не интегрируются.

Первичные материалы: [Park2021§3.2](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf),
[Vines2017EIHactionстр.3](https://fiteoweb.unige.ch/~maggiore/GWVol1/EIHLagrangian.pdf),
[IAS15](https://arxiv.org/abs/1409.4779).
[СуществующаяfixedJ2модель](oblateness.md), [EIH-onlyконтроль](eih-year-validation.md).
