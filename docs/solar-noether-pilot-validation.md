# Пилот балансов энергии и момента для десяти тел

2026-10-16T17:51:41+03:00. Этапы 219–222. [Протокол пилота](solar-noether-pilot-protocol.md),
[протокол высокоточной диагностики](solar-noether-precision-protocol.md),
[полные измерения, исходники и SHA](solar-noether-pilot-validation.json).

**Численные проверки пройдены; критерий различимости источников не пройден.**
Исходный аудит завершён с `complete=True`, `numerical_checks_passed=True`,
`checks_passed=False`; CLI exit=1 сохранён. Это запланированный отказ критерия,
а не прерванный расчёт. Порог не ослаблялся. Новых сил и годовой квалификации нет.

## Что именно проверялось

Исходный strict checkpoint: десять тел, SI, SSB, Ecliptic J2000,
JD 2461321.5 TDB, прежние массы и Origin. EIH 1PN плюс фиксированные
J2 Солнца/Земли с реакциями. Трое суток, пять снимков,
три пакета по 20 часов и последний 12 часов. Все Settings прежние.
Это отдельный короткий пилот, не замена годовых проверок движения/JPL.

Сначала согласованы tensor-J2, vector-J2 и runtime-J2, градиент потенциала,
полная EIH сила, усиленная PN-поправка, реакция и момент сил.
Все snapshot критерии прошли. Без реакций на источники нормированный
дисбаланс силы 0.489197; правильный вариант — 3.214112e-17.

Tensor/vector J2 расхождение 1.274141e-13 относительное, tensor/runtime
1.643194e-16. Дополнительный snapshot с явно переданной относительной
Earth–Moon координатой уменьшил первое расхождение до 5.192237e-16.
Изолированное изменение способа передачи координат объясняет вклад
вычитания близких абсолютных координат после перевода в AU. Силы runtime
не менялись; это диагностический опыт, не новая квалификация траектории.

## Правильные балансы модели

E/P/J вычислены из независимого скалярного EIH действия, не из runtime
диагностики. В энергию входит V2. Отдельно интегрированы 21 переменная:
figure torque, H_PN a_PN и H_PN a_Q, по энергии и трём компонентам P/J.
Вычитаются источники усечения порядка PN²/PN×Q и момент фиксированных осей.
Эти источники являются диагностикой заданных уравнений; новые 2PN или
смешанные физические силы не добавлялись. При фиксированных осях
полный орбитальный J не обязан сохраняться.

Независимый RK45 использует прежний `fixed_j2_ias.reference`:
matrix-EIH, tensor-J2, длина 1e8 м, время 86.746708 с,
rtol=3e-14, max_step=1800/900/450 с, atol=1e-17.
RHS 902/1754/3482; времена 2.693215/5.485896/10.954501 с.
Последнее уточнение: все тела 0.002970099 м, Moon−Earth 0.000195413 м.
Первое: 0.001485052 м и 0.000217002 м. По общей позиции разность выросла:
немонотонность сохранена. Чувствительность не является строгой границей ошибки.

Последняя нормированная разность бюджетов по компонентам ≤3.127383e-29;
относительная разность каждого активного блока ≤8.866049e-13.
Поэтому малые величины интегралов не скрыли плохую *относительную*
сходимость бюджета. Начальный roundtrip, конечность, пакеты и reference gate прошли.

## Кандидаты и цена

| Режим | Численная Moon−Earth, мм | Исправленный E, float64 | Тот же E, Decimal70 | Медиана расчёта, с |
|---|---:|---:|---:|---:|
| legacy_python | 0.157288 | 1.491070e-15 | 2.311850e-16 | 0.225269 |
| legacy_rust | 0.150286 | 1.863611e-15 | 8.625162e-16 | 0.122031 |
| continuous_rust | 0.171451 | 1.863611e-15 | 2.453961e-16 | 0.050619 |

E нормирован на |E0|; P на Σm|v0|, J на |J0|. Все три режима прошли
прежние позиционные/скоростные критерии и баланс <1e-10.
Максимум по всем телам относительно reference 0.002453590 м;
максимум исправленных float64 балансов кандидатов 1.863611e-15.
Reference corrected E/P/J: 2.234969e-15 / 5.144495e-16 / 3.175787e-16.
Все повторы побитны, legacy checkpoint/continue проверен, Origin сохранён.
Три чередующихся замера включают setup/снимки, исключают диагностику/диск.
Нагрузка CPU не фиксирована; эти времена не являются общим обещанием скорости.
Полный пилот с аудитом занял 23.461430 с.

## Почему критерий различимости не прошёл

В нормировке глобальных величин источники очень малы:

| Источник | Нормированный сигнал | Уровень диагностики пилота |
|---|---:|---:|
| Figure torque, J | 2.863105e-16 | 7.105427e-15 |
| PN², E | 1.117993e-18 | 7.105427e-15 |
| PN×Q, E | 7.331479e-22 | 7.105427e-15 |

Все семь ненулевых блоков не достигли заранее заданного signal/resolution>10.
Два точных нуля E/P группы figure torque не считаются пропавшим сигналом.
Уровень включает 32*float64_eps и измеренные остатки/чувствительность;
это практическая диагностика, не строгая граница ошибки.
Остатки при исключении каждой группы сохранены. Малый общий баланс
сам по себе мог бы пропустить отсутствие этих источников.

