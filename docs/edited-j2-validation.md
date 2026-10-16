# Изменённые системы EIH + J2: результат

15 октября 2026, этапы193–197. **Все27сочетаний девяти сценариев и трёх
режимов расчёта прошли предобъявленные модельные критерии.** Runtime,
GUI, исходные данные и рабочие настройки не менялись.
[Основной протокол](edited-j2-protocol.md),
[уточнение эталона](edited-j2-refinement-protocol.md),
[протокол изменения состава](edited-j2-three-protocol.md),
[полные результаты, IC, времена, бюджеты и SHA](edited-j2-validation.json).

## Сценарии и проверенные пути

Искусственная наклонная пара Alpha/Beta: a=1e8м, e=.2, mu/(ac²)=1e-6,
массовые доли(.8,.2), ненулевые COMoffset/drift. Две фиксированные J2:
Alpha(.005,R=a/5,осьz), Beta(−.003,R=a/7,ось(.6,0,.8)). SI, произвольные
инерциальные оси, childt0=0, без эфемеридной эпохи. Полные IC в JSON.
J2, радиусы и оси после правки массы остаются заданными параметрами;
внутреннее устройство тела и новый равновесный радиус не рассчитываются.

Шесть двухтелесных веток: Alpha.mass×1.25, сдвиг положения Beta
на a(.03,−.02,.04), относительная скорость Beta×.9 — каждое изменение
отдельно в исходном parent и послеP/4. Три дополнительных ветки: добавить
Gamma на старте, удалить Gamma из тройки послеP/4, изменить Alpha.mass×1.25
в тройке послеP/4. Gamma.mass=.05Moriginal, bare point, без новой J2.

Родитель сохранён, IC дочернего опыта проверены побитово, автоматического
recentring нет. ParentпослеP/4 — результат прежнего native расчёта;
проверяется свободное развитие записанного child, а не точность предыстории.
Редактирование массы/состава — внешнее вмешательство. Балансы начинаются
заново, а не требуют равенства энергии до и после разных опытов.

Каждый опыт:61эпоха за2первоначальных номинальных периода. Сравнены
реальный GUI/headless путь advance_towards с Python и Rust и отдельный
nativeContinuousRun. Общие packet20/выходные границы; каждый outputepoch
достигается точно. Legacyперезапускает DOP853 на каждом пакете, continuous
сохраняет контроллер. Settingsодинаковы:rtol3e-14,xatol1e-7м,vatol1e-13м/с,
per-body,dt=P/100. IAS15 не добавлялся в этот блок.

## Эталон и обнаруженное ограничение проверки

Независимый RK45 решает полную матрицу EIH и тензорный градиент J2,
одновременно интегрируя τQ,PN² иPN×Q. Длина1e8м; нормирующая масса
и время пересчитаны из actualchildmasses. Проверка короткого SI source
против referenceintegral/Δt подтвердила единицы; приt0 бюджеты нулевые.

Первоначальные уровни193:P/200,P/400,P/800. В mass_start и velocity_start
два последних ограничения оказались неактивны:RK45 уже выбрал меньшие
шаги. ЧислаRHS14678 и13742 и массивы совпали. Это не нулевая ошибка эталона.
Первоначальный two194 сохранён. До дополнительных расчётов объявлен195:
для всех6случаев добавлены P/1600,P/3200,rtol3e-14, без пересчёта или
подбора кандидатов. На обоих уровнях числоRHS выросло. Три новых опыта
с изменением состава сразу использовали P/800,P/1600,P/3200.

| Группа/сценарий | RHS1600→3200 | Чувствительность всех тел, м | Beta−Alpha, м |
|---|---|---:|---:|
| 2/mass_start | 19730→38408 | 1.28453541e-05 | 1.63072701e-05 |
| 2/position_start | 19244→38408 | 4.83803622e-05 | 6.08679148e-05 |
| 2/velocity_start | 19604→38408 | 5.24062124e-05 | 6.51959997e-05 |
| 2/mass_quarter | 20036→38420 | 0.000122545194 | 0.000145493779 |
| 2/position_quarter | 19226→38408 | 4.46165352e-05 | 5.63055238e-05 |
| 2/velocity_quarter | 19874→38414 | 0.000149225106 | 0.000186940982 |
| состав/add_start | 19250→38408 | 3.03765973e-05 | 3.77049232e-05 |
| состав/remove_quarter | 19262→38408 | 1.59067435e-05 | 2.08597523e-05 |
| состав/mass_quarter | 20036→38420 | 0.000209702815 | 0.000253407079 |

