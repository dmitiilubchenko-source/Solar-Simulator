# Свободный лунный ротор на96сутках:266–272

17 октября2026. [Протокол266](free-lunar-months-protocol.md) записан до
результатов; [полный JSON](free-lunar-months-validation.json) содержит
пять решений, все385эпох, диагностику по окнам, источники/данные SHA.
Численные критерии прежней модели260 на новом интервале прошли.

Moon−Earth max DE441:baseline182.36154м,
nominal free0.356235528м,
tight free0.356397547м.
Это результат385проверенныхвыходов96суток, не годовая точность и не
неопределённость реальных наблюдений/параметров. Рабочий режим прежний.

## Модель и независимость проверок

10тел/SI/SSB/EclipticJ2000/JD2461321.5TDB, прежние orbitIC/GM/I/q/S.
OR EIH1PN+fixed Sun/Earth J2+Newton solid-equivalent Moon Q2 с реакциями.
Начальная q/S толькоt0; будущие DE441R/Rdot не используются в RHS.
Для каждого96day расчёта интегрирование начато заново сt0, без restart
по32day траектории. Старые32day NPZ используются только в последующем
анализе префикса; их source/input/array SHA проверены до вычисления.

Физические уравнения/интеграторы/допуски не менялись относительно
[260–265](free-lunar-rotation-validation.md); добавлены только драйвер
длинного опыта и геометрическая диагностика. Первичные формулы/выводы
прежние из [договора260](free-lunar-rotation-protocol.md).
M0=Sun mass,L0=AU,T0=sqrt(L0³/(GM0)), S масштабирован начальной нормой.
EMB+rho — численные переменные, скорости в EIH остаются SSB.

DOP853:nominal1e-12/3600s/1e-3m/1e-9m/s/qS1e-13;
tight3e-14/1800s/1e-4m/1e-10m/s/qS1e-14.
RK45:два независимых уровня с rawR/bodyEulerPi/scalar EIH/body-frame
inertia force, rtol1e-12/3e-14,maxstep1800/900s. Контроль худшего блока
каждого тела/relative pair/rotation/budgets, не общий RMS состояния.
Нет проекции raw solver q/R. Physical PN-I/clock/triad/SSC mapping,
figure–figure, mantle/core, деформации и приливы не добавлены.

## Сходимость и старый32day префикс

| Сравнение | Allbody, м | Earth–Moon, м | v, м/с | R Frobenius | S/initial norm |
| --- | ---: | ---: | ---: | ---: | ---: |
| production_refinement | 0.0177082264 | 0.000169127239 | 2.942905e-09 | 2.230650e-14 | 4.665947e-15 |
| reference_refinement | 0.025245868 | 0.000357349636 | 3.291721e-09 | 7.496348e-14 | 7.335261e-15 |
| independent | 0.0252458666 | 0.000235926829 | 2.830212e-09 | 3.515327e-14 | 7.115507e-15 |

Пороги260 оставлены без ослабления. Эталонная чувствительность отдельно
показана в reference_refinement; разность программ не строгий error bound.
По-тельные ошибки хранятся в JSON, в том числе далёкие большие координаты.

|96day против прежнего32day, первые129выходов|Allbody, м|Pair, м|Битово равных строк|
|---|---:|---:|---:|
| nominal | 0 | 0 | 129 /129 |
| tight | 0 | 0 | 129 /129 |
| reference_nominal | 0 | 0 | 129 /129 |
| reference_tight | 0 | 0 | 128 /129 |
| baseline | 0 | 0 | 129 /129 |

Изменённый t_bound влияет на последний укороченный шаг/интерполяцию32day;
полная bitexact идентичность префикса не требовалась. Заранее заданы
allbody<.1м/pair<.01м/v<1e-6м/с/R<1e-9/S<1e-9, они соблюдены.
Это проверка воспроизводимости начального участка, не новый fit к JPL.
Фактически orbit и R префикса bitexact во всех5вариантах. У строгогоRK45
на последнем32day выходе отличается только body-Pi_y на5.421011e-20
начальной нормыS. После преобразования к spatialS разность округляется
к нулю; сырое отличие явно сохранено, поэтому bitexactrows128/129.

