# Метрический пробный спин: договор изменений75–78

Это исследовательские инструменты SI. Они пока не подключены к runtime,
лунному профилю, H57 или чтению DE441. Источник поля, координаты, время,
начальная эпоха и отсутствие self-field должны быть заданы явно.

## Поле и часы

Для заданных внешних spinless точечных масс U=ΣGM/|x−xA|,
Ui=ΣGM viA/|x−xA|. Производные учитывают движения и ускорения источников.
Метрика стенда: g00=−1+2U/c², g0i=−4Ui/c³,
gij=(1+2U/c²)δij; x0=ct, сигнатура−+++.
[Soffel et al.2003, (8)](https://arxiv.org/pdf/astro-ph/0303376)
задаёт порядки IAU-метрики. Здесь пропущены c^-4 g00, PN-часть скалярного
потенциала и спины источников. Точное обращение этой конечной метрики
не восстанавливает пропущенные коэффициенты. Она не является полной1PN
метрикой или проверенной моделью BCRS конкретной эфемериды.

Leading centre local-coordinate-clock rate: dTCX/dt=1−(v²/2+Uext)/c²,
его derivative=−[v·a+∂tUext+v·gradUext]/c².
Это ведущая часть [Turyshev2026, Appendix C (182)](https://arxiv.org/html/2507.22145v2).
Собственное поле тела исключено. Функция не задаёт абсолютный TCX,
offset/эпоху, TDB→TCB, постоянную LL или ход часов на лунной поверхности.
Скорости/ускорения и GM уже должны относиться к одной выбранной системе
координат и времени. Область стенда явно ограничена U/c²≤1e-3,
|v|²/c²≤1e-3 для центра и источников. Это допуск модели, не оценка ошибки.

## Метрический транспорт

Для supplied g/dg и timelike траектории вычисляются Levi-Civita Γ,
геодезическое coordinate acceleration, covariant4D parallel transport.
SSC: S0=−β·Si, β=v/c. Выбрана положительная симметричная gauge:
S=H Si, H²=G, Gij=gij−g0iβj−g0jβi+g00βiβj (здесь g с верхними индексами).
Это [DJS2008, (5)–(14)](https://arxiv.org/html/0711.1048v2).
Hdot определяется из H Hdot+Hdot H=Gdot через Sylvester equation.
V=(Hdot+H Vtilde)Hinv должен быть антисимметричным при геодезическом a
той же метрики. Проверяется rawV; его симметричная часть не удаляется.

Выбранный H — преобразование компонент covariant spin, не SO(3)-поворот
ориентации тела. Qdot=VQ переносит тестовый триэдр выбранной gauge.
Это linear test-spin limit: backreaction силы спина на траекторию здесь
не моделируется. Норма этого pointspin не заменяет динамический момент
импульса протяжённого ротора с обратными моментами и переменной |S|.
Нет полного harmonic→ADM-centre/SSC/PN-multipole преобразования.

Метод transport возвращает proper_rate=sqrt(−g_mu_nu wmu wnu), w=(1,β),
точный лишь для supplied конечной метрики. Это другая функция, чем
усечённая leading coordinate-clock rate: их higher-order значения не
следует взаимозаменять или считать измеренными лунными часами.

## Независимый предел

Exact exterior Schwarzschild отдельно используется как аналитический
эталон, а не как метрика протяжённой Луны. Isotropic radiusρ отличается
от areal radiusR=ρ(1+GM/(2c²ρ))². Circular coordinate frequency
Ω²=GM/R³. Proper rate sqrt(1−3GM/(c²R)) получается непосредственно из
standardmetric и нормировки круговой скорости.
[Bini et al.2005, (2.1),(2.7)](https://arxiv.org/pdf/gr-qc/0506017)
даёт standardmetric и круговую геодезическую. Независимый oracle
интегрирует 4D ковектор в сферических координатах, используя отдельные
аналитические Γ и скалярные eigenvalues boost, без productionH/Γ.

Прецессия за оборот 2π[1−sqrt(1−3GM/(c²R))],
[Barack/Pound2018, (92)](https://arxiv.org/html/1805.10385v2).
В HTML раздела7.5 выражение z0 дано без sqrt, несмотря на определение
z=dτ/dt; для часов оно не используется. Эталон clock выведен из метрики.
Это зафиксированное расхождение источника, а не подгонка результата.

## Код и проверки: проверенные строки

| Определение | Код | Проверка |
|---|---|---|
| External sources/единицы | [Sources](C:/Users/Admin/Desktop/Solar-simulator/scripts/external_metric.py:43) | [копии/flat](C:/Users/Admin/Desktop/Solar-simulator/tests/test_external_metric.py:66) |
| U/Ui и derivatives | [potentials](C:/Users/Admin/Desktop/Solar-simulator/scripts/external_metric.py:81) | [complex-step](C:/Users/Admin/Desktop/Solar-simulator/tests/test_external_metric.py:25) |
| Weak g/dg | [weak_metric](C:/Users/Admin/Desktop/Solar-simulator/scripts/external_metric.py:111) | [тот же independent derivative](C:/Users/Admin/Desktop/Solar-simulator/tests/test_external_metric.py:25) |
| Coordinate clock/material derivative | [leading_clock](C:/Users/Admin/Desktop/Solar-simulator/scripts/external_metric.py:132) | [material/translation](C:/Users/Admin/Desktop/Solar-simulator/tests/test_external_metric.py:47) |
| Γ и metriccompatibility | [christoffel](C:/Users/Admin/Desktop/Solar-simulator/scripts/metric_spin_transport.py:38) | [4D/SSC/norm](C:/Users/Admin/Desktop/Solar-simulator/tests/test_metric_spin_transport.py:30) |
| Hdot | [root_rate](C:/Users/Admin/Desktop/Solar-simulator/scripts/metric_spin_transport.py:50) | [independent difference](C:/Users/Admin/Desktop/Solar-simulator/tests/test_metric_spin_transport.py:51) |
| Geodesic/spin/properclock | [transport](C:/Users/Admin/Desktop/Solar-simulator/scripts/metric_spin_transport.py:84) | [moving sources/negativecontrol](C:/Users/Admin/Desktop/Solar-simulator/tests/test_metric_spin_transport.py:73) |
| Exact Schwarzschild/circle | [metric](C:/Users/Admin/Desktop/Solar-simulator/scripts/schwarzschild_metric.py:22), [orbit](C:/Users/Admin/Desktop/Solar-simulator/scripts/schwarzschild_metric.py:41) | [order/derivatives](C:/Users/Admin/Desktop/Solar-simulator/tests/test_metric_spin_audit.py:16) |
| Spherical4D reference | [generator](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_schwarzschild_spin.py:19), [Jacobian/gauge](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_schwarzschild_spin.py:44) | [SSC/Gram](C:/Users/Admin/Desktop/Solar-simulator/tests/test_metric_spin_audit.py:27) |
| Raw epoch0 | [integrate_raw_initial](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_metric_spin.py:56) | [RK45/DOP853 signedzero](C:/Users/Admin/Desktop/Solar-simulator/tests/test_metric_spin_audit.py:114) |
| Source freeze/criteria/freshoutputs | [audit](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_metric_spin.py:114) | [closure](C:/Users/Admin/Desktop/Solar-simulator/tests/test_metric_spin_audit.py:69), [oldoutputs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_metric_spin_audit.py:86) |

[Результат, отказы и ограничения](metric-spin-validation.md).
