# Трое суток изменённого Solar: проверка198–199

Все9сочетаний трёх изменённых стартов и трёх режимов прошли численные
критерии. Использованы исходные10тел строгого профиля. Runtime, настройки
и данные родителя сохранены; новых сил и JPLзапросов не было.
[Протокол](edited-solar-protocol.md),[полные данные/SHA](edited-solar-validation.json),
[предшествующие few-body балансы193–197](edited-j2-validation.md).

## Что менялось

Из pinnedstrictcheckpoint созданы три отдельные ветки:Sun.mass×1.25;
Earth.position+(1e6,−2e6,3e6)м;Moon.velocity+(100,−50,25)м/с.
Остальные состояния не корректировались автоматически. Parentсодержит
исходную эпохуJD2461321.5TDB/SSB/EclipticJ2000;childимеетorigin=None иt0=0.
Числа и скорости остаются в прежних инерциальных осях,SI. Это внешнее
изменение опыта с собственным стартом, а не новый набор эфемерид.
Наружные гиганты остаются системными барицентрами;массы спутников не дублировались.

Период259200с,25эпох,packet20. EIH1PN+fixedSun/EarthJ2;rtol3e-14,
xatol1e-3м,vatol1e-9м/с,per-body/relativeEarthMoon/dt3600с.
Сравнены actualGUIlegacyPython/Rust и continuousRust с одинаковыми
IC и выходными границами. Source-reaction и weak-field/exterior guards
сохранены. Радиусы/J2/оси не пересчитывают устройство тела после изменения массы.

## Независимый расчёт

Повторно использован старый independent_reference:RK45 вAU/year,
interleavedEMB+Moon−Earth, отдельная scalarRustEIH DLL и body-axis vectorJ2.
Рабочий PyO3nativeforce и DOP853 не формируют этот reference.
Новый mapping и дублирующий интегратор не создавались. Исходный код,
actualDLL/compiler/native.pyd/SciPyи входы закреплены вJSON.

ScalarDLL отдельно сверена с matrixEIH на трёх childIC:fullphysicalC
relativeerror≤2.10e-16; при проверочномC/10 separatePNerror≤2.32e-11.
УсилениеPN применялось только в snapshotконтроле; интегрирование
использует физическоеC. Начальный roundtrip≤3.052e-5м по всем телам,
relativeMoon≤1.863e-9м;cachedreferenceперваяточканеподменялась.

Уровни(1e-13,1800с),(3e-14,900с),(3e-14,450с),atol1e-17.
Pass-throughfigurecallback зафиксировал872→1730→3458RHS для каждого
сценария. Последнее ограничение шага реально увеличило вычисление.
Все три промежуточных referenceмассивы и исходныеIC сохранены.

| Сценарий | Различие900→450, все тела, м | Луна−Земля, м | Reference+progresscache, с |
|---|---:|---:|---:|
| sun_mass | 0.00488807871 | 3.05175818e-05 | 0.798236 |
| earth_position | 0.0107338655 | 3.14568075e-05 | 0.795311 |
| moon_velocity | 0.010733864 | 3.14568174e-05 | 0.796490 |

Чувствительность reference прошла прежние условия:<1м/1e-6м/с по всем
и<0.01м/1e-7м/с для Луны относительно Земли. Это эмпирическая разница
расчётов, не строгая глобальная граница. Она ограничивает сравнение
микрометровых/миллиметровых результатов между режимами.

## Результат

Критерии до результатов:каждое тело<10м/1e-4м/с,relativeMoon<0.1м/1e-5м/с.
По-тельные значения и скорости всех10тел сохранены вJSON.

| Сценарий | Режим | Все тела, м | Луна−Земля, м | Луна−Земля, м/с | Медиана, с |
|---|---|---:|---:|---:|---:|
| sun_mass | legacy_python | 0.0107437588 | 6.15104386e-05 | 1.06189821e-10 | 0.545146 |
| sun_mass | legacy_rust | 0.0100661766 | 6.15104272e-05 | 1.03714552e-10 | 0.331367 |
| sun_mass | continuous_rust | 0.00694408299 | 3.41196969e-05 | 7.27630455e-12 | 0.055971 |
| earth_position | legacy_python | 0.00782066157 | 9.1552822e-05 | 1.10745485e-10 | 0.541425 |
| earth_position | legacy_rust | 0.00684601178 | 9.15528438e-05 | 1.12498528e-10 | 0.324729 |
| earth_position | continuous_rust | 0.00488283075 | 3.1456803e-05 | 4.06800454e-12 | 0.056070 |
| moon_velocity | legacy_python | 0.00887343868 | 9.28175282e-05 | 9.91252132e-11 | 0.530948 |
| moon_velocity | legacy_rust | 0.00895368086 | 9.43722808e-05 | 9.62027224e-11 | 0.326473 |
| moon_velocity | continuous_rust | 0.00491324456 | 3.14568136e-05 | 7.27623863e-12 | 0.052300 |

Все9кандидатов прошли. Каждый повтор/3timingruns побитово совпал;
parent/child/настройки и общие границы сохранены. Legacycheckpoint
продолжается точно на одинаковом следующем пакете. Continuousbuffers
не сохраняются вcheckpoint, поэтому для перезапуска такого обещания нет.

Для стоимости выполнен repeat/прогрев и3чередующихся fullruns; setup,
силы и25снимков включены, reference/диагностика/report/hash исключены.
Referencewall включает запись progresscache. Rawвремена и счётчики
вJSON. Это цена конкретного запуска трёх суток, не универсальный FPS
или коэффициент скорости. GUIdefault не переключался наcontinuous.

**397связанных тестов прошли за52.06с**, включая6новыхSolar и25
новыхfew-bodyпроверок текущего блока. Новых отказов пилота нет.

## Границы результата

Это численное согласие трёх counterfactualстартов на25эпохах трёх суток.
Оно не гарантирует годовую точность, поведение других правок или всех
сближений. С реальными JPLтраекториями изменённые системы не сравнивались;
исходный годовой результат JPL~719м относится к прежнему неповреждённому старту.
Реальная физическая достоверность также ограничена fixedaxes и усечениемEIH+J2.

21источник Noether здесь не интегрировался. RawE/P/J не применялись
как conservationgate; correctedbudgets модельных задач193–197 не
приписываются реальному составу10тел. Новый portable/Cargo/fullold
не запускались:runtime/Rust/упаковка не менялись. Все прежние научные
отказы и проверенная ZIP155 сохранены.

## Воспроизведение

```powershell
.venv/Scripts/python.exe -X utf8 -B -m pytest -p no:cacheprovider -q tests/test_edited_solar.py
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_edited_solar --output .tools/new-solar-pilot/report
```

Из корня проекта, с существующим nativeмодулем и rustc для проверки/кеша
независимого scalaroracle. Выход внутриproject.tools должен быть новым;
все referencecaches также защищены от перезаписи старого запуска.
Сеть/JPL/REBOUND не нужны. Ошибка сохраняет частичныйJSON/NPZ.

Проверенные точки реализации:

- [assess_edited_solar.fixture](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar.py:28)
- [assess_edited_solar.oracle_check](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar.py:41)
- [assess_edited_solar.run](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar.py:56)
- [test_edited_solar.test_pilot_is_one_edit_of_the_pinned_ten_body_start](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar.py:12)
- [test_edited_solar.test_loaded_scalar_oracle_matches_independent_matrix_before_use](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar.py:27)