Следовательно, успешная траектория и баланс <1e-10 не доказывают, что
в этой задаче по глобальному дрейфу удалось напрямую проверить каждый
малый источник. Годовой расчёт ради прохождения критерия не запускался.

## Проверка причины в высокой точности

На тех же 30 сохранённых снимках использовано независимое аналитическое
выражение Noether из того же действия. Decimal.from_float сохраняет
точные бинарные states/masses/G/c/Q. Большие величины вычитаются до
перевода в float. Между 50 и 70 цифрами максимум нормированной разности
4.211653e-49, при заранее заданном пороге 1e-40. Цена — 1.509848 с,
одиночное измерение с формированием отчёта и записью промежуточных данных.

Разность изменений энергии, вычисленных float64 и Decimal70,
достигает 1.739860e-15 для continuous Rust. Это подтверждённый вклад
арифметики диагностики, а не изменение траектории. Некоторые остатки
уменьшились, некоторые выросли: например, reference J стал 5.637509e-16
против float64 3.175787e-16. Меньшее напечатанное число не обязательно точнее.

Reference Decimal corrected E остаётся 1.462236e-15, существенно выше
PN² сигнала 1.117993e-18. Оценка сохранённых состояний в Decimal не устраняет
погрешности их вычисления или интегрирования источников. Полное разложение
этих погрешностей здесь не выполнено. Исходный FAILED не переоценивался.
Новая высокоточная диагностика остаётся исследовательским инструментом.

## Проверки и воспроизведение

226 относящихся тестов прошли за 22.70 с, включая 20 новых случаев:
согласование физических выражений, отрицательные контроли, источник ниже
глобального порога, аналитическую свободную частицу, static pair U² term,
усиленный алгебраический PN-контроль и сохранность исходных данных.
Полный набор этапа 218 (1671 Python / 17 Rust) здесь не повторялся:
ядро, native/Rust, GUI и упаковка не менялись. Точная команда и SHA в JSON.

```text
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_solar_noether --output .tools/noether-repeat/pilot
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_decimal_noether --pilot-receipt .tools/noether-repeat/pilot.json --output .tools/noether-repeat/precision
```

Первый процесс при сохранённом исходе должен вернуть exit=1; перед второй
командой проверить `complete=True`, numerical=True и причину отказа.
При системном исключении, неготовом reference или SHA mismatch зависимую
проверку не продолжать. Нужны проверенные native/SciPy и Rust compiler
для oracle. Предыдущие пути не переиспользовать. Raw .tools/noether219
содержит все уровни, бюджеты, логи и контрольные суммы.

Нет нового JPL, вращения, приливов, физического повышения точности или
балансов на год. Результаты прежнего годового nominal20h остаются в силе.
Следующий шаг — независимые мгновенные Noether-тождества по отдельным
порядкам на сохранённых десяти-тельных состояниях, без вычитания крупных
глобальных величин и без новых физических сил.

## Проверенные определения

- [epoch_grid](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_noether.py:37)
- [packet_check](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_noether.py:41)
- [snapshot_controls](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_noether.py:47)
- [budget_refinement](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_noether.py:89)
- [normalized_balance](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_noether.py:108)
- [observability](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_noether.py:121)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_noether.py:141)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_solar_noether.py:259)
- [exact](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_noether.py:15)
- [quantities](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_noether.py:19)
- [compare_readouts](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_noether.py:75)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_decimal_noether.py:18)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_decimal_noether.py:78)
- [test_ten_body_tensor_vector_runtime_gradient_and_reaction_controls](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_noether.py:12)
- [test_three_day_grid_preserves_full_twenty_hour_packets_and_final_twelve_hours](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_noether.py:19)
- [test_small_global_budget_difference_does_not_hide_bad_source_relative_refinement](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_noether.py:27)
- [test_zero_or_disappearing_source_is_not_normalized_by_an_added_epsilon](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_noether.py:36)
- [test_invalid_source_integrals_and_scales_are_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_noether.py:45)
- [test_balances_below_a_loose_global_gate_do_not_qualify_unresolved_sources](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_noether.py:54)
- [test_existing_pilot_evidence_is_preserved_before_reading_inputs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_solar_noether.py:66)
- [test_exact_conversion_preserves_binary_inputs_instead_of_decimal_spelling](C:/Users/Admin/Desktop/Solar-simulator/tests/test_decimal_noether.py:13)
- [test_one_free_body_analytic_energy_momentum_and_angular_momentum](C:/Users/Admin/Desktop/Solar-simulator/tests/test_decimal_noether.py:17)
- [test_ten_body_analytic_readout_agrees_with_independent_scalar_action](C:/Users/Admin/Desktop/Solar-simulator/tests/test_decimal_noether.py:30)
- [test_constant_stored_state_has_exact_zero_decimal_changes_without_reintegrating](C:/Users/Admin/Desktop/Solar-simulator/tests/test_decimal_noether.py:42)
- [test_invalid_precision_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_decimal_noether.py:53)
- [test_coincident_bodies_are_rejected_without_softening](C:/Users/Admin/Desktop/Solar-simulator/tests/test_decimal_noether.py:57)
- [test_amplified_pn_analytic_readout_matches_scalar_action_for_ten_bodies](C:/Users/Admin/Desktop/Solar-simulator/tests/test_decimal_noether_action.py:12)
- [test_static_pair_has_the_positive_potential_squared_energy_term](C:/Users/Admin/Desktop/Solar-simulator/tests/test_decimal_noether_action.py:30)
