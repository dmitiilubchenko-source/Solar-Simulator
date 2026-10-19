# Локальный бюджет различий модели Solar и DE441

2026-10-16T22:08:23+03:00,239–242. [Протокол до измерений](solar-defect-protocol.md),
[все10тел/5вариантов/6компонентов/bridges](solar-defect-validation.json).
Новых сил, параметров, начальных условий или интегрирований нет.

Измерено a_model(r_DE,v_DE,t)−d²r_DE/dt² на440эпохах прежнего года.
Это **локальный дефект уравнения на пути полиномиального эталона**,
не ошибка свободной орбиты и не прямое ускорение из наблюдений.
Нельзя умножить максимум на t²/2 и объявить причиной годового остатка.
Исходный лунный орбитальный остаток≈726м сохраняется.

## Результат без подбора параметров

| Предзаданный вариант | RelativeMoon max, м/с² | RMS, м/с² |
|---|---:|---:|
| newton | 1.42758336e-09 | 1.06444005e-09 |
| point_eih | 1.59572774e-09 | 1.18766675e-09 |
| strict | 3.90564088e-11 | 2.85558983e-11 |
| earth_orientation | 3.89649814e-11 | 2.86050935e-11 |
| earth_orientation_plus_moon | 1.12483794e-11 | 8.08828201e-13 |

На этой сетке вариант с заданными ориентациями Земли и Луны и уже
существующим номинальным луннымJ2/C22 уменьшил RMS относительноstrict в35.305270раз.
Лунное поле — обоснованный кандидат для следующего независимого модельного
эксперимента; полная причина годовой ошибки этим не установлена.
ПолюсЗемли/лунныеуглы заданы извне; это не консервативный прогноз вращения.
Никакойbest-fitGM/фазы/J2 или выбора новогоdefault по440остаткам нет.

Неудобные результаты сохранены: pointEIH хужеNewton в этом частичном
сравнении, а одна смена полюсаЗемли увеличилаRMSstrict. Меньший остаток
частичной модели сам по себе не выбирает физически правильные уравнения:
отдельные вклады могут компенсироваться. Максимум иRMS показаны оба.

## Как проверены вычисления

Те же10масс/Origin/SSB/TDB/EclipticJ2000/SI, полная3Dгеометрия;
Moon−Earth подставляется непосредственно в парную геометрию. Шесть
включений:Newton,PN,Sunfixed,Earthfixed,Earthprescribed,Moonprescribed.
Варианты4–5 заменяютEarthfixed, не прибавляют второйEarthJ2.
Native EIH на каждой440эпохе сверён с отдельно реализованной матрицей;
максимальная относительная норма1.18816088e-15<3e-14.
Четыреtensorfigure сверены с body-axis vectorформулой: max
2.29349944e-15<5e-12.
Ненулевые источники нормировались на собственную силу, безepsilon.
ВсеNPZкомпоненты/векторыдефектов иSHA сохранены в.tools/de441236/defect240.
ПубличныйJSON содержит все бюджеты иSHA; сыройNPZ воспроизводится командой ниже.

Первичные основание/границы: локальные Park2021 §§2.2,3.1–3.3 и
Vines EIHaction (см.[запас](offline-data.md)). DE441 включает дополнительные
малые тела, более высокиегармоники и деформации, которые здесь не добавлялись.
Оставшийся вклад каждого из них количественно этим этапом не установлен.

## Пик на границе интерполянтов — отдельное ограничение

Вариант+Moon имеет максимум1.124837943e-11м/с² на6480000с. После просмотра
максимума выполнена **posthocдиагностика**, не новый критерийPASS:
это точная4-дневная граница геоцентрических лунных полиномов (record3,
segment1,x=−1). Две вторые производные отличаются на
1.24945613e-11м/с²;
defect справа1.12483794e-11, слева
3.39288266e-12м/с². Все исходные максимумы/точки оставлены.
FDскоростиh1000/100/10/1с дали соответственно
[5.253877408299602e-09, 5.2683144606015094e-11, 5.46917305181152e-12, 5.369645656835615e-12]м/с².
Это не замена эталона более удобной кривой и не уточнение физической ошибки.

Максимальныйскачок луннойвторойпроизводной по115records:
1.52339621e-11м/с².
Он сопоставим с остаточным пиком; оценки не являются rigorouserrorbar.
Decimal проверял вычисление полиномов, а не погрешность их второй
производной относительно исходногоинтегратора JPL. Поэтому нельзя объявлять
весьостаточный пик ошибкойruntime и нельзя считатьRMS8e-13 гарантией силы.

## Воспроизведение и следующий шаг

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_de441_reader --output .tools/my-reader.json
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_solar_defect --reader-receipt .tools/my-reader.json --output .tools/my-defect
```

Выходыновые; сеть/старая.tools не нужны, nativeRustмодуль должен быть собран.
Freshpubliccopy повторила все scientificvalues exact с той жеnative.pyd.
Время modeldriver4.509703с после подготовкиreader/эталонных
ускорений; одиночный замер, CPUнефиксирован. Это цена диагностики, не
ускорениедвижка.86relatedtests/38newpassed3.47с; полный2411801Python/17Rust
иfmt/links passed. Исследовательские годовые траектории215 не пересчитывались.

Следующий независимый шаг — проверить применимость уже имеющегося
консервативного вращения/инерции/обратных моментов Луны к текущейEIHмодели,
сначала отдельные модельные задачи и балансы. Prescribedвариант не
подменяет такуюпроверку. Новые приливы и измененияdefault отложены.
Прежний Noether visibilityFAILED220/годовыеNoetherfalse/standardfalse/
anyICfalse остаются;3D/Койпер/GitHub не затрагивались.

- [relative_gap](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_defect.py:27)
- [compose](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_defect.py:35)
- [statistics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_defect.py:45)
- [snapshot](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_defect.py:54)
- [source_derivative_jumps](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_defect.py:73)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_defect.py:91)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_defect.py:173)
- [test_declared_variants_replace_earth_field_without_double_counting_it](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_defect.py:8)
- [test_unexpected_component_inventory_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_defect.py:18)
- [test_exact_zero_source_cannot_hide_spurious_nonzero_force_with_epsilon](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_defect.py:26)
- [test_invalid_force_comparison_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_defect.py:35)
- [test_vector_rms_and_worst_epoch_have_known_geometric_values](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_defect.py:40)
- [test_previous_diagnostic_failure_is_preserved_before_inputs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_defect.py:47)
