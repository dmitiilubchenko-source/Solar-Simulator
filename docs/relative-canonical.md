# Относительная каноническая пара Земли и Луны

Изменение 62, 11 октября 2026 года. Исследовательское представление прежнего
[конечного H57](rigid-pn.md) и [условного initial десяти тел](canonical-solar.md).
Одна rigid-фигура Moon, остальные девять point-spin равны нулю. Рабочее
приложение, данные, физический перенос Луны и приливы здесь не изменяются.

## Уравнения и физический договор

Для масс ma, mb, M=ma+mb, fa=ma/M, fb=mb/M задаём

```
X = xa + fb*(xb-xa),       r = xb-xa
P = pa+pb,                pr = fa*pb-fb*pa
xa = X-fb*r,              xb = X+fa*r
pa = fa*P-pr,             pb = fb*P+pr
```

Остальные x/p, все пространственные S и q не меняются. Из подстановки
получаем тождество канонической одноформы
`pa·dxa+pb·dxb = P·dX+pr·dr`. Поэтому преобразование каноническое
и для выбранного PN-гамильтониана с его каноническими импульсами.
`X` — массовое среднее **координат**, не релятивистский центр энергии.
Формула `pr=mu*rdot` относится к ньютоновскому кинетическому пределу;
в этом PN-стенде скорости вычисляются через производные полного H.
Нельзя преобразовывать p той же матрицей, что x или v.