## Балансы и стоимость

E=E_EIH+Trot+Ufixed+UMoon,P=P_EIH,J=J_EIH+S. Отдельные источники:
PN²,PN×Q и внешний fixed-axis torque; Moon orbital torque уже сокращён
с Sdot. Фиксированные поля не дают внешней работы в E, но дают torque в J.
Глобальные totals вычислены Decimal70 с вычитанием initial ДО float;
сверка70/90цифр на9индексах0,48,…384 каждого расчёта.
Нормировки:|E0|,sum m|v0|,|J0|;векторные блоки — евклидова норма.

| Расчёт | Corrected E | Corrected P | Corrected J | Raw q/R defect | RHS calls | Integration, с |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| nominal | 6.357714e-15 | 9.090811e-16 | 2.523401e-15 | 1.776357e-15 | 28805 | 104.169261 |
| tight | 6.051246e-15 | 2.226912e-15 | 2.718228e-15 | 2.664535e-15 | 56453 | 262.301083 |
| reference_nominal | 6.282131e-15 | 2.216294e-15 | 2.798477e-15 | 3.686671e-14 | 27650 | 281.268503 |
| reference_tight | 1.280849e-14 | 2.512201e-15 | 6.710688e-15 | 1.518568e-14 | 55298 | 561.938706 |
| baseline | 6.276521e-15 | 9.662155e-16 | 2.521314e-15 | 2.220446e-15 | 28805 | 112.569248 |

Пределы1e-11 для corrected E/P/J и1e-8 rawrotation соблюдены.
Интегрирования суммарно1322.246801с;
исходный268 драйвер с диагностикой1336.780976с. Нагрузка/тесты
частично пересекались, это не контролируемый benchmark и не ускорение.
8day preflight:DOP8.496239с/RK4522.688306с,pair2.810611e-6м/all.005281571м.

Raw дрейф и3бюджета каждого решения сохранены в JSON. Малые PN sources
могут быть ниже глобального численного дрейфа. Глобальный PASS не доказывает
их отдельную видимость; Noether visibilityFAIL219–222 не отменяется.
Повышенная арифметика totals не делает float интегратор точнее.
Ухудшения отдельных метрик при ужесточении допусков не скрываются.

## Остатки к DE441

Будущие состояния/ориентации загружены после всех5propagations.
Reader проверен ранее против440JPLснимков/Decimal/стыков;385новых выходов
сверяются с локальным reader, не с новой HorizonsAPIвыгрузкой.
Ни IC/GM/I,ни q/S,ни фаза по этим будущим данным не подбирались.
Baseline и nominal free имеют одинаковые настройки; tight показывает
численную чувствительность. Полные внешние метрики всех5решений в JSON.

| Тело | Baseline max, м | Nominal free max, м | Tight free max, м | Nominal−baseline, м |
| --- | ---: | ---: | ---: | ---: |
| Sun | 15.5997561 | 15.5997561 | 15.5997581 | +0 |
| Mercury | 12.756439 | 12.756424 | 12.7525758 | -1.49729125e-05 |
| Venus | 29.4091393 | 29.408933 | 29.4070309 | -0.000206261776 |
| Earth | 26.1190341 | 28.2684735 | 28.269979 | +2.1494394 |
| Moon | 207.781395 | 28.5973025 | 28.5989983 | -179.184092 |
| Mars | 81.6698802 | 81.6699105 | 81.6686374 | +3.02342738e-05 |
| Jupiter | 16.4580543 | 16.4580543 | 16.4600161 | +0 |
| Saturn | 2.28487011 | 2.28487011 | 2.2812047 | +0 |
| Uranus | 1.19226036 | 1.19226036 | 1.18184109 | +0 |
| Neptune | 4.45591543 | 4.45591543 | 4.44808355 | +0 |

| Интервал, суток | Baseline pair max, м | Free tight pair max, м | Free tight RMS, м | R error max, arcsec |
| --- | ---: | ---: | ---: | ---: |
| 0-32 | 53.3398899 | 0.0456273126 | 0.0282097236 | 1.52928825 |
| 32-64 | 112.166809 | 0.14335708 | 0.0954466032 | 5.61705365 |
| 64-96 | 182.36154 | 0.356397547 | 0.241097348 | 12.4010783 |

