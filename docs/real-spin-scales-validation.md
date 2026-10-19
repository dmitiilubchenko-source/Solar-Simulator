# Реальные масштабы PN×Q и ведущего spin coupling: 254–259

17 октября 2026. [Протокол](real-spin-scales-protocol.md) записан до чисел;
[полный JSON](real-spin-scales-validation.json) содержит все результаты,
по-тельные нормы, 440 проверок, 10 наборов производных и SHA источников.
Рабочие силы, IC, Rust, runtime guard и настройки приложения не изменены.

Получена оценка амплитуд на заданном пути DE441, **не свободная траектория**.
На этом этапе нет нового сертификата точности орбит или вращения.
Малые члены дают миллиметровые–сантиметровые баллистические масштабы;
ньютоновское Q2 поле Луны существенно больше. Это обосновывает следующий
короткий свободный research-прогноз Q2, но не доказывает верхнюю границу
ошибки и не позволяет вычесть такие оценки из прежнего остатка JPL ≈726 м.

## Модель, данные и независимость

Солнце, 8 планет, Луна; прежние GM/G, SI/SSB/Ecliptic J2000,
JD 2461321.5 TDB, c=299792458 м/с, 440 выходов номинального года.
Существующий DE441 reader и его отдельная квалификация238 неизменны.
Для вычисления мгновенных расстояний позиции центрируются на Луне,
Earth=-rho из прямого Earth–Moon полинома; скорости остаются SSB.
Это численное центрирование снимка, а не движущаяся система интегратора.
R и Rdot заданы DE441 во всех эпохах, solid-equivalent I прежняя из51.

Две группы имеют разные договоры и **не складываются в сертифицированный
физический бюджет**:

- Harmonic point-EIH H1: D1(b)=M0⁻¹H1 b и Dfinite(b)=(M0+H1)⁻¹H1 b,
  b отдельно aPN, lunar Newton Q2, fixed Sun/Earth Q2. Это источники/различия
  усечений выбранной модели253, не полные физические 2PN/PN-multipole силы.
