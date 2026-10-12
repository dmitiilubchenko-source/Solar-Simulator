# Связанные орбита, вращение и перенос: аудит 74

Все **31 максимальный критерий, 5 минимальных контролей и 5 подтверждений**
прошли. [Неизменяемый JSON](local-rotation-validation.json) содержит
параметры, исходное состояние, масштабы, исходники/SHA, массивы/SHA,
время jobs и точные метрики. [Конфигурация до запуска](../scripts/local-rotation-policy.json),
[физический договор и первичные статьи](local-rotation-contract.md).
Результат проверяет конечную синтетическую модель; физический перенос
Луны и физическая точность **не сертифицированы**.

## Состав проверки

SI-пара: m1=10¹⁵kg, m2=2·10¹⁴kg, G=6.6743·10⁻¹¹,
начальный радиус12000m, minimumdistance1000m, Cbody diagonal
(2,2.5,3)·10²⁰kg m². Mbody имеет собственные значения
(4,−1,−3)·10¹⁹kg m² и оси, повёрнутые относительно Cbody.
Оба тензора постоянные в body-frame. Параметры феноменологические;
общая физическая плотность и PN-реализуемость не подразумеваются.
Первоначальное поступательное движение имеет небольшой эксцентриситет
и наклон; вращение не совпадает с главной осью. Нет заданной орбиты.

Четыре nominalperiods,257эпох: период29184.902890s,
длительность116739.611561s (≈1.351модельных SI-суток).
T(t)=t+0.12P sin(πt/(2P)), dT/dt≥1−0.12π/2>0
аналитически, а не только на sampledgrid. B — произведение двух
вращений вокруг непараллельных осей с непостоянными скоростями.
Амплитуды намеренно заметные, это проверка переноса, не лунные PN-часы.

Production использует SciPy DOP853 со стандартной RMS-нормой,
rtol1e-11; tighter3e-13. Абсолютные допуски каждого r/p/S компонента
равны rtol·0.01·заданному масштабу соответствующего блока, q —
rtol·0.01; maxstep=P/128. Ledger — отдельная координата с энергомасштабом.
Это не прежний worstblock-интегратор H57. Итоговое сравнение всё равно
отдельно оценивает каждый r/p/S/R-блок, не только общую RMS.

Независимый reference работает в локальном T на той же преобразованной
сетке T(t): rawmatrix R и bodyspin Π, scalarH-gradient complex-step,
bodyEuler, RK45 при3e-13 и3e-14. Он не использует productionforce/torque,
quaternionfield, matrix conversion или перенос. Общие параметры задают
ту же конечную математическую модель; согласие не проверяет их истинность.
R не ортогонализуется, q в production не проецируется. Строгий reference
используется для agreement; разность двух referencelevels показана отдельно.

## Численный результат

Все значения ниже — максимумы на заранее заданной сетке либо24 seed74
состояниях производных. Scaled r/p/S делятся на фиксированные исходные
масштабы12000m,4.305777772·10¹⁴kg m/s,8.101987657·10¹⁶kg m²/s;
R измеряется матричной Frobenius-нормой, не углом в arcseconds.

| Проверка | Значение |
| --- | --- |
| independent H / full flow / K flow | 4.397e−16 / 3.103e−15 / 4.170e−15 |
| independent energy derivative / orbital reaction | 3.457e−16 / 8.638e−14 |
| inverse target v/W / clock/basis derivatives | 2.345e−15 / 4.255e−16 |
| local H / J drift | 4.266e−14 / 2.270e−14 |
| target h / pulled BᵀJ drift | 1.002e−13 / 5.726e−14 |
| K−K0−integrated explicitpower, scaled by abs(h0) | 1.321e−13 |
| maximum quaternion norm error | 1.554e−15 |
| independent R orthogonality / determinant | 2.563e−12 / 2.085e−12 |

| Сравнение | r scaled | p scaled | S scaled | R absolute |
| --- | --- | --- | --- | --- |
| agreement local и inverse-target vs strictreference | 5.934e−12 | 8.920e−12 | 6.039e−13 | 1.163e−11 |
| referencelevel sensitivity | 5.106e−11 | 7.577e−11 | 5.577e−12 | 9.944e−11 |
| target vs tighter | 2.675e−13 | 4.077e−13 | 2.372e−14 | 3.456e−13 |
| target vs mapped local trajectory | 4.668e−13 | 5.117e−13 | 4.594e−14 | 5.207e−13 |