В каждом окне129выходов, общие граничные точки включены в оба соседних
окна. Эти RMS не независимые выборки и не складываются в общий RMS.
Префиксные0–32/0–64/0–96метрики и все385норм сохранены отдельно.
Цели10км/body и1км/pair на снимках — отдельные статусы, не критерий
арифметической правильности/physical uncertainty/годовой квалификации.
Рост остатков по времени и ухудшения отдельных тел сохранены.
Pair maxima по окнам выросли примерно4.56см→14.34см→35.64см; это намного
больше измеренной численной чувствительности, но конкретная причина
модельного/входного остатка этим опытом не установлена. Квадратичная
экстраполяция на год не заменяет проверку и не используется как сертификат.
Малые изменения, сопоставимые с численной чувствительностью, не
приписываются физике. Прежний годовой≈726м — иной интервал/модель.

## Либрационная геометрия

u=Rᵀ(-rho)/|rho|;longitude=atan2(u_y,u_x),latitude=atan2(u_z,hypot(u_x,u_y)).
Longitude непрерывно развёрнута, ошибки углов вычислены через sin/cos
разности без ложного скачка±pi. Это sub-Earth геометрия в principal-axis
базисе Луны, не IAU Euler angles. Она зависит и от орбиты,и от ориентации;
ошибкаR приведена отдельно. Диапазоны включают геометрию оптических
либраций; амплитуда одной чистой свободной моды/частоты не оценивалась.
Изменение диапазона между32day окнами само по себе не доказывает
рост свободной моды: окна покрывают разные фазы вынужденного движения.

| Окно free tight, суток | Longitude span, deg | Latitude span, deg | Max lon residual, arcsec | Max lat residual, arcsec |
| --- | ---: | ---: | ---: | ---: |
| 0-32 | 11.7448627 | 13.2230094 | 1.10840575 | 0.670908287 |
| 32-64 | 14.1467566 | 13.1184734 | 4.80397065 | 1.17739846 |
| 64-96 | 15.5262223 | 13.3616781 | 11.3709274 | 2.15379513 |

Три лунных цикла без численного сбоя не доказывают долговременную
устойчивость, правильность mantle/core mapping или отсутствие missing physics.
Mean-solid I и ordinary Newton spin в одном coordinate-time остаются
оговорённым приближением, не полной физической моделью вращения Луны.

## Сохранённый неуспех повторной обработки270

Первый offline nominal96 совпал точно, но exact-проверка обработки пяти
NPZ выявила3 различия spin_relative_initial последних разрядов:два
0→1.110900e-16 и одно отличие1.501518e-19. Все31externalseriesarray и
траектории совпадали. Причина:default ndarray.copy() переводил сохранённые
Fortran-order массивы в C-order, меняя порядок суммирования в S=R Pi.
Порог не ослаблен;loader теперь copy(order='K'),есть regression test.
Это исправление воспроизводимости обработки, не повышение точности орбит.

Original268 receipt/NPZ/source/test/failure сохранены. Derived270 receipt
явно разделяет propagation_source_sha256 старого исполнения и текущий
postprocessing source_sha256;два изменённых служебных файла доступны
в executionarchives,все physics/RHS/integrator источники прежние.
Анализ после исправления и31seriesarray совпали с original268 точно.
Пять интеграций для этого не пересчитывались;затем current-код отдельно
прошёл свежий nominal96 и полную обработку пятиNPZ без сети.

## Тесты и повтор без сети

263related tests passed32.67с, включая15новых;source/publicfiles frozen.
Full2461819Python/17Rust/fmt исторический,не повторялся. Проверены
аналитический знакRz/широта,угловая branchcut,общие границы окон,385эпох,
NaN/missingbody/partial/fresh-output и существующие физические tests.

