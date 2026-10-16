# Измеренная оптимизация отрисовки135–137

14октября2026. [Критерии до измерений](runtime-performance-protocol.md),
[rawsamples, исходники и версии](runtime-performance-validation.json).
10тел, исходный EIH1PN+fixedSun/EarthJ2 профиль, те же dt3600с/packet20/
rtol1e-13/x1e-3м/v1e-9м/с, EclipticJ2000/SSB/TDB/SI. Физика не изменена.

## Что ограничивало скорость

60пакетов за50суток из одинакового старта, прогрев и3повтора:

|Режим|Python, медиана с|Rust, медиана с|
|---|---:|---:|
|Толькоинтегрирование|1.52968|0.91129|
|С report каждого пакета|1.59711|0.97036|
|Одиндлинныйинтервал вместо60|0.24303|0.13908|

Добавлениедиагностики не меняетcheckpoint. Report~0.95мс; одинпакетфизики
~15.2мсRust. 60solve_ivp/6624RHS Python и6600Rust. Одиндлинныйинтервал
даёт другиеокругления: maxpositiondiff0.01016/0.01856м. Это иное разбиение,
а не оптимизация того же пользовательского режима; ожиданиепаузы растёт.
Принятые/отклонённые внутренниешаги не подсчитаны отдельныминтерфейсом.
ОтдельныйcProfileRust показал~0.84с figureacceleration из1.39с всегоjob;
профилировочные времена не смешиваются с обычнымиwalltime.

Отрисовка стоила90–113мс накадр и доминировала вданномGUIпрофиле. Каждый
кадр повторноочищал обеоси, создавалcollections/scatter/energyline/legend.
Теперь обновляются данные существующихartists; легенда меняется при
смене состава/вида/цветов. Данные/допуски/история1500снимков сохранены.

## До и после на одинаковых данных

ОтдельныеTkпроцессы, окно1180×820/canvas1180×533, прогрев+5повторов,
синхронныйполныйcanvas.draw. CPU/wallcost безworkeroverlap/периодического
polling/ожиданияUI.1500кадров —25повторов60физическихснимков для stress,
не новая1500пакетнаятраектория. Синтетическое повторение одинаково до/после.

|История/вид|Построение до→после, мс|Полныйкадр до→после, мс|Ускорение|
|---|---:|---:|---:|
|60/all10|13.382→3.110|109.387→84.618|1.293×|
|60/Земля–Луна|10.784→2.629|90.363→64.130|1.409×|
|1500/all10|16.342→7.008|111.640→86.281|1.294×|
|1500/Земля–Луна|12.255→3.814|100.549→71.035|1.415×|

Главныйкритерий≥15%прошёл:all1500 уменьшениестоимости22.72%.
PNG всехчетырёхсценариев совпалипобитно, пределыосейidentical, эксперимент
не изменён. Tracemallocpeakall1500:1954439→1186152байт; измерениепамяти
отдельно оттайминга, nativeMatplotlib/Tkallocations учитываются не полностью.
Artistcountbounded:2orbitcollections и1energyline; данные не прореживаются.

Первыеemptyhistoryтестыотказали: reuseавтомасштаб отличается отAxes.clear.
ИсследованиеinstalledMatplotlib выявило сохранение старогоdataLim играниц
энергетическойоси при пустыхданных. Сохранена прежняясемантика, критерии
не изменены. Сохранены обе неудачныепроверки ипервыеperformance receipts.
ПроекцииXY/XZ/YZ,hiddenreference,merge/shrinking/emptyhistory,1500кадров,
354синтетическихтела,boundedartists,science labels/reset/physicschange
проверены. Это не квалификацияфизики354тел, а проверкасохранностиграфика.

## Повторение и ограничения

`python -X utf8 -B -m scripts.profile_runtime physics --output fresh/physics.json`
считаетизодинаковогостарта. Renderиспользует полученныйrender-input135.json:
`python -X utf8 -B -m scripts.profile_runtime render --inputs fresh/render-input135.json --output fresh/render.json`.
Каталогfresh нужносоздать заранее. Output не перезаписывается; sourcebefore
и изображения сохранены локально.tools/performance135. Они не требуются
дляобычногоGUI, publicJSON содержитrawtimings/входнойSHA/версии/codeSHA.

Результаты на текущемWindows/CPython3.14t/SciPy1.18.1/Matplotlib3.11.0,
одном10bodyпрофиле/viewport. Нет гарантииFPS/скорости всехмашин/30–528тел.
Расчётфизики,допуски,данные иyearJPLпоказатели остались прежними;
численная ифизическаяточность не улучшались этимrendererизменением.
Свежаясборка/общаярегрессия фиксируются после фактическихпроверок.

Общаяпроверка:1364Python за175.18с/17Rust/fmtboth прошли,5новыхcases
поверх1359. СвежийZIP105729848байт:
[SolarSimulator-0.2.0-20261014-214443.zip](C:/Users/Admin/Desktop/Solar-simulator/dist/SolarSimulator-0.2.0-20261014-214443.zip),
[SHA256](C:/Users/Admin/Desktop/Solar-simulator/dist/SolarSimulator-0.2.0-20261014-214443.zip.sha256)
`45ca585ec5a900296d08c0c6f33962667f68df920629f3556ac5d52356462378`.
CRC/340relativeMarkdownlinks/runtimebytes/privateexclusionpassed.
Isolatedrelocation вновыйпуть с пробелами: всеoldnative/science/Tkjourneys,
Moon/solar/target/checkpoint/parent/add/remove/CSV прошли сновымrenderer.
ПредыдущийZIP134 сохранён иSHAпроверен, GitHub/commit/push не выполнялись.

[Переиспользованиеartists](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/plot_artists.py:20),
[стенд](C:/Users/Admin/Desktop/Solar-simulator/scripts/profile_runtime.py:90),
[проверки](C:/Users/Admin/Desktop/Solar-simulator/tests/test_plot_artists.py:17).
