# Свободное вращение Луны на96сутках: протокол266

17 октября2026. Критерии записаны до чисел96day опыта. Модель, силы,
интеграторы, IC, GM/I и договор времени/координат прежние из
[протокола260](free-lunar-rotation-protocol.md). Старые исходники,
квитанции32day и runtime guard не меняются. Новых физических сил нет.

## Что проверяем

96суток,385 выходов через21600с. Те же10тел/SI/SSB/EclipticJ2000,
JD2461321.5TDB; q/S толькоt0. OR point EIH+fixed Sun/Earth J2+Newton
solid-Moon Q2. Независимый RK45 с rawR/bodyEuler и scalar point force;
production DOP853, EMB/rho, worst-block/q/S/3budgets. Никакой будущей
R/Rdot в RHS, никакой подгонки по будущим данным.
Основание/первичные формулы прежние из260; кеш достаточен, сеть не нужна.

Пять непрерывных расчётов сt0: nominal/tight/reference_nominal/
reference_tight/baseline. Допуски и шаги, абсолютные численные gates,
E/P/J источники и нормировки **те же**, что260:

| Сравнение | Allbody, м | Pair, м | v, м/с | R Frobenius | S/initial norm |
| --- | ---: | ---: | ---: | ---: | ---: |
| Production refinement | 4 | .2 | 1e-5 | 2e-7 | 2e-7 |
| Reference refinement | 1 | .05 | 3e-6 | 1e-7 | 1e-7 |
| Tight independent | 2 | .1 | 5e-6 | 1e-7 | 1e-7 |

Raw rotation defect<1e-8; на всех385 эпохах corrected scaled E/P/J<1e-11.
Decimal70/90 comparison<1e-30 на9 индексах0,48,…384.
Noether global source visibility не переквалифицируется; источники могут
быть ниже глобального численного дрейфа. Fixed-axis torque остаётся в J.

## Диагностика нескольких лунных циклов

- Все385 состояний/10тел конечны. Отдельные внешние max/RMS по каждому
  телу, прямой Moon−Earth и ориентации. Сравнение с DE441 только ПОСЛЕ
  свободного расчёта. Цели10км/body и1км/pair на снимках — отдельно от
  арифметического PASS, не физическая uncertainty/годовая квалификация.
- Префиксы32/64/96суток и окна[0,32],[32,64],[64,96]суток, по129выходов
  в каждом окне. Граничные точки общие; отдельные оконные RMS не являются
  независимыми выборками и не суммируются как общий RMS.
- Геометрия либрации: unit u=Rᵀ(-rho)/|rho|, longitude=atan2(u_y,u_x),
  latitude=atan2(u_z,hypot(u_x,u_y)). Сохранять непрерывно развёрнутую
  longitude, диапазон каждой компоненты по окнам и max/RMS difference
  к таким же DE441 геометрическим углам через atan2(sin(delta),cos(delta)).
  Это sub-Earth angles principal-axis basis, **не IAU Euler angles**,
  не амплитуда одной чистой моды и не fitted phase/parameter estimate.
- Сравнить первые129выходов каждого96day расчёта с сохранённым32day
  вариантом, проверив старые source/input/NPZ SHA. Новая длина t_bound
  меняет последний короткий шаг и интерполяцию на границе32суток:
  не требовать bitexact; allbody<.1м/pair<.01м/v<1e-6м/с/R<1e-9/S<1e-9.
  Записать отдельно количество битово совпавших строк. Старые данные
  нужны только для анализа ПОСЛЕ propagation, не как IC/restart/force.
- Не отбрасывать рост остатка и малые ухудшения; разделять physical
  model difference, numerical sensitivity и reader precision.

## Воспроизводимость и стоимость

Перед96day проверить неизменные32day receipts и провести короткий8day
cost/consistency preflight без внешних R(t). СохранитьJSON/NPZ/sourceSHA.
Во время jobs scientific closure заморожен; incremental evidence,
fresh outputs, ошибки/partial сохранять. Измерять wall/nfev, не обещать
ускорение и не уменьшать точность ради длительности.

После96day — свежая publiccopy с пробелами в пути/без старой.tools,
запретsocket.connect/create_connection. Заново квалифицировать reader.
Выполнить полное96day nominal интегрирование БЕЗ сохранённых траекторий
и сверить decodedarrays точно. Затем передать5закреплённыхNPZ как явный
вход и заново вычислить все385epoch balances/external/window/libration/
refinement показатели. Это **повтор одного интегрирования и полный
повтор обработки пяти решений**, не повтор всех пяти96dayинтеграций.
32day full5job offline replay уже выполнен264; он не выдаётся за96day.
Те же установленные библиотеки, новая платформа не квалифицируется.
Относящиеся тесты, корректные ссылки/номера строк, обновление контекста.
Годовой расчёт/новый runtime/приливы/3D/GitHub вне этого блока.
