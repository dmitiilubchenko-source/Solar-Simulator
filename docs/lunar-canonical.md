# Условная каноническая задача Солнце–Земля–Луна

Изменение 60, 11 октября 2026 года. 32-суточная независимая проверка
[конечного PN/rigid H57](rigid-pn.md) на физических масштабах трёх тел.
Использованы [совместная начальная инверсия58](canonical-initial.md) и
[строгий research checkpoint59](canonical-checkpoint.md). Это не рабочий
PN-режим Experiment и не полная физическая миграция DE441.

## Начальная модель и область утверждения

Sun/Earth/Moon выбраны из закреплённого 10-body файла, остальные тела
не участвуют в этой задаче. Sun/Earth — точки с нулевым ideal point-spin,
Moon — одна rigid-solid-equivalent фигура. Newton Trot/Q2 + orbital 1PN
+ leading SO берутся из того же H57; смешанные члены конечной системы
не называются полным PN extended-body усечением. Нет ядра, deformation,
Earth figure/Q2–Q2, PN corrections к I или tides.

Единственная эпоха JD 2461321.5 TDB, Ecliptic J2000, SSB, SI; SHA входов:
orbital d58227299b10b217246aa5c63f33da51b0fd331b5c7a75bee400d577d6d1f702,
spin 733d91c85c47f991fa7b39dcf66b61efcf62e0990ab74dbf7756af797a4081ba.
Проверены совпадение GM/epoch/frame/parent SHA и касательность Rdot.
M0=GM_Sun/G, L0=149597870700 m, T0=√(L0³/(G M0)), c=299792458 m/s;
G берётся из прежнего профиля. Моменты I, p и S масштабируются явно.

**Условная boundary projection:** прежние x и R/Rdot объявлены начальными
каноническими центрами и finite-H spatial-Euclidean ориентацией/rate.
Затем одновременно решаются v=H_p и W=I^-1 S+ΩSO. Начальный S не просто
скопирован из Newton профиля. Инверсия пересчитана именно для трёх тел,
а не вырезана из 10-body решения58. Нет последующего принуждения к DE441.

Это явный модельный договор, не проверенный полный SSC/tetrad/PN-Q2/time
переход. LO centre-shift и отличия локального spin обсуждены в 58, но этот
расчёт не применяет к исходному x полный physical transform. Нет
преобразования TDB↔TCB↔proper time. В отчёте physical_lunar_mapping_certified
и physical_accuracy_claimed остаются false. Формулы/первичные источники
согласованы в 57–58, а значения источников и рабочие модули не менялись.

## Протокол до результатов

[lunar-canonical-policy.json](../scripts/lunar-canonical-policy.json):
32 суток=2764800 s, 129 эпох, split=64, no fit/future ephemerides.
Выполнены пять свободных paths: production, tighter, два независимых
RK45 и prefix/save/load/suffix. Все их исходники фиксированы на время jobs.
Каждый завершённый job записан в новый локальный NPZ со своим SHA.

Production worst-block DOP853: rtol=1e-11, x-atol=1e-4 m,
p-atol=m ×1e-10 m/s; figure-S atol=1e-13 × initial |S|,
q atol=1e-13, max_step=21600 s. Идеально нулевые point-S имеют заранее
заданную абсолютную atol=1e-30 в model units; это не epsilon, смягчение
сил или назначенная физическая величина spin.

Tighter: rtol=3e-13, все atols ×.03, max_step=10800 s.
Независимые scalar-H complex-step + standard-I/body-Euler/R-matrix RK45:
rtol=3e-13 и3e-14, atols=.01 rtol × начальные x/p/S нормы,
R абсолютный scale=1, нулевые point-spin — явная абсолютная atol.
Сырой q и матрицы эталона не нормируются; ортогональность/det проверяются.

Критерии: H/J/q <1e-9, P/sum|p0| <1e-10; ошибки абсолютных положений
каждого тела **и отдельно Earth–Moon относительной орбиты** <1 m;
figure-S/matrix ошибки <1e-8. Те же пороги для reference uncertainty,
tighter sensitivity и restart. Отдельно требуют exact-zero ideal
point-spins, bitwise checkpoint, сохранение metadata и SHA. Локальный
rtol и общий H/J не заменяют эти независимые орбитальные проверки.

