# Свободный лунный ротор с EIH: 260–265

17 октября2026. [Протокол](free-lunar-rotation-protocol.md) записан до
результатов; [полный JSON](free-lunar-rotation-validation.json) содержит
все5 расчётов, по-тельные ошибки, бюджеты, затраты и SHA.
Численные критерии короткого исследовательского опыта прошли.
Это не включение новой физики в приложение и не квалификация года.

## Что проверено

10 тел,32 суток,129 выходов через6 часов. Прежние орбитальные IC,
GM/I, SI/SSB/Ecliptic J2000/JD2461321.5 TDB. Moon q/S только из одного
начального профиля51; после t0 в RHS нет заданных R/Rdot DE441.
Орбиты: взаимные point Newton+order-reduced EIH1PN и прежние fixed
Sun/Earth J2 с реакциями. Луна: Newton solid-equivalent rigid Q2,
согласованные инерция/сила/обратный момент. Нет figure–figure, PN-I/SO,
clock/triad/SSC карты, ядра/мантии, деформаций и приливов.

Использован прежний [вывод Newton rotor](conservative-rotation.md) и
[harmonic EIH/rotor](hybrid-rotation-protocol.md), первичный
[Vines action, стр3](https://fiteoweb.unige.ch/~maggiore/GWVol1/EIHLagrangian.pdf).
Кеш Vines сверён с SHA b46e92e61735189459b1732cc29a1330c6480ab1bb2dd13630cebed2de4c4c2f.
Это выбранное приближение, не полные PN уравнения протяжённой Луны.

Численные переменные: SSB с линейным EMB+rho для Earth/Moon;
M0=Sun mass,L0=AU,T0=sqrt(L0³/(GM0)), spin нормирован начальным |S|.
Скорости в EIH остаются SSB. Локальное центрирование Q геометрии на Луне
с прямой rho не является boost или moving-frame физикой.

Production DOP853 контролирует худший блок каждого x/v, прямые rho/vrel,
q/S и3 бюджета. Независимый RK45 использует raw R/body-Euler Pi,
scalar-target EIH, body-inertia Q force и fixed tensor field; в его RHS
нет runtime quaternion или Newton figure force. Его PN коэффициент
выделен формальным c=1 и затем разделён на реальный c²: это арифметика
коэффициента, не интегрирование физики со скоростью света1.
Конверсия начального q→R общая, дальнейшие представления разные.
Дополнительная проверка входов: max initial body position gap к reader
.9842мм, direct Earth–Moon5.300мкм; difference strict orbit vs one-epoch
spin profile pair12.430мкм. Ни орбита, ни spin не подгонялись/не сбрасывались.

## Численная сходимость

Номинальный DOP rtol1e-12/maxstep3600s/xatol1e-3m/vatol1e-9m/s;
строгий3e-14/1800s/1e-4m/1e-10m/s. q/Sscaled atol1e-13/1e-14.
RK45 два уровня с такими же rtol/SI atols, maxstep1800/900s.
Нет проекции raw q или R в процессе интегрирования.

| Сравнение | Max allbody, м | Max Earth–Moon, м | Max v, м/с | R Frobenius | S / начальная норма S |
| --- | ---: | ---: | ---: | ---: | ---: |
| production_refinement | 0.00781633704 | 2.11580522e-05 | 3.590846e-10 | 3.642353e-15 | 1.443598e-15 |
| reference_refinement | 0.00980521833 | 4.96117614e-05 | 2.761286e-10 | 1.496175e-14 | 3.664830e-15 |
| independent | 0.00980521833 | 1.74581695e-05 | 2.870216e-10 | 2.043965e-14 | 5.109370e-15 |

Пороги заранее зафиксированы в протоколе. Чувствительность самого
эталона показана отдельно; малое различие двух программ не строгая
верхняя граница истинной ошибки. Ошибки каждого тела сохранены в JSON.

## Энергия, импульс и угловой момент

Читаются E_EIH+Trot+Ufixed+UMoon, P_EIH и J_EIH+S.
У OR сумма имеет источники PN² и PN×Q. Фиксированные Sun/Earth оси
также дают внешний torque: он вынесен в третий бюджет полного J.
Moon orbital torque уже сокращается с Sdot и повторно не добавляется.
Статические fixed поля не дают внешней работы в E.

Глобальные totals читаются Decimal70; начальная строка вычитается ДО
преобразования к float. На9 эпохах каждого расчёта сверены70/90цифр.
Успешный readout не означает повышение точности float интегратора.
Масштабы фиксированы при старте: энергия |E0|, импульс sum m|v0|,
угловой момент |J0|. Векторные P/J строки показывают евклидову норму;
это безразмерные относительные изменения, не метры ошибки орбиты.

| Расчёт | Corrected E | Corrected P | Corrected J | Raw rotation defect | Время, с | RHS calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| nominal | 2.138494e-15 | 6.065719e-16 | 1.220380e-15 | 1.776357e-15 | 35.137429 | 9617 |
| tight | 3.694695e-15 | 2.018491e-15 | 1.744247e-15 | 7.771561e-16 | 69.764487 | 18833 |
| reference_nominal | 3.688380e-15 | 1.992049e-15 | 1.744063e-15 | 1.274753e-14 | 82.269247 | 9224 |
| reference_tight | 5.774069e-15 | 2.512201e-15 | 3.022618e-15 | 4.599050e-15 | 176.994082 | 18434 |
| baseline | 2.132568e-15 | 6.121888e-16 | 1.219791e-15 | 1.332268e-15 | 35.360863 | 9617 |

Предел corrected scaled E/P/J1e-11 и raw q/R дефекта1e-8 соблюдён.
Raw drift, три источника и все precision rows есть в JSON. Некоторые
глобальные дрейфы выросли при ужесточении допуска; эти результаты
сохранены. На уровне округления меньший rtol не гарантирует улучшения.
Малые PN источники ниже глобального численного дрейфа: отдельная их
наблюдаемость не доказана. Noether visibility FAIL219–222 сохраняется.
H1 бюджеты здесь float64, Decimal используется для totals; это не новая
квалификация own-body tiny responses из254–259 и не отмена их ограничений.

## Сравнение с DE441 после свободных расчётов

Только после завершения5 integrations загружены будущие DE441 состояния
и ориентации. Читатель ранее проверен на440 Horizons snapshots, полиномных
стыках и Decimal;129 новых выходов сверяются с reader, не с новой API
выгрузкой Horizons. JPL/DE441 не перескачивались, параметров по holdout
не подбирали. Это сравнение разных физических моделей/данных, не чистая
численная ошибка и не физическая неопределённость параметров.

Baseline — point EIH+fixed без Moon Q. Baseline и nominal free имеют
одинаковые численные настройки. Tight free приведён для чувствительности;
отдельного baseline RK45 в этом протоколе нет. Ни один результат не скрыт.

| Тело | Baseline max, м | Nominal free max, м | Tight free max, м | Tight−baseline, м |
| --- | ---: | ---: | ---: | ---: |
| Sun | 1.72826295 | 1.72826295 | 1.72826362 | +6.6766804e-07 |
| Mercury | 2.18695804 | 2.18695804 | 2.18719196 | +0.000233916973 |
| Venus | 2.37910987 | 2.37909628 | 2.37889245 | -0.000217426149 |
| Earth | 2.82252611 | 2.5738605 | 2.57400613 | -0.248519971 |
| Moon | 52.0394485 | 2.57452459 | 2.57466518 | -49.4647833 |
| Mars | 9.17572677 | 9.17572677 | 9.17530898 | -0.000417790597 |
| Jupiter | 1.78533367 | 1.78533367 | 1.78598716 | +0.000653490763 |
| Saturn | 0.25842139 | 0.25842139 | 0.256728016 | -0.00169337371 |
| Uranus | 0.133377692 | 0.133377692 | 0.141137955 | +0.00776026315 |
| Neptune | 0.490983836 | 0.490983836 | 0.488990752 | -0.00199308366 |

| Earth–Moon | Max, м | RMS, м | Ориентация max, rad | Цель10км/1км на снимках |
| --- | ---: | ---: | ---: | --- |
| baseline | 53.3398899 | 36.7744055 | 0.00072662766 | True |
| nominal | 0.0456138174 | 0.0282013822 | 7.41419868e-06 | True |
| tight | 0.0456273126 | 0.0282097236 | 7.41419868e-06 | True |

Baseline rotor без Q — torque-free диагностическое состояние; его R
не физический прогноз Луны. Ориентационный остаток свободной модели
не сертифицируется заданной точностью: mean-solid модель не DE441 mantle/core.
Основной Moon−Earth максимум уменьшился53.33989м→.04562731м;
nominal free .04561382м при тех же настройках, что baseline. Эта разность
намного больше измеренной численной чувствительности. Однако изменение
Uranus tight−baseline≈+7.76мм сопоставимо с production refinement≈7.82мм:
его нельзя приписывать ухудшению физической модели. Внешние таблицы не
являются измерением неопределённости реальных наблюдений/параметров.
Рабочий прежний годовой остаток≈726м относится к другому интервалу/модели;
с этими32сутками его нельзя напрямую сравнивать как «до/после».

## Проверки, стоимость и воспроизводимость

Суточный preflight: pair production/reference3.308128e-7м,
allbody.003554741м;1.542559с DOP/5.419732с RK45. Initial independent
Q force5.234500e-12, torque8.526707e-13 relative; контроли без реакции
и torque≈.5/1. Первые12tests прошли; после усиления inventory guard13passed.
RHS после preflight не менялся; old driver/tests сохранены отдельно.
Новых непройденных научных критериев этого блока нет; ухудшения отдельных
метрик при уточнении/смене модели видны в таблицах и JSON.

248 связанных тестов прошли за28.88с, включая13 новых. Проверены circular
Kepler limit без Q, отдельная реакция/body Euler, запрет будущей ориентации,
Decimal readout, pair visibility, domain/fresh-output/inventory guards и
существующие rotation/relative coordinates/error control проверки.
Full2461819Python/17Rust/fmt — исторический, сейчас не повторялся.
Тесты и force jobs частично шли одновременно; wall times не benchmark.
Времена в таблице относятся к интегрированиям, без отдельного Decimal
postprocessing и записи отчёта; сумма интегрирований399.526108с.

Отдельная publiccopy с пробелами в пути, без старой .tools/личных docs,
с запрещёнными socket.connect/create_connection: reader квалифицирован
заново,5 jobs повторены; все научные показатели и10 decoded NPZ arrays
совпали точно. Те же установленные Python/NumPy/SciPy, не новая среда.
Стоимость полного повторения сохранена в JSON; сохранены все5NPZ и SHA.

Из корня публичного checkout с установленными зависимостями:

```powershell
python -X utf8 -B -m scripts.assess_de441_reader --output .tools/free-reader.json
python -X utf8 -B -m scripts.assess_free_lunar_rotation --output .tools/free-replay --reader-receipt .tools/free-reader.json
python -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_free_lunar_rotation.py
```

Output должен быть свежим; старый неуспех не перезаписывается.

## Решение и следующий шаг

Получен проверенный короткий свободный исследовательский прогноз,
без подстановки будущей ориентации. Рабочие runtime/IC/силы/Rust/default
и EIH+dynamic-spin guard прежние. Это не годовая квалификация и не
доказательство полноты физики Луны, истинной точности или arbitrary IC.

Следующий266 — заранее объявить96суток на нескольких лунных циклах:
проверить рост свободных либраций/остатков, чувствительность эталона,
модельные бюджеты и стоимость до решения о годовом опыте. Не подбирать
I/GM/q/S по будущему JPL. Не включать новые приливы/3D или runtime-комбинацию
по одному короткому успеху. Kuiper420 FAIL/528checks passed с выросшими
остатками KBO и остальные прежние ограничения не менялись.

## Проверенные определения

- [free_lunar_rotation.Model](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:23)
- [free_lunar_rotation.Model.__post_init__](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:33)
- [free_lunar_rotation.Model.source](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:47)
- [free_lunar_rotation.Model.masses](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:50)
- [free_lunar_rotation.Model.moments](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:53)
- [free_lunar_rotation.Model.spin_scale](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:56)
- [free_lunar_rotation.Model.c](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:59)
- [free_lunar_rotation.initial](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:62)
- [free_lunar_rotation.unpack](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:82)
- [free_lunar_rotation.geometry](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:90)
- [free_lunar_rotation.fields](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:103)
- [free_lunar_rotation.rhs](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:121)
- [free_lunar_rotation.FreeDOP853](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:129)
- [free_lunar_rotation.FreeDOP853.__init__](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:130)
- [free_lunar_rotation.tolerances](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:143)
- [free_lunar_rotation.integrate](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_rotation.py:151)
- [independent_free_lunar.initial](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_free_lunar.py:13)
- [independent_free_lunar.rhs](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_free_lunar.py:19)
- [independent_free_lunar.BlockRK45](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_free_lunar.py:48)
- [independent_free_lunar.BlockRK45._estimate_error_norm](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_free_lunar.py:49)
- [independent_free_lunar.BlockRK45.__init__](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_free_lunar.py:53)
- [independent_free_lunar.integrate](C:/Users/Admin/Desktop/Solar-simulator/scripts/independent_free_lunar.py:63)
- [free_lunar_diagnostics.readout](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_diagnostics.py:11)
- [free_lunar_diagnostics.scales](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_diagnostics.py:43)
- [free_lunar_diagnostics.norms](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_diagnostics.py:54)
- [free_lunar_diagnostics.balances](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_diagnostics.py:59)
- [free_lunar_diagnostics.decoded](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_diagnostics.py:82)
- [free_lunar_diagnostics.comparison](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_diagnostics.py:98)
- [free_lunar_diagnostics.within](C:/Users/Admin/Desktop/Solar-simulator/scripts/free_lunar_diagnostics.py:112)
- [assess_free_lunar_rotation.initial_bridge](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_rotation.py:28)
- [assess_free_lunar_rotation.external_metrics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_rotation.py:47)
- [assess_free_lunar_rotation.qualification](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_rotation.py:63)
- [assess_free_lunar_rotation.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_rotation.py:88)
- [assess_free_lunar_rotation.run.save](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_rotation.py:117)
- [assess_free_lunar_rotation.main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_rotation.py:152)
- [test_free_lunar_rotation.model_pair](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:16)
- [test_free_lunar_rotation.test_free_rhs_agrees_with_independent_body_euler_and_field_reaction](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:26)
- [test_free_lunar_rotation.test_initial_encoded_pair_matches_physical_roundtrip](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:37)
- [test_free_lunar_rotation.test_no_lunar_q_baseline_has_analytic_circular_kepler_limit](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:44)
- [test_free_lunar_rotation.test_rhs_never_reads_future_attitude](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:52)
- [test_free_lunar_rotation.test_rhs_never_reads_future_attitude.forbidden](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:54)
- [test_free_lunar_rotation.test_decimal_readout_agrees_across_precision_and_rotor_representations](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:62)
- [test_free_lunar_rotation.test_both_rhs_reject_unsupported_geometry](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:72)
- [test_free_lunar_rotation.test_pair_only_error_is_visible_in_comparison_and_bad_metrics_fail](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:83)
- [test_free_lunar_rotation.test_fresh_output_guard_preserves_failed_receipt](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:92)
- [test_free_lunar_rotation.test_model_rejects_wrong_pair_mass_fraction](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:99)
- [test_free_lunar_rotation.test_true_flags_cannot_qualify_missing_body_or_balance_evidence](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_rotation.py:104)
