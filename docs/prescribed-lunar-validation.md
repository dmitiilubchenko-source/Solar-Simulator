# Влияние заданной ориентации Луны: диагностика280–286

18 октября 2026. [Протокол280](prescribed-lunar-protocol.md) записан до
результатов. [Полный JSON](prescribed-lunar-validation.json) содержит сетку,
метрики всех 10 тел и четырёх решений, данные проверок и SHA локальных NPZ.
Численные проверки и проверки силового баланса **пройдены**.
Замена ориентации не улучшила остаток относительно DE441.

**Это внешне управляемый диагностический опыт, не свободный прогноз.**
Ориентация MoonQ2 задаётся будущей DE441R(t); её совпадение с DE441
не проверяет качество прогноза вращения. Runtime не переключался.

Свободный годовой tight Earth–Moon max: **3.29164931652 м**.
Заданная ориентация, nominal: **5.66349090431 м**;
tight: **5.66374633858 м**.
Максимальная разность двух орбит от замены ориентации:
**2.54790737046 м**. Это разные измеряемые величины;
разность максимумов не равна максимуму векторной разности.

Выполненная замена **ухудшила**, а не устранила годовой остаток.
Поэтому ориентация сама по себе не объясняет всю проблему. На эпохе
максимального free-остатка изменение направлено частично против него:
в этой контролируемой модели видна компенсация части различий.
Это не доказывает, что свободная ориентация физически вернее DE441.

## Что изменено и что удержано

Год31557600с/1462эпохи/10тел, SI/SSB/EclipticJ2000/JD2461321.5TDB.
Те же orbitIC/GM/I51, point OR EIH1PN, fixed Sun/EarthJ2 и NewtonMoonQ2
с реакциями. Единственная физическая интервенция — вся R_Moon(t)
задана по DE441. Начальная матрица отличается от прежней на
1.24138829e-16 по Frobenius: это описательная диагностика,
не новый подобранный порог. Начальные орбиты совпадают точно.

Состояние6N+21:орбиты и3источника; spin/q не интегрируются. Нулевой spin
использован только как адаптер существующего readout. В orbital totals
нет вращательной энергии и углового момента. Будущие положения/скорости
DE441 не участвуют в RHS; сравнение с ними выполнено после4integrations.
Нет корректировки сил по остаткам и нет подгонки массы/инерции/фазы.