Все последние различия прошли referencegates:<0.01м/1e-5м/с для всех
тел и пары; нормированные компоненты бюджета<1e-10. Начальный roundtrip
<1e-6м/1e-8м/с, без подмены первой referenceточки. Это эмпирическая
чувствительность, не строгая граница. Субмиллиметровое численное согласие
нельзя выдавать за такую же достоверность реальных тел или ранжировать
методы ниже чувствительности эталона.

## Расхождение траекторий с уточнённым эталоном

Пороги193:каждое тело и Beta−Alpha<0.1м/1e-4м/с, corrected E/P/J<1e-9.
Для Gamma также выполняется самостоятельная по-тельная проверка.

| Группа/сценарий | Режим | Все тела, м | Beta−Alpha, м | Beta−Alpha, м/с | max corrected E/P/J |
|---|---|---:|---:|---:|---:|
| 2/mass_start | legacy_python | 4.48696629e-05 | 5.41300038e-05 | 2.50672365e-07 | 1.16889e-14 |
| 2/mass_start | legacy_rust | 3.5137194e-05 | 4.23215854e-05 | 1.94873568e-07 | 2.51642e-14 |
| 2/mass_start | continuous_rust | 4.22503736e-05 | 5.12367473e-05 | 2.37684633e-07 | 1.16577e-14 |
| 2/position_start | legacy_python | 1.63509404e-05 | 1.92867313e-05 | 4.79025886e-08 | 2.05072e-14 |
| 2/position_start | legacy_rust | 1.05221298e-05 | 1.27171786e-05 | 3.80650288e-08 | 3.05499e-14 |
| 2/position_start | continuous_rust | 1.21117753e-05 | 1.51726386e-05 | 3.16922674e-08 | 2.84931e-14 |
| 2/velocity_start | legacy_python | 1.65777076e-05 | 2.1326144e-05 | 8.7688682e-08 | 1.24614e-14 |
| 2/velocity_start | legacy_rust | 1.90097939e-05 | 2.42804671e-05 | 9.85321775e-08 | 1.06826e-14 |
| 2/velocity_start | continuous_rust | 1.83278043e-05 | 2.34542952e-05 | 9.50399788e-08 | 1.08602e-14 |
| 2/mass_quarter | legacy_python | 8.7579829e-05 | 0.000106262575 | 6.40217459e-07 | 1.95645e-14 |
| 2/mass_quarter | legacy_rust | 9.34143325e-05 | 0.000113230774 | 6.81045009e-07 | 2.05017e-14 |
| 2/mass_quarter | continuous_rust | 9.22986826e-05 | 0.000111940784 | 6.74949962e-07 | 2.43184e-14 |
| 2/position_quarter | legacy_python | 2.62948375e-05 | 3.44492933e-05 | 9.65834943e-08 | 1.93784e-14 |
| 2/position_quarter | legacy_rust | 2.75291684e-05 | 3.59750727e-05 | 1.04760033e-07 | 2.00228e-14 |
| 2/position_quarter | continuous_rust | 3.38549267e-05 | 4.39129914e-05 | 1.33027287e-07 | 2.9045e-14 |
| 2/velocity_quarter | legacy_python | 5.34351651e-05 | 6.43940125e-05 | 3.21319887e-07 | 2.46145e-14 |
| 2/velocity_quarter | legacy_rust | 5.38342556e-05 | 6.5008129e-05 | 3.23460192e-07 | 2.79519e-14 |
| 2/velocity_quarter | continuous_rust | 4.88606599e-05 | 5.89426728e-05 | 2.94075359e-07 | 2.51707e-14 |
| состав/add_start | legacy_python | 6.04974299e-05 | 7.58135658e-05 | 2.72466013e-07 | 1.331e-14 |
| состав/add_start | legacy_rust | 6.03556189e-05 | 7.54212761e-05 | 2.69525181e-07 | 1.17805e-14 |
| состав/add_start | continuous_rust | 6.01462848e-05 | 7.50875663e-05 | 2.69023075e-07 | 1.23607e-14 |
| состав/remove_quarter | legacy_python | 9.02223165e-06 | 1.11414957e-05 | 3.43892154e-08 | 2.78679e-14 |
| состав/remove_quarter | legacy_rust | 9.99817948e-06 | 1.26585606e-05 | 3.49950084e-08 | 2.91644e-14 |
| состав/remove_quarter | continuous_rust | 1.53010185e-05 | 1.90751219e-05 | 5.45077305e-08 | 4.36386e-14 |
| состав/mass_quarter | legacy_python | 1.48086657e-05 | 1.77719072e-05 | 9.31533599e-08 | 1.03333e-14 |
| состав/mass_quarter | legacy_rust | 1.61730877e-05 | 1.97233066e-05 | 1.06627848e-07 | 1.28614e-14 |
| состав/mass_quarter | continuous_rust | 1.35508836e-05 | 1.63625606e-05 | 8.45956239e-08 | 1.02501e-14 |

