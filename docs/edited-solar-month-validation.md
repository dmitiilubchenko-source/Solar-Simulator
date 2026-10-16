# Изменённый Solar: 30 суток и сдвинутая выходная сетка

15 октября 2026, этапы 200–202. [Протокол](edited-solar-month-protocol.md),
[все измерения и SHA](edited-solar-month-validation.json),
[прежние три суток](edited-solar-validation.md). Три изменённых старта
десяти тел прошли 30 суток на двух заранее заданных сетках, каждый в трёх
режимах: **18/18 сочетаний прошли критерии**. Силы, настройки и runtime прежние.

Сравниваются реализации одной модели EIH1PN+fixedSun/EarthJ2, а не
физическая точность относительно реальной системы. Нет JPL для editedIC.
SI; исходные инерциальные оси/скорости SSB/EclipticJ2000, без recentering.
Child.time=0/origin=None; родитель JD2461321.5TDB/DE441 — происхождение.
GM гигантов системные, массы не дублировались. Состав и три правки точно
совпадают с198: Sun.mass×1.25, Earth.position+(1e6,−2e6,3e6)м,
Moon.velocity+(100,−50,25)м/с. DOP853/rtol3e-14/per-body/relativeEarthMoon,
xatol1e-3м/vatol1e-9м/с/dt3600с/packet20.

Регулярная сетка121эпоха через6ч; сдвинутая122эпохи с внутренними
моментами на3ч позднее. Общие только0 и30суток. Смена сетки меняет
перезапуски legacy-контроллера; остальные параметры сохранены.

| Сетка / правка | Moon−Earth, legacyPython, м | legacyRust, м | continuousRust, м | Последний reference, м |
|---|---:|---:|---:|---:|
| regular / sun_mass | 0.00027571553 | 0.0002794266 | 3.4125109e-05 | 3.4136495e-05 |
| regular / earth_position | 0.00024798071 | 0.00024798091 | 4.3162592e-05 | 4.8323949e-05 |
| regular / moon_velocity | 0.0034618483 | 0.0034618567 | 6.8302651e-05 | 3.4123382e-05 |
| shifted / sun_mass | 0.0011404717 | 0.0014700911 | 3.4125395e-05 | 3.4131647e-05 |
| shifted / earth_position | 0.00098041022 | 0.0010972124 | 3.4126763e-05 | 4.8324812e-05 |
| shifted / moon_velocity | 0.00013127194 | 0.00011622252 | 4.3172624e-05 | 3.4124718e-05 |

Каждое тело отдельно проходит 10 м / 1e-4 м/с, Moon−Earth — 0,1 м / 1e-5 м/с.
Максимальное позиционное расхождение среди отдельных тел — 0,070357 м.
Это максимумы на выбранных эпохах, не непрерывная оценка глобальной ошибки.

Независимый RK45 AU/year+EMB, scalarRustEIH/vectorJ2, три уровня
(1e-13,1800с)/(3e-14,900с)/(3e-14,450с), atol1e-17. На обоих сетках:

- regular: RHS [8648, 17288, 34562]; last all≤0.0214511311м/
  2.75476502e-09м/с, relative velocity≤8.01937872e-11м/с.
- shifted: RHS [8648, 17288, 34562]; last all≤0.0214511311м/
  2.75476502e-09м/с, relative velocity≤8.386984e-11м/с.

Рост RHS подтверждён в каждом опыте, оба ограничения шага активны.
Initial roundtrip/scalar-vs-matrix physicalC/test-onlyC/10 прошли старые
пороги. В траекториях используется физический C. Последняя разность
reference — чувствительность, не строгая граница; методы ниже неё не ранжируются.

| Правка | Максимум Moon−Earth за3суток, м | За30суток на двух сетках, м |
|---|---:|---:|
| sun_mass | 6.15104386e-05 | 0.00147009113 |
| earth_position | 9.15528438e-05 | 0.00109721242 |
| moon_velocity | 9.43722808e-05 | 0.00346185672 |

Разные горизонты и сетки: это рост измеренной ошибки с длительностью,
а не before/after улучшение интегратора. Параметры по результатам не выбирались.

Общие endpoints 201 против 200, максимум среди трёх стартов:

- legacy_python: all≤0.0234376589м, Moon−Earth≤0.00336407267м.
- legacy_rust: all≤0.0109183017м, Moon−Earth≤0.00336739143м.
- continuous_rust: all≤0.00781655207м, Moon−Earth≤3.41711051e-05м.
- reference: all≤0м, Moon−Earth≤0м.