Первичный текст [Chen, Li, Tao2021, GRIT, II–III](https://arxiv.org/html/2103.12767v2)
повторно проверен; исходный HTML сохранён с SHA в JSON. Из вариации
потенциала δU=−τ·δθ и Rdot Rᵀ=hat(ω) получен внешний source:
∂U/∂t|x=−ω·τ и dJ_orbit/dt|Q=−τ. Специализация фигура–точка и
оговорка об индексах HTML10 прежние из [договора50](conservative-rotation.md).
Новые гравитационные эффекты и алгоритм GRIT не реализованы.

## Численная чувствительность

DOP853:rtol1e-12/3e-14,maxstep3600/1800s,xatol1e-3/1e-4м,
vatol1e-9/1e-10м/с. RK45:те же rtol/atol,maxstep1800/900s.
Worst-body/pair/budgets; independent scalarEIH/rawR/body-inertia field.
Исходники260/273 не изменены. Attitude и zero-spin differences в JSON
технические: заданное вращение не является интегрируемой величиной.

|Сравнение|Allbody,м|Earth–Moon,м|v,м/с|
|---|---:|---:|---:|
|production_refinement|0.0634939316681|0.000366479042367|7.66137197e-09|
|reference_refinement|0.10159392971|0.00260610521483|3.10843733e-08|
|independent|0.10159392971|0.000233415959079|9.33463734e-09|

Пороги260 не ослаблены:4м/.2м/1e-5м/с production,
1м/.05м/3e-6м/с reference refinement,2м/.1м/5e-6м/с independent.
Сверка по каждому телу в JSON; измеренная чувствительность не строгий bound.

## Энергия и моменты открытой орбитальной системы

E_orbit=E_EIH+Ufixed+UMoon(t),P=P_EIH,J_orbit=J_EIH. PN² и PN×Q
источники сохранены. Третий блок — external_prescription:
[−ω·τ,0,0,0,Σx×m a_fixed−τ]. Он включает внешнюю работу и момент,
поэтому не назван fixed_axes_torque. Это не энергия закрытой системы.

Totals Decimal70, initial вычтен до float; собственные нормировки
|E_orbit0|,sum m|v0|,|J_orbit0|.9сверок70/90цифр на протокольных индексах.
Пороги correctedE/P/J<1e-11 и precision<1e-30.

|Расчёт|Corrected E|Corrected P|Corrected J|RHS calls|Integration,с|
|---|---:|---:|---:|---:|---:|
|nominal|1.21469569e-14|1.52293690e-15|4.74664597e-15|109580|279.771980|
|tight|7.03611067e-15|7.19077593e-15|4.30246608e-15|214784|590.820480|
|reference_nominal|6.91814411e-15|7.22480633e-15|4.23009705e-15|105200|702.399021|
|reference_tight|1.61308647e-14|3.82754861e-15|7.36504996e-15|210386|1278.873856|

Глобальная наблюдаемость малых PNисточников219–222 остаётся FAIL.
Глобальный баланс может не заметить пропущенную малую работу; поэтому
введены отдельные own-norm проверки и отрицательные контроли.

|Probe index|Force|Torque|Potential|Net force|Orbital torque+τ|FD torque max|FD power max|
|---|---:|---:|---:|---:|---:|---:|---:|
|0|1.827637e-12|4.062966e-13|1.752369e-12|4.529087e-17|3.876458e-16|7.277123e-08|6.877455e-08|
|182|5.545251e-14|2.285084e-13|1.672969e-13|4.394445e-17|1.656602e-16|3.396879e-08|2.928793e-08|
|365|1.975800e-13|1.208529e-13|6.004809e-13|1.130201e-16|2.943267e-16|4.352419e-08|8.447292e-09|
|547|1.309702e-12|1.967560e-13|2.047953e-13|1.153033e-16|8.231135e-17|5.416510e-08|1.833102e-08|
|730|1.226375e-12|4.764938e-14|1.070458e-12|1.188828e-16|1.421235e-16|2.249856e-08|5.686800e-09|
|913|3.882828e-12|4.507266e-13|3.361751e-12|8.203837e-17|1.010616e-16|5.184297e-08|4.958429e-08|
|1095|1.104913e-12|4.051479e-14|5.740212e-14|1.795371e-16|2.472081e-17|2.175113e-08|9.094067e-09|
|1278|4.456116e-13|3.091076e-13|5.809549e-13|8.196212e-17|4.641732e-16|1.629820e-08|1.103475e-08|
|1461|1.274199e-13|5.646119e-13|7.265689e-13|1.104152e-16|1.027159e-15|6.706087e-08|8.528863e-09|

Force/torque/potential<5e-10, Newton netforce/angular<5e-12;
градиент по двум h=1e-4/5e-5rad и power<2e-6. Центральные производные
вычислены независимо через поворот потенциала. Два шага и все собственные
нормы сохранены; tiny scalar cancellation не скрывается общим RMS.

|Пропуск/ошибка|Максимальный собственный сигнал|
|---|---:|
|missing_work_signal|0.732115892587|
|wrong_work_sign_signal|1.46423185395|
|missing_torque_signal|1|
|wrong_torque_sign_signal|2|

Контрольный сигнал должен превышать1e-3; исходный корректный опыт при
этом сохраняется. Порог не является разрешением физически опускать член.

## Векторная интервенция и остаток

На каждом времени d_free=rho_free−rho_DE441,
d_control=rho_control−rho_DE441,d_switch=rho_free−rho_control.
Тождество d_free=d_control+d_switch проверяется по векторам, не максимумам.

Max невязка тождества:6.39323042e-08м при пороге1e-6м.
Наибольшая измеренная pair sensitivity control/free:
0.0032526989095м. Разность от интервенции
>5×sensitivity: **True**.
Это различимость изменения внутри данного опыта, не доказательство
реальной физической причины всего остатка. При худшей free-эпохе
index1406 signed projection d_switch на d_free,
делённая на |d_free|²:-0.6970111387388086.
Это геометрическая проекция, не доля ошибки в причинном бюджете.

|Окно tight,сутки|Снимки|Control pair max,м|Control pair RMS,м|Free pair max,м|
|---|---:|---:|---:|---:|
|0.0-96.0|385|0.368856673746|0.154612572185|0.356397554452|
|96.0-192.0|385|1.69038282651|0.953564622574|1.48573131987|
|192.0-288.0|385|3.40125503907|2.38236820495|2.52000455206|
|288.0-365.25|310|5.66374633858|4.39613375354|3.29164931652|

|Тело|Free max,м|Control nominal max,м|Control tight max,м|
|---|---:|---:|---:|
|Sun|218.804817719|218.804817458|218.804817714|
|Mercury|207.693867995|207.696358205|207.694180077|
|Venus|257.453236509|257.46705729|257.453236509|
|Earth|170.255335695|170.247984687|170.252903775|
|Moon|172.029329386|172.535066509|172.54031587|
|Mars|571.341585683|571.344684476|571.341585683|
|Jupiter|273.281584912|273.276622951|273.281584912|
|Saturn|31.1056179298|31.1089436723|31.1056179298|
|Uranus|17.1053302921|17.1241381895|17.1053302921|
|Neptune|64.8172906856|64.771822614|64.8172906856|

Общие границы окон сохранены;4окна содержат385/385/385/310точек.
Все max/RMS/скорости, включая ухудшения, в JSON и локальных NPZ.
Смена ориентации — единственное контролируемое физическое вмешательство,
включая нелинейную орбитальную обратную связь. Она не устанавливает,
какое отсутствующее свойство реальной Луны создаёт отличия свободной R.
Оставшийся control residual не атрибутирован другим эффектам без проверки.
В [предыдущей snapshot-проверке243–247](lunar-coupling-validation.md)
уже различались solid-inertia и nominal-J2/C22 поля. Их соответствие
массовым моментам всего тела/твёрдой части и исходным данным — следующая
проверяемая гипотеза, а не установленная причина5.66м. Инерция не подгоняется.
Улучшение или достижение внешней цели не требуется для numeric PASS.

Два уже существующих набора из243–247 имеют J2=0.000203214360135
(nominal) против0.000203235 (solid-I) и C22=0.000022380850528171017
против0.0000224275. Старый отчёт повторно проверен по закреплённому SHA.
Эти значения в текущем опыте не заменялись. Сначала необходимо проверить
определения и происхождение параметров; выбирать набор по лучшему
годовому остатку нельзя. Различие само по себе не доказывает причину5.66м.

## Стоимость, воспроизводимость, ограничения

Основной стенд:1300.655178с,максимум3процесса;
сумма времён jobs:2851.865337с.
Тесты частично выполнялись одновременно, частоты/нагрузка не контролировались.
Это стоимость диагностики, не benchmark/оптимизация production.
8day preflight:DOP5.243189с,
RK4512.123886с.

310связанных тестов/23новых прошли16.94с;857publicfiles неизменны.
Полный246:1819Python/17Rust/fmt — исторический, сейчас не повторялся.
Freshpubliccopy/безстарой.tools/личныхdocs/запрет socketconnect;
freshreader и полный nominal-year:2NPZarrays exact. Только после него
импортированы4control+5freeNPZ:полный analysis и
18seriesarrays exact.
Это повтор одного интегрирования и обработки четырёх решений, не4повторных
integrations. Те же установленные библиотеки; новая среда не квалифицирована.

Все исходные свободные результаты273 и прежние неуспехи сохранены.
Новых runtimeсил/приливов/3D/Rust/fit/публикации нет. Модельные параметры,
physicalPNmapping,core/mantle/deformations/figure–figure не пересматривались.
Контрольные остатки при внешней ориентации не являются точностью свободного
движка, физической uncertainty или гарантией между снимками/на иных IC.

## Повтор и код

Из корня, со старыми проверенными receipts и новым незанятым output:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_prescribed_lunar --output .tools/control-year-replay-example --reader-receipt .tools/de441236/audit238-final.json --previous-report .tools/year273/audit276.json --workers 3
```

- [prescribed_lunar_control.attitude](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:15)
- [prescribed_lunar_control.external_source](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:23)
- [prescribed_lunar_control.embed](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:31)
- [prescribed_lunar_control.expanded](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:37)
- [prescribed_lunar_control.initial](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:41)
- [prescribed_lunar_control.rhs](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:49)
- [prescribed_lunar_control.blocks](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:65)
- [prescribed_lunar_control.OrbitalDOP853](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:72)
- [prescribed_lunar_control.OrbitalRK45](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:80)
- [prescribed_lunar_control.integrate](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:88)
- [prescribed_lunar_control.balances](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:105)
- [prescribed_lunar_control.probes](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:112)
- [prescribed_lunar_control.__init__](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:73)
- [prescribed_lunar_control.__init__](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:81)
- [prescribed_lunar_control.gap](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:123)
- [prescribed_lunar_control.energy](C:/Users/Admin/Desktop/Solar-simulator/scripts/prescribed_lunar_control.py:131)
- [assess_prescribed_lunar.free_receipt](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_prescribed_lunar.py:24)
- [assess_prescribed_lunar.load_trajectories](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_prescribed_lunar.py:33)
- [assess_prescribed_lunar.vector_decomposition](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_prescribed_lunar.py:46)
- [assess_prescribed_lunar.statistics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_prescribed_lunar.py:59)
- [assess_prescribed_lunar.analyse](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_prescribed_lunar.py:72)
- [assess_prescribed_lunar.qualification](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_prescribed_lunar.py:106)
- [assess_prescribed_lunar.integrate_job](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_prescribed_lunar.py:148)
- [assess_prescribed_lunar.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_prescribed_lunar.py:157)
- [assess_prescribed_lunar.main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_prescribed_lunar.py:206)
- [assess_prescribed_lunar.save](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_prescribed_lunar.py:179)
- [test_prescribed_lunar.test_external_work_and_orbital_torque_match_analytic_triaxial_potential](C:/Users/Admin/Desktop/Solar-simulator/tests/test_prescribed_lunar.py:11)
- [test_prescribed_lunar.test_external_work_gradient_has_correct_sign_at_two_rotation_steps](C:/Users/Admin/Desktop/Solar-simulator/tests/test_prescribed_lunar.py:29)
- [test_prescribed_lunar.test_invalid_external_source_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_prescribed_lunar.py:44)
- [test_prescribed_lunar.test_vector_identity_retains_cancellation_and_does_not_add_scalar_maxima](C:/Users/Admin/Desktop/Solar-simulator/tests/test_prescribed_lunar.py:48)
- [test_prescribed_lunar.test_invalid_intervention_vectors_are_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_prescribed_lunar.py:59)
- [test_prescribed_lunar.valid_evidence](C:/Users/Admin/Desktop/Solar-simulator/tests/test_prescribed_lunar.py:67)
- [test_prescribed_lunar.test_true_flags_cannot_hide_failed_control_evidence](C:/Users/Admin/Desktop/Solar-simulator/tests/test_prescribed_lunar.py:90)
- [test_prescribed_lunar.test_no_residual_improvement_is_required_to_qualify_diagnostic](C:/Users/Admin/Desktop/Solar-simulator/tests/test_prescribed_lunar.py:106)
- [test_prescribed_lunar.test_fresh_output_and_incomplete_ensemble_are_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_prescribed_lunar.py:111)
- [test_prescribed_lunar.test_real_initial_adapter_removes_spin_without_changing_orbit](C:/Users/Admin/Desktop/Solar-simulator/tests/test_prescribed_lunar.py:118)

Следующий287:Проверка соответствия инерции51 и номинальных MoonJ2/C22 по первичным данным и force/torque-defect, без подгонки.
GPT-6.1 Sol High длянезависимойдиагностикимодели.
