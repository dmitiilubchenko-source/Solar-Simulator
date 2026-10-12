# Исследовательское сохранение канонического состояния

Изменение 59, 11 октября 2026 года. Отдельный формат для
[конечного H 57](rigid-pn.md) и [инверсии начальных условий 58](canonical-initial.md).
Рабочие Experiment/schema 9–10 и ньютоновское вращение Луны не изменены.
Этот формат не мигрирует прежние скорости/spin в физическую PN-модель.

## Договор сохранения

`kind=solar-simulator-research-canonical-checkpoint`, schema 1,
`model=finite-adm-1pn-lo-so-newton-one-rigid-q2-v1`.
Начальное и текущее состояния явно хранят positions, momenta, spins и
quaternion(wxyz). Сохраняются массы, c, фигура/I/Rbound/index, elapsed model
time, координатный базис/время, единицы, интеграционные допуски и источники SHA.

Допустимый базис — fixed-no-reboost, canonical-ADM-centres и
finite-H-spatial-Euclidean. Синтетическое время не имеет Julian epoch;
условные TDB-входы явно помечаются TDB-as-input-coordinate-time. Это не
сертификация TDB/TCB/собственного времени. SIUnits сохраняются в виде
M0/L0/G, T0 вычисляется по явной similarity, а не угадывается при загрузке.
`physical_mapping_certified` должен оставаться false: более сильные физические
утверждения этим исследовательским schema не поддерживаются.

Состояния хранятся неизменяемыми tuple; метаданные выдаются отдельной копией.
Начальный q проверяется с 1e-12, текущий сырой q — с 1e-9. Загрузка не
перенормирует q/S и не меняет систему отсчёта. При t=0 current=initial
побитово. Числа finite; строки вместо чисел, bool, неизвестные поля,
повторные JSON-ключи, NaN/Infinity и ошибочные схемы отвергаются.

Canonical payload SHA обнаруживает изменение содержимого документа;
это проверка целостности, не подпись доверенного автора. Для продолжения
обязательны SHA работающих физических модулей/алгоритма; источники читаются
только внутри указанного корня. Проверяются версия, загруженная процессом,
и файлы перед/после интеграции. Отсутствующий или изменённый источник даёт
явный отказ. Нельзя подложить другой source-root при работе текущих модулей.

Сохранение создаёт новый файл эксклюзивно: имеющийся файл не перезаписывается.
Диагностический velocity-export вычисляет dx_canonical/dt из H, а не p/m.
Он явно отделён от harmonic velocity, содержит единицы/SI-export и checksum
исходного checkpoint; загрузчик состояния этот диагностический документ
отвергает. Прежние Experiment документы также отвергаются без миграции.

## Интегратор и протокол

[canonical-checkpoint-policy.json](../scripts/canonical-checkpoint-policy.json)
записан до расчётов. Четыре номинальных периода, 257 эпох, split=128,
rtol=1e-11, atol=0.01 rtol × начальные x/p/S нормы каждого тела,
единичный q-scale, max_step=T/128. Worst-block DOP853 использует уже
проверенную формулу оценки 5(3) из Newton-rotation, с новой раскладкой
9N+4 и отдельным контролем каждого x/p/S/q блока. Добавление неактивных
уравнений не разбавляет оценку. Заданный max_step на этом опыте приводит
к тому же численному пути, что 57; это не доказательство большей скорости.

Выполнены полный путь, независимый prefix, запись middle.json, настоящая
загрузка и suffix в сохранённом фиксированном базисе. Начальные данные,
параметры, сетка и оба matrix/body-Euler RK45 эталона взяты из неизменяемого
57 **после** проверки SHA всех его исходников/архива и совпадения данных.
RK45 заново не запускался: эталон корректно переиспользуется для того же H,
а новый формат/интегратор/restart проверяются новым расчётом. Оба уровня
нужны, чтобы не скрыть чувствительность самого независимого эталона.

Критерии H/J/point-spin/q <1e-9, P/sum|p0| <1e-10,
independent agreement <1e-7, uncertainty/restart <1e-8.
Норма S фигуры по-прежнему не считается инвариантом.

Дополнительно условное 10-body lunar состояние 58 записано/прочитано
побитово и экспортировано в SI. Его скоростные остатки должны быть <1e-12.
Лунная траектория в 59 не интегрировалась; её сохранённые atols демонстрируют
явную политику записи, но не сертифицированы как протокол будущего прогона.
При запуске нужен отдельный заранее заданный научный протокол. Никаких
будущих DE441 или подгонки не было.

## Результаты

[Аудит](canonical-checkpoint-validation.json): passed=true, все шесть
логических подтверждений пройдены — synthetic/lunar bitwise round-trip,
metadata preservation, sources verified, legacy/export rejection.