Все повторы и каждый из трёх замеров воспроизвели сохранённые массивы
побитово. Legacycheckpoint/save/load даёт точное совпадение дальнейшего
одинакового пакета. Continuouscontrollerbuffers в checkpoint не сохраняются;
для перезапуска continuous такое побитовое обещание не даётся.

## Балансы и независимые отрицательные контроли

Используется прежнее aN+aPN+aQ. Фиксированные оси дают внешний орбитальный
момент τQ. Для EIHaction H_PN=∂²L_PN/∂v∂v, R2=H_PN aPN, Rmix=H_PN aQ:

```text
Δ(E_EIH+V2) = ∫Σ v·(R2+Rmix) dt
ΔP_EIH      = ∫Σ (R2+Rmix) dt
ΔJ_EIH      = ∫[τQ+Σ r×(R2+Rmix)] dt
```

Scales берутся из childstart. Максимальный исправленный остаток27кандидатов
— около4.364e-14, при этом rawорбитальный J меняется вплоть до0.005162
в своём масштабе. Его принудительное постоянство было бы неверным критерием.
Раздельные rawE/P/J и три интеграла сохранены для каждого случая.
Бюджет кандидата использует источники вдоль независимой referenceкривой;
он не является отдельно накапливаемым callbackbudget самого кандидата.
Это учёт усечения, а не добавление PN×J2/2PN сил или рост физической полноты.

