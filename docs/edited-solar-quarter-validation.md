# Изменённый Solar: 90 суток

15 октября 2026, этапы 203–205. [Протокол](edited-solar-quarter-protocol.md),
[полные измерения, времена и SHA](edited-solar-quarter-validation.json),
[предыдущие 30 суток](edited-solar-month-validation.md).
Все **18/18 сочетаний** трёх стартов, трёх режимов и двух выходных сеток
прошли заранее заданные пороги. Это численное согласие одной физической
модели, а не измеренная физическая точность относительно реальной системы.

Как в 30-дневном опыте: десять тел, EIH1PN+fixedSun/EarthJ2, те же массы/фигуры/оси,
G и DOP853/per-body/relativeEarthMoon/rtol3e-14/xatol1e-3 м/vatol1e-9 м/с,
dt3600 с/packet20. Одна правка pinned strictcheckpoint на каждый опыт:
Sun.mass×1.25; Earth.position+(1e6,−2e6,3e6) м;
Moon.velocity+(100,−50,25) м/с. Начальные позы/скорости остаются в исходных
инерциальных осях SSB/EclipticJ2000; SI, без recentering. Child.time=0,
origin=None; исходная эпоха родителя JD2461321.5TDB/DE441 — происхождение.
Нет новых спутников и повторных масс; GM гигантов системные.

7776000 с: регулярная сетка361 эпоха через6ч, сдвинутая362 эпохи с+3ч
внутри интервала. Общие только0 и90суток. Смена сетки меняет перезапуски
legacy-контроллера. Обе сетки объявлены до результата, параметры не выбирались.

| Сетка / правка | Moon−Earth legacyPython, м | legacyRust, м | continuousRust, м | Последнее уточнение reference, м |
|---|---:|---:|---:|---:|
| regular / sun_mass | 0.00292632459 | 0.00107744872 | 0.000123138497 | 0.000122178047 |
| regular / earth_position | 0.00184173447 | 0.00209272945 | 6.15132537e-05 | 0.000226615481 |
| regular / moon_velocity | 0.0126127663 | 0.0103652935 | 0.000365755715 | 7.20615148e-05 |
| shifted / sun_mass | 0.00591667876 | 0.00313842014 | 9.67365765e-05 | 0.000107976574 |
| shifted / earth_position | 0.00248683347 | 0.0048758364 | 0.000133263648 | 0.00022076712 |
| shifted / moon_velocity | 0.00101047556 | 0.00197690618 | 9.17524598e-05 | 7.86937535e-05 |

Максимум среди отдельных тел: 0.170955723 м / 3.35639368e-08 м/с.
Проверяется каждое тело <10 м/1e-4 м/с, Moon−Earth <.1 м/1e-5 м/с.
Критерии применены к каждому телу отдельно.

Reference: прежний RK45/AU-year/EMB+Moon−Earth/scalarRustEIH/vectorJ2,
(rtol,max_step)=(1e-13,1800с)/(3e-14,900с)/(3e-14,450с), atol1e-17.
В каждой сетке сначала квалифицированы все три reference, затем кандидаты.

- regular: RHS [25928, 51842, 103682]; последняя разность всех тел ≤0.029317074 м/8.48321061e-09 м/с.
- shifted: RHS [25928, 51842, 103682]; последняя разность всех тел ≤0.029317074 м/8.48321061e-09 м/с.

Все три старта показали рост RHS на обоих уточнениях. Старые reference-пороги
1 м/1e-6 м/с по всем и .01 м/1e-7 м/с для Moon−Earth сохранены.
Initialroundtrip и scalar-vs-matrix physicalC/test-onlyC/10 snapshots прошли.
В интегрировании используется физический C. Последняя разность —
чувствительность, не строгая граница; ниже неё методы не ранжируются.

Абсолютные координаты не показывают монотонного уменьшения разности:

- regular/earth_position: 0.0233661848→0.0293128963 м
- regular/moon_velocity: 0.0238459561→0.029317074 м
- shifted/earth_position: 0.0229349315→0.0293115738 м
- shifted/moon_velocity: 0.0234133544→0.029317074 м

Поэтому здесь не подтверждён асимптотический порядок сходимости эталона.
Рост RHS подтверждает активное уточнение, а не исключает влияние float64.
Заданные пороги проходят; не приписывать последней разности статус точной ошибки.

| Режим | Общий endpoint: все тела, м | Moon−Earth, м |
|---|---:|---:|
| legacy_python | 0.0419927558 | 0.0116054681 |
| legacy_rust | 0.0117212938 | 0.00841605465 |
| continuous_rust | 0.0136760041 | 0.000330127744 |
| reference | 0 | 0 |

