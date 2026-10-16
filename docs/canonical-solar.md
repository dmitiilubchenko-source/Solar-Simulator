# Канонический conditional аудит исходных десяти тел

Изменение 61, 11 октября 2026 года. Расширение независимой численной
проверки [задачи60](lunar-canonical.md) до исходной системы Sun, Mercury,
Venus, Earth, Moon, Mars, Jupiter, Saturn, Uranus, Neptune. Это отдельный
research аудит [конечного H57](rigid-pn.md), а не рабочая полная эфемерида.
Астероиды, KBO и кольцо не добавлены; одна фигура Moon, остальные тела
имеют точно нулевые ideal point-spin.

## Начальные данные и протокол

[canonical-solar-policy.json](../scripts/canonical-solar-policy.json)
записана до результатов. Загружен неизменяемый conditional checkpoint
58–59 с SHA 5c619067a113779491afbd97f811d65bb77af9a5bb45a14f8f3bc49be9edf76d.
Его p/S/q/x сохранены побитово. Это именно 10-body совместная инверсия58,
а не дополнение семи планет к 3-body initial60. Solver controls отдельно
заданы для нового опыта; сохранён выбранный базис/единицы/эпоха/provenance.
Физический SSC/tetrad/PN-Q2/time перенос по-прежнему не сертифицирован.

32 суток=2764800 s, 129 эпох, split64. Production worst-block DOP853
rtol1e-11, x atol1e-4 m, p atol=m×1e-10 m/s, figure-S atol1e-13
×initial norm, q atol1e-13, zero point-spin absolute atol1e-30 model units,
max_step21600 s. Tighter rtol3e-13, atol×.03, max_step10800 s.
Два **новых** independent matrix/body-Euler RK45 имеют rtol3e-13/3e-14,
atol=.01 rtol×nonzero initial x/p/S norm, R scale1, zero point-spin
явную абсолютную atol. Исходники не меняются во время всех jobs.

Как в60, H/J/q <1e-9, scaled P <1e-10; каждая абсолютная позиция
и отдельная Earth–Moon relative orbit <1 m; matrix/figure-S differences
<1e-8. Те же критерии для ref uncertainty/tighter/file restart.
Идеальные point-spin должны оставаться точно нулевыми, initial/current
round-trip — bitwise, metadata и source SHA — сохранены.
Будущие DE441 не читаются, подгонки нет. Структура source checks и
checkpoint описана в [59](canonical-checkpoint.md).

## Результаты

[Неизменяемый аудит](canonical-solar-validation.json): passed=true,
failed_criteria=[], все пять обязательных подтверждений true. Идеальные
point-spin остальных девяти тел остаются точно нулевыми; начальный
10-body x/p/S/q и file round-trip сохранены побитово.

| Измерение | Максимум |
|---|---:|
| H /scaled P /J drift | 2.0518968e-15 /2.4376014e-16 /6.1341306e-16 |
| Сырая норма q | 6.6613381e-16 |
| Reference orthogonality /det | 3.0190538e-12 /2.1352919e-12 |

| Сравнение | Все позиции, m | Earth–Moon, m | Figure S relative | Raw matrix difference |
|---|---:|---:|---:|---:|
| Production /strict independent | 0.008509054 | 0.002021056 | 1.4017590e-14 | 1.5526354e-13 |
| Два independent levels | 0.011693575 | 0.003131365 | 1.9438705e-14 | 1.4078963e-12 |
| Production /tighter | 0.002191343 | 0.001852323 | 1.0103778e-14 | 3.3744986e-14 |
| JSON restart, весь path | 0.000093976 | 0.000096851 | 2.3744933e-16 | 1.0567314e-15 |

Численное agreement меньше чувствительности эталона: 8.51 mm против
11.69 mm по всем телам, 2.02 mm против3.13 mm по Earth–Moon. Эти числа
не являются строгими верхними границами ошибки. Tightening production
не гарантирует истинного глобального улучшения при float64; измеренная
чувствительность показана отдельно. Как в60, сравнение сырого R включает
остаток ортогональности, а не только физический угол ориентации.

Production29.92 s, tighter54.33 s, независимые55.64/88.93 s,
restart-prefix/suffix13.97/13.75 s. Source и архивы фиксировались после
каждого job, без редактирования выполняемых исходников. Все массивы и
checkpoint файлы находятся локально в .tools/rotation61 с SHA в отчёте.
3 новых теста0.95 s, 149 относящихся тестов21.12 s; неудачных запусков
в61 не было. Неизменяемый input и false-certification проверены отрицательно.
Полный runtime/Rust прогон не повторялся: рабочие модули не менялись.

## Проверенные ссылки и ограничения

- [Исходное состояние и новые допуски](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_canonical_solar.py:22),
  [отдельные SI/relative сравнения](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_canonical_solar.py:51),
  [аудит](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_canonical_solar.py:68).
- [Initial bitwise /independent derivatives](C:/Users/Admin/Desktop/Solar-simulator/tests/test_canonical_solar.py:16),
  [relative Earth–Moon criterion](C:/Users/Admin/Desktop/Solar-simulator/tests/test_canonical_solar.py:28),
  [отклонение источников/ложного claim](C:/Users/Admin/Desktop/Solar-simulator/tests/test_canonical_solar.py:38).

Новый размер N проверяет численную реализацию выбранного H; полный PN
extended-body model, рабочий runtime и physical accuracy от этого не
появляются. Старые годовые Moon/DE441 и KBO/SB441 остатки этим исследованием
не объясняются. Полный состав384/кольцо528 здесь не сертифицирован.
Следом — физическая применимость initial projection, относительное
каноническое представление и сквозной runtime по отдельному договору.
Приливы после консервативных проверок; визуальные модели для будущего3D
не заменяют закреплённые физические I/массы/ориентационные соглашения.

Сохранность: [rotation61-provenance.json](rotation61-provenance.json).

Последующее исследование62: [относительная каноническая пара](relative-canonical.md).
Это новый численный опыт, исходный аудит61 остаётся неизменным.