Отдельная PNпоправка Python/Rust сверена с полной матрицей, а J2 —
с complex-stepградиентом tensorpotential, реакцией и covarianceпод
поворотом/переносом. На тройках сумма изолированных pair-only EIH отличается
от fullPN на1.749% /1.482% **малой PNпоправки**. Это ожидаемый отрицательный
контроль потери трёхтелесных слагаемых, не ошибка всего гравитационного поля.
Удаление реакции Alpha даёт netforceоколо0.5 суммы норм, тогда как
правильная сумма на уровне0–5e-17. Все негативные контроли сработали.
[Скалярный EIHaction](https://fiteoweb.unige.ch/~maggiore/GWVol1/EIHLagrangian.pdf),
[point/figure модель](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf);
формулы H_PN и первичные Decimalпроверки подробно разобраны [в184–186](fixed-j2-ias-validation.md).

## Вычислительная стоимость

Один повтор/прогрев, затем3чередующихся полноценных запуска на режим.
Включены setup/forces/61снимок, исключены reference/диагностика/hash/report.
Все rawвремена в JSON; таблица показывает медианы. RHSlegacyне измеряется,
число пакетов не подставляется вместо него. Разные контроллеры и разные
задачи нельзя обобщать одним коэффициентом ускорения/FPS.

| Группа/сценарий | LegacyPython, с | LegacyRust, с | ContinuousRust, с |
|---|---:|---:|---:|
| 2/mass_start | 1.251389 | 0.684797 | 0.379802 |
| 2/position_start | 1.051964 | 0.585080 | 0.256986 |
| 2/velocity_start | 1.190445 | 0.670979 | 0.364079 |
| 2/mass_quarter | 1.284328 | 0.717873 | 0.397914 |
| 2/position_quarter | 1.082965 | 0.609616 | 0.270324 |
| 2/velocity_quarter | 1.252958 | 0.686319 | 0.369197 |
| состав/add_start | 1.207700 | 0.686297 | 0.322576 |
| состав/remove_quarter | 1.130164 | 0.632065 | 0.287541 |
| состав/mass_quarter | 1.376362 | 0.768263 | 0.420244 |

Referencetwo194: суммарно 60.538с; все уровни/RHS/стоимость отдельно в JSON.

Referencerefined195: суммарно 100.966с; все уровни/RHS/стоимость отдельно в JSON.

Referencethree196: суммарно 77.379с; все уровни/RHS/стоимость отдельно в JSON.

## Отказы и сохранность

Первый unitзапуск:17failed. Старый researchmodel создавал numpy.float64
компоненты векторов, а checkpointвалидатор принимает Pythonfloat/int.
Отказ произошёл до новых траекторий. Новый fixture преобразует типы
с побитовой проверкой исходных чисел; старый generator/storage/пороги
сохранены. Исходный helper, тесты и полный отказ сохранены локально,
их SHA опубликованы в JSON. После исправления18новых проверок прошли;
ещё7проверок добавления/удаления/fullNbodyPN тоже прошли.

Общая регрессия: **391тест прошёл за51.14с**, включая25новых.
Это связанный набор branch/IO/GUI/CLI/EIH/J2/native/continuous/cache,
не весь проект. Все источники, scientificinputs, actualnative.pyd и
SciPyimplementation проверены до/после. Старые артефакты и ZIP155
сохраняются; новый portable/fullCargo не запускались, поскольку runtime,
Rust и упаковка не менялись. Личные документы остаются локально.

Ограничения:это девять few-body модельных опытов на61эпохе, не
изменённая реальная Солнечная система, не JPL-точность и не гарантия
для произвольного близкого сближения. Прежние отказы generalKepler0.1м,
Solar139 и Койпер420, а также рост KBOостатков после528 не исправлялись
и не скрывались. Новых непройденных динамических критериев здесь нет.

## Воспроизведение

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest -p no:cacheprovider -q tests/test_edited_j2.py tests/test_edited_j2_three.py
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_edited_j2 --output .tools/new-j2-audit/two
.venv/Scripts/python.exe -X utf8 -B -m scripts.refine_edited_j2 --input .tools/new-j2-audit/two.json --output .tools/new-j2-audit/refined
.venv/Scripts/python.exe -X utf8 -B -m scripts.edited_j2_three --output .tools/new-j2-audit/three
```

Нужны среда проекта и существующий nativeмодуль. Сеть/JPL/REBOUND
не требуются. Каждый выходной путь должен быть новым; при отказе
сохраняется частичный JSON/NPZ. Переиспользование twoтраекторий вrefine
проверяет SHA и exactmodel/IC/time/provenance до повторной квалификации.

Проверенные точки реализации:

- [edited_j2.fixture](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_j2.py:26)
- [edited_j2.verify_branch](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_j2.py:49)
- [edited_j2.variants](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_j2.py:60)
- [edited_j2.legacy_trajectory](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_j2.py:66)
- [edited_j2.checkpoint_check](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_j2.py:78)
- [edited_j2.agreement](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_j2.py:89)
- [edited_j2.reference_gate](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_j2.py:104)
- [edited_j2.metrics](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_j2.py:122)
- [assess_edited_j2.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_j2.py:25)
- [refine_edited_j2.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/refine_edited_j2.py:18)
- [edited_j2_three.fixture](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_j2_three.py:32)
- [edited_j2_three.snapshot_controls](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_j2_three.py:51)
- [edited_j2_three.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_j2_three.py:73)
- [test_edited_j2.test_only_declared_parameter_changes_without_recentring](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_j2.py:22)
- [test_edited_j2.test_child_j2_and_pn_corrections_separately_match_independent_force](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_j2.py:48)
- [test_edited_j2.test_reference_uses_child_mass_clock_and_resets_source_integrals](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_j2.py:71)
- [test_edited_j2.test_legacy_checkpoint_and_packet_times_match_continuous](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_j2.py:89)
- [test_edited_j2.test_failed_reference_and_inconsistent_arrays_cannot_certify](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_j2.py:101)
- [test_edited_j2.test_storage_boundary_conversion_preserves_historical_model_bits](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_j2.py:114)
- [test_edited_j2_three.test_membership_edit_preserves_unedited_states_and_parent](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_j2_three.py:18)
- [test_edited_j2_three.test_full_three_body_pn_is_not_a_sum_of_isolated_pairs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_j2_three.py:33)
- [test_edited_j2_three.test_three_body_figure_gradient_reaction_and_covariance](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_j2_three.py:48)
