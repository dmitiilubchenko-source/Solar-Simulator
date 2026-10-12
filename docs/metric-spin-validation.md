# Проверка локальных часов и пробного метрического спина75–78

Модель и первичные источники: [metric-spin-contract](metric-spin-contract.md).
Критерии заданы до расчётов в [policy](C:/Users/Admin/Desktop/Solar-simulator/scripts/metric-spin-policy.json:1).
Успешный fresh78: [JSON](metric-spin-validation-r3.json).
SHA256 d23bb51775f750fcc6e6049b386a395ea9d874695c4ad336e3c915f336004b2a.

## Стенд

Synthetic GM=1e12m³/s², isotropicρ=1e6m, c=50000/100000/200000m/s.
Это модельные числа, не астрономические данные. Без JPL/подгонки/oldtrajectory.
Интегрируется случай c=50000,4круговых оборота,257равномерных epochs.
Эволюция вычисляется по orbitalphase=Ωt; coordinate time сохранено в SI.
DOP853 rtol2e-12 и tighter2e-13, RK45 sphericalreference1e-11 и2e-13;
atol=rtol/50, максимальный phase step2π/64. Никакой norm/SO3 projection.
Контроль properclock идёт через интеграл по phase с явным Ω переводом.

Fresh78 завершился за8.31s,7jobs. Все16maximum/4minimum/5boolcriteria
прошли.218Python/policy SHA закреплены вместе с выполненными копиями,
7NPZ повторно проверены: SHA/shape/finite/bitwiseinitial/phase/timegrid.
Версии Python/NumPy/SciPy сохранены; бинарники сторонних библиотек
не включены в sourceSHA, это ограничение воспроизводимости.

## Численные результаты

| Проверка | Результат | Предел |
|---|---:|---:|
| Scaled metricderivative complex-step | 3.918e-16 | 1e-11 |
| Circular acceleration relative | 8.253e-16 | 1e-11 |
| Properclock analytical absolute | 1.110e-16 | 1e-11 |
| Raw symmetry defect | 3.876e-16 | 1e-10 |
| Euclidean triad vs spherical covector, Frobenius | 1.443e-12 | 1e-8 |
| Referencelevel sensitivity, Frobenius | 7.188e-11 | 1e-8 |
| Production tighter difference | 1.337e-15 | 1e-8 |
| Holonomy at integer orbital endpoints | 1.570e-16 | 1e-8 |
| Properclock integral scaled | 5.230e-15 | 1e-9 |
| Euclidean Gram defect | 8.951e-16 | 1e-9 |
| Reference4D Gram defect | 1.465e-10 | 1e-9 |
| Reference SSC defect | 9.233e-17 | 1e-9 |
| All correct triads orthogonality/determinant | 1.465e-10 / 1.036e-10 | 1e-9 |

Referencelevel sensitivity не является строгой оценкой истинной ошибки.
Совпадение с аналитикой circularSchwarzschild подтверждает именно этот
предел и gauge; не подтверждает multipolarMoon или эфемеридную точность.

При удвоении c остатки leadingclock, leadingH и LOgeodetic уменьшаются
в15.9912–15.9986раз; заданный интервал15.9–16.1 пройден.
Это ожидаемый c^-4 порядок, а не измеренная абсолютная ошибка Луны.
Внешняя weakmetric дополнительно проверена на собственной согласованной
круговой геодезической: acceleration relative7.217e-16.

Интегрируемые отрицательные контроли:

| Намеренный дефект | Difference Frobenius | Требование |
|---|---:|---:|
| Wrong sign V | 0.042646 | >1e-4 |
| Double V | 0.021324 | >1e-4 |
| Omitted Hdot | 0.00028318 | >1e-4 |

OmittedHdot rawsymmetry defect0.632835>1e-4. Эти варианты правильно
обнаружены; productionV не маскирует ошибку antisymmetrization.

## Сохранённые отказы

Первый subset:44passed/1failed из-за ошибочного пути в новом тесте
sourceclosure. Настоящий spin_initial.py уже присутствовал в broadfreeze.
Путь исправлен; критерий не менялся. Результат сохранён локально.

Первый fresh77 (.tools/rotation77) выполнил7jobs, но strictreportcollector
отклонил numpy.float64 вместо Pythonfloat. Criteria ещё не оценены.
Исправлен collector и добавлена проверка типа; sources/NPZ/failure сохранены.

Второй fresh77 (.tools/rotation77-r2): [failedJSON](metric-spin-validation.json).
Numerical16max/4min прошли, но raw_initial_preserved=false.
В denseoutput RK45 приt0 четыре −0.0 обоих references превратились в+0.0.
Причина найдена по локальному SciPy RkDenseOutput._call_impl и по битам
сохранённых NPZ: нулевой increment складывается с y_old.
[Документация solve_ivp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html)
описывает t_eval как выходную сетку, не гарантию bitwiseepoch0.

78 исправляет формирование epoch0: rawinitial.copy() плюс solveroutput
строго послеt0; IVP начинается с прежнего rawinitial вt0.
[Regression обоих методов](C:/Users/Admin/Desktop/Solar-simulator/tests/test_metric_spin_audit.py:114)
проверяет также реальную динамику следующих строк и исходные биты input.
Policy numericalcriteria/rtols/grid неизменны. Старый failedreport
не перезаписан. Successful78 использует полностью новые jobs и NPZ.
47новых тестов75–78 passed0.71s перед freshaudit, входят в полный набор.

## Границы результата

Реализован выбранный transport linearpointspin и leadingcentreclock.
Нет измеренной PN-инерции Луны, полного ADM/SSC/multipole boundary,
surfaceclock/эпохи/TDB→TCB, физически квалифицированного initialspin,
внутреннего ядра или диссипативных приливов. Runtime/data/strictreceipts
не редактировались. Полный energy/J баланс консервативной пары72–74
остаётся отдельной проверкой; этот тестовый гироскоп движется во внешней
метрике и не является замкнутой системой орбита+источник+rotor.

Полный check_project:1024Python passed171.26s (включая47новых),17Rust,
fmt solar_core/solar_native passed;1074file/line links в полном запуске.
Сохранены327исходных statusentries/main, прежний runtime/data/receipts.
Finalverification и full-check.log находятся локально в.tools/rotation75-77.
