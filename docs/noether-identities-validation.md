# Мгновенные Noether-тождества десяти тел

2026-10-16T18:26:19+03:00. Завершены этапы 223–228. [Протокол до измерений](noether-identities-protocol.md),
[полные уровни, снимки, проверки и SHA](noether-identities-validation.json).

**Все 30 снимков прошли проверки тождеств и сверку источников с рабочим кодом.**
Прежний [неуспех глобальной различимости](solar-noether-pilot-validation.md)
сохранён. Проверка математических выражений не заменяет проверку ошибок
интегрирования и не повышает физическую точность орбит.

## Исходные данные и область

Те же шесть наборов по пять снимков: три уровня reference пилота220,
legacy Python, legacy Rust, continuous Rust. Десять тел, трое суток,
SI, исходные SSB/Ecliptic J2000/Origin/JD2461321.5TDB, прежние массы,
G/c и фиксированные Q Солнца/Земли. Все исходные float64 значения
перенесены точно через Decimal.from_float; новых траекторий нет.

Модель прежняя: EIH 1PN плюс аддитивные fixed J2 с реакциями.
Опорные материалы: [Vines, действие на стр.3](https://fiteoweb.unige.ch/~maggiore/GWVol1/EIHLagrangian.pdf),
[Park et al. 2021, §3.1–3.2](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf).
Состав тел и фигуры проще DE441; это не воспроизведение всей её динамики.

## Метод и результаты

Формально L=L_N+λL_PN−ηV2 и a=a_N+λa_PN+ηa_Q.
Метки λ/η нужны для разделения порядков; runtime их не вводит.
F=(E,P,J) разделено на Newton, PN и figure части.
Центральные направленные производные вычислены отдельно для частей,
при 70/90 цифрах и h=1e-3,1e-5,1e-7 с. Decimal-сдвиги не округляются
обратно в float. Скалярные силы вычисляются независимо в Decimal;
округлённая total float acceleration в эти тождества не подставляется.

| Канал | Максимальный нормированный дефект на последнем h |
|---|---:|
| newton | 4.364438e-29 |
| pn_linear | 7.025025e-29 |
| figure | 6.790211e-28 |
| pn2 | 1.045366e-42 |
| pn_q2 | 2.127115e-42 |

Newton и линейный PN каналы имеют нулевую правую часть.
Figure канал учитывает момент фиксированных осей; PN² и PN×Q —
действие гессиана PN-лагранжиана на соответствующее ускорение.
Это bookkeeping усечённых уравнений, не добавление 2PN/PN×J2 сил.

Все E/P/J блоки проверяются отдельно. Для нулевых правых частей
масштабы построены из не сокращённых вкладов, без epsilon.
Для ненулевых источников проверено и относительное расхождение
с собственным сигналом: максимум 6.962527e-40 при пороге 1e-8.
Таким образом, крупный Newtonian масштаб не мог скрыть ошибку малого источника.
Это **дефект вычисления тождества**, а не точность симуляции в метрах.

Максимальная разность последних h — 6.789532e-24 в той же нормировке,
при пороге 1e-8. Максимум 70→90 цифр: 5.593231e-45 по масштабу,
3.583354e-42 относительно ненулевого источника, при пороге 1e-30.
Все три h и обе точности сохранены, ни одна эпоха не исключена.

## Проверки, которые должны обнаруживать ошибку

Минимальные дефекты отрицательных контролей по всем 30 снимкам:

| Намеренная ошибка | Минимальный дефект | Требование |
|---|---:|---:|
| Убрать реакции на источники J2 | 0.488366 | >1e-3 |
| Убрать static U_i² часть PN-энергии | 0.00570416 | >1e-3 |
| Сложить только изолированные парные PN силы | 1.496373e-5 | >1e-6 |

Исключение каждого PN²/PN×Q источника даёт относительный дефект >.9
для каждого ненулевого E/P/J блока. Контроли сработали в каждом наборе;
фактически первые три сработали во всех снимках, хотя протокол требовал
лишь хотя бы один из пяти. Это алгебраические контроли, не варианты орбит.

## Связь с существующими Python/Rust вычислениями

На тех же 30 снимках отдельные Newton, matrix-PN и runtime-J2 силы
сверены с Decimal. Максимальные относительные расхождения:
7.285502e-16 / 9.963068e-16 / 8.380027e-16 при пороге 5e-13.
Полная native EIH: 6.225596e-16 при пороге 3e-14.
Усиленная native PN при c/10: 8.266678e-12 при пороге 3e-9;
это отдельный snapshot контроль, не изменение физического c траекторий.

Каждый ненулевой E/P/J блок трёх групп источников float-кода
сверен относительно своего сигнала с Decimal. Максимум 7.908145e-14,
при пороге 5e-10. Точные нули figure E/P разобраны отдельно.
Реальные native pyd/SciPy и источники закреплены SHA исходного пилота
и повторно проверены до/после. Этот мост связывает тождества с рабочим
кодом, а не только две исследовательские записи формулы.

## Стоимость, тесты и воспроизведение

Математический аудит: 15.085717 с внутри драйвера, 16.519940 с процесс.
Мост: 1.075719 с внутри драйвера, 2.849506 с процесс.
Это единичные наблюдения с промежуточной записью результатов;
нагрузка CPU не фиксирована, ускорение физического ядра не заявляется.

Полный scripts/check_project.py прошёл: **1715 Python-тестов и 17 Rust-тестов**,
форматирование обеих Rust crates и ссылки. В этом блоке 24 новых случая;
от последнего полного 1671 добавились также 20 случаев этапов219–222.
Лог и точная команда/SHA в JSON. Публичные исходники не менялись во время
полного прогона; этот отчёт и обновление паспорта созданы после него,
их ссылки проверены отдельно. Физический код и прежние отчёты сохранены.

```text
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_noether_identities --pilot-receipt .tools/noether219/pilot220.json --output .tools/identities-repeat/audit
.venv/Scripts/python.exe -X utf8 -B -m scripts.bridge_noether_sources --pilot-receipt .tools/noether219/pilot220.json --identity-receipt .tools/identities-repeat/audit.json --output .tools/identities-repeat/bridge
```

Пилот220 и его проверенные исходные NPZ нужны как входные снимки;
их можно получить по [прежнему протоколу](solar-noether-pilot-protocol.md).
Сначала проверять complete/numerical/source/SHA. Exit=1 пилота допустим
только для сохранённого критерия глобальной различимости; системное
исключение или неготовый reference не являются подходящим входом.
Использовать новые пути, не переписывать исходные результаты.

## Что остаётся открытым

Успешные локальные тождества не отменяют FAILED пилота220: малые источники
по-прежнему не различимы его глобальным дрейфом. Годовые Noether21 балансы
не выполнены. Нового JPL, ошибок орбит, физических сил, rotating bodies,
приливов, default, portable ZIP или публикации GitHub нет.
Точность производной 70/90 цифр не переносится на float64 траектории.

Следующий полезный шаг — расширить JPL-покрытие реальных выходов20h.
Сначала проверить представление TDB-эпох в запросе/ответе API и задать
учёт возможного несовпадения времени. Пока нельзя обещать 440 точно
совпавших эпох; существующие 24 совпадения и старые125 остаются отдельными
проверенными наборами. Не менять IC/силы и не интерполировать кандидатов.

## Проверенные определения

- [dec](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:20)
- [dot](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:24)
- [norm](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:28)
- [cross](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:32)
- [plus](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:36)
- [convert](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:40)
- [pack](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:53)
- [parts](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:58)
- [forces](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:94)
- [response](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:126)
- [direction](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:139)
- [strength](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:148)
- [score](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:155)
- [snapshot](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:167)
- [precision_agreement](C:/Users/Admin/Desktop/Solar-simulator/scripts/noether_identities.py:222)
- [verified_pilot](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_noether_identities.py:19)
- [controls_passed](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_noether_identities.py:31)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_noether_identities.py:39)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_noether_identities.py:90)
- [source_metrics](C:/Users/Admin/Desktop/Solar-simulator/scripts/bridge_noether_sources.py:24)
- [bridge](C:/Users/Admin/Desktop/Solar-simulator/scripts/bridge_noether_sources.py:39)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/bridge_noether_sources.py:67)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/bridge_noether_sources.py:109)
- [test_sum_of_separate_parts_matches_frozen_decimal_noether_readout](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identities.py:18)
- [test_scalar_decimal_newton_pair_is_analytic_and_has_full_reaction](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identities.py:29)
- [test_direction_preserves_decimal_velocity_perturbations_far_below_float_ulp](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identities.py:38)
- [test_separate_decimal_forces_and_hessian_match_existing_scalar_formulas](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identities.py:48)
- [test_zero_signal_does_not_acquire_an_epsilon_denominator](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identities.py:64)
- [test_undeclared_precision_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identities.py:73)
- [initial_identities](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identities.py:78)
- [test_initial_ten_body_identities_and_precision_refinement](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identities.py:83)
- [test_initial_negative_controls_are_detectable](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identities.py:89)
- [row](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identity_audit.py:9)
- [test_missing_negative_control_cannot_be_hidden_by_other_successes](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identity_audit.py:17)
- [test_dropped_source_control_must_resolve_each_active_block](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identity_audit.py:22)
- [test_incompatible_pilot_receipt_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identity_audit.py:28)
- [test_previous_identity_audit_is_preserved_before_input_reads](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_identity_audit.py:39)
- [test_tiny_source_cannot_pass_because_absolute_error_is_small](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_source_bridge.py:12)
- [test_spurious_exact_zero_source_is_rejected_without_epsilon](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_source_bridge.py:18)
- [test_real_ten_body_native_and_source_bridge](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_source_bridge.py:25)
- [test_invalid_source_arrays_are_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_source_bridge.py:32)
- [test_existing_source_bridge_evidence_is_preserved](C:/Users/Admin/Desktop/Solar-simulator/tests/test_noether_source_bridge.py:39)
