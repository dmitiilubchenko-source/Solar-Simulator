# Ускорения DE441: метрология294–300

18 октября2026. **Численное дифференцирование reader прошло независимую
проверку.** Существенные скачки ускорений принадлежат кусочному
полиномиальному представлению, они не устраняются повышением точности
его вычисления. Истинное астрономическое ускорение этим не определено.
[Протокол до результатов](de441-acceleration-protocol.md),
[полные измерения и SHA](de441-acceleration-validation.json).

## Исходные данные и методы

Тот же закреплённый `de441-reader-inputs.zip`,115ASCIIrecords и header;
официальный первичный
[JPL ASCII format](https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/ascii_format.txt)
повторно прочитан из архива, SHA ee3c94fcb66eb15efa6fd0084e1629c8464defafa547d73c641eb692a7bb73dd.
Сети не было. Сохранены SI/SSB/EclipticJ2000/JD2461321.5TDB,
10тел/прямой Moon−Earth, прежние GM системных барицентров.

Reader: NumPy Chebyshev derivative и Clenshaw в float64.
Новый независимый oracle: T_n→степенные коэффициенты через
T_(n+1)=2xT_n−T_(n−1), обычная производная и Horner в Decimal70/90.
Reader.locate/chebval/chebder/старая derivative recurrence не используются
oracle. Выбор подинтервалов сделан через границы исходных ASCIIзаписей,
left/right задаются явно, без epsilon и сдвига эпохи к выгодному полиному.
Ось/поворот/EMRAT общие с прежним reader — их физические значения здесь
не перепроверяются независимо. Производная имеет множитель(2/span_s)^order.

Два набора коэффициентов: точные D-токены и точные Decimal.from_float
представления binary64. Frame/EMRAT в обоих случаях одинаковые binary64.
Их различие измеряет только округление коэффициентов при чтении,
а не точность исходной эфемериды относительно природы.

## Годовая сетка

1462эпохи0..31557600с через21600с,11отдельных векторов:
10барицентрических ускорений и прямой Moon−Earth. Все эпохи сохранены,
в том числе91стык. Никакой орбитальной интеграции, нового RHS или fit.

|Проверка|Max абсолютной нормы,м/с²|Max собственной относительной нормы|
|---|---:|---:|
|binary_precision|4.566271326e-71|2.412123853e-69|
|raw_precision|3.433840957e-71|1.831069188e-69|
|reader_binary|1.482343842e-17|6.718131136e-16|
|raw_binary|3.880191964e-18|1.523920978e-16|

Пороги до опыта:70/90 relative<1e-50,reader−binary90 absolute<1e-15м/с²
и relative<5e-13 по **каждому** вектору. Оба прошли. Raw−binary —
диагностика без требования улучшения. Различие с orbital model нельзя
считать ошибкой дифференцирования только из-за большого model defect.

## Точные односторонние пределы

Объединение границ активных10позиционных блоков внутри года содержит
91эпоху: от3 до363суток с шагом4суток. На остальных блоках, не меняющих
полином в данную эпоху, левый и правый пределы одинаковы. Пределы
p/v/a и jumps=right−left получены Decimal90; малые разности вычтены
**до** преобразования в float. Raw-source и binary64 jumps сохранены оба.

Максимальные прямые Earth–Moon скачки:

|Производная|Max норма в SI|Эпоха,с|Заранее заданный legacy236 порог|
|---|---:|---:|---:|
|Положение,м|1.885962420e-07|22032000|1e-02|
|Скорость,м/с|6.844587407e-13|259200|1e-07|
|Ускорение,м/с²|1.347533505e-11|6825600|1e-09|

Порог согласованности полиномов прошёл каждый вектор. Он не означает,
что ускорения точны до1e-9м/с² или что между записями скачка нет.
Max относительного скачка ускорения1.347533505e-11м/с² сопоставим с
максимальными model defects после MoonQ. Это ограничение интерпретации
локальной диагностики, а не сертификат ошибки JPL или всего year residual.

## Разделение скачка и плавного движения

D(h)=a_right(t+h)−a_left(t−h)=J+S(h),
J=a_right(t)−a_left(t),
S(h)=[a_right(t+h)−a_right(t)]+[a_left(t)−a_left(t−h)].
Используются реально представленные float64 t±h; их интервалы сохранены.
Скрытой коррекции времени нет. Тождество проверено Decimal90 по векторам;
максимальная невязка0 на этой точности, порог1e-50м/с².
Сравнение D с floatreader<2e-15м/с², измерено1.438707e-16м/с² по всем телам.

|h,с|Max norm D relative,м/с²|Max norm S relative,м/с²|
|---|---:|---:|
|1|1.944112868e-08|1.943240140e-08|
|0.1|1.951986949e-09|1.943240169e-09|
|0.01|2.032574829e-10|1.943240459e-10|
|0.001|2.962250921e-11|1.943236839e-11|

Максимумы разных векторов/эпох не складываются и не вычитаются.
Отсутствующий J даёт собственный контрольный сигнал max1, неверный знак
max2, оба>1e-3. Нормы D могут уменьшаться или расти из-за компенсации.

На прежней худшей эпохе75суток: norm J=1.249456149e-11,
norm S(.001)=1.855148373e-11, norm D(.001)=8.872520260e-12м/с².
Сумма **векторов** J и S имеет меньшую норму из-за направления.
Значение2.96225094e-11м/с² из287–293 было max конечной разности,
оно не являлось чистым скачком. Старый отчёт и исходные массивы сохранены.

## Остатки по двум ветвям