- Ведущий канонический HSO: первичный [Hartung–Steinhoff, Eq.66](https://arxiv.org/pdf/1011.1179v3),
  §IV(C), стр9; SI c восстановлено. Только спин Луны, условно p=m v,
  S=R I Rᵀ omega_DE. Физическая harmonic→ADM/SSC/triad/clock карта не
  сертифицирована. Omega не добавляется к уже глобальной DE441 Rdot.

H1 block50/70 проверен против отдельно существующей scalar response70,
с дополнительным сравнением50/70 до преобразования float. На входе одни
и те же float64 состояния/поля; Decimal улучшает арифметику оператора,
но не точность исходных ускорений или физических параметров.
Finite solve выполняется в float64 после mass conditioning; max condition
1.000000154344. Обе H1 формы учитывают собственную норму каждого тела.

SO сила, канонический velocity shift и Omega проверены complex-step
производными только малого HSO, без вычитания из большого orbital H.
Транспорт delta_v проверен независимыми центральными сдвигами x±hv,
S±h tauQ; ориентационный отклик Q — конечными поворотами runtime фигуры.
Аналитический test-spin circular предел, линейный/вращательный HSO balance
и отрицательные контроли входят в тесты. F/m отдельно не равно полному
SO ускорению: обязательна материальная производная velocity shift.
Добавка через tauQ — отдельная mixed-диагностика, не полный PN-закон тела.

## Численные проверки и стоимость

| Проверка, максимум по заявленной выборке | Результат | Порог |
| --- | ---: | ---: |
| H1 block/scalar по собственной норме тела после float | 0 | 5e-12 |
| Decimal50/70 до float | 8.663131e-45 | 1e-30 |
| Mass-conditioned solve residual | 4.705667e-16 | 5e-13 |
| SO force / velocity / Omega bridge | 6.2893e-15 / 1.2751e-15 / 1.3672e-15 | 5e-11 |
| SO linear / angular identity | 1.6277e-16 / 7.0770e-15 | 5e-12 |
| Material derivative, h=1 s | 2.855380e-8 | 1e-6 |
| Orientation derivative, h=1e-4 rad | 6.706806e-9 | 1e-6 |

Равенство float результатов H1 не означает бесконечной физической точности.
Отрицательные контроли без velocity term / source reaction дают максимумы
0.43143 / 0.499997 > 1e-3; малые эффекты не спрятаны нормой большого тела.
Все 440 эпох сохранены; для производных10 эпох/все уровни h, без отбора
и без требования монотонного улучшения на каждом float уровне.

Полный успешный расчёт257:19.366367 с. Предшествующий полный неуспех256:
15.391130 с; различие включает повышенную арифметику и нагрузку машины,
это не контролируемый benchmark. Нет интегрирования орбит в этих затратах.
164 связанных теста прошли за2.58 с, включая23 новых случая этого блока.
Full246:1819 Python/17 Rust/fmt — историческая проверка, сейчас не повторялась.

## Масштабы Moon−Earth

Для ускорения proxy=.5 T² max_sample|delta a|; для скорости proxy=T max|delta v|,
T — номинальный год. Это оценка с замороженным максимальным ускорением,
**не строгий error bound**, не propagated orbital response. Максимум взят
на440 снимках, а не по непрерывному времени. Нельзя складывать строки как
независимые ошибки: несколько строк — составные части одних величин.

| Канал | Max относительной амплитуды, SI | Баллистический proxy, м |
| --- | ---: | ---: |
| pn2_first | 9.407649628e-18 m/s2 | 0.00468445502 |
| pn2_finite | 9.407649208e-18 m/s2 | 0.00468445481 |
| moon_pnq_first | 1.474852546e-18 m/s2 | 0.000734389638 |
| moon_pnq_finite | 1.474852481e-18 m/s2 | 0.000734389606 |
| fixed_pnq_first | 5.926674097e-17 m/s2 | 0.0295113438 |
| fixed_pnq_finite | 5.926673841e-17 m/s2 | 0.0295113425 |
| moon_newton_q | 3.789559501e-11 m/s2 | 18869.7727 |
| so_force_over_mass | 1.002311679e-17 m/s2 | 0.00499092139 |
| so_transport | 5.854610653e-19 m/s2 | 0.000291525103 |
| so_q_torque_transport | 3.295060634e-22 m/s2 | 1.64074598e-07 |
| so_acceleration | 9.568376176e-18 m/s2 | 0.00476448737 |
| so_acceleration_with_q_torque | 9.568376192e-18 m/s2 | 0.00476448737 |
| so_orientation_q_delta_year | 2.095529989e-18 m/s2 | 0.00104345042 |
| so_velocity_shift | 4.881799673e-13 m/s | 1.54057881e-05 |

По каждому из10 тел max/RMS/initial/final/worst time также есть в JSON.
Max|Omega|=3.463168e-15 rad/s; maxrate×T=0.02254253 arcsec,
|trapezoid integral Omega|=0.01954062 arcsec. Max|deltaS|/|S|=1.300946e-9.
Это условные масштабы канонического спина на заданном пути; нельзя
объявлять их измеренной ошибкой ориентации или просто прибавлять к Rdot.

## Сохранённые неуспехи и причины

1. Preflight256: SIUnits отверг NumPy scalar массы; драйвер приводит его
   к Python float. Научный отчёт ещё не был создан; отдельная квитанция
   отказа записана вручную и не выдаётся за audit output.
2. Полный256 завершился complete=true/checks=false: Moon-PNQ H1 bridge
   7.180074e-11 > 5e-12. Decimal90 на эпохе273 выявил компенсацию внутренних
   Earth/Moon вкладов в Neptune response≈1.197104e-32 м/с². Ошибки двух
   float путей относительно одинаковых входов2.59034e-11 и4.59409e-11.
   longdouble на этой Windows имеет15 значащих цифр и проблему не решает.
   Исправлена только арифметика H1 response; прежний порог не ослаблен.
   Протокол уточнён отдельным разделом257 после сохранённого FAIL.
3. Первый тест Decimal block обнаружил перезапись диагонального вклада
   пары при следующей итерации. Исправлено накопление (=→+=), добавлен
   тест перестановки тел. Неуспех1failed/21passed и исходник сохранены;
   ни один полный440 расчёт не запускался с этой ошибкой.
4. Первый offline helper передал reader output без .json, но затем
   ожидал .json; reader прошёл, scales не стартовал. Неуспех/копия/helper
   сохранены. Исправлен путь только локального helper, повтор из новой
   чистой копии прошёл. Командная опечатка -m .tools отклонена ещё до helper.

До/после исправления H1:13 из19 массивов bitexact, изменены только6
H1-derived полей. Moon-PNQ max absolute change≤7.734e-34 м/с²;
исходные параметры/силы/ориентации не менялись. Сравнение и SHA всех
старых executed sources/первого протокола/JSON/NPZ хранятся в квитанции.
Числа сравнения характеризуют округление расчёта, не физическое улучшение.

## Воспроизведение без сети

Отдельная publiccopy с пробелами в пути, без старой .tools и личных docs;
socket.connect/create_connection запрещены. Reader заново квалифицирован,
затем440scales: все19 decoded NPZ arrays и научные поля JSON совпали точно.
Child24.295195 с. Установленные Python/NumPy/SciPy те же; это проверка
независимости от локальных результатов/сети, не сертификация новой среды.

Из корня public checkout с зависимостями, для свежих output:

```powershell
python -X utf8 -B -m scripts.assess_de441_reader --output .tools/real-scales-reader.json
python -X utf8 -B -m scripts.assess_real_spin_scales --output .tools/real-scales-replay --reader-receipt .tools/real-scales-reader.json
python -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_real_spin_scales.py
```

Повтор не перезаписывает существующий output. Публичные архивы уже содержат
нужные JPL/DE441 данные. Новый primary PDF сохранён отдельно локально;
это provenance формулы, не зависимость исполнения, JPL не скачивался заново.

## Следующий шаг и границы решения

Текущие оценки не дают основания считать полную PN-I/SSC теорию обязательным
блокером первой орбитальной версии1км. Это **техническое решение о порядке
работ**, а не доказательство, что все такие эффекты заведомо меньше1км.
Наибольший из исследованных source scales — Newton lunar Q2; ранее его
поле на prescribed R уменьшало local defect, но ещё не давало прогноза.

Следующий260: заранее объявить короткий (ориентир32суток) свободный
исследовательский прогноз10тел с EIH и Newton solid-Moon Q2, начальными
q/S из одного состояния и той же I. После t0 не брать R(t) из DE441.
Проверить relative Earth–Moon control, независимый reference/refinement,
полные E/P/J с источниками данного усечения и внешний JPL holdout.
Сначала проверить стоимость/устойчивость короткого опыта; не обещать год.
Runtime guard сохранять до самостоятельной квалификации модели.
Приливы,3D, новая подгонка IC/GM и публикация не входят в этот блок.

Прежние Noether219–222 visibility FAIL, annual Noether false, physical
lunar mapping false и ограничения покрытия рабочего strict профиля
сохраняются. Кольцо Койпера экспериментальное:420 geometry FAIL;
528 прошло заданные проверки, но отдельные KBO residuals выросли.

## Проверенные определения

- [real_spin_scales.mixed_responses](C:/Users/Admin/Desktop/Solar-simulator/scripts/real_spin_scales.py:10)
- [real_spin_scales.relative](C:/Users/Admin/Desktop/Solar-simulator/scripts/real_spin_scales.py:41)
- [real_spin_scales.vector_relative](C:/Users/Admin/Desktop/Solar-simulator/scripts/real_spin_scales.py:53)
- [real_spin_scales.spin_orbit](C:/Users/Admin/Desktop/Solar-simulator/scripts/real_spin_scales.py:62)
- [real_spin_scales.spin_identities](C:/Users/Admin/Desktop/Solar-simulator/scripts/real_spin_scales.py:108)
- [real_spin_scales.hat](C:/Users/Admin/Desktop/Solar-simulator/scripts/real_spin_scales.py:122)
- [independent_real_spin.hamiltonian](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_real_spin.py:5)
- [independent_real_spin.derivatives](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_real_spin.py:17)
- [decimal_real_response.converted](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_real_response.py:13)
- [decimal_real_response.block_responses](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_real_response.py:18)
- [decimal_real_response.scalar_responses](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_real_response.py:50)
- [decimal_real_response.agreement](C:/Users/Admin/Desktop/Solar-simulator/scripts/decimal_real_response.py:58)
- [assess_real_spin_scales.statistics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_real_spin_scales.py:40)
- [assess_real_spin_scales.field_statistics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_real_spin_scales.py:56)
- [assess_real_spin_scales.snapshot](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_real_spin_scales.py:63)
- [assess_real_spin_scales.local_derivative_checks](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_real_spin_scales.py:97)
- [assess_real_spin_scales.qualification](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_real_spin_scales.py:121)
- [assess_real_spin_scales.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_real_spin_scales.py:148)
- [assess_real_spin_scales.main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_real_spin_scales.py:227)
- [test_real_spin_scales.geometry](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:16)
- [test_real_spin_scales.test_circular_test_spin_has_known_leading_de_sitter_rate_and_angle](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:21)
- [test_real_spin_scales.test_isolated_spin_terms_match_scalar_hamiltonian_and_full_angular_identity](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:33)
- [test_real_spin_scales.test_zero_spin_keeps_precession_rate_but_exact_zero_orbital_reaction](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:44)
- [test_real_spin_scales.test_spin_rate_transport_is_the_velocity_operator_applied_to_spin_rate](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:52)
- [test_real_spin_scales.test_mass_conditioning_matches_naive_finite_matrix_on_small_known_system](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:59)
- [test_real_spin_scales.test_distant_internal_pair_cancellation_has_analytic_nonzero_response](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:74)
- [test_real_spin_scales.test_response_is_invariant_under_body_permutation](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:90)
- [test_real_spin_scales.test_small_body_error_is_not_hidden_by_large_body_or_epsilon](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:99)
- [test_real_spin_scales.test_statistics_use_explicit_velocity_units_and_label_proxy_as_unqualified](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:107)
- [test_real_spin_scales.test_incomplete_evidence_does_not_qualify_even_with_true_flags](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:117)
- [test_real_spin_scales.test_existing_failed_audit_is_preserved_before_reader_load](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:145)
- [test_real_spin_scales.test_spin_diagnostic_rejects_unsupported_input](C:/Users/Admin/Desktop/Solar-simulator/tests/test_real_spin_scales.py:155)