## Результаты

[Неизменяемый аудит](lunar-canonical-validation.json): passed=true,
failed_criteria=[], четыре обязательных логических подтверждения true.

| Измерение | Максимум |
|---|---:|
| H относительный дрейф | 2.4871252e-15 |
| P scaled /J relative drift | 6.5030527e-16 /7.2845186e-16 |
| Сырая норма q | 6.6613381e-16 |
| Reference orthogonality /det error | 1.8134595e-12 /1.2811974e-12 |
| Начальные v/W остатки | 1.5084758e-15 /1.3352293e-16 |

| Сравнение | Все позиции, m | Earth–Moon, m | Figure S relative | Matrix difference |
|---|---:|---:|---:|---:|
| Основной /строгий независимый | 0.000655818 | 0.000598694 | 4.9551554e-15 | 8.9319662e-14 |
| Два независимых уровня | 0.001801581 | 0.001816705 | 9.4750431e-15 | 8.2211510e-13 |
| Основной /tighter | 0.001297462 | 0.001265217 | 8.3764466e-15 | 3.1164484e-14 |
| Новый JSON restart, весь path | 0.000105047 | 0.000126491 | 2.5500083e-16 | 9.7571064e-16 |

Главное ограничение: agreement 0.599 mm не доказывает субмиллиметровую
точность. Чувствительность независимого эталона 1.817 mm, production
1.265 mm — больше этого agreement. Это измеренная численная чувствительность
на заданной сетке, не строгая верхняя оценка ошибки и не точность природы.
Matrix norm сравнивает сырой R и включает потерю ортогональности, а не только
физический угол ориентации. Абсолютные Cartesian x ~1 AU также имеют
float64 разрядность; нет заявления о микронной физической точности.

Длительности jobs: production 2.82 s, tighter 6.34 s, RK45 4.90/6.86 s,
prefix/suffix 1.44/1.44 s. Scientific SHA сохранены; runtime/data unchanged.
3 новых теста passed за0.97 s; 146 относящихся тестов за19.02 s.
Неудачных запусков в60 не было; несовместимые источники/basis/certification
проверены явными отрицательными тестами, критерии не менялись.

После принятия критериев отдельно описательно измерены:
figure-spin norm variation=8.5357344e-5, ΩSO norm=2.6547357e-15…
3.4109574e-15 /s; Earth–Moon distance=364407406.7…404640984.3 m.
Норма figure-S меняется по моменту Q2 и не является point-spin инвариантом.
Эти дополнительные значения не использовались для выбора/ослабления порогов;
локально `.tools/rotation60/descriptive-diagnostics.json`.

## Что этим ещё не выполнено

Нет 10-body интеграционного PN/rigid аудита, рабочего CLI/GUI-режима,
полного физического лунного начального переноса и новой physical accuracy
certification. Прежние 121.84″ year/DE441 и Kuiper/KBO расхождения не
объясняются этим аудитом: будущие DE441 вообще не вызывались.

Следом зафиксировать применимость boundary projection и необходимые
физические tetrad/SSC/инерционные/временные поправки, затем проверить полный
состав тел и relative canonical representation перед сквозным runtime.
Приливы после консервативных проверок; полный проектный/Rust набор нужен
при будущем сквозном изменении рабочего приложения. Portable/commit/push
в60 не выполнялись.

## Проверенные ссылки

- [Начальная projection/масштабы/metadata](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_canonical_diagnostic.py:19),
  [SI и отдельный относительный критерий](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_canonical_diagnostic.py:81),
  [независимый аудит](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_canonical.py:22).
- [Градиенты начального H и bitwise state](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_canonical_diagnostic.py:18),
  [неверные данные/базисы/claim](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_canonical_diagnostic.py:35),
  [отдельная относительная ошибка](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_canonical_diagnostic.py:43).

Сохранность: [rotation60-provenance.json](rotation60-provenance.json).

Продолжение61: [исходные10тел](canonical-solar.md) прошли отдельный новый
32-day independent audit. Исходный3body результат60 не переписывался;
данные для10body взяты из полной инверсии58/checkpoint59, а не из3body.
