# Реальные SI-масштабы: протокол254–258

17 октября2026. До вычисления численных результатов. Не менять рабочие
силы, IC, guard EIH+q/S или default. Никакой подгонки по эфемеридам.

Вход: те же10тел/440эпох одного года, SI/SSB/EclipticJ2000,
JD2461321.5TDB, квалифицированный reader238, прежние GM/G, c=299792458m/s.
Mean-solid equivalent I из профиля51. R/Rdot заданы DE441 во все эпохи:
это анализ на внешнем пути, **не свободный прогноз вращения**.
Для мгновенной геометрии перевести позиции к Moon-origin и положить
Earth=-rho из прямого геоцентрического полинома; скорости оставить SSB.
Это только численное центрирование снимка, не движущаяся система интегратора.

## Источники и смысл сравниваемых членов

Vines EIH action стр3, локальный PDF проверен ранее; [вывод248](hybrid-rotation-protocol.md).
[Hartung–Steinhoff, PRD83,044008, arXiv1011.1179v3](https://arxiv.org/pdf/1011.1179v3),
§IV(C), (64)–(66), стр9. Уравнение(66) повторно проверено по первичному
тексту; c восстановлено явно. Сохранённый PDF286448bytes,
SHA256 `b5daf350e62aa3c95a32ac7ccf9cfb8cf4f7d796f47978044756d1d99e96344e`.
Не реализуются NLO, spin–spin или полная PN-модель протяжённого тела.

Две группы **не складываются в сертифицированный физический бюджет**:

1. Harmonic point-EIH mass Hessian H1 и Newton quadrupoles. Для b=aPN,
   aQ_Moon, aQ_Sun+Earth вычислить D1(b)=M0^-1 H1 b и
   Dfinite(b)=solve(M0+H1,H1 b). Это различие выбранных OR/finite-action
   усечений253, **не полная физическая2PN/PN-мультипольная поправка**.
   Решать через sqrt(M0): K=M0^-1/2 H1 M0^-1/2 и identity+K;
   записать спектр/condition и residual, не вычитать почти равные ускорения.
2. Ведущий канонический point-spin SO из(66), только Moon spin.
   Для масштаба назначить p_i=m_i v_i, S=R I R^T omega_DE.
   Это leading-order/conditional assignment, не физическая harmonic→ADM,
   SSC/triad/clock миграция Луны. Не добавлять Omega к имеющейся global Rdot.

Для r=x_a-x_j, w=1.5v_a-2v_j, k=Gm_j/(c²r³):

```text
HSO = sum k (r cross w)·S, Omega = sum k r cross w
F_a = -k [w cross S-3((r cross w)·S)r/r²], F_j=-F_a
delta_v_a = 1.5k(S cross r)/m_a, delta_v_j=-2k(S cross r)/m_j
delta_a_point = F/m + D_x(delta_v) v
delta_a_with_Qtorque = delta_a_point + D_S(delta_v) tau_Q
```

Вторая acceleration величина — дополнительный диагностический mixed-term
выбранного Newton rotor, не полный PN-мультипольный закон. Учитывать
канонический velocity shift обязательно: F/m сам по себе не delta acceleration.
Отдельно сохранить Omega по каждому источнику, |Omega|max*T,
trapezoid integral Omega и integral|Omega|, norm(deltaS=R I R^T Omega)/norm(S).
Это масштабы, не предсказанная ошибка ориентации. SO в compact-spin PN-счёте
не определяет его величину для медленно вращающейся Луны.

Влияние условной годовой смены ориентации на Q поле оценить линейно:
deltaQ=T(hat(Omega)Q-Qhat(Omega)), получить deltaaQ из линейного Q поля.
Не считать это свободным решением spin/orbit; R(t) остаётся заданной.

Для каждого поля сохранить max/RMS всех10тел и Moon−Earth.
Для acceleration дополнительно `.5*T²*max_sample_norm` в метрах,
для velocity — `T*max_sample_norm`. Это **баллистические proxies**,
не строгая граница, не интегрированный orbital response, не сертификат1km.
Статус годовой точности/реального вращения по таким числам не менять.
Не ставить критерий, что proxy обязан оказаться меньше1km.

## Критерии правильности вычисления

- Все440снимков/10тел/все заявленные компоненты конечны, ничего не исключать.
- H1 response против отдельно проверенной scalar pn_response: relative<5e-12
  по собственной норме каждого ненулевого компонента, без epsilon.
  Force/velocity/H1 сравнения — по вектору каждого тела, Omega — по вектору
  источника; большое тело не должно скрывать ошибку малого.
- Mass-scaled solve residual<5e-13, identity+K SPD; нулевой b даёт exact zero.
- Изолированные SO force/velocity/Omega против complex-step производных
  **только HSO** (без вычитания полного большого H/RHS): relative<5e-11.
- Sum F_SO / sum norms<5e-12. Rotational identity
  sum x cross F + sum delta_v cross(mv) + Omega cross S, нормированная
  суммой норм этих слагаемых, <5e-12. Контроли без velocity term и без
  реакции должны дать максимальный дефект>1e-3 каждый.
- На10индексах0,1,2,13,55,110,220,330,438,439: material derivative
  delta_v независимого HSO при сдвигах x±h v и S±h tauQ, h=100/10/1s.
  Последнийh: own relative<1e-6; все уровни сохранить, монотонность не требовать.
- На тех же10индексах deltaaQ от deltaQ против центрального поворота
  runtime-фигуры на±1e-3/±1e-4rad вокруг Omega/|Omega|;
  последний уровень relative<1e-6. Нулевой Omega обрабатывается как exactzero.
- Аналитический circular test-spin limit: Omega=1.5GM(r cross v)/(c²r³),
  угол за оборот3piGM/(c²r), plus H1 static-pair/SPD/linearity tests.
- Общие force formulas/IC/SHA не меняются во времяjobs; freshoutputs,
  JSON+полныеNPZ, источники и библиотеки зафиксировать. Все неуспехи сохранить.

После измерений выбрать дальнейшую работу по реальному масштабу и целям.
Не объявлять недостающую physical PN-I/SSC теорию обязательной целиком,
если для текущего допуска достаточно явно проверяемого приближения.
Для включения рабочего режима всё равно нужен свободный расчёт и независимая
проверка при зафиксированных initial/time/model договорах.

## Уточнение257 после сохранённого FAIL256

Строгий own-body H1 bridge выявил компенсацию на слабом Neptune response.
Decimal90probe разделил ошибки обеих float64 форм. Числа/входы/старыйFAIL
сохранены, порог5e-12 прежний. Исправление — Decimal block response50/70,
независимый scalar response70; дополнительный критерий согласия50/70
до float-преобразования <1e-30 по собственной норме каждого тела.
Mass-scaled finite solve остаётся float64 на матрице с condition≈1;
его RHS формируется из повышенно-точного отклика, без повторного вычитания.
Это исправляет арифметику диагнoстики на фиксированных float64 входах,
но не улучшает физическую точность эфемерид/I или самих входных aQ.
