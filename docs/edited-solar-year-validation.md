# Изменённый Solar: юлианский год

Этапы 206–209 начаты 15 октября 2026. Отчёт сформирован: 2026-10-16T00:06:02+03:00.
[Протокол](edited-solar-year-protocol.md),
[полные измерения и SHA](edited-solar-year-validation.json),
[прежние 90 суток](edited-solar-quarter-validation.md),
[протокол настоящего CLI](edited-solar-cli-six-protocol.md).
Кандидатные критерии: **18/18 сочетаний прошли**. Итог для объявленной
области: **PASSED**.

Это численное воспроизведение заданной модели. Ошибки относительно реальной
Солнечной системы по этим контрфактическим опытам не измеряются.

Те же десять тел, EIH 1PN и заданные J2 Солнца и Земли; G, радиусы, оси и системные GM гигантов прежние.
Одна правка на старт: Sun.mass×1.25; Earth.position+(1e6,−2e6,3e6) м;
Moon.velocity+(100,−50,25) м/с. Child.time=0, origin=None; единицы SI, исходные
инерциальные оси и скорости SSB/EclipticJ2000, без recentering.
Родитель JD 2461321.5 TDB/DE441 означает происхождение. Нет новых спутников
и повторных масс; изменение массы Солнца не моделирует его внутреннюю структуру.
DOP853, контроль по телам и паре Земля–Луна; rtol=3e-14, xatol=1e-3 м, vatol=1e-9 м/с,
dt=3600 с, packet_steps=20 с ограничением по выходным эпохам. Runtime, GUI, схема, Rust и зависимости прежние.

Юлианский год: 365.25 суток = 31557600 с; regular — 1462 эпохи через 6 ч;
shifted — 1463 эпохи со сдвигом внутренних точек на 3 ч и концами 0/год. Пороги и сетки
объявлены заранее. Ни один неудобный результат не выбирался или исключался.

| Сетка / правка | Moon−Earth legacyPython, м | legacyRust, м | continuousRust, м | Последнее уточнение reference, м |
|---|---:|---:|---:|---:|
| regular / sun_mass | 0.0413223835 | 0.036601654 | 0.00171912346 | 0.000848563486 |
| regular / earth_position | 0.00556871646 | 0.0368171281 | 0.000278604226 | 0.000838119207 |
| regular / moon_velocity | 0.0394502328 | 0.0811499155 | 0.000647737594 | 0.000773261145 |
| shifted / sun_mass | 0.0267347499 | 0.00817241766 | 0.000603290732 | 0.000851305751 |
| shifted / earth_position | 0.0563430884 | 0.0367375724 | 0.000692281254 | 0.00085249639 |
| shifted / moon_velocity | 0.00355077226 | 0.0703436218 | 0.000246141301 | 0.000768871833 |

Максимум среди отдельных тел: 0.67514027 м/2.17258926e-07 м/с.
Критерии применены к каждому телу: <10 м/1e-4 м/с; Moon−Earth <.1 м/1e-5 м/с.
Остатки по каждому телу и скорости и статусы каждого режима сохранены в JSON.

Reference прежний: RK45/AU-year/EMB+Moon−Earth/scalarRustEIH/vectorJ2,
(rtol,max_step)=(1e-13,1800с)/(3e-14,900с)/(3e-14,450с), atol1e-17.
Сначала все три reference, затем кандидаты; физический C в интегрировании.

- regular: RHS[105194, 210392, 420776], lastall≤0.0927846111 м/6.41908336e-08 м/с.
- shifted: RHS[105194, 210392, 420776], lastall≤0.0927830942 м/6.4187081e-08 м/с.

Пороги reference:1 м/1e-6 м/с по всем и .01 м/1e-7 м/с для пары.
Восстановление начального состояния и сравнение скалярной и матричной сил проверены по прежним порогам.
Рост RHS подтверждает активное уточнение, не исключает float64 и не
доказывает строгую границу или асимптотический порядок. Последняя разность —
чувствительность; методы ниже неё не ранжируются. Немонотонные изменения:


