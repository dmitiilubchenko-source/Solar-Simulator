# Лунный квадруполь и консервативное вращение:243–247

Проверена граница совместимости существующих моделей и выполнен
[предварительный протокол](lunar-coupling-protocol.md). Рабочие силы,
начальные данные, Rust, интегратор и default **не изменены**.
Результат — проверенный Newton Q2 coupling и измерение различия двух
лунных полей; это не подключённое к EIH вращение.

Исследованы Newton runtime, H57, совместная инверсия58 и conditional
инициализация67–71, последующие local/metric/continuum contracts.
H57 уже решает отдельную консервативную каноническую задачу; её не
переписывали. Physical harmonic→ADM/SSC/PN-I mapping остаётся открытым.
В `nbody_rotation.validate` запрет EIH+q/S сохранён и покрыт прежними тестами.

## Метод и независимость

440 годовых эпох,10тел, SI/SSB/EclipticJ2000/JD2461321.5TDB, прежние GM.
Геометрия от квалифицированного DE441reader; Moon−Earth прямо из геоцентрических
полиномов. R/Rdot — заданная внешняя DE441ориентация, а не расчёт из начального
spin. Модельная задача проверяет локальное Newton тождество на этих состояниях.

Независимый oracle использует MacCullagh с главным I и complex-step
производными скалярного потенциала по координатам/углам/направлению движения.
Он не импортирует runtime Q, force, torque или quaternion formulas.
Силы, момент и U сверены отдельно. Power identity включает работу орбиты,
omega·tau и Udot; общий угловой момент включает обратный момент фигуры.
Это локальные тождества, не результат годового интегрирования энергии.

| Максимальный относительный дефект | Результат | Заданный порог |
| --- | ---: | ---: |
| Сила против независимого градиента | 3.997839e-12 | 5e-10 |
| Момент против производной по углу | 2.428275e-11 | 5e-10 |
| Потенциал против inertia-form | 3.776484e-12 | 5e-10 |
| Локальный обмен энергией | 1.329402e-10 | 5e-10 |
| Поле I через J2/C22 evaluator | 8.773730e-13 | 5e-10 |
| Сумма сил | 1.449251e-16 | 5e-12 |
| Орбитальный момент + torque | 9.244070e-15 | 5e-12 |

Все440снимков прошли, без ослабления критериев. Отрицательные контроли
без реакции, torque и spin power дали максимальные дефекты
0.499999994/0.499998654/0.4999999999995 >1e-3 каждый.
Последний критерий power имеет меньший запас, чем остальные; это не
основание уменьшать заявленную физическую ошибку или обещать нулевой дрейф.

## Два набора параметров: без подгонки

Опорный радиус обоих полей1738000m. Nominal DE441:
J2=0.000203214360135, C22=0.000022380850528171017.
Из прежнего mean-solid I:
J2=0.00020323499999994383, C22=0.000022427500000015814.
I не менялась; коэффициенты выведены, а не оценены по будущим данным.
Изотропная добавка к I сохраняет Q/J2/C22 и меняет spin/Trot:
данные о gravity сами по себе не определяют среднюю инерцию.

У всех следующих вариантов одинаковый EIH+Sunfixed+Earthprescribed,
меняется только наличие/параметры Moon Q2 на той же заданной ориентации.
Ранее strict использует Earthfixed; его не следует смешивать с этим baseline.
Все статистики baseline и nominal-варианта для10тел точно воспроизвели бюджет240.

| Локальный Moon−Earth acceleration defect | Max,m/s² | RMS,m/s² |
| --- | ---: | ---: |
| Без Moon Q2 | 3.8964981392701934e-11 | 2.860509353264871e-11 |
| Nominal Moon | 1.1248379431095697e-11 | 8.088282014598321e-13 |
| Solid-equivalent Moon | 1.1242864993674504e-11 | 8.075562770673469e-13 |

Различие самих Moon полей в относительном ускорении:
max3.3771056315401373e-14/RMS2.5391131585103597e-14m/s².
Малое различие и чуть меньший RMS solid-варианта не выбирают физически
предпочтительную I: это не свободный spin-прогноз и не анализ наблюдательной
неопределённости. Все10тел/все440точек сохранены в [JSON](lunar-coupling-validation.json)
и локальном `.tools/lunar243/audit245-final.npz`.
Пик обоих вариантов остаётся на6480000s, известной границе полиномов240;
погрешность интерполяционной второй производной не объявляется известной.

