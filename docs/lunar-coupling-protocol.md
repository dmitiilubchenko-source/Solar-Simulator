# Совместимость лунного квадруполя и вращения: аудит243, протокол244–245

16 октября2026. Сначала изучены фактические определения и прежние отчёты.
Это продолжение локального бюджета240, а не повторная разработка стендов50–90.

Подтверждённое состояние:

- [Newton runtime](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/nbody_rotation.py:139)
  интегрирует N тел и одну жёсткую фигуру с q/S, реакцией и моментом из
  общего Q2-потенциала. [Проверка настроек](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/nbody_rotation.py:45)
  требует Newton/DOP853/per-body и отсутствие заданных фигур. Это явное ограничение.
- [H57](C:/Users/Admin/Desktop/Solar-simulator/scripts/rigid_pn_model.py:73)
  уже соединяет ADM point1PN/LO SO и Newton rigid-Q2. Его точные H/P/J
  относятся к конечному гамильтониану, не к полному PN-протяжённому телу.
  Нельзя копировать в harmonic EIH его p, S или q без договора переноса.
- [Начальная инверсия](C:/Users/Admin/Desktop/Solar-simulator/scripts/canonical_initial.py:72)
  решает v=H_p и W=I^-1 S+Omega_SO, поэтому p=m v и повторное добавление
  Omega к уже заданной Rdot неверны. [Условный источник](pinned-lunar-initial.md)
  и [граница](lunar-initial-boundary.md) уже существуют, physical_mapping=false.
- [Жёсткий профиль51](lunar-spin-initial.md) использует mean-solid equivalent I;
  [заданный Moon](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/oblateness.py:248)
  использует nominal DE441 J2/C22 и заданную мантийную ориентацию.
  Их поля не следует считать одинаковыми или смешивать без измерения.

Первоисточники: Williams et al.2014 §5, DOI10.1002/2013JE004559, определения
solid moments проверены при создании51; это не новая загрузка статьи.
Park et al.2021 §4.2, [первичный PDF](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf),
прочитан из локального резерва234: различаются total/mantle/core inertia,
undistorted/variable parts, geodetic precession и torque ядра. Это препятствует
молчаливому переносу одной mean-solid I в полную модель DE441.
Связь I/Q и потенциал MacCullagh проверены по источникам [50](conservative-rotation.md)
и [57](rigid-pn.md). Новые PN-мультипольные формулы здесь не вводятся.

Минимальное следующее исследование: изолировать Newton Q2 coupling и измерить
различие двух закреплённых наборов параметров, прежде чем выбирать динамику.
Рабочие EIH/IC/default/контроллер/Rust не меняются. Нет приливов или 3D.

## Предварительный протокол до результатов

SI, SSB/Ecliptic J2000, JD2461321.5 TDB; те же440 эпох одного года,10 тел,
массы strict checkpoint. DE441reader должен иметь полный успешный аудит238.
Ориентация R(t), Rdot(t) — прежняя внешняя DE441, **не свободный прогноз**.
Для Moon→Earth использовать -rho из прямого геоцентрического полинома.

Из имеющейся Ibody вычислить без подгонки
J2=(C-(A+B)/2)/(M Rref²), C22=(B-A)/(4M Rref²), Rref=1738000m.
Инерция и bounding radius остаются прежними. Q=(3I-tr(I)identity)/M.
Добавление lambda identity к I не меняет Q: gravity J2/C22 не определяют
среднюю инерцию, spin или rotational kinetic energy. Проверить это отдельно.

Независимый oracle не импортирует runtime Q/force/torque/rotation functions:
U2=sum_j G m_j [3 nbody^T Ibody nbody-tr(Ibody)]/(2d_j³).
Complex-step производные по r и левым углам R дают F и tau; совместная
направленная производная по rdot и Rdot=hat(omega)R даёт Udot.
Использовать bilinear dot/sqrt без complex conjugation; h=1e-20.
Сравнить все440снимков с correction(), включая источник и все9точек.

Заранее заданные численные критерии (не критерии физической точности Луны):

- Сила, torque и U относительно собственной ненулевой нормы: <5e-10.
  Запас учитывает вычитание почти сферической I; масштаб общей monopole
  силы здесь не используется, нулевой эталон не маскируется epsilon.
- Сумма сил / сумма норм сил <5e-12; полный момент
  sum_j r_j cross F_j+tau, делённый на сумму норм слагаемых, <5e-12.
- Обмен энергией sum_j F_j·(v_j-v_M)+omega·tau+Udot, делённый
  на сумму модулей этих power terms, <5e-10. Это локальное Newton Q2
  тождество, **не полная энергия EIH и не годовой Noether-баланс**.
- Поле из I через прежний prescribed evaluator с полученными J2/C22
  совпадает с dynamical correction на тех же R до5e-10 своей нормы.
- Отрицательные контроли должны обнаружить пропуск source reaction,
  torque и spin power: максимум каждого нормированного дефекта >1e-3.
  Если чувствительности недостаточно — сохранить отказ, не снижать порог.

На том же эталонном пути отдельно сохранить local acceleration defects
для EIH+Sunfixed+Earthprescribed; с nominal Moon; с solid-equivalent Moon.
Их ориентация одинакова и задана. Вывести max/RMS всех10тел и Moon−Earth,
различие самих Moon полей, коэффициенты, полные массивы и цену расчёта.
**Не требовать улучшения** ни одного дефекта и не выбирать I по остатку.
Скачки второй производной DE441 и границы применимости прежние240.

SHA входов/исполненных исходников до/после, fresh output без перезаписи
неуспеха, полный JSON/NPZ. Повторить независимые oracle tests и относящиеся
Newton/PN-rotation tests; автономный replay из публичной копии без сети.
Никакой полученный PASS не снимает physical_mapping=false, запрет EIH+q/S,
прежний Noether source-visibility FAILED или отсутствие годового spin forecast.