Для каждой из4силовых моделей289 удержана общая F(t) из прежней правой
траектории. Меняется только reference acceleration:
d_left=F−a_left,d_right=F−a_right. Сила по немного отличающимся левым
p/v не пересчитывается. Проверено d_right−d_left=−J, max3.986814e-18м/с²
при пороге2e-15. Это контролируемая смена reference branch,
не новая модель и не независимый расчёт истинного ускорения.

|Модель|RMS left на91стыке|RMS right на91стыке|Max left|Max right|
|---|---:|---:|---:|---:|
|strict|2.891190347e-11|2.855155479e-11|4.694252237e-11|4.142042701e-11|
|solid_fixed|2.875747456e-12|2.871383308e-12|1.125718891e-11|1.122898973e-11|
|nominal_fixed|2.877424989e-12|2.870133921e-12|1.127992651e-11|1.123402913e-11|
|nominal_earth_prescribed|2.858311892e-12|2.854120187e-12|1.134394367e-11|1.124837980e-11|

Все значения в м/с², для прямого Moon−Earth. На75сутках solid left
3.606375092e-12 против right1.122898973e-11, но максимум всех91left
1.125718891e-11 остаётся того же порядка. Выбирать сторону отдельно
по меньшему остатку было бы подгонкой эталона. Никакая сторона не
выбрана «истинной», границы не удалены из старых общих1462метрик.
Причина реального орбитального остатка3.29/5.66м не установлена.

## Стоимость, проверки и ограничения

21новый тест: известный кубический полином/производные/масштаб времени,
явный выбор сторон, независимость отreader, исчезающе малая разность
доfloat, собственная норма малой силы, компенсация J+S и отрицательные
контроли.346связанных тестов passed15.89с;868публичных файлов неизменны
во время проверки. Полный исторический набор246 (1819Python/17Rust/fmt)
здесь не повторялся. Runtime, Rust, IC и профиль51 не изменены.

Preflight3эпохи/3стыка0.108с;19его массивов точно совпали с выбранными
строками полного опыта. Основная вычислительная стадия1462/91/4h и
сохранение8.782с;таймер не включает загрузку старого force evidence,
читателя и созданиеoracle. Это диагностика, не ускорение интегратора.

В чистой publiccopy с пробелами, без старой.tools/личныхdocs и с запретом
socket-сети заново выполненыreader2.197с,1462силы10.037с и новый опыт8.108с.
Весь child21.899с;19новых и27силовых массивов, все научные метрики exact.
Установленные Python/NumPy/SciPy общие, новая платформа не квалифицирована.

Для воспроизведения из корня, каждый output должен быть новым:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_de441_reader --output .tools/reader-new.json
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_lunar_inertia_field --output .tools/field-new.json --reader-receipt .tools/reader-new.json
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_de441_acceleration --output .tools/acceleration-new.json --force-receipt .tools/field-new.json
.venv/Scripts/python.exe -X utf8 -B -m pytest tests/test_de441_acceleration.py -q -p no:cacheprovider
```

Численный reader менять оснований нет. Дальше — первичный контракт
недеформированных I/Q2 и начального вращения для условной жёсткой модели
Луны, с явным учётом отсутствующих мантии/ядра/деформаций и без подгонки
к годовым остаткам. Это ещё не разрешение перенести её в рабочий профиль.
Текущие strict/runtime accuracy и прежние ограничения Noether/PNmapping
сохранены. Новая физическая точность, непрерывный bound и общая причина
неполноты модели данным аудитом не доказываются.

Код и тесты с проверенными строками:

- [de441_power.decimal](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:10)
- [de441_power.power_basis](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:14)
- [de441_power.derivative](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:33)
- [de441_power.horner](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:42)
- [de441_power.choose](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:48)
- [de441_power.Oracle](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:57)
- [de441_power.Oracle.__init__](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:58)
- [de441_power.Oracle.polynomials](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:78)
- [de441_power.Oracle.evaluate](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:90)
- [de441_power.Oracle.seams](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:115)
- [de441_power.errors](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:119)
- [de441_power.split_difference](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_power.py:137)
- [assess_de441_acceleration.previous](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_acceleration.py:24)
- [assess_de441_acceleration.qualification](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_acceleration.py:38)
- [assess_de441_acceleration.metrics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_acceleration.py:63)
- [assess_de441_acceleration.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_acceleration.py:87)
- [assess_de441_acceleration.main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_acceleration.py:170)
- [test_de441_acceleration.test_known_cubic_conversion_and_derivatives_have_analytic_coefficients](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:12)
- [test_de441_acceleration.test_constant_and_linear_polynomials_have_exact_zero_acceleration](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:23)
- [test_de441_acceleration.test_exact_join_selection_is_explicit_and_does_not_use_epsilon](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:29)
- [test_de441_acceleration.test_missing_block_or_ambiguous_side_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:34)
- [test_de441_acceleration.test_smooth_motion_and_true_jump_are_separated_vectorially](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:38)
- [test_de441_acceleration.test_jump_and_smooth_change_can_cancel_without_a_monotone_norm](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:50)
- [test_de441_acceleration.test_subtraction_precedes_float_and_keeps_sub_ulp_difference](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:57)
- [test_de441_acceleration.test_own_norm_retains_a_small_outer_body_error](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:67)
- [test_de441_acceleration.test_invalid_polynomial_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:74)
- [test_de441_acceleration.test_unsupported_derivative_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:79)
- [test_de441_acceleration.test_real_oracle_does_not_call_reader_selector_or_chebyshev_evaluator](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:83)
- [test_de441_acceleration.test_raw_decimal_token_retains_information_lost_in_binary64](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:93)
- [test_de441_acceleration.test_existing_output_is_rejected_before_loading_scientific_sources](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:98)
- [test_de441_acceleration.test_missing_raw_inventory_cannot_qualify_by_success_flags](C:/Users/Admin/Desktop/Solar-simulator/tests/test_de441_acceleration.py:103)