[Rein и Tamayo, 2015, WHFast, §2.1](https://arxiv.org/pdf/1506.01084)
описывают линейные Jacobi-координаты и различие преобразования импульсов.
Публикация найдена и карточка получена через Consensus; формулы сверены
с первичным PDF. Здесь используется только одна фиксированная пара,
а не полная иерархия планет и не Wisdom–Holman splitting. Интегратор
остаётся адаптивным DOP853; каноничность координат не делает его симплектическим.
HTML-адрес статьи вернул 404; первичный PDF доступен.

H зависит от разностей положений. Для вычисления поля переводим лишь
временные геометрические аргументы к первому телу пары:
`xa_local=0, xb_local=r, xj_local=(xj-X)+fb*r`.
Импульсы, S, ориентация, время и внешний инерциальный frame не получают
boost или перенастройку. Обратное преобразование абсолютных положений
используется только как диагностический экспорт: при большом X оно может
потерять малое r. Внутренний вектор эволюционирует самостоятельно.
Общий J пары равен `X×P+r×pr+Sa+Sb`; общий P учитывает P пары один раз.

G=1, масштабы SI, epoch JD2461321.5 TDB-as-input-coordinate-time,
Ecliptic J2000/SSB и conditional ADM/spatial-Euclidean договор сохранены
из 58–61. Перевод единиц не является TDB/TCB или proper-time преобразованием.
Полного SSC/tetrad/PN-Q2/I/time переноса DE441 по-прежнему нет.

## Протокол и реализация

[Протокол](../scripts/relative-canonical-policy.json) записан до результатов:
32 суток, 129 эпох, production worst-block DOP853 rtol1e-11,
atol для X/r 1e-4 m, для P/pr эквивалент 1e-10 m/s с **общей/приведённой**
массами соответственно. S/q допуски исходного опыта61; max_step21600 s.
Tighter rtol3e-13, atol×.03, max10800 s. Два новых независимых RK45
rtol3e-13/3e-14, atol=.01rtol×initial Jacobi block norm, raw R scale1,
нулевой point-spin имеет явный absolute atol1e-30 model units.

Независимый scalar H дифференцируется complex-step **непосредственно
по Jacobi-переменным**; геометрия привязана ко второму телу пары.
Фигура представлена сырым R и body-spin, её Euler torque выведен через
стандартную инерцию. Production использует raw q и пространственный S.
Ни q, ни R, ни S после шагов не нормируются. Новые source SHA фиксируются
до всех jobs и проверяются после. Будущие эфемериды не читаются, fit нет.

Каждая абсолютная позиция и отдельно сохранённый r должны согласоваться
до1m для независимого эталона, его чувствительности и tighter-прогона;
figure-S и raw matrix differences до1e-8. H/J/q drift до1e-9,
scaled P до1e-10; ортогональность/det R до1e-8; point-spin ровно0,
initial S/q bitwise и input/source SHA должны сохраняться.
Абсолютную ошибку пары вычисляем **из разности Jacobi-переменных**,
без вычитания двух экспортированных AU-положений.

Проверенные точки реализации:

- [Пара и массы](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical.py:15),
  [начальный перевод](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical.py:43),
  [геометрия/экспорт](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical.py:54),
  [RHS](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical.py:80),
  [H/P/J](C:/Users/Admin/Desktop/Solar-simulator/scripts/relative_canonical.py:92).
- [Независимая геометрия](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_relative_canonical.py:11),
  [полный scalar H](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_relative_canonical.py:24),
  [его производные](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_relative_canonical.py:29),
  [matrix/body Euler](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_relative_canonical.py:35).
- [Отдельное сравнение r](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_relative_canonical.py:21),
  [аудит](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_relative_canonical.py:43).

## Результаты

[Аудит](relative-canonical-validation.json): passed=true,
failed_criteria=[], все четыре обязательных подтверждения true.
32 суток/129 эпох, все девять point-spin точно0, initial S/q bitwise,
input и source SHA сохранены.

| Измерение | Максимум |
|---|---:|
| H /scaled P /J drift | 2.0518968e-15 /2.1154245e-16 /6.1344899e-16 |
| Сырая норма q | 4.4408921e-16 |
| Reference orthogonality /det | 2.1715204e-12 /1.5338841e-12 |

| Сравнение | Все позиции, m | Earth–Moon, m | Figure S relative | Raw matrix difference |
|---|---:|---:|---:|---:|
| Production /strict independent | 0.010791107 | 0.000251779 | 1.4136502e-15 | 1.0734562e-13 |
| Два independent levels | 0.009581364 | 0.002089857 | 4.5844308e-15 | 1.0105192e-12 |
| Production /tighter | 0.002191343 | 0.000087946 | 8.2403692e-16 | 3.6178763e-15 |

Согласие Earth–Moon0.252mm меньше чувствительности эталона2.090mm;
оно не означает субмиллиметровую истинную точность. Production sensitivity
0.088mm также не является строгой global-error границей. Сырая matrix
разность включает её неортогональность, а не только физический угол.

По сравнению с опытом61 относительная sensitivity уменьшилась с1.852mm
до0.088mm; при этом согласие всех абсолютных позиций изменилось с8.509mm
до10.791mm. Это показывает пользу отдельного относительного контроля,
но не универсальное улучшение всех координат. Два опыта имеют разные
масштабы error-control/reference в преобразованных переменных.
Дополнительная **описательная**, не приёмочная сверка с проверенным SHA
production61: максимум различия внутреннего вектора0.488129mm,
локальный протокол `.tools/rotation62/cartesian-comparison.json`.

Production35.42s, tighter60.47s, independent75.13/111.67s.
Четыре новые NPZ содержат исходное представление и имеют SHA в отчёте.
Отказов вычислительных запусков в62 не было; отрицательные входы,
ошибочное преобразование p и потеря абсолютной геометрии проверены тестами.

## Проверки и ограничения

8 новых тестов прошли за1.19s, 157 относящихся — за23.42s:

- [Каноническая двухформа и одноформа](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical.py:21),
  [round-trip и H/P/J](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical.py:35).
- [Независимые full-H/body-Euler производные на24 состояниях](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical.py:45),
  [потеря геометрии при большом начале](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical.py:64).
- [Ошибочное преобразование импульса обнаруживается](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical.py:76),
  [явные отклонения входов](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical.py:83).
- [Прямое измерение малой относительной ошибки](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_audit.py:10),
  [отклонение некорректных сравнений](C:/Users/Admin/Desktop/Solar-simulator/tests/test_relative_canonical_audit.py:21).

Первый прогон тестов прошёл, пороги не корректировались после результатов.
Полный check_project/Rust/portable не запускался: runtime и Rust не менялись.

Геометрический стресс-тест с X=2^54 модельных единиц воспроизводит
слияние координат двух разных тел при абсолютном float64-экспорте;
относительная геометрия сохраняет расстояние и RHS. Это намеренная
численная модельная задача, не допустимое физическое состояние системы
в глобальном PN-базисе. Уже потерянные при начальном вычитании xb-xa
биты преобразование не восстанавливает. Оно не устраняет roundoff для
произвольной другой тесной пары или общий float64 предел.

В этом этапе нет нового постоянного checkpoint формата Jacobi.
Локальные NPZ — научные архивы с явным названием представления и SHA,
а не загрузочные сохранения приложения. Cartesian checkpoint59 нельзя
считать Jacobi checkpoint: одинаковая длина массива не означает одинаковую
семантику. Строгий формат, file round-trip/restart — следующий отдельный шаг.

Эта проверка численной реализации не объясняет старые121.84″/год Moon
или KBO/SB441 остатки. Она не сертифицирует астероиды, кольцо420/528,
полную PN-фигуру или физическую точность условных стартов.

Сохранность: [rotation62-provenance.json](rotation62-provenance.json).

Последующее63: [строгий Jacobi checkpoint](relative-canonical-checkpoint.md)
с bitwise raw-state сохранением и32-суточным file restart в новом процессе.
Прежний аудит62 и все его научные JSON/источники сохранены.
