# Рабочий профиль Solar: что именно проверено

Паспорт составляется по завершённым измерениям; это не обещание точности
произвольной пользовательской системы. Текущий блок начат 16 октября 2026.

## Модель и начальные данные

Десять взаимно взаимодействующих тел: Солнце, восемь планет и Луна.
Трёхмерные координаты и скорости в SI; исходный центр SSB,
оси Ecliptic J2000, эпоха JD 2461321.5 TDB, источник DE441.
Внешние планеты представлены барицентрами систем: массы спутников уже
включены. [Начальный strict JSON](solar-sandbox-strict-checkpoint.json).

Точечная ньютоновская гравитация и полная EIH-поправка порядка 1PN,
аддитивные J2 Солнца и Земли с обратными силами. Оси фигур заданы
постоянно. Динамическое вращение, приливы и PN×J2 силы в этом профиле
не интегрируются. Его нельзя называть полной ОТО или полной физикой Солнечной системы.

Интегратор — SciPy DOP853. Rust вычисляет native-силы; управление состоянием
и интегрирование пока используют Python/SciPy. Strict:
rtol=3e-14, position_atol=1e-3 м, velocity_atol=1e-9 м/с,
контроль по телам и относительной паре Earth–Moon, dt=3600 с.
Standard `solar_sandbox` имеет rtol=1e-13 и является другим профилем.
dt и размер пакета задают выдачу/границы расчёта, а внутренний шаг адаптивный.
Режим legacy перезапускает контроллер на пакетах; continuous сохраняет его.

## Измерения, которые нельзя смешивать

| Область | Результат | Что он означает |
|---|---|---|
| Исходный strict, год, 125 эпох и 499 границ пакетов, continuous DOP853 | Все тела ≤0.069474 м; Moon−Earth ≤0.040074 м | Согласие с независимым RK45 той же модели |
| Тот же исходный continuous DOP853, 125 эпох DE441 | Moon−Earth ≤718.841 м | Остаток относительно JPL, без подгонки |
| Три edited-старта, год, две сетки через 6 ч, три режима | 18/18 прошли; все тела ≤0.675141 м; Moon−Earth ≤0.081150 м | Численная проверка конкретных изменённых систем |
| Настоящие пакеты 20 ч, те же edited-старты | 9/9 прошли; все тела ≤0.270396 м, Moon−Earth ≤0.0887936 м | Отдельная численная проверка всех 440 эпох |

Источники: [исходный годовой профиль](fixed-j2-year-validation.md),
[плотные данные JPL](dense-jpl-validation.md),
[год edited-систем и реальные CLI6](edited-solar-year-validation.md),
[заранее заданный протокол пакетов 20 ч](edited-solar-packet20-protocol.md).
Меньшие допуски не устраняют автоматически остаток около 719 м относительно JPL.
Изменённые начальные условия с реальными эфемеридами не сравниваются.

Независимый RK45 использует AU/year и EMB+Moon−Earth, отдельные реализации
EIH/J2 и контроль уточнения. Последняя разность уточнений — чувствительность,
не строгая оценка ошибки. Сетка снимков не гарантирует точность между ними.

## Запуск и границы применимости

Для исходного опыта выбрать Strict в исходном GUI, `--profile strict` в CLI
или загрузить strict JSON. [Выбор и область проверки](profile-selection.md).
Сначала сохранять исходник;
изменения массы/положения/скорости на паузе создают дочерний опыт со своим t=0,
прежними инерциальными осями и сохранённым родительским состоянием.
Origin=None у edited-опыта означает отсутствие реальной календарной эфемериды.
Это не признак потери единиц или автоматической научной квалификации.

Для повторения исследовательских чисел и создания конкретных входов CLI
следовать командам в связанных протоколах/отчётах. Готовый portable ZIP
этапа 155 прежний; новые исследовательские отчёты не означают новый релиз.

GUI по умолчанию использует batch=20: при strict dt=3600 с годовая цель
даёт пакеты до 20 ч. Continuous CLI по умолчанию также packet_steps=20.
Обычное воспроизведение GUI и расчёт до цели имеют разные конечные границы;
произвольный batch и standard-профиль требуют собственной проверки.
Загрузка continuous final.json создаёт новый контроллер, его скрытые буферы
в JSON не сохраняются. Пауза legacy между пакетами не создаёт этих буферов.