Скоростные endpoint-остатки также сохранены и прошли прежние пороги.
Разные эпохи не интерполируются. Нулевой reference-endpoint ожидаем:
t_eval не управляет RKшагами. Это одинаковая внутренняя траектория,
а не нулевая неопределённость. Между выбранными эпохами гарантии нет.

| Правка | Максимум Moon−Earth за30суток, м | За90суток, м |
|---|---:|---:|
| sun_mass | 0.00147009113 | 0.00591667876 |
| earth_position | 0.00109721242 | 0.0048758364 |
| moon_velocity | 0.00346185672 | 0.0126127663 |

Смена горизонта/сетки измеряет рост численного расхождения. Это не
before/after улучшение интегратора: силы и допуски не менялись.

| Сетка | legacyPython, с | legacyRust, с | continuousRust, с | reference, с/опыт |
|---|---:|---:|---:|---:|
| regular | 14.7439–14.9448 | 8.6003–8.8266 | 1.0836–1.1064 | 40.6454–44.5463 |
| shifted | 14.5367–14.9665 | 8.5416–8.8619 | 1.0851–1.1258 | 39.8926–40.9867 |

Медианы3 чередующихся full-запусков с setup/снимками; перед ними повтор/прогрев.
Диагностика/NPZ/SHA вне timing кандидата, reference включает progress-cache IO.
Все времена сохранены. Внешняя нагрузка/частотаCPU не фиксированы;
между сетками нельзя приписывать разницу цены одним выходным эпохам.

Стенды198/200 и runtime не менялись. Новый edited_solar_interval принимает
явную сетку/протокол и переиспользует frozen helpers; формулы сил, интегратор
и mapping координат в него не копировались. До90суток он повторил полный
30-dayregular: **все24массива побитно совпали** с frozen month200b.
Эта переквалификация относится к orchestration, а не улучшению точности сил.

429 относящихся тестов прошли за80.30с; 19 новых случаев.
Проверены некорректные эпохи, несоответствие горизонта/source/dependencies/
qualification, относительная ошибка Луны, сохранность ранее записанных отказов.
Полный набор/Cargo/portable не повторялись: runtime/Rust/упаковка прежние.
ZIP155 сохранён, новой сборки нет. Контроль метрик изNPZ, исходных правок,
source/input/scalarDLL/native.pyd/SciPy/старых файлов/архива/личных документов
и публичных ссылок записан в локальном integrity205.

**Ограничения:** три конкретных опыта/90суток/две сетки, не год,
не все параметры или сближения. Нет JPL-сравнения изменённых IC;
Noether21sourceintegrals для этих десяти тел не интегрировались,
fewbody-балансы их не заменяют. Нет новых приливов/вращения/GRпорядков.
Численное согласие не является истинной физической точностью модели.

Повторный запуск из корня проекта в закреплённом локальном окружении
(оба пути должны быть новыми, старые аудиты не перезаписываются):

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_edited_solar_quarter --grid regular --output .tools/quarter-repeat90/regular
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_edited_solar_quarter --grid shifted --output .tools/quarter-repeat90/shifted --regular-receipt .tools/quarter-repeat90/regular.json
```

SHA-привязки предшествующих отчётов включают пути и бинарники текущего
локального окружения. Перенос исследования на другой ПК/сборку требует
отдельной переквалификации; это не готовый переносимый verificationbundle.

Проверенные определения:

- [validate_epochs](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_solar_interval.py:23)
- [check_regular](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_solar_interval.py:31)
- [cross_grid](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_solar_interval.py:39)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/edited_solar_interval.py:50)
- [epoch_grid](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_quarter.py:13)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_edited_solar_quarter.py:21)
- [test_quarter_grids_have_only_common_endpoints_and_do_not_change_month_grid](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_interval.py:12)
- [test_bad_epoch_contract_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_interval.py:25)
- [test_epoch_validation_takes_a_copy_and_preserves_each_exact_time](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_interval.py:30)
- [test_regular_receipt_rejects_wrong_horizon_sources_or_qualification](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_interval.py:40)
- [test_cross_grid_checks_relative_moon_even_when_each_absolute_position_passes](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_interval.py:51)
- [test_grid_mismatch_is_rejected_before_writing_any_output](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_interval.py:61)
- [test_saved_receipt_is_preserved_before_loading_dependencies](C:/Users/Admin/Desktop/Solar-simulator/tests/test_edited_solar_interval.py:69)
