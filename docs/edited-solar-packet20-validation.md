# Год edited Solar с настоящими пакетами 20 ч

Этапы 210–213. Отчёт сформирован: 2026-10-16T15:54:08+03:00.
[Заранее заданный протокол](edited-solar-packet20-protocol.md),
[все измерения и SHA](edited-solar-packet20-validation.json),
[паспорт профиля](solar-working-profile.md).

Кандидатные критерии прошли **9/9** сочетаний. Общая область: **PASSED**.
GUI target/strict Rust: **True**; continuous CLI/strict Rust: **True**.
Это статусы трёх конкретных edited-стартов, не стандартного или исходного nominal-профиля.

Первый запуск оборвался при выключении ПК на reference-фазе, до кандидатов.
Его JSON/NPZ/log и кеши сохранены с SHA. Полный job выполнен заново в новом пути
тем же frozen-кодом: два завершённых трёхуровневых reference и два уровня третьего
побитно совпали с новым расчётом. Незавершённое состояние RK45 не загружалось;
старые частичные данные не подменяли новую квалификацию. Полная цена прерванного
третьего reference неизвестна; времена нового job и прежние завершённые замеры раздельны.

Физика, исходные данные, допуски и три изменения прежние: Sun.mass×1.25;
Earth.position+(1e6,−2e6,3e6) м; Moon.velocity+(100,−50,25) м/с.
Десять тел, EIH 1PN + fixed Sun/Earth J2, G и фигуры прежние, SI,
исходные инерциальные оси и скорости SSB/Ecliptic J2000 без recentering.
Child.time=0/origin=None; родитель JD 2461321.5 TDB/DE441 — происхождение.
Внешние GM — системные барицентры, новые спутники не добавлялись.
DOP853/per-body/relative Earth–Moon, rtol=3e-14, xatol=1e-3 м, vatol=1e-9 м/с.
Год: 31557600 с; 440 состояний, 438 полных пакетов по 72000 с и последний 21600 с.
Промежуточные запросы через 6 ч не сокращали эти пакеты.

| Правка / режим | Moon−Earth, прежние 6 ч, м | Настоящие 20 ч, м | Статус 20 ч |
|---|---:|---:|---|
| sun_mass / legacy_python | 0.0413223835 | 0.0256568501 | True |
| sun_mass / legacy_rust | 0.036601654 | 0.0211529431 | True |
| sun_mass / continuous_rust | 0.00171912346 | 0.0887936074 | True |
| earth_position / legacy_python | 0.00556871646 | 0.049774831 | True |
| earth_position / legacy_rust | 0.0368171281 | 0.0708331569 | True |
| earth_position / continuous_rust | 0.000278604226 | 0.0315528083 | True |
| moon_velocity / legacy_python | 0.0394502328 | 0.0197123082 | True |
| moon_velocity / legacy_rust | 0.0811499155 | 0.0174966048 | True |
| moon_velocity / continuous_rust | 0.000647737594 | 0.0560199982 | True |

Измеренная чувствительность к пакетам, пример Sun.mass / continuous Rust:
Moon−Earth 0.00171912346 → 0.0887936074 м;
RHS 17618 → 10862.
Силы и допуски прежние. [Граница DOP853](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/continuous.py:147)
и [обновление t_bound](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/continuous.py:152)
меняют историю адаптивных шагов. Вклад усечения и округления отдельно не измерялся;
меньшее число вычислений силы оценивается вместе с фактической глобальной ошибкой.

Максимум среди отдельных тел: 0.270395988 м; Moon−Earth: 0.0887936074 м.
Пороги по каждому телу <10 м/<1e-4 м/с; по паре <.1 м/<1e-5 м/с.
Скорости, по-тельные остатки и все неуспехи сохранены в JSON.

Reference вычислен заново во всех 440 эпохах: независимые scalar Rust EIH и vector J2,
AU/year, EMB+Moon−Earth, RK45. Три уровня прежние: (1e-13,1800 с),
(3e-14,900 с), (3e-14,450 с), atol=1e-17; физический c в интегрировании.
Все три reference квалифицированы прежде кандидатов.

| Правка | RHS по уровням | Последняя разность: все тела, м | Moon−Earth, м |
|---|---|---:|---:|
| sun_mass | [105194, 210392, 420776] | 0.0732878871 | 0.000850452401 |
| earth_position | [105194, 210392, 420776] | 0.0918057265 | 0.000833263928 |
| moon_velocity | [105194, 210392, 420776] | 0.0869257201 | 0.000745579695 |

Reference пороги: 1 м/1e-6 м/с по всем и .01 м/1e-7 м/с по паре.
Активное уточнение не доказывает строгую границу ошибки. Последние разности —
чувствительность; ниже неё варианты не ранжируются. Немонотонные уточнения:

По максимальной позиции всех тел роста не обнаружено; это само по себе не доказательство порядка сходимости.

