# Годовой свободный ротор Луны:273–279

18 октября2026. [Протокол273](free-lunar-year-protocol.md) записан до
годовых чисел. [Полный JSON](free-lunar-year-validation.json) содержит
сетку 1462 эпох, метрики всех 10 тел и пяти решений, SHA источников,
входов и локальных массивов. Полные траектории сохранены локально в NPZ.
Численные критерии **пройдены**. Цели менее 10 км для каждого тела
и менее 1 км для Earth–Moon **пройдены на проверенных снимках**.

Прямой Earth–Moon max относительно DE441:baseline
725.579200998м → nominal free
3.29017625342м; tight free
3.29164931652м. Это измеренные остатки модели
на снимках одного юлианского года, не физическая неопределённость,
не гарантия между выходами и не включение нового рабочего режима.

## Модель и исходные данные

31557600с=365.25суток; t=21600kс,k=0,…1461. Десятьтел,
SI/SSB/EclipticJ2000/JD2461321.5TDB; барицентры гигантов как прежде.
Point order-reduced EIH1PN + fixed Sun/EarthJ2 с реакциями + Newton
solid-equivalent MoonQ2. OrbitIC/GM/I/q/S не менялись. Каждое решение
заново отt0; старые96day состояния только для последующего сравнения.
Нет внешних R/Rdot послеt0 в RHS и нет подгонки по будущим данным.

Первоисточники и уравнения прежние из [260](free-lunar-rotation-protocol.md),
дополнительные силы не введены. Production DOP853/q/spatialS,
independent RK45/rawR/bodyPi/scalarEIH/body-frame inertia field.
EMB/rho и worst-block error control. M0=массаСолнца,L0=AU,
T0=sqrt(L0³/(GM0)); spin масштабирован начальной нормой.
DOP nominal rtol1e-12/maxstep3600s/xatol1e-3m/vatol1e-9m/s/qS1e-13;
tight3e-14/1800s/1e-4m/1e-10m/s/1e-14. RK45 maxstep1800/900s,
те же уровни rtol/atol; исходники и все допуски260 сохранены.

## Независимость, сходимость, префикс96суток

| Сравнение | Allbody, м | Earth–Moon, м | v, м/с | R Frobenius | S/initial |
|---|---:|---:|---:|---:|---:|
|production_refinement|0.0634939316681|0.001589928232|7.66137197e-09|2.92118657e-12|7.26269513e-14|
|reference_refinement|0.10159392971|0.0032526989095|3.10843733e-08|5.92235260e-12|1.54569511e-13|
|independent|0.10159392971|0.00122299788987|1.24780816e-08|3.67947045e-12|8.19577939e-14|

Пороги260 не ослаблялись. По-тельные значения в JSON. Ref-refinement —
измеренная чувствительность независимого решения, не строгая граница
ошибки; совпадение двух реализаций не доказывает полноту физики.

| Год против прежних96суток,385эпох | Allbody, м | Pair, м | Битово равных строк |
|---|---:|---:|---:|
|nominal|0.000244140625|0|384/385|
|tight|0.0001220703125|6.49094054159e-08|384/385|
|reference_nominal|0|0|384/385|
|reference_tight|0|0|384/385|
|baseline|0.000244140625|0|384/385|

Заранее заданы prefix gates:.1м/.01м/1e-6м/с/1e-9R/1e-9S.
Изменение конечной границы может менять последний укороченный шаг
прежнего опыта; битовое совпадение не является критерием. Проверены
текущие96day source/input и отдельные executed source с архивами270.
Первые384строки каждого варианта битово совпадают; отличия только на
прежней конечной эпохе96суток (строка384). Raw normalized differences
по x/v/q/R/S/Pi и каждому бюджету сохранены отдельно в JSON.

## Энергия, импульс и стоимость

E=E_EIH+Trot+Ufixed+UMoon,P=P_EIH,J=J_EIH+S. Источники OR:
PN²,PN×Q,fixed-axis torque. Moon orbital torque уже сокращён с Sdot;
фиксированные оси дают внешний момент в J, без внешней работы в E.
Totals Decimal70; initial вычтен до float. Нормировки|E0|,sum m|v0|,|J0|;
векторные нормы евклидовы. Критерии:на всех1462эпохах corrected E/P/J<1e-11,
rawq/R<1e-8;70/90цифр<1e-30 на индексах0,182,365,547,730,913,1095,1278,1461.
Реальный PASS/FAIL каждого блока в таблице/JSON, пороги не меняются.