Нет годового интегрированного баланса Noether21 sources для десяти тел.
Обычная ньютоновская энергия не является достаточным инвариантом EIH+fixedJ2.
Few-body проверки не заменяют этот баланс. Кольцо Койпера экспериментальное:
420 тел не прошли геометрию; 528 прошли заданные проверки, но остатки KBO выросли.
В демонстрацию точности десяти тел оно не включено.


## Завершённая проверка реальных пакетов

2026-10-16T15:54:08+03:00: [отчёт 20 ч](edited-solar-packet20-validation.md).
GUI target strict Rust для трёх edited-стартов: **True**;
continuous CLI strict Rust: **True**. Все состояния GUI/CSV/final.json
побитно совпали с соответствующим режимом стенда. GUI окно скрыто, опрос ручной;
это не проверка отзывчивости видимого окна и не ordinary playback.
На момент отчёта210–213 исходный nominal strict на свободных20h ещё не был
квалифицирован: прежние125эпох задавали499границ. Его отдельная проверка
завершена215–217; результаты ниже, без переноса edited-квалификации.
Реестр источников и областей: [JSON паспорта](solar-working-profile.json).


## Исходный strict: настоящие пакеты 20 ч

16 октября2026: [отдельный протокол](nominal-solar-packet20-protocol.md),
[отчёт215–217](nominal-solar-packet20-validation.md)/JSON. Год,440эпох,
439пакетов (438×20h+6h), неизменные исходныеIC/Origin/Settings/массы.
Три режима прошли прежние10м/0.1м numerical gates:
Python all0.121451м/pair0.075261м; Rust0.136978м/0.075092м;
continuousRust0.067330м/0.038345м. Последнее уточнение reference:
all0.087893м/pair0.000340м — чувствительность, не error bound.
ActualCLI и GUItarget/batch20 по всем440состояниям побитно совпали
с corresponding continuous/legacyRust, календарная provenance сохранена.
JPL только24точно общие эпохи: Moon−Earth≤691.644676м, все тела≤747.775757м.
Прежний JPLмаксимум≈718.84м на125эпохах не отменён: различается покрытие,
по24точкам нельзя утверждать улучшение физики. Новых сил/подгонки нет.
Standard, ordinaryplayback, другиеbatch/IC/горизонты не квалифицированы.
Годовых Noether21sources десяти тел по-прежнему нет. Нового релиза нет.


## Короткий пилот балансов десяти тел

[Отчёт219–222](solar-noether-pilot-validation.md)/JSON: трое суток,
пять снимков, прежние исходные данные и силы. Траектории и исправленные
балансы трёх режимов прошли численные критерии. **Критерий различимости
источников не прошёл**: PN²/PN×Q и torque малы в глобальной нормировке.
Высокоточная диагностика тех же снимков подтвердила вклад округления
глобальных величин, но не переоценивает исходный FAILED и не улучшает
траекторию. Годовых Noether21 балансов по-прежнему нет. Новых сил нет.


## Мгновенные тождества и рабочие источники

[Отчёт223–228](noether-identities-validation.md)/JSON: все30снимков
прошли раздельные Newton/1PN/J2/PN²/PN×Q тождества, уточненияh и70/90цифр.
Намеренные ошибки реакций/staticU²/парныхPN/пропускаисточников обнаружены.
Источники рабочегоfloatкода согласованы с Decimal по каждому ненулевому
E/P/J блоку. Это проверка выражений, не новая точность орбит: прежний
globalvisibilityFAILED220 и отсутствие годовыхNoether21балансов сохраняются.
Полный набор227:1715Python/17Rust/fmt/links прошёл;24новыхслучая этого блока.
JPL24совпадающиеэпохи истарые125 — прежние отдельныепокрытия.


## JPL на всех440 выходах исходного strict-года