r-agreement≈7.121·10⁻⁸m; referencelevel sensitivity≈6.127·10⁻⁷m.
Согласие меньше чувствительности эталона. Эти числа нельзя называть
истинной глобальной ошибкой, точностью Луны или пределом между эпохами.
Не требуется монотонное улучшение от уменьшения rtol при float64.

Три неправильных интегрируемых варианта дали максимальную
dimensionless blockdifference2.828425/2.672680/1.880066:
wrong-sign всей connection; отсутствует orbitalconnection при наличии
spinconnection; spinconnection добавлена дважды. Все больше порога1e-4.
Naive initial S=CgWg отличается от канонического на0.282806spin-scale.
K действительно меняется на0.300439abs(h0); требование постоянного K
было бы неправильным. Правильные conservedquantities и ledger проходят.

## Воспроизводимость и код

Полный аудит118.74s. Восемь свежих jobs:
local2.23s, target11.85s, tighter10.37s, reference0/1 22.97/30.50s,
wrong-sign12.46s, missingorbital11.07s, doublespin15.79s.
210projectPython/policy исходников обнаружены по src/scripts/tests,
заморожены до jobs и перепроверены после. Это намеренно широкий manifest,
чтобы не повторять missing-import ошибку71; сторонние NumPy/SciPy/Python
версии записаны отдельно, их бинарники этим SHA не покрываются.

В `.tools/rotation74`8NPZ и report.json. Сверены SHA всех210sources,
их сохранённых executedcopies, всех8NPZ, grid/shape/finitevalues,
все8 initialstates побитово равны первой строке соответствующего массива;
копия отчёта совпадает с docs JSON. Rawq сохранён, никаких JPLfuturetables,
старых lunartrajectories или fitting. SHA отчёта:
`f46cd0a43e9552792444224b2cf02cd5b1b453f2fbe371879c3d96e24bba0222`.

- [Сбор источников / guard](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_local_rotation.py:23),
  [строгое решение по всем критериям](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_local_rotation.py:40),
  [synthetic input](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_local_rotation.py:54),
  [аналитические часы/оси](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_local_rotation.py:75),
  [отдельные blockcomparisons](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_local_rotation.py:103),
  [independent instantaneous audit](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_local_rotation.py:123),
  [freshtrajectory audit](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_local_rotation.py:171).
- [Тесты всех критериев](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_rotation_audit.py:31),
  [неполных/nonfinite reports](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_rotation_audit.py:42),
  [реальной мутации sourceclone](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_rotation_audit.py:52),
  [существующих outputs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_rotation_audit.py:69),
  [переполнения K/RHS/power](C:/Users/Admin/Desktop/Solar-simulator/tests/test_local_rotation_transfer.py:101).

44новых72–74passed1.83s. Полный check_project завершился:
**977Python passed242.45s +17Rust**, fmt обоих crates,1043file/line links
на момент полного запуска.44new входят в977;933 — прежний общий счётчик71.
Научных непройденных
критериев и прерванных jobs74 нет. Вспомогательная документарная правка
дважды отклонена apply_patch из-за неверного контекста; изменений
не произошло, исправлена по текущему тексту, source/criterion не менялись.

## Оставшиеся границы

Модель — ведущая monopole/M2, а не полная PN-пара. C/M значения,
metric/tetrad/SSC, sourcebound local time и harmonic→ADM mapping Луны
по-прежнему не квалифицированы. Не подключены runtime/storage/GUI,
PN tidal/reaction corrections, Earthfigure, fluidcore, deformation,
spinspin, radiation и диссипативные приливы. Нет нового checkpoint
persistence/restart договора. Этот результат не меняет аудит71,
годовой residual121.84″ или экспериментальное кольцо528/KBO351.9808m.

Следующая модельная задача75 — источник PN localclock/metric и выбранного
тетрадиного/SSC договора с независимым пределом. Только после полной
квалификации физических параметров и динамики возможен physicalPN-runtime;
прежний conditional H57 runtime требует отдельного явно условного режима
и сквозной проверки. Приливы остаются после conservativechecks.

Сохранность:130прежнихJSON и68baseline runtime/Rust files побитово
прежние;316исходныхgitstatusentries сохранены, main. Старый portable
pointer SolarSimulator-0.2.0-20261011-133046 прочитан, сборка не менялась
и не перепроверялась. Финальный аудит дерева/source/array/links находится
в локальном `.tools/rotation72-74/verification.json`. Личная памятка76строк,
предыдущая сохранена в архиве; публикация не выполнялась.