Свежая publiccopy с пробелами в пути/без прежней.tools и личных документов,
socket.connect/create_connection запрещены. Reader квалифицирован заново.
Полный96day nominal выполнен ДО передачи сохранённых траекторий:
2decodedNPZarrays совпали точно. Затем5NPZи32dayконтроль переданы как
явные inputs, все385epoch balances/external/windows/angles/comparisons
пересчитаны:все показатели и31seriesarray совпали точно.
Это **одна повторная интеграция и полная повторная обработка пяти решений**,
не пять повторных96daypropagations. Те же установленные библиотеки,
новая среда/платформа не квалифицируется. Стоимость каждой фазы в JSON.

Для полностью нового расчёта из publiccheckout с зависимостями:

```powershell
python -X utf8 -B -m scripts.assess_de441_reader --output .tools/months-reader.json
python -X utf8 -B -m scripts.assess_free_lunar_rotation --output .tools/months-prior32 --reader-receipt .tools/months-reader.json
python -X utf8 -B -m scripts.assess_free_lunar_months --output .tools/months96 --reader-receipt .tools/months-reader.json --previous-report .tools/months-prior32.json
python -X utf8 -B -m pytest -q -p no:cacheprovider tests/test_free_lunar_months.py
```

Все outputs свежие;существующие failure/partial не перезаписываются.
Для публикации/новой установки32dayконтроль пересоздаётся,его наличие
в старой.tools не требуется;данные DE441/JPL уже есть в publicarchives.

## Решение

Физические runtime/силы/IC/Rust/default/guard не изменены. Loader postprocessing исправлен отдельно. Годовая точность,
полный PN-I/SSC mapping, tiny-source visibility и arbitrary IC не
сертифицированы. Исследовательский numerical PASS не включает новую
комбинацию сил в приложение. Нет новых приливов/3D/подгонки/GitHub.

Следующий273: Протокол годовой квалификации свободного ротора с оценкой стоимости и независимой численной погрешности. Сначала заранее объявить gates/стоимость,не переносить96dayуспех на год.

## Проверенные определения

- [assess_free_lunar_months.validate_grid](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:26)
- [assess_free_lunar_months.body_angles](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:31)
- [assess_free_lunar_months.circular_difference](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:45)
- [assess_free_lunar_months.external_series](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:51)
- [assess_free_lunar_months.series_statistics](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:69)
- [assess_free_lunar_months.previous_receipt](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:89)
- [assess_free_lunar_months.load_trajectories](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:100)
- [assess_free_lunar_months.analyse](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:112)
- [assess_free_lunar_months.orbit_comparison_qualified](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:152)
- [assess_free_lunar_months.qualification](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:158)
- [assess_free_lunar_months.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:192)
- [assess_free_lunar_months.run.save](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:217)
- [assess_free_lunar_months.main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_free_lunar_months.py:241)
- [test_free_lunar_months.series](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:10)
- [test_free_lunar_months.test_body_longitude_has_analytic_rotating_axis_sign_and_no_branch_jump](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:16)
- [test_free_lunar_months.test_body_latitude_and_longitude_match_known_cartesian_direction](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:24)
- [test_free_lunar_months.test_shared_window_boundary_is_retained_without_changing_global_sample_count](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:34)
- [test_free_lunar_months.test_exact_epoch_inventory_rejects_wrong_duration_or_epoch](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:46)
- [test_free_lunar_months.test_external_statistics_rejects_incomplete_or_nonfinite_channels](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:55)
- [test_free_lunar_months.test_large_jpl_residual_is_recorded_as_failed_goal_not_filtered](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:63)
- [test_free_lunar_months.test_one_bad_body_cannot_be_hidden_by_aggregate_comparison_scalar](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:71)
- [test_free_lunar_months.test_reanalysis_rejects_missing_forecasts_before_readout](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:81)
- [test_free_lunar_months.test_existing_failed_receipt_cannot_be_overwritten_before_input_read](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:87)
- [test_free_lunar_months.test_geometric_angle_rejects_zero_direction_and_nan](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:94)
- [test_free_lunar_months.test_npz_loader_preserves_stored_memory_order_for_bitwise_diagnostics](C:/Users/Admin/Desktop/Solar-simulator/tests/test_free_lunar_months.py:99)