Для всех этих сравнений сохранены и скоростные остатки; endpoints прошли
предобъявленные кандидатные/reference пороги. Сравнение не интерполирует
разные эпохи и не подменяет полный reference новой сетки.
Нулевая разность reference в общих endpoints ожидаема: t_eval не задаёт
внутренние шаги RK45. Это тот же ход интегрирования, а не нулевая
неопределённость. Она оценивается отдельным уточнением max_step выше.

Стоимость: медиана трёх чередующихся запусков всей траектории с созданием
расчёта и снимками. До них отдельный повтор/прогрев; reference, диагностика,
SHA и запись отчёта исключены из кандидатного timing. Данные этого компьютера:

| Сетка | legacyPython, с | legacyRust, с | continuousRust, с | reference, с/опыт |
|---|---:|---:|---:|---:|
| regular | 2.9240–3.0337 | 1.7379–1.8847 | 0.2258–0.2600 | 7.8623–8.2786 |
| shifted | 3.9607–5.0307 | 2.4099–2.7887 | 0.3292–0.3625 | 9.0328–13.1930 |

Три сырых timing каждого опыта в JSON, referencecost включает progress-cache IO.
Это не универсальный коэффициент ускорения и не основание менять GUI/default.
Сетки запускались последовательно, внешняя нагрузка/частота CPU не фиксировались.
Рост времени между сетками нельзя приписать одной смене выходных эпох.

При независимой проверке нового стенда до201 найден ложный отказ:
asdict(Settings) сохраняет tuple, а JSON декодирует list; прямое сравнение
ошибочно отклоняло бы одинаковый опыт. Воспроизведение, assert/traceback,
первый driver/тесты и первый regular200 сохранены в локальном аудите.
Исправлено только сравнение одинаковых JSON-представлений, без изменения
параметров. Новый regression принимает реальные Settings после roundtrip
и отвергает изменённые rtol/childSHA/массу/имя. Полный regular200b
повторён после правки: **все массивы bitexact с первым200**. Научных
порогов не ослабляли. Непрошедшее служебное сравнение не выдаётся за
ошибку движения тел или исправление runtime.

410 относящихся тестов прошли за 77,61 с;
13 новых тестовых случаев этого блока. Остальные покрывают унаследованные
силы, редактирование, storage/time/continuous и предыдущие стенды.
Полный проектный набор/Cargo/portable повторно не запускались: runtime,
Rust, зависимости и упаковка не менялись. ZIP155 прежний, новой сборки нет.

Проверены finite/shape/IC/masses/epochs, точные повторения всех кандидатов,
одинаковые packet endpoints, legacy-checkpoint continuation, parent/child,
фактические scalarDLL/native.pyd/SciPy и неизменность исходников/входов.
Итоговый локальный integrity202 дополнительно проверяет старые данные,
архив памятки, personal-doc exclusions, публичные ссылки и ZIP.

**Ограничения:** три конкретных опыта,30суток и две сетки; нет гарантии
всех сближений, произвольных масс или года. Noether21sourceintegrals
в этом Solar-стенде не интегрировались; fewbody-балансы не являются
проверкой E/P/J этих десяти тел. Нет новых приливов/вращения/GR-порядков.
Согласие численных решений не равно истинной физической точности.

Реализация и проверенные определения:
- [epoch_grid](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_month.py:26)
- [finite_states](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_month.py:34)
- [reference_gate](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_month.py:39)
- [candidate_metrics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_month.py:48)
- [endpoint_comparison](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_month.py:56)
- [check_same_experiment](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_month.py:61)
- [packet_check](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_month.py:70)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_month.py:79)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_month.py:254)
- [test_declared_grids_have_distinct_interiors_and_identical_endpoints](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_month.py:10)
- [test_identical_or_incomplete_rhs_refinement_cannot_qualify](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_month.py:22)
- [test_single_body_or_moon_relative_failure_cannot_be_hidden_by_averaging](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_month.py:29)
- [test_endpoint_comparison_uses_only_common_physical_epochs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_month.py:41)
- [test_actual_settings_compare_after_json_without_accepting_parameter_changes](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_month.py:50)
- [test_packet_guard_rejects_missing_duplicate_or_unordered_epochs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_month.py:76)
- [test_nonfinite_states_and_existing_receipts_are_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_month.py:81)

Следующий шаг: отдельный контракт на90суток с оценкой
роста ошибки и referencefloor, затем обоснованный выбор рабочего режима.
GPT-6.1 Sol High: нужна проверка conditioning и воспроизводимости,
новые силы и общие абстракции для этого не требуются.
