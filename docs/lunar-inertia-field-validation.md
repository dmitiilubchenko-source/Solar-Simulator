# Инерция и гравитационное поле Луны: аудит287–293

18 октября 2026. Независимые арифметические и силовые проверки прошли.
Рабочая физика, начальные условия, профиль инерции51 и прежние годовые
траектории сохранены. Нового свободного прогноза здесь нет.
[Протокол до расчётов](lunar-inertia-field-protocol.md),
[полные измерения, SHA и ограничения](lunar-inertia-field-validation.json).

## Что установлено и что остаётся открытым

Код использует один I для вращения и Q2 — это согласованность модели.
Но mean-solid жёсткий эквивалент51 и недеформированный полный тензор
Луны в DE441 описывают разные физические величины. Аудит69 уже отмечал
эту границу. Текущий опыт количественно проверяет поле, а не объявляет
старое ограничение новой найденной ошибкой программы.

Повторно прочитан локальный первичный
[Park et al.2021, §4.2, Eq46–54](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf):
undistorted total, mantle, core и mean не взаимозаменяемы; средняя приливная
деформация ненулевая. SHA PDF сверён с закреплённым source manifest.
[Williams2014 §5](https://doi.org/10.1002/2013JE004559) используется только
через прежнюю транскрипцию51/69. Новая попытка полного текста дала HTTP403,
поисковые инструменты — transport error; ответ403 не является статьёй.
Новой независимой проверки этой транскрипции в данном блоке нет.

## Арифметика и происхождение

Нормировка a,b,c = A,B,C/(M Rref²), Rref=1738000м;
exclusion radius=1800000м не используется вместо Rref.
J2=c−(a+b)/2, C22=(b−a)/4. Обратная задача при заданном среднем h:
a=h−J2/3−2C22, b=h−J2/3+2C22, c=h+2J2/3.

|Величина|Из offsets профиля51|ASCII header441|
|---|---:|---:|
|J2|0.000203235|0.000203214360135000010|
|C22|0.0000224275|0.0000223808505281710172|
|C22/J2|0.110352547543484|0.110134197766845|

Номинальные J2/C22/AM точно совпадают с orientationJSON. Точное чтение
Decimal70 выполнено из D-токенов исходного header, не из float.
В JPL tech-comments C22M=2.2380845245752079e-5 отличается от закреплённого
ASCII header; это сохранённый вариант источника, он не подменяет header.
Причина расхождения файлов в этом блоке не установлена.

Условное округление каждого опубликованного offset до1e-8, nearest,
даёт J2∈[0.000203225,0.000203245],
C22∈[0.000022425,0.000022430]. Перебраны все8вершин. Оба номинальных
значения вне этих интервалов. Это **не** covariance или доверительный
интервал физических данных: проверена только заявленная модель округления.
Общая uncertainty среднего ±.000012 сокращается из J2/C22. Общая смена
массы/радиуса сохраняет C22/J2, поэтому не объясняет различие обоих чисел.

В условной подстановке J2M как недеформированного J2 в Eq47–51 Park
получены a=.392762257516934,b=.392851780919046,c=.393010233578125;
восстановленный C22 отличается от header на−2.88237e-22.
Это алгебраическая совместимость набора header, не сертификат физического
переноса его полной инерции в ротор51 без мантии/ядра/деформаций.

Средние h=.392728 и1.1h — только два математических дополнения того же
Q2. Roundtrip float J2/C22≤3.05201e-13 при пороге5e-12; Decimal70
невязка на используемой точности нулевая. Изотропный сдвиг I меняет
S и энергию вращения при той же ω, хотя поле Q2 сохраняется.
Ни одно дополнение не назначено новыми начальными условиями вращения.

## Силы на годовой сетке

10тел, SI/SSB/EclipticJ2000/JD2461321.5TDB,1462эпохи через21600с
до31557600с включительно. Общая предписанная DE441 траектория и R(t).
Strict=point EIH1PN+fixed Sun/Earth J2; solid добавляет Q2 из I51;
nominal заменяет только MoonQ на headerJ2/C22; последний случай также
использует прежнюю приближённую Earth orientation. Она не равна точному
вращению DE441. Все обратные силы включены.

Ускорение модели сравнивается со второй производной полинома DE441.
Это локальный acceleration defect, а не ошибка новой интегрированной
орбиты, не наблюдательная погрешность и не причинная доля прежних5.66м.

|Случай|Earth–Moon RMS всех эпох,м/с²|Max всех эпох,м/с²|RMS внутри полиномов,м/с²|
|---|---:|---:|---:|
|strict|2.855162663e-11|4.142042683e-11|2.855163140e-11|
|solid_fixed|7.706160914e-13|1.122898972e-11|2.932834905e-13|
|nominal_fixed|7.696705528e-13|1.123402913e-11|2.914417082e-13|
|nominal_earth_prescribed|7.522655192e-13|1.124837980e-11|2.505495157e-13|

Переход solid→nominal не обязан улучшать результат: общий максимум
чуть вырос, RMS изменился слабо. Все невыгодные результаты сохранены.
Max изменения относительного Moon-поля3.377105632e-14м/с²;
max изменения ньютоновского момента на Луне1.324810963e17Н·м.
Момент здесь диагностический: нового интегрирования S и баланса закрытой
системы нет. Простая замена коэффициентов не доказана решением остатка.

Максимум norm(defect) по каждому телу, без исключений:

|Тело|strict,м/с²|solid_fixed,м/с²|nominal_fixed,м/с²|nominal_earth_prescribed,м/с²|
|---|---:|---:|---:|---:|
|Sun|8.326603594e-13|8.326603594e-13|8.326603594e-13|8.326603594e-13|
|Mercury|2.253786059e-11|2.253786059e-11|2.253786059e-11|2.253786059e-11|
|Venus|7.008931144e-12|7.008931144e-12|7.008931144e-12|7.008931144e-12|
|Earth|2.507560063e-12|2.631233588e-12|2.631101112e-12|2.631348581e-12|
|Moon|4.038330765e-11|1.178590504e-11|1.178830608e-11|1.178694830e-11|
|Mars|2.430723200e-12|2.430723200e-12|2.430723200e-12|2.430723200e-12|
|Jupiter|6.064228611e-13|6.064228611e-13|6.064228611e-13|6.064228611e-13|
|Saturn|7.095122744e-14|7.095122744e-14|7.095122744e-14|7.095122744e-14|
|Uranus|3.723272685e-14|3.723272685e-14|3.723272685e-14|3.723272685e-14|
|Neptune|1.356198466e-13|1.356198466e-13|1.356198466e-13|1.356198466e-13|

91эпоха находится не далее1с от границы Moon/slot9,1371 — внутри.
Все91 включены в общие RMS/max. Худший solid/nominal относительный
defect находится на такой границе; interior max также сохранён и ненулевой.
Это не разрешает удалять границы или объявлять весь остаток ошибкой JPL.
Сохранены ускорения t−.001 и t+.001с и их разность: max2.962250940e-11м/с².
Эта конечная двусторонняя разность включает **плавное физическое изменение**;
она не изолирует чистый скачок полиномов в точных односторонних пределах.
Именно поэтому следующий полезный шаг — независимая метрология эталонного
ускорения на стыках и внутри сегментов до более сильной атрибуции причин.

## Независимость и воспроизводимость

Собственная норма каждого тела, каждой эпохи: point EIH две реализации
max1.295493e-15<5e-12; nominal коэффициентная векторная формула против
runtime-тензора2.984746e-15; force-completions I→Q2 max1.558829e-12
и8.544773e-13<5e-10. Большая сила у другого тела не скрывает малую.
Сверка полного point-force не переаттестует отдельно видимость малого PN.

15новых независимых аналитических/чувствительных тестов;
325связанных тестов passed13.74с, без изменения862публичных файлов.
Полный исторический набор246 (1819Python/17Rust/fmt) здесь не повторялся.
Преflight3эпохи0.033с; все его27массивов совпали с соответствующими
строками полного опыта.1462snapshots8.046с на текущем компьютере.
Это стоимость диагностики, а не ускорение годового интегратора.

В свежей публичной копии с пробелами в пути, без старой.tools и личных
документов, сетевые socket-подключения запрещены. Повторно выполнен reader
(2.097с), затем все1462snapshots (9.155с);27декодированных массивов
и все научные метрики **точно совпали**. Установленные Python/NumPy/SciPy
общие; переносимость на иной компьютер и новую среду этим не доказана.

Команды из корня проекта (новые пути вывода обязательны):

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_de441_reader --output .tools/reader-new.json
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_lunar_inertia_field --output .tools/field-new.json --reader-receipt .tools/reader-new.json
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_lunar_inertia_field.py -q -p no:cacheprovider
```

Код и тесты с проверенными строками:

- [assess_lunar_inertia_field.own_relative](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_inertia_field.py:41)
- [assess_lunar_inertia_field.complete_moments](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_inertia_field.py:53)
- [assess_lunar_inertia_field.coefficients](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_inertia_field.py:58)
- [assess_lunar_inertia_field.decimal_header](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_inertia_field.py:63)
- [assess_lunar_inertia_field.arithmetic](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_inertia_field.py:73)
- [assess_lunar_inertia_field.boundary_distance](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_inertia_field.py:120)
- [assess_lunar_inertia_field.snapshot](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_inertia_field.py:126)
- [assess_lunar_inertia_field.grouped_metrics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_inertia_field.py:158)
- [assess_lunar_inertia_field.qualification](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_inertia_field.py:168)
- [assess_lunar_inertia_field.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_inertia_field.py:190)
- [assess_lunar_inertia_field.main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_inertia_field.py:293)
- [test_lunar_inertia_field.source_arithmetic](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:13)
- [test_lunar_inertia_field.test_known_integer_quadrupole_and_mean_are_inverted_independently](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:19)
- [test_lunar_inertia_field.test_isotropic_inertia_freedom_preserves_potential_force_torque_but_not_spin](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:26)
- [test_lunar_inertia_field.test_decimal_rounding_corners_have_analytic_widths_and_common_mean_cancels](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:36)
- [test_lunar_inertia_field.test_common_scaling_cannot_change_c22_to_j2_ratio](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:50)
- [test_lunar_inertia_field.test_park_inversion_satisfies_definitions_without_certifying_physics](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:57)
- [test_lunar_inertia_field.test_orientation_mismatch_cannot_silently_replace_header](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:67)
- [test_lunar_inertia_field.test_own_body_norm_detects_small_outer_field_hidden_by_global_max](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:74)
- [test_lunar_inertia_field.test_invalid_force_comparison_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:83)
- [test_lunar_inertia_field.test_grouped_metrics_retain_seam_outlier_in_overall_error](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:91)
- [test_lunar_inertia_field.test_real_boundary_distance_is_zero_at_known_moon_segment_join](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:101)
- [test_lunar_inertia_field.test_existing_output_is_rejected_before_source_or_scientific_work](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_inertia_field.py:111)