| Режим | Cross-grid endpoint: все тела, м | Moon−Earth, м |
|---|---:|---:|
| legacy_python | 0.0615341359 | 0.0536965047 |
| legacy_rust | 0.0485916293 | 0.0253303356 |
| continuous_rust | 0.0254052927 | 0.00190150907 |
| reference | 0 | 0 |

Сохранены также скоростные критерии. Reference-endpoint0 ожидаем при
одном RKhistory: t_eval не задаёт шагов; это не нулевая неопределённость.

| Сетка | legacyPython, с | legacyRust, с | continuousRust, с | reference, с/опыт |
|---|---:|---:|---:|---:|
| regular | 78.9892–93.2086 | 50.7553–53.0574 | 5.8694–6.7284 | 236.5711–249.6009 |
| shifted | 119.5848–131.9729 | 72.5024–79.4784 | 8.9502–9.9664 | 156.3544–349.4489 |

Медианы трёх чередующихся полных замеров после отдельного повтора/прогрева.
Инициализация и снимки включены; диагностика, SHA и отчёт вне замера кандидата.
Reference включает запись промежуточного кеша. Все три времени каждого режима сохранены.
Внешняя нагрузка и частота CPU не фиксированы: цены локальные, не универсальный
speedup и не чистый эффект выходной сетки между последовательными jobs.
LegacyRust и continuousRust используют nativeEIH/J2: их разница не является
чистым эффектом языка. Организация интегрирования различается; качество
оценивается отдельными ошибками, а не меньшим временем выполнения.

Первые 90 суток годового расчёта сопоставлены с quarter203/204 по точному
пересечению эпох. Regular — 361 точка до 7776000 с; shifted — 361 точка до 7765200 с
(89.875 суток). Принудительная конечная эпоха квартала 7776000 с отсутствует на сдвинутой годовой сетке.
Интерполяция и сравнение индексов вместо времени не используются.

| Сетка / режим | Максимум Moon−Earth prefix-разности, м | Bitexact во всех трёх стартах |
|---|---:|---|
| regular / legacy_python | 0 | True |
| regular / legacy_rust | 0 | True |
| regular / continuous_rust | 0 | True |
| regular / reference | 0 | True |
| shifted / legacy_python | 0 | True |
| shifted / legacy_rust | 0 | True |
| shifted / continuous_rust | 0 | True |
| shifted / reference | 0 | True |

Применены прежние кандидатные/reference пороги и проверки всех тел/скоростей.
Bitexact не является обязательным критерием: t_bound способен изменить
последний внутренний шаг около90суток. NPZ аудита хранит точные индексы/эпохи,
источники траекторий закреплены SHA и не перезаписывались.