| Измерение | Максимум |
|---|---:|
| H / J относительный дрейф | 3.0562103e-14 /4.7162940e-15 |
| P divided by sum of initial momentum norms | 1.0580828e-15 |
| Point-spin norms /raw q norm | 9.2724870e-16 /2.7755576e-15 |
| Независимый RK45 agreement | 1.9092490e-11 |
| Чувствительность двух RK45 | 2.0726558e-10 |
| Новый file restart, весь путь | 8.8024848e-14 |
| Conditional lunar SI velocity/rate export residual | 6.9175742e-15 /4.9724222e-18 |

Production 12.34 s, prefix+save/load+suffix 11.53 s. Все checkpoints и
новый массив находятся локально в `.tools/rotation59`; SHA указаны в аудите.
8 новых тестов прошли за 1.68 s. Относящийся набор checkpoint/initial,
моделей 55–57, Newton-rotation, relativity и error-control: **143 passed
за 17.73 s**. Неуспешных запусков в 59 не было; неверные документы, SHA,
недопустимые времена/источники и схемы проверены отрицательными тестами.

## Ограничения и следующий шаг

Полный runtime/Rust набор не повторялся; рабочий код и данные не изменены.
Schema исследовательское: CLI/GUI/portable его не читают. Checkpoints,
ссылающиеся на `.tools` архив, потребуют наличия этого локального источника
для воспроизведения; переносимая поставка этим аудитом не проверяется.

Физический перенос DE441 в selected canonical tetrad/SSC/figure/time ещё
открыт. Успешный JSON restart не доказывает эквивалентность базисов и не
объясняет годовой остаток ориентации 121.84″. Следом отдельный договор
условной/физической начальной Луны и новый независимый N-body прогон;
реальное включение и приливы только после относящихся проверок.
Кольцо 420/528 и проблемы KBO/MPC остаются прежними.

## Проверенные ссылки

- [Metadata contract](C:/Users/Admin/Desktop/Solar-simulator/scripts/canonical_checkpoint.py:58),
  [неизменяемый checkpoint](C:/Users/Admin/Desktop/Solar-simulator/scripts/canonical_checkpoint.py:115),
  [запись документа](C:/Users/Admin/Desktop/Solar-simulator/scripts/canonical_checkpoint.py:151),
  [чтение](C:/Users/Admin/Desktop/Solar-simulator/scripts/canonical_checkpoint.py:163).
- [Strict JSON](C:/Users/Admin/Desktop/Solar-simulator/scripts/canonical_checkpoint.py:188),
  [файл save](C:/Users/Admin/Desktop/Solar-simulator/scripts/canonical_checkpoint.py:204),
  [velocity-export](C:/Users/Admin/Desktop/Solar-simulator/scripts/canonical_checkpoint.py:214).
- [Worst-block integrator](C:/Users/Admin/Desktop/Solar-simulator/scripts/canonical_checkpoint.py:229),
  [source verification](C:/Users/Admin/Desktop/Solar-simulator/scripts/canonical_checkpoint.py:239),
  [продолжение](C:/Users/Admin/Desktop/Solar-simulator/scripts/canonical_checkpoint.py:254),
  [аудит](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_canonical_checkpoint.py:27).
- [Bitwise/raw q/metadata](C:/Users/Admin/Desktop/Solar-simulator/tests/test_canonical_checkpoint.py:44),
  [legacy rejection](C:/Users/Admin/Desktop/Solar-simulator/tests/test_canonical_checkpoint.py:59),
  [повреждение и договор](C:/Users/Admin/Desktop/Solar-simulator/tests/test_canonical_checkpoint.py:69),
  [NaN/duplicate keys](C:/Users/Admin/Desktop/Solar-simulator/tests/test_canonical_checkpoint.py:96).
- [SI export](C:/Users/Admin/Desktop/Solar-simulator/tests/test_canonical_checkpoint.py:105),
  [file restart](C:/Users/Admin/Desktop/Solar-simulator/tests/test_canonical_checkpoint.py:122),
  [неразбавляемый контроль](C:/Users/Admin/Desktop/Solar-simulator/tests/test_canonical_checkpoint.py:138),
  [source/frame verification](C:/Users/Admin/Desktop/Solar-simulator/tests/test_canonical_checkpoint.py:155).

Сохранность: [rotation59-provenance.json](rotation59-provenance.json).

Продолжение60: [conditional Sun/Earth/Moon 32-day audit](lunar-canonical.md)
проверил новый checkpoint/restart уже на лунных масштабах. Полной physical
миграции исходного DE441 по-прежнему нет; исходный аудит59 сохранён.

Продолжение61: [10body canonical audit](canonical-solar.md) дополнительно
проверил bitwise initial и file restart на исходной системе10тел;
physical initial projection и рабочее включение остаются отдельными.