## Сохранённые отказы и исправления

1. Первый запуск244:1failed/16passed2.27s. Синтетический fixture дал
   J2=.075/C22=.0125 вне existing prescribed .01 domain. Опорный радиус
   представления того же поля изменён1000→3000m, I/Q и bounding sphere прежние.
   Это исправление тестового входа, не ослабление допуска. Исходный тест и
   причина сохранены `.tools/lunar243/test244-initial.py`/`failure244.json`.
2. Первыйaudit245 и diagnosticprobe245 завершились complete=false:
   asdict копирует Vector3 без value equality, поэтому guard ошибочно
   считал неизменное состояние изменённым. Сравнение заменено детерминированным
   primitive storage document; тест проверяет повторение и реальное изменение
   массы. Ни модель, ни SHA не менялись. Scientificmetrics до/после исправления
   совпали точно. Старые JSON и исполненный исходник сохранены, не перезаписаны.

## Воспроизведение, цена и границы

В публичной копии без `.tools` и без сети:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_de441_reader --output .tools/reader.json
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_lunar_coupling --output .tools/coupling --reader-receipt .tools/reader.json
```

Выходы должны быть новыми: повтор в существующий путь отвергается,
включая failed report. Команды используют фактические CLI обоих модулей;
replay вызывал те же `run` функции в отдельном child interpreter.
Выполненный автономный child-process из пути с пробелами пересоздал reader
и audit: все scientificmetrics и17decodedNPZarrays совпали точно.
Использован тот же установленный native binary/venv: новая сборка или другая
платформа не квалифицированы. SHA closure/inputs проверены до и после.

Audit245:4.2080369s после подготовки входов; offline replay process12.5688585s.
Это одиночные измерения стоимости, не доказательство ускорения.
18новых тестов прошли2.48s; полный246:1819 Python/17Rust/fmt/links,
wall477.312s, 817 публичных файлов неизменны во время выполнения.
Предыдущий полный241:1801Python/17Rust; новые18 входят в1819.
Неудачный начальный тест и ошибочный guard не скрыты успешной регрессией.

Следующий минимальный этап: на отдельной синтетической harmonic EIH+Newton
Q2 задаче проверить порядок усечения и источники баланса E/P/J при динамических
q/S. Использовать прежние Noether/действие, явно отличать phenomenological
hybrid от полного PN-протяжённого тела; не снимать runtime guard заранее.
Перенос real Moon требует отдельного доказательства I/clock/triad/SSC.
Приливы, ядро, деформации, 3D и подгонка IC здесь не добавлены.
Прежний global Noether visibility FAILED и отсутствие годового spin/EIH
баланса сохраняются. Койпер420/528 экспериментальный, его ограничения прежние.
Рекомендуемая следующая модель: GPT-6.1 Sol High для проверки порядка и реакций.

## Код и независимые проверки

- [hat](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_lunar_coupling.py:9)
- [potential](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_lunar_coupling.py:14)
- [derivatives](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_lunar_coupling.py:21)
- [model_snapshot](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_coupling.py:36)
- [coefficients](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_coupling.py:41)
- [fraction](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_coupling.py:50)
- [coupling_checks](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_coupling.py:60)
- [qualification](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_coupling.py:91)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_coupling.py:102)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_coupling.py:213)
- [test_complex_derivative_has_known_radial_force_and_power_in_si](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_coupling.py:12)
- [test_spatial_torque_sign_and_orientation_power_have_analytic_value](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_coupling.py:23)
- [test_gravity_does_not_determine_mean_inertia_or_spin_energy](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_coupling.py:34)
- [test_invalid_reference_radius_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_coupling.py:45)
- [test_coupling_identity_uses_reaction_and_spin_power](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_coupling.py:50)
- [test_incomplete_or_failed_scientific_evidence_cannot_qualify](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_coupling.py:87)
- [test_exact_zero_scale_cannot_hide_a_nonzero_defect](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_coupling.py:102)
- [test_model_snapshot_compares_numeric_state_and_detects_a_real_change](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_coupling.py:108)
- [test_existing_failed_audit_is_preserved_before_any_input_read](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_coupling.py:120)