|Расчёт|Corrected E|Corrected P|Corrected J|Raw q/R defect|RHS calls|Integration,с|
|---|---:|---:|---:|---:|---:|---:|
|nominal|1.21138024e-14|1.52562080e-15|4.74555329e-15|3.44169138e-15|109580|211.327004|
|tight|7.03394010e-15|7.22444325e-15|4.30234921e-15|4.21884749e-15|214784|477.391248|
|reference_nominal|6.93688383e-15|7.17166814e-15|4.23196797e-15|1.55781496e-13|105200|682.038680|
|reference_tight|1.61191464e-14|3.83134945e-15|7.36469910e-15|2.75537638e-14|210386|1167.370355|
|baseline|1.17098988e-14|1.59806836e-15|4.67067194e-15|2.22044605e-15|109580|292.544362|

Wall всего стенда:1193.884604с;сумма времен пяти процессов
2830.671649с. Максимум3процесса,
первым запускался самый длинный96day job. Тесты частично пересекались.
Это организация независимых опытов, не контролируемый benchmark
и не доказательство ускорения ядра. Предварительная serial оценка5086с
была по прежнему96day измерению; текущие нагрузка/частоты и стоимость иные.
8day preflight и полный повтор nominal-year отдельно в JSON.

Raw drift/три source budgets/Decimalprecision сохранены. Малые PN источники
могут быть ниже глобального дрейфа; Noether visibilityFAIL219–222 остаётся.
Глобальный баланс не сертифицирует отдельный малый источник; повышенная
арифметика readout не улучшает float-интегрирование автоматически.

## Остатки относительно DE441 и рост по времени

Reader проверен ранее против440JPLснимков, Decimal и стыков полиномов.
1462новые эпохи сравниваются с локальным DE441 reader, новой выгрузки
Horizons нет. Future orbit/R readout выполнен после всех5forecast.
Baseline и nominal имеют одинаковые допуски, tight отделён как
численная чувствительность. По-тельные ухудшения не исключены.

|Тело|Baseline max,м|Nominal free max,м|Tight free max,м|Nominal−baseline,м|
|---|---:|---:|---:|---:|
|Sun|218.804817423|218.804817461|218.804817719|3.82019322842e-08|
|Mercury|207.708295874|207.696358205|207.693867995|-0.011937669174|
|Venus|257.463982842|257.46705729|257.453236509|0.00307444840746|
|Earth|175.048362253|170.251211347|170.255335695|-4.79715090651|
|Moon|772.517731329|172.024403108|172.029329386|-600.493328221|
|Mars|571.344833653|571.344684476|571.341585683|-0.00014917764031|
|Jupiter|273.276622951|273.276622951|273.281584912|0|
|Saturn|31.1089436723|31.1089436723|31.1056179298|0|
|Uranus|17.1241381895|17.1241381895|17.1053302921|0|
|Neptune|64.771822614|64.771822614|64.8172906856|0|

|Окно tight,сутки|Снимки|Pair max,м|Pair RMS,м|Orientation max,rad|
|---|---:|---:|---:|---:|
|0.0-96.0|385|0.356397554452|0.150880652659|6.01221239784e-05|
|96.0-192.0|385|1.48573131987|0.854653578788|0.000206978011714|
|192.0-288.0|385|2.52000455206|1.79149733084|0.0004084908714|
|288.0-365.25|310|3.29164931652|2.61650994622|0.000558406150288|

|Префикс tight,сутки|Pair max,м|Pair RMS,м|Orientation max,rad|
|---|---:|---:|---:|
|32.0|0.0456273125975|0.0282097236202|7.4141986825e-06|
|64.0|0.143357079861|0.0705118889212|2.72322445758e-05|
|96.0|0.356397554452|0.150880652659|6.01221239784e-05|
|192.0|1.48573131987|0.613940881874|0.000206978011714|
|288.0|2.52000455206|1.14954729619|0.0004084908714|
|365.25|3.29164931652|1.57817511804|0.000558406150288|

В окнах общие границы; последнее окно310снимков, первые три по385.
Геометрические sub-Earth углы: u=Rᵀ(-rho)/|rho|, longitude=atan2(u_y,u_x),
latitude=atan2(u_z,hypot(u_x,u_y)). Longitude unwrap, остатки через
atan2(sinδ,cosδ). Это principal-axis направления, не IAU Euler angles,
не амплитуда отдельной свободной моды. Все span/max/RMS в JSON/NPZ.
Рост модельного остатка не объясняется одним фактом численного PASS;
конкретная причина требует отдельной диагностики, без fit к holdout.
Годовой pair residual порядка3.29м существенно больше измеренных
1.2–3.3мм расхождений независимого метода/его refinement. Эти расхождения
не являются строгой границей ошибки; причина остатка пока не атрибутирована.