[Отчёт229–233](nominal-jpl440-validation.md)/JSON и отдельный архив
содержат все440выходов×10тел. Три режима прошли10км/1км также после
временных запасов10м/.2м. Moon−Earth max725.514939/725.509709/725.565822м;
все тела max772.162785м. До:24эпохи Moon−Earth≈691.645м;
старый125максимум≈718.84м сохранён. Рост — покрытие, динамика прежняя.
JDпечатьотличаетсядо28.8мкс; календарныеотметки совпали с целыми секундами,
но440эпох не объявлены математически точными совпадениями Horizons.
Без новых сил/IC/интегрирования. SHA/provenance/модель проверены;
полностью автономный повтор без сети/старой.tools воспроизвёл все числа.
Полный232:1747Python/17Rust/fmt/links passed,32новых случая.
Прежние ограничения Noether/standard/anyIC/между снимками сохраняются.


## Автономный эталон и локальный бюджет сил

[Читатель236–242](de441-reader-validation.md)/JSON воспроизвёл440годовых
JPLвекторов: bodymax1.973мм, directMoon−Earth0.150мм. Это чтениеэталона,
не точностьнашейсимуляции.10летdata≠10летквалификациисимулятора.
[Локальныйбюджет](solar-defect-validation.md)/JSON: существующий prescribed
MoonJ2/C22 на путиDE441 уменьшилrelativeRMSдефекта ускорения≈35.3раз,
ноэто не доказательство всейгодовойошибки≈726м и не консервативноевращение.
EIHvsNewton/Earthorientationvsstrict дали отдельныеухудшенияRMS, сохранены.
Остаточныйпик совпал с границейинтерполянтов:2ndderivativejumpсопоставим;
исходныймаксимумневыбрасывался. Runtime/IC/default/силы прежние.
Full2411801Python/17Rust/fmt/links passed;38new+16prefetchпослеfull232.
NoetherFAILED220/annualfalse/standardfalse/anyICfalseпрежние.


## Граница вращения и лунного поля243–247

[Независимый аудит](lunar-coupling-validation.md) проверил Newton Q2 силу,
реакцию, torque и локальный обмен энергией на440снимках. Из прежней I
получены J2/C22; различие nominal/solid Moon поля RMS2.5391e-14m/s²
на одинаковой заданной ориентации не сертифицирует свободный spin-прогноз.
H57/conditional начальная инверсия уже существуют; physical PN-I/SSC map
остаётся false. EIH+dynamic q/S runtime guard и все прежние ограничения
сохранены. Full246:1819Python/17Rust/fmt/links. Силы/IC/default прежние.


## Синтетическое согласование EIH и вращения248–253

[Отдельный стенд](hybrid-rotation-validation.md) проверил harmonic pointEIH
и Newton rotor на3телах/2периодах сискусственнымc=400. OR rawE≈4.05e-7
объясняетсяPN²/PN×Q источниками, corrected≈1.34e-14; выбранныйfinite-action
postulate сохраняетE/P/J безбюджетов. Это не полнаяPN-физика Луны и не
изменение рабочего профиля.8jobs/9Decimalснимков/6visibilityканаловpassed,
offline arrays exact;133related tests/20newpassed. Full2461819/17исторический.
Следом оценитьмасштабпропущенныхчленовнаrealSI, а не переноситьtoyсразу.
EIH+dynamicrotation guard/annualNoetherfalse/physicalmapfalse сохранены.


## Реальные SI-масштабы254–259

[Отдельный аудит](real-spin-scales-validation.md) проверил14 полей на440
снимках DE441; Decimal H1/scalar, SO derivatives/identities и10 FD наборов
прошли. PN×Q/ведущий SO дают условные mm–cm ballistic scales против
гораздо большего Newton Moon Q2; это не ошибки свободных орбит и не
доказанные годовые bounds. Harmonic и canonical группы не суммируются
в сертифицированный бюджет. Исходный float FAIL256 сохранён; компенсация
исправлена повышенной арифметикой диагностики, допуск5e-12 прежний.
164related/23new passed; offline19arrays exact. Full2461819/17 исторический.
Runtime/IC/силы/default/guard/annual Noether/physical mapping flags прежние.
Следующий260 — короткий свободный research Moon rotor с независимой
проверкой; обновление рабочего EIH+dynamic q/S ещё не разрешено моделью.