Проверен настоящий CLI в трёх отдельных процессах, каждый на год:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m solar_simulator.continuous_cli --input CHILD.json --target 31557600 --packet-steps 6 --output NEW_FOLDER
```

По 1461 пакету, 1462 эпохам и 14620 строкам тел
на каждый опыт. CSV проверены без сортировки: точные названия/массы/порядок/
единицы SI, пустая эпоха при origin=None, нулевая работа заданных фигур и конечность значений.
Все состояния CSV и final.json побитно совпали с годовым continuousRust regular.
Побитность проверяется по uint64-представлению float64, включая знак нуля.
Это IO/packetпроверка того же ядра, не новый независимый физический эталон.
Ненулевые ошибки относительно независимого RK45 остаются в таблице выше.
Проверенные CHILD.json создаёт verify_edited_solar_cli.py; в этом локальном
аудите они сохранены как .tools/edited_solar206/cli209/CASE-input.json.
NEW_FOLDER должен быть новым: существующие результаты CLI не перезаписывает.

CLI receipt сохраняет experimental=True, automatically_scientifically_qualified=False,
controller_buffers_saved=False. Загрузка final.json запускает новый контроллер;
точное продолжение скрытых буферов здесь не обещается. Время отдельного
CLIпроцесса с егоCSV/JSON/report (а не чистого solver):

- sun_mass: 7.34951 с, exit0, bitexact=True.
- earth_position: 7.03257 с, exit0, bitexact=True.
- moon_velocity: 6.83735 с, exit0, bitexact=True.

Операционная область: этот результат относится к явно выбранному packet_steps=6.
В app.py batch по умолчанию 20 при strict dt=3600 с даёт 72000 с / 20 ч; у continuous CLI
packet_steps по умолчанию также 20. Исследовательские выходы через 6 ч ограничивают пакет.
Проверка двух годовых сеток через 6 ч не сертифицирует пакеты по 20 ч и GUI с настройками по умолчанию.
[GUIbatch](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:62),
[GUIsubmit](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:424),
[длительностьadvance](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/experiment.py:142),
[границыпакета](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/time_control.py:31).

До траекторий первоначальный тест ошибочно предполагал, что все 362 эпохи
сдвинутого квартала присутствуют в годе. Он получил 7786800 с вместо 7776000 с:
searchsorted вернул следующий момент на3ч позже. Отказ воспроизведён,
исходные test/protocol/driver и traceback сохранены локально (SHA вJSON).
Исправлено сопоставление и уточнён протокол до вычислений: exactintersection,
361 общий момент для каждой сетки. Годовая сетка, силы и допуски не менялись.

450 относящихся тестов прошли за145.27с; новые случаи указаны вJSON.
Full/Cargo/portable не повторялись: runtime/Rust/упаковка прежние; ZIP155 сохранён.
Source/input/actualscalarDLL/native.pyd/SciPy/finite/shape/IC/masses/settings/
packetgrid/repeats/checkpoint/parent, старые файлы и личные документы
проверены локальным integrity209. Нового релиза или GitHub-публикации нет.

**Область:** три конкретных изменённых старта/год/две сетки и общие эпохи
первых90суток. Нет гарантии любых масс/сближений/времён между снимками.
Нет JPL-сравнения editedIC и интегрированных Noether21sources для десяти тел;
fewbody-балансы их не заменяют. Нет новых приливов/вращения/GRпорядков.
Численное согласие не равно истинной физической точности модели.
Локальные SHA включают пути/бинарники окружения; другойПК/сборка требует
переквалификации, это не новый переносимый verificationbundle.

Проверенные определения:

- [epoch_grid](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_year.py:13)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_year.py:21)
- [matching_indices](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_prefix.py:17)
- [reference_metrics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_prefix.py:28)
- [same_bits](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_prefix.py:34)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_prefix.py:40)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_prefix.py:132)
- [read_snapshots](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_edited_solar_cli.py:24)
- [check_bits](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_edited_solar_cli.py:49)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_edited_solar_cli.py:55)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/verify_edited_solar_cli.py:145)
- [test_julian_year_grids_have_exact_horizon_spacing_and_common_endpoints](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_year.py:9)
- [test_quarter_overlap_uses_exact_common_times_and_distinguishes_forced_endpoint](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_year.py:19)
- [test_undeclared_annual_grid_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_year.py:35)
- [test_regular_overlap_preserves_all_quarter_epochs_exactly](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_prefix.py:10)
- [test_shifted_overlap_omits_the_forced_endpoint_instead_of_using_searchsorted](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_prefix.py:16)
- [test_a_missing_or_changed_epoch_cannot_silently_change_the_comparison](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_prefix.py:27)
- [test_reference_gate_checks_lunar_relative_and_outer_body_errors_separately](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_prefix.py:37)
- [test_numeric_zero_equality_is_not_reported_as_bitwise_identity](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_prefix.py:48)
- [test_existing_prefix_evidence_is_preserved_before_loading_inputs](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_prefix.py:55)
- [write_rows](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_cli.py:10)
- [test_csv_reader_retains_exact_si_values_and_packet_order](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_cli.py:27)
- [test_cli_bit_guard_rejects_the_opposite_sign_of_zero](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_cli.py:35)
- [test_invalid_csv_cannot_qualify_a_trajectory](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_cli.py:43)
