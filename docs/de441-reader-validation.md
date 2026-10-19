# Автономный DE441: проверенное чтение годового эталона

2026-10-16T22:08:23+03:00,236–242. [Протокол до измерений](de441-reader-protocol.md),
[полные результаты](de441-reader-validation.json), [исходные данные](de441-reader-inputs.zip).
Сеть не использовалась; проверка работала с запрещёнными socket-соединениями.

Читатель из115полных DE441записей возвращает предписанные позиции,
скорости и аналитические вторые производные. Это отдельный researchtool,
не сила симулятора и не подстановка будущего движения в runtime.
Начальные условия, строгий профиль, Rust, интегратор и траектории215 прежние.

## Что сравнивали

Все440номинальных20hвыходов года,10тел,SI/SSB/EclipticJ2000,
JD2461321.5TDB. Сохранённый Horizons DE441 архив229–233 заново проверен
поSHA/ID/рамке/Origin/временам/сыромуparser. Ни одной новой сетевой загрузки.

| Тело | Максимум позиции, м | Максимум скорости, м/с |
|---|---:|---:|
| Sun | 2.74466941e-07 | 7.16416517e-15 |
| Mercury | 2.29328435e-05 | 3.82211023e-11 |
| Venus | 0.000106820038 | 2.93374276e-11 |
| Earth | 0.000124843407 | 1.9590199e-11 |
| Moon | 0.000122855916 | 1.96260959e-11 |
| Mars | 0.000129647104 | 1.16187991e-11 |
| Jupiter | 0.000224200698 | 9.44781399e-12 |
| Saturn | 0.00122129903 | 7.91081727e-12 |
| Uranus | 0.00197304338 | 3.05067037e-12 |
| Neptune | 0.00195556726 | 2.79358079e-12 |

Прямая Moon−Earth: максимум0.000149657671м,
скорость1.45449816e-11м/с. Все тела
прошли заранее заданные .01м/1e-8м/с, пара .001м/1e-8м/с.
**Это точность чтения тех же данных, не истинная астрономическая точность**.
Максимумы симуляции≈772м/relative726м из229–233 остаются прежними.

## Уравнения чтения и независимые проверки

Первичные источники сохранены235: официальный ASCIIformat и header,
руководствоHorizons (поворотε=84381.448arcsec), Park2021.
GROUP1050задаёт 1-based индексы, количество коэффициентов/подинтервалов.
Полиномы вkm/ICRF, времяTDB; скорость/ускорение получены аналитически,
с2/span_seconds и его квадратом. Затем Rx(−ε),km→SI.
Earth=EMB−Moon_geo/(1+EMRAT),Moon=Earth+Moon_geo; relative читается
напрямую. БольшаяfloatJD в основном вычислении не формируется.
Её диагностический roundtrip на сетке даётдо1.34110451e-05с;
векторы этим сдвигом не исправлялись. Строгий gate прошёл без использования
поблажки100мкс/10м/.2м из прежней методики представления времени.

19начальных тестов: известный кубический полином/две производные,
секундные множители, EMB, оси, границы и неподдерживаемые данные.
На10предобъявленных эпохах отдельная Decimalrecurrence T_n/T'_n/T''_n:
70→90 разность≤1.66334402e-65scaled (gate1e-50).
Doublevs90digits max[position,velocity,acceleration]SI:
[0.001150428469887533, 1.1615307177336193e-11, 7.13903404448233e-18]; для relative[6.24111409001907e-08, 1.7625060225453932e-13, 4.960607595328785e-19].
Это контроль арифметики на тех жеfloatкоэффициентах, не их физической ошибки.
ПоследниеFDh10с относительные ошибки dp/dt,dv/dt≤[7.618489586083679e-09, 1.3536547965166135e-08];
всеh1000/100/10с сохранены. Все9допустимых эпох прошли gates1e-6/1e-5.

Все2749стыков записей/подинтервалов115records/11позиционныхколонок:
максимумы[0.002861653462735554, 4.282472153683004e-11, 2.0448551536048442e-11]SI для0/1/2производных;
прошли .01м/1e-7м/с/1e-9м/с². Даже малый скачок второй производной
нельзя автоматически считать истинной ошибкой силы — см.[бюджет](solar-defect-validation.md).
Неверный поворот/его знак/Earth=EMB/EMRAT81.3/скоростьвсутках обнаружены;
минимальный позиционный контрольокругленияEMRAT≈31.76м. Критерии не менялись.

При self-review дополнен gateполноты:10тел,10Decimalэпох,2749границ,9FDэпох;
пустой/неполный отчёт не проходит по all([]). Ранние audit/source сохранены,
повторная проверка дала в точности те же научные числа, не меняя читатель.
Строгих научных FAILED в этом блоке нет; старые FAILED не переоценены.

## Воспроизведение и стоимость

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_de441_reader --output .tools/my-reader.json
```

Только публичные файлы; выходновый, старая.tools/резерв235не нужны.
Архив5files/1303565байт,
SHA`eaf32db3d18daffc1ec7fd0193c8811b05e2cc2013f34918aca541cbb6e9ee06`. Загрузка0.121737с;
440states+relative1.211957с;
полныйreaderаудит4.898845с. Одиночные замеры/CPUнефиксирован.
Freshpubliccopyс пробелами/запрещённойсетью/безстарой.tools воспроизвела все
числаreaderиmodelbudget exact; process10.855021с.
Budgetчасть использовала ту же уже собранную native.pyd, не новую сборку.

Полный241:1801Python/17Rust/обаfmt/ссылки passed,505.892837с.
38новых случая этого блока+16prefetch после предыдущегоfull2321747.
Все809публичных файлов во время проверки были неизменны.

Данные покрывают10лет, проверка againstJPL — только440эпох одного года.
Границы/формат115records не дают квалификации точности симулятора на10лет,
между эпохами, на новыхтелах/IC или для наблюдений. Runtimedefaultне менялся.

- [ecliptic_matrix](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_reader.py:23)
- [polynomial](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_reader.py:28)
- [Reader.__init__](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_reader.py:42)
- [Reader.locate](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_reader.py:83)
- [Reader.coefficients](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_reader.py:97)
- [Reader.component](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_reader.py:107)
- [Reader.vectors](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_reader.py:112)
- [Reader.states](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_reader.py:119)
- [Reader.relative](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_reader.py:122)
- [load_archive](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_reader.py:127)
- [dec](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_decimal.py:9)
- [recurrence](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_decimal.py:13)
- [snapshot](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_decimal.py:31)
- [difference](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_decimal.py:64)
- [agreement](C:/Users/Admin/Desktop/Solar-simulator/scripts/de441_decimal.py:72)
- [errors](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_reader.py:21)
- [jpl_metrics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_reader.py:26)
- [boundaries](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_reader.py:41)
- [decimal_check](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_reader.py:65)
- [finite_differences](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_reader.py:83)
- [negative_controls](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_reader.py:108)
- [qualification](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_reader.py:131)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_reader.py:142)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_de441_reader.py:196)
