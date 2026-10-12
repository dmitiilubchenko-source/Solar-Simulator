# Сохранение относительного канонического состояния

Изменение 63, 11 октября 2026 года. Исследовательский формат для
[проверенной Jacobi-пары](relative-canonical.md), конечный H57 неизменен.
Рабочие Experiment schema9/10 и Cartesian research checkpoint59 сохраняют
прежнее значение. Полного физического переноса Луны, runtime PN-режима
и приливов этот формат не добавляет.

## Формат и совместимость

JSON kind `solar-simulator-research-relative-canonical-checkpoint`, schema1,
model `finite-adm-1pn-lo-so-newton-one-rigid-q2-v1`. Representation обязательно
равно `mass-weighted-pair-Jacobi-X-r-P-pr-spatial-S-quaternion` с двумя
явными фиксированными pair_indices. Ordered body_names уникальны, N совпадает
с массами и размером всех блоков. Initial и current записаны отдельно.

- `coordinate_slots`: у первого индекса X, у второго r; у остальных x.
- `momentum_slots`: у первого P, у второго pr; у остальных p.
- `spatial_spins`: исходный пространственный S каждого тела, включая фигуру.
- `quaternion`: сырой q в порядке wxyz; его норму/знак не исправляют.
- Параметры: массы, c, figure_index, I и bounding_radius.
- Elapsed model time, fixed frame/basis/epoch, SI similarity scales,
  solver method/rtol/component atol/max_step, происхождение и source SHA.

Все ключи проверяются точно, неизвестные/пропущенные поля, строки и bool
в числовых полях, NaN/Infinity и повторные JSON keys отвергаются.
При t=0 initial/current должны совпадать **побитово**, включая signed zero.
Начальная норма q допускает отклонение до1e-12, текущая до1e-9.
Raw-state/metadata после загрузки неизменяемы; metadata accessor выдаёт копию.

Модельные геометрические ограничения проверяются через локальную геометрию
пары. Они не требуют обратного абсолютного экспорта, который способен
потерять r при большом X. Модельный стресс X=2^54 проходит file round-trip
с сохранением прямого r; это проверка чисел, не физическая сертификация такого
глобального состояния. Начальные уже потерянные биты не восстанавливаются.

Loader явно отвергает Cartesian59, velocity Experiment9/10 и velocity export.
Cartesian loader59 также отвергает новую schema. Явная factory-конверсия
принимает только проверенный typed CanonicalCheckpoint, пару, ordered names
и **отдельно заданные новые integration controls**. Автоматического переноса
старых atol для body-p в новые P/pr нет: их массы и масштабы различаются.
Физический SSC/tetrad/I/time перенос не выводится из преобразования координат.

Payload SHA256 покрывает scientific fields и обнаруживает повреждение.
Это контроль целостности, не подпись доверенного автора: пересчитанный SHA
сам по себе не доказывает происхождение произвольно изменённых параметров.
Новые файлы создаются исключительно через mode'x', существующие не затираются.

## Продолжение и экспорт

Перед и после evolve проверяются все declared sources в текущем дереве.
Обязательные model/solver/coordinate/checkpoint core SHA должны совпадать
с версиями, загруженными исполняющим процессом. Outside-root/недоступные
источники отклоняются. Требуется строго возрастающая конечная time-grid,
начинающаяся ровно с сохранённого времени. Saved solver controls используются
без reboost, смены pair/order/frame или нормирования S/q.

История адаптивных шагов DOP853 не сохраняется. Побитовая загрузка состояния
не обещает побитовую дальнейшую траекторию относительно непрерывного запуска;
это проверяется отдельно заданным numerical restart criterion.
Исследовательские файлы с локальными .tools source refs продолжаются только
при наличии этих закреплённых источников. Portable/рабочая загрузка ещё не добавлены.

Диагностический velocity export возвращает `dx_canonical/dt`, прямой
`rdot`, spatial attitude rate и SI значения при сохранённых similarity units.
Он использует производные полного H, не p/m или pr/mu. Это не harmonic
velocity и не импортируемая legacy schema. T0 остаётся единицей,
не TDB/TCB/proper-time преобразованием.

## Проверяемый протокол

[Протокол](../scripts/relative-canonical-checkpoint-policy.json) записан
до результатов: исходные10тел,32суток/129эпох,split64; fresh full run,
prefix→JSON→**новый Python process**→suffix. Production controls побитово
соответствуют опыту62. Критерии H/P/J/q, отдельные absolute тела/r,
S/rawR как62; restart каждого тела/r <1m, S/rawR <1e-8.
Файлы должны сохранять initial/current bitwise, pair/order/frame/metadata
и SHA; suffix начинается побитово с prefix endpoint. Full production
должен побитово воспроизвести архив62 при неизменных controls/RHS.

Tighter и **оба** independent matrix/body-Euler RK4562 переиспользуются
только после проверки immutable report SHA, all source/array SHA,
input original/relative initial, SI units, pair/параметров через неизменный
родительский checkpoint, raw representation, finite shapes и time grid.
Новый checkpoint ничего не меняет в H/RHS эталонов. Их неопределённость
остаётся показанной отдельно. Будущие JPL/SB441 не вызываются; fit нет.