| Правка / режим | Медиана прежних 6 ч, с | Медиана 20 ч, с |
|---|---:|---:|
| sun_mass / legacy_python | 85.1815 | 13.1105 |
| sun_mass / legacy_rust | 50.7553 | 7.61438 |
| sun_mass / continuous_rust | 6.12489 | 1.67541 |
| earth_position / legacy_python | 78.9892 | 12.7567 |
| earth_position / legacy_rust | 51.6924 | 7.39279 |
| earth_position / continuous_rust | 6.7284 | 1.61514 |
| moon_velocity / legacy_python | 93.2086 | 12.7551 |
| moon_velocity / legacy_rust | 53.0574 | 7.46396 |
| moon_velocity / continuous_rust | 5.86945 | 1.5874 |

Медианы трёх чередующихся полных прогонов после отдельного повтора/прогрева.
Инициализация и снимки включены; SHA/диагностика/отчёт вне замера кандидата.
Reference включает промежуточный cache IO. Внешняя нагрузка/частота CPU не фиксированы:
таблица описывает локальные прогоны, не универсальный speedup. Legacy Rust и continuous Rust
используют native EIH/J2; различается организация интегрирования, не только язык.

Со старой 6h-сеткой сопоставлены ровно 148 общих эпох, включая оба конца года.
Ни ближайшие точки, ни интерполяция не использованы. Все разности по четырём режимам
(включая reference) сохранены как диагностика без нового подобранного порога.

Три реальных CLI процесса и три настоящих Tk Laboratory прошли год каждый.
CLI: 440 эпох/4400 строк тел, CSV и final.json побитно совпали с continuous Rust.
GUI: загрузка JSON через _load, batch=20, _start_target, настоящие ThreadPool futures,
_poll/_record/_draw и остановка у годовой цели; все 440 состояний и final.json
побитно совпали с legacy Rust. Сравнение по uint64-представлению float64.
Окно скрыто, _poll вызывается вручную; выбор файла задан тестом, модальная ошибка
превращается в исключение. Формулы/силы не подменялись. Это не измерение отзывчивости
видимого GUI, ввода мышью, ordinary playback или тайминга настоящего mainloop.
Аналитический тест отдельно прогоняет неподвижное одиночное тело через весь год.
CLI сохраняет experimental=True, automatically_scientifically_qualified=False,
controller_buffers_saved=False. После загрузки final.json контроллер continuous новый.

| Опыт | CLI, с | Tk worker, с | CSV и GUI состояния побитно точны |
|---|---:|---:|---|
| sun_mass | 2.31678 | 10.011 | True |
| earth_position | 2.23357 | 9.90014 | True |
| moon_velocity | 2.25897 | 9.84886 | True |

CLI и GUI времена включают IO/инициализацию/диагностику. GUI обновляет графические объекты
и ставит draw_idle в очередь; фактическая перерисовка mainloop здесь не измерена.
их нельзя сравнивать как чистое время интегратора. Полные outputs/logs/SHA сохранены локально.

Для повторения из корня исходного проекта, в новых путях:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_edited_solar_packet20 --output .tools/NEW_PACKET20/run
.venv/Scripts/python.exe -X utf8 -B -m scripts.verify_edited_solar_packets audit --packet-receipt .tools/NEW_PACKET20/run.json --six-receipt .tools/edited_solar206/year206.json --output .tools/NEW_PACKET20/io
```

Для нового окружения старый 6h receipt следует пересчитать по прежнему годовому протоколу;
чужой бинарник/изменённый источник отклоняются SHA-проверками. Нового portable verification bundle нет.

467 относящихся тестов прошли за 57.61 с, из них 16 новых случаев.
Full/Cargo/portable не повторялись: runtime/Rust/упаковка прежние. Старый ZIP сохранён.
Нет нового JPL для editedIC, полного Noether21 баланса десяти тел, гарантии сближений
или непрерывной точности между снимками. Nominal/standard и произвольный batch отдельно не проверены.
Численное согласие не равно истинной физической точности. GitHub/коммит/новая сборка не выполнялись.

Проверенные определения:

- [epoch_grid](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_packet20.py:14)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_packet20.py:18)
- [check_packet_boundaries](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_edited_solar_packets.py:24)
- [shared_indices](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_edited_solar_packets.py:30)
- [verified_input](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_edited_solar_packets.py:39)
- [gui_worker](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_edited_solar_packets.py:54)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_edited_solar_packets.py:123)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_edited_solar_packets.py:232)
- [test_actual_packet_grid_has_438_twenty_hour_packets_then_six_hours](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_packet20.py:8)
- [test_packet_grid_uses_exact_shared_epochs_without_nearest_time_matching](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_packet20.py:16)
- [completed_packets](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_packets.py:15)
- [test_full_twenty_hour_packets_are_accepted_with_short_final_packet](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_packets.py:19)
- [test_unfinished_or_miscounted_packet_run_cannot_pass](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_packets.py:24)
- [test_output_truncation_and_missing_terminal_packet_are_detected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_packets.py:30)
- [test_shared_comparison_retains_exact_epochs_and_both_endpoints](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_packets.py:37)
- [test_changed_time_cannot_be_replaced_with_a_nearby_epoch](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_packets.py:45)
- [test_existing_operational_evidence_is_preserved_before_input_reads](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_packets.py:55)
- [test_incomplete_or_changed_receipt_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_packets.py:68)
- [test_real_gui_year_packets_preserve_an_analytically_stationary_body](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_packets.py:84)
