# Ограниченный опыт379: dynamic max_step обычного Solar DOP853

28 октября2026, до измерений. Base dev941eda322366d5c8f2b53a05fc255da612fb0af9.
Машинный immutable plan: scripts/runtime-step-379-plan.json; отдельный новый
план не меняет [протокол376](runtime-reliability-376.md) или его результаты.

## Четыре фиксированных условия

Точные IC/G/массы, наклонные SI-оси, COM offset/drift, 49 бинарных эпох и
один номинальный период из376: e=.99 peri/apo × Python/Rust point forces.
Только strict-relative A/B, per-body DOP853, rtol3e-14, atol1e-3m/1e-9m/s.
Границы49 эпох остаются теми же48 cold packets, не внутренними шагами.
Никаких фазовых подгонок, EIH/J2/вращения/контактов или JPL residuals.

Два режима: instrumentation disabled cap и dynamic d=32. Все четыре
uncapped-контроля обязаны byte-for-byte повторить массивы376 до первого
ограниченного запуска. Отключённая instrumentation дополнительно проверяется
на синтетической ODE против неизменного PerBodyDOP853, включая RHS и коэффициенты.

## Один ограничитель и его применение

Перед вызовом исходного SciPy `_step_impl` диагностический subclass задаёт
`max_step = sqrt(|rho|³ / mu64) / 32`. rho берётся из внутреннего relative
слота B (`y[3:6]`), а не из разности relative и barycentre слотов.
mu64=G*(mA+mB), binary64 только для выбора шага; силы и эталон не меняются.
Размерность: sqrt(m³/(m³/s²))=s; d безразмерен. При rejected trial состояние
не меняется, последующие попытки исходного контроллера уменьшают шаг.
Пересчёт cap выполняется на следующем accepted-step cycle. Граница пакета
и dense evaluation endpoint остаются прежними.

d32 — наименее дорогой заранее исследованный уровень158. Для e=.95 чистые
caps давали немонотонные результаты; более дорогой d не гарантировал улучшения.
Sum/carry кандидаты не прошли весь holdout160. Поэтому здесь только один
лёгкий cap, без смены арифметики или подбора d по новым ошибкам.
См. [157](kepler-step-protocol.md), [158](kepler-dynamic-step-protocol.md),
[159](kepler-roundoff-protocol.md) и [результаты156–164](kepler-phase-validation.md).

Источник механизма max_step и accepted/rejected ветвления —
[SciPy1.18.1 rk.py](https://raw.githubusercontent.com/scipy/scipy/v1.18.1/scipy/integrate/_ivp/rk.py).
Коэффициенты и исходный controller наследуются без копирования/редактирования.
Наблюдаются nfev, успешные `_step_impl`, вызовы error norm и их h/norm.
Rejection означает norm>=1 в этой закреплённой версии. nfev включает также
инициализацию и endpoint dense stages. В trace ноль cap означает off, не dt=0.

## Эталон и наблюдаемые величины

Decimal f/g70/100 из exact binary64 IC, exact(G)*(exact(mA)+exact(mB));
результат100 обязан совпасть с сохранённым376. Независимый mpmath80/110
восстанавливает eccentricity-vector basis p/q, a/e/E0 из Cartesian IC,
решает E-e sin(E)=M0+n*t и строит r/v в orbital plane. Это другой код/библиотека/
представление, но общая ньютоновская эллиптическая модель. Формулы plane position
и её производной сверены с [Orekit KeplerianOrbit](https://raw.githubusercontent.com/CS-SI/Orekit/develop/src/main/java/org/orekit/orbits/KeplerianOrbit.java).
[NASA PROP2B](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/FORTRAN/spicelib/prop2b.html)
предупреждает об обычной float-арифметике элементов около e=1; здесь80/110 цифр
проверяются на всех эпохах против Cartesian f/g, а не выдаются за внешний review.
Прежний oracle check: <1e-6m/<1e-12m/s. Ни один runtime threshold не меняется.

Ошибка r/v — относительное состояние B−A, как376. Полные E/L/P и их
нормировки вычисляются прежними Decimal130 и независимым Fraction/Decimal120
observer, включая исходный COM. Это не гарантия фазовой или физической точности.
Все49 эпох, maxima/index/time, endpoint и peri windows сохраняются.
Peri window задаётся до результатов: peri start t/P<=.01 либо t/P>=.99;
apo start |t/P-.5|<=.01. Граница P — прежний номинальный rounded clock,
а эталон вычисляется именно на этих временах, без исправления фазы.

Необходимый exploratory screen: во всех4 условиях оба sampled max r/v
уменьшаются минимум на10%; peri/endpoint не ухудшаются за1e-6m/1e-12m/s
oracle resolution, RHS<=2x. Это лишь основание следующей проверки, не production
GO. Остальные E/L/P/cost/worsenings сообщаются независимо. Один замер CPU/wall
не устойчивый benchmark. Если screen не выполнен — NO-GO, нового d не пробовать.

## Бюджет, сохранность и выполнение

Всего120CPU s/300wall s/1GiB private/64MiB результатов, включая основной worker,
независимый observer и надзор. РаспределениеCPU65/25/10 +20reserve.
Оценка по376:15..60CPU, <250MiB private, <8MiB outputs; это оценка до измерений.
Внешний уже проверенный resource monitor останавливает на110CPU/280wall/
900MiB worker tree/56MiB disk, оставляя резерв. Контроль50ms с retained Windows
handles для final CPU; short spikes/необнаруженные сверхкороткие процессы и
задержка sampled stop отмечаются. Сумма worker+observer+parent обязана уложиться
в исходные120/300; превышение не объявляется complete. Parent private учитывается
отдельно. Worker дополнительно останавливается на95CPU/250wall до внешнего cap.

У monitor используется только инструментарий надзора, не REBOUND или результаты
Solar-Research; SHA/версии/команды фиксируются в отдельном execution binding.
Никакой зависимости Solar runtime от monitor/psutil/mpmath не добавляется.
Между scientific start и окончанием audit исходники не редактировать.
Новые каталоги создаются exclusive, после каждого завершённого packet state
добавляется в JSONL; каждый job и partial сохраняются отдельно, старые не затирать.

Команды worker и независимого observer (только под заданным aggregate guard):

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.check_runtime_step379 run --output NEW_DATA
REFERENCE_PYTHON -X utf8 -B -m scripts.assess_runtime_step379 --work NEW_DATA --output NEW_ASSESSMENT.json
```

REFERENCE_PYTHON — отдельная среда с mpmath1.4.1/NumPy2.5.1, не native backend.
Production остаётся неизменным. Даже успешный screen не разрешает внедрение:
нужны иные IC/фазы/горизонты, многотельный/EIH профиль и lifecycle/regression.
Нельзя превращать этот этап в последовательность переборов или новую статью.