## Воспроизводимость и пределы вывода

287связанных тестов (24новых годовых случая) прошли13.67с; все851public
файла неизменны во время проверки. Полный246:1819Python/17Rust/fmt —
исторический, сейчас не повторялся. Научные closure SHA неизменны.

Чистая publiccopy с пробелами в пути, без прежней.tools/личных docs,
с запрещёнными socket.connect/create_connection. Reader заново проверен.
Полное nominal-year отt0 без готовых траекторий:2NPZмассива exact.
Только затем явно импортированы5annual+5prior96NPZ и пересчитаны все
1462epoch показатели/31seriesarrays: exact. Это не5повторных годовых
интегрирований; установленные NumPy/SciPy общие, новая платформа не проверена.
NPZ memory order сохранён order=K; ранее выявленный96day FAIL270 остаётся
в старом отчёте, он не переписан и не скрыт текущим успешным повтором.

Runtime/IC/GM/I/Rust/default неизменны; guard EIH+dynamicrotation сохраняется.
Нет physical PN-I/triad/clock/SSC mapping, mantle/core/deformations/tides,
figure–figure или произвольных систем. Модельная и параметрическая
неопределённость не измерена. Профиль51 задаёт normalized mean solid inertia
0.392728 с исходной uncertainty1.2e-5; она не распространялась в годовой
прогноз. Мантия/ядро не заменяются одним ротором без физической ошибки.
Sampled year evidence не даёт гарантию между
снимками, для другого года/набора/IC и не равна полной физике Луны.
Публикации/commit/push/нового portable нет.

## Повтор расчёта

Из корня проекта с существующими проверенными reader/96day receipts:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_free_lunar_year --output .tools/year-replay-example --reader-receipt .tools/de441236/audit238-final.json --previous-report .tools/months266/audit270.json --workers 3
```

Каталог output и одноимённый JSON должны отсутствовать: существующие
результаты, включая неуспехи, не перезаписываются. Старые receipts и массивы
проверяются по SHA; повреждённые или несовместимые данные отклоняются.
Офлайн-повтор в этом исследовании выполнен отдельно по протоколу273.

## Код и проверки

- [assess_free_lunar_year.validate_grid](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_year.py:29)
- [assess_free_lunar_year.previous_receipt](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_year.py:34)
- [assess_free_lunar_year.load_trajectories](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_year.py:49)
- [assess_free_lunar_year.external_series](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_year.py:65)
- [assess_free_lunar_year.series_statistics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_year.py:82)
- [assess_free_lunar_year.analyse](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_year.py:102)
- [assess_free_lunar_year.qualification](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_year.py:139)
- [assess_free_lunar_year.integrate_job](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_year.py:183)
- [assess_free_lunar_year.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_year.py:194)
- [assess_free_lunar_year.main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_year.py:254)
- [assess_free_lunar_year.save](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_year.py:225)
- [test_free_lunar_year.series](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:11)
- [test_free_lunar_year.comparison](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:17)
- [test_free_lunar_year.valid_evidence](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:22)
- [test_free_lunar_year.test_julian_year_grid_includes_final_quarter_day_and_precision_endpoints](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:41)
- [test_free_lunar_year.test_wrong_annual_grid_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:49)
- [test_free_lunar_year.test_shared_windows_and_short_final_window_do_not_drop_boundary_or_double_global_rms](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:58)
- [test_free_lunar_year.test_missing_or_nonfinite_annual_channels_are_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:69)
- [test_free_lunar_year.test_external_goal_failure_remains_separate_from_numerical_qualification](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:78)
- [test_free_lunar_year.test_true_flags_cannot_hide_incomplete_or_failed_evidence](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:88)
- [test_free_lunar_year.test_fresh_guard_runs_before_missing_inputs_and_preserves_failure](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:104)
- [test_free_lunar_year.test_partial_trajectory_and_changed_sha_cannot_be_loaded](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:111)
- [test_free_lunar_year.test_archived_executed_source_is_checked_independently_of_current_source](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_year.py:124)

Следующий280: Диагностика причин годового модельного остатка и области применимости свободного ротора перед решением о runtime.
GPT-6.1 Sol High — численная метрология и диагностика модели.