## Короткий свободный ротор260–265

[Research32day forecast](free-lunar-rotation-validation.md)/JSON:10тел,
129эпох, q/S толькоt0, дальнейшая ориентация свободная.5jobs с независимым
RK45/R/bodyEuler, source-aware Decimal E/P/J и refinement прошли критерии260.
Baseline/free/DE441 все остатки и ухудшения сохранены. Это не рабочая
квалификация EIH+q/S и не годовая точность.248related/13newtests passed;
offline10arrays exact. Full2461819/17 исторический. Runtime/IC/default/
Rust/guard/physicalmapfalse/annualNoetherfalse прежние. Следом96day research.


## 96day исследовательский ротор266–272

[Отчёт](free-lunar-months-validation.md)/JSON:385эпох/96day/5решений,
прежние силы и numerical gates260 прошли. Baseline pairmax182.36154м,
free tight0.356397547м;это sampledmodelresidual,неbound/не год.
263related/15newpassed;offlineполныйnominal96/2arrays ивесь5jobanalysis/31arrays exact,
не5повторныхintegrations. Рабочий runtime/IC/default/Rust/guard/physicalmapfalse
прежние;NoetherglobalvisibilityFAIL/annualfalseсохранены. Следующий273:Протокол годовой квалификации свободного ротора с оценкой стоимости и независимой численной погрешности.


## Годовой исследовательский ротор273–279

[Отчёт](free-lunar-year-validation.md)/JSON:1462эпохи/365.25суток/10тел,
5continuousjobs;прежние260gates numericalPASS=True.
Baseline pairmax725.579200998м→nominalfree
3.29017625342м/tight3.29164931652м.
287related/24newpassed;offlineполныйnominal-year2arrays и5jobanalysis31arrays exact.
Это sampledresearch,не runtimequalification/physicaluncertainty/continuousbound.
Runtime/IC/Rust/default/guard/physicalmap/sourcevisibilityflags прежние.
Следующий280:Диагностика причин годового модельного остатка и области применимости свободного ротора перед решением о runtime.


## Диагностика заданной ориентации280–286

[Отчёт](prescribed-lunar-validation.md)/JSON:год1462эпохи/4jobs,
DE441R(t)вMoonQforce — внешнее управление, **не свободный прогноз**.
Freepair3.29164931652м/control5.66374633858м;
switch2.54790737046м,resolved=True.
Externalwork/torque/FD/Noether/independentgates PASS=True.
310related/23newpassed;offline nominal-year2arrays/fullanalysis18arrays exact.
Working/free-year точность иruntimeguardsнепереквалифицированы.
Следующий287:Проверка соответствия инерции51 и номинальных MoonJ2/C22 по первичным данным и force/torque-defect, без подгонки.


## Инерция и поле Луны287–293

[Отчёт](lunar-inertia-field-validation.md)/JSON:1462эпохи/365.25суток,
10тел/4случая на одной DE441траектории,без интегрирования.
Номинальные J2/C22 вне условных интервалов округления offsets51;
mean/radius scaling не объясняет разные отношенияC22/J2.
Это различие физических определений/моделей,не обнаруженныйforce-codebug.
Park§4.2/47–51 reviewed из SHAкеша; Williams fulltext403/searchtransporterror,
новая независимая проверка Williams не заявляется.
Force bridges own-body passed;325related/15newpassed13.74с.
Основнойопыт8.046с;offlinefreshreader+все1462snapshots/27arrays/metrics exact.
91boundaryвключена в общийRMS/max;±.001сразностьускоренийнечистыйскачок.
Solid→nominal RMS7.70616e-13→7.69671e-13м/с²,максимум слегка вырос;
не доказательство физической точности/причины прежних5.66м.
Runtime/IC/I51/Rust/default/guard/physicalmap/sourcevisibilityflags прежние.
Следующий294:Метрология эталонного ускорения DE441: точные односторонние пределы на стыках и независимая проверка внутри сегментов; затем выбор физически обоснованной связи I/Q2 без подгонки.