## Код и тесты

- [Immutable relative state/validation](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical_checkpoint.py:33),
  [JSON](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical_checkpoint.py:77),
  [strict parsing](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical_checkpoint.py:92),
  [save/load](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical_checkpoint.py:120).
- [Explicit conversion](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical_checkpoint.py:130),
  [source checks](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical_checkpoint.py:156),
  [evolve](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical_checkpoint.py:163),
  [velocity export](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical_checkpoint.py:188).
- [Fresh-process continuation](C:/Users/Admin/Desktop/Solar-simulator/scripts/resume_relative_canonical.py:14),
  [reference reuse guards](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_relative_canonical_checkpoint.py:23),
  [initial/controls binding](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_relative_canonical_checkpoint.py:49),
  [audit](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_relative_canonical_checkpoint.py:78).
- [Bitwise round-trip](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_checkpoint.py:50),
  [schema compatibility rejection](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_checkpoint.py:62),
  [payload/contract guards](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_checkpoint.py:71),
  [sub-ulp geometry](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_checkpoint.py:88).
- [Nonfinite/signed-zero](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_checkpoint.py:98),
  [independent/SI velocity export](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_checkpoint.py:108),
  [actual process restart](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_checkpoint.py:123),
  [sources/frame/grid](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_checkpoint.py:141).
- [Parent controls/ref scope](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_checkpoint_audit.py:15),
  [changed source/state/claim rejection](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_checkpoint_audit.py:28).

Первые8тестов прошли за3.15s. Первый общий новый прогон дал9passed/1failed
за4.15s: assert.array_equal для atol использовал другой порядок операций
mass*(SIatol/unit) вместо закреплённого62 mass*SIatol/unit и получил1ulp.
Отказ, исходники и SHA сохранены `.tools/rotation63/test-failure`.
Исправлена ожидаемая последовательность операций **в тесте**, scientific
controls и все критерии/битовая проверка parent production неизменны.
Повтор:10новых тестов прошли за3.40s.

## Результаты

[Неизменяемый аудит](relative-canonical-checkpoint-validation.json):
passed=true, failed_criteria=[], все9обязательных подтверждений true.
Fresh full production побитово совпал с опытом62, initial/current file
round-trip и первый suffix sample также bitwise. Все point-spin ровно0.
Сохранены исходный initial, pair/order, metadata, источники и fixed frame.

| Измерение | Максимум |
|---|---:|
| H /scaled P /J drift | 2.0518968e-15 /2.1154245e-16 /6.1344899e-16 |
| Сырая норма q | 4.4408921e-16 |
| Reference orthogonality /det | 2.1715204e-12 /1.5338841e-12 |

| Сравнение | Все позиции, m | Earth–Moon, m | Figure S relative | Raw matrix difference |
|---|---:|---:|---:|---:|
| Production /strict independent62 | 0.010791107 | 0.000251779 | 1.4136502e-15 | 1.0734562e-13 |
| Два independent levels62 | 0.009581364 | 0.002089857 | 4.5831167e-15 | 1.0105192e-12 |
| Production /tighter62 | 0.002191343 | 0.000087946 | 8.2403692e-16 | 3.6178763e-15 |
| File restart в новом процессе | 0.000093953 | 0.000021905 | 1.8385393e-17 | 9.8119892e-16 |

Restart21.9micrometre по внутреннему r — численное согласие двух способов
запуска той же модели на заданной сетке. Оно не является физической точностью:
reference agreement0.252mm, sensitivity2.090mm; strict global-error bound
не установлен. Raw matrix differences включают неортогональность.
Побитовая отдельная проверка initial body-Euler обоих архивов62 сохранена
локально в `.tools/rotation63/extra-checks.json`, вместе с SHA suffix-grid.

Новые jobs: production37.89s, prefix19.59s, fresh-process suffix19.92s.
Они выполнялись одновременно с полными tests; это времена этих запусков,
не изолированный performance benchmark. Full/prefix-final/resumed JSON и
новые NPZ закреплены SHA в отчёте; модельные source bytes не редактировались.
Scientific criteria не менялись. Неудачных integration запусков не было;
отказ test-float64 выше сохранён отдельно.

Полная проверка `scripts/check_project.py`: **835 Python tests passed**
за250.13s, **17 Rust tests passed**, fmt solar_core/solar_native прошёл,
ссылки937валидны на момент прогона. После закрытия документации ссылки
проверяются отдельно; старый full738/17 относится к53 и не заменяет этот прогон.

## Ограничения

Условный физический initial projection и неполная PN-фигура остаются
открытыми: SSC/tetrad/PN-Q2/инерция/время, core/deformation/tides отсутствуют.
Численное agreement не является истинной точностью. Этот10body договор
не сертифицирует астероиды/KBO/экспериментальное кольцо420/528 и не объясняет
прежние Moon121.84″/год или KBO/SB441 residuals. Рабочее приложение не менялось.

Сохранность: [rotation63-provenance.json](rotation63-provenance.json).