## Метрология ускорений DE441294–300

[Отчёт](de441-acceleration-validation.md)/JSON:1462эпохи/91точныйстык,
10тел+directMoonEarth/4h/4modelbranches,без интегрирования.
Независимыйpower-basis/HornerDecimal70/90 поrawD иbinary64:
reader−binary90 max1.482344e-17м/с²,coefficientrounding3.880192e-18.
Exactrelativeaccelerationjumpmax1.347533505e-11м/с²;
±.001сразностьнечистыйjump,содержитsmoothvariation.
Обаleft/rightmodelresidualсохранены:общиеmax≈1.13e-11,невыбиратьлучшуюветвь.
346related/21newpassed15.89с;offlinefreshreader+1462силы+полныйoracle:
19новых/27силовыхarrays/metrics exact,21.899сchild,sharedinstalledenv.
Reader/силы/runtime/IC/I51/Rust/default/guards/physicalmappingпрежние.
Неphysicalephemerisaccuracy/непричинагодовых3.29/5.66м/неcontinuousbound.
Следующий301:Первичный контракт недеформированных I/Q2 и начального вращения для условной жёсткой модели Луны: проверить определения мантии/ядра/осей/времени до изменения параметров; не выбирать модель по лучшему годовому остатку.


## Стабилизация по ревью301–309

[Отчёт](runtime-stabilization.md)/JSON:исправленыparentloss/CLIbranch/
дробныйdtсрадиусомovershoot. Единыйsave_experiment;v1совместима,v2сохраняет
отдельныеSettingsребёнкапри неизменномparent. Не дерево/неполныйжурнал.
Python/Rustвремяcompleted_steps×dt;actualcontactсохранён,безepsilon/cap.
14reviewcases+6archivecontrols;полный1993Python/19Rust/fmt/skip0passed.
Первыйfull1983PASS/4provenanceFAILсохранён. Fresh12Kepler/RK45/editedcases
далиexactпрежниенаучныеметрики;oldlimitsreceiptотдельносохранён.
SHApinned8sourceархивиспользуетсятолькодляfrozenистории,неcurrentaccuracy.
Freshpubliccopy14casespassed2.32сбезсети/старой.tools,installedenvобщая.
Формулы/IC/параметры/допуски/default/physicalaccuracyflagsпрежние;
nativeпересобран,новыйJPLгоднеинтегрировался,portable/GitHubнет.
Следующий310:review4–5 — явныйStandard/Strict/реестрквалификации и
обязательныйnativeрежимchecker;затеминструкцияconstraints(7),
безопаснаяотмена/lastcommittedcheckpoint(6). I/Q2исследованиепослестабилизации.


## Доступ к профилям после изменения 311

Пункты4–5 ревью выполнены: в исходном GUI появился явный выбор
Standard/Strict, в CLI — `solar-sandbox --profile strict`; старый CLI default
остаётся Standard. [Запуск и область распознавания](profile-selection.md).
Полный checker с `--require-native`: 2011 Python/19 Rust/fmt, пропусков нет.
Настройки Strict совпали с закреплённым checkpoint; новый выбор не является
повторной годовой научной квалификацией. Прежние JSON измерений сохранены.
Следующий шаг продукта — проверенный путь установки, затем безопасная отмена
с сохранением последнего завершённого состояния. Portable155 остаётся прежним.


## Стабилизация установки и остановки312–314

Основные инструкции теперь используют constraints/pipcheck/native+standalonebuild
и --require-native. Локальные18версий/CPython3.14t/Windowsx64 совпали;
чистая установка снуля повторно не выполнялась, прежние clean-copy измерения — история.
Управляемые GUIstop/close и CLIinterrupt сохраняют завершённое состояние вместе
с parent; ошибка worker пишет копию до уведомления. Исправлен сброс parent в
конструкторе при первоначальном открытии. [Поведение и восстановление](controlled-stop.md).
Полный 2023Python/19Rust/fmt/skip0 PASS, source/data/native frozen.
Численные формулы/пакеты/допуски прежние; новой годовой квалификации/portable нет.
