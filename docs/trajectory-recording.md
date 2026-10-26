# Расчёт, запись и независимый просмотр траектории

Изменение316, 19 октября2026. Это дополнительный режим поверх существующего
`advance_towards`, без новых сил, изменения допусков или перехода на experimental
continuous. Обычные `run-until` и живой режим GUI сохраняют свои алгоритмы.
В исходном GUI прежнее поле «Шагов за кадр (скорость)» теперь подписано
«Шагов в расчётном пакете»: это численная настройка, а не скорость просмотра.

## Как пользоваться

1. Открыть checkpoint/ветку, проверить настройки, конечное `t` в секундах
   от начала опыта и размер расчётного пакета. Для исходного Strict-года:
   31557600с, dt3600с, пакет20. Другие IC/параметры требуют своих проверок.
2. Нажать «Записать траекторию…» и выбрать родительский каталог.
   Приложение создаст новую папку `solar-trajectory-UTC-UUID`.
   Работа идёт в том же единственном worker; редактирование заблокировано.
   Исходный опыт в лаборатории остаётся на прежнем времени.
3. Пауза/«Стоп и копия»/закрытие ждут завершения текущего пакета и его записи.
   Остановленная запись остаётся доступной. Обычный recovery лаборатории
   относится к её исходному опыту; рассчитанные снимки находятся в папке траектории.
4. Нажать «Просмотр траектории…» и выбрать папку с manifest.json.
   В отдельном окне доступны снимки/с, пауза, ползунок, XY/XZ/YZ и относительный вид.
   Длительность показа выбирается независимо от расчётных пакетов.
   При высокой скорости экран может пропускать показ отдельных снимков;
   все они сохраняются в записи и доступны ползунком.
5. «Снимок JSON…» сохраняет выбранный полный checkpoint/child+parent в другой
   каталог. Его можно открыть обычной кнопкой «Открыть JSON» и продолжить.
   Сохранение внутрь исходной траектории запрещено, чтобы не повредить запись.

В просмотре нет вызовов решателя или интерполяции. Ползунок выбирает индекс
сохранённого снимка; строка состояния показывает его фактическое время.
Это не произвольная непрерывная эпоха. Родитель и все компоненты состояния,
включая скорости, spin/q/S, события и работу ориентации, сохраняются в каждом кадре.

CLI из исходного проекта:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator record-trajectory input.json trajectory --time 31557600 --batch 20
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator view-trajectory trajectory
```

Каталог результата должен быть новым. Ctrl+C возвращает130 и сообщает recovery.
Существующие каталоги/входной JSON не заменяются. Этот режим появился в исходниках
после portable315; сохранённая сборка `20261019-010144` его ещё не содержит.

## Формат и сохранность

`manifest.json`: format solar-trajectory/schema_version1/unitsSI,
engine advance-towards-packets, packet_steps, start/target/status и список
file/time/SHA256. `frame-000000.json` — исходное состояние, далее каждый
завершённый численный пакет. Границы задаются соседними фактическими временами;
последний пакет может быть короче. Старые checkpoint/bundle форматы не изменены.

Сначала атомарно записывается полный кадр, затем атомарно обновляется индекс.
Не опубликованный в индексе файл не считается кадром. Ошибка не заменяет
ранее опубликованные снимки; последний вычисленный результат дополнительно
сохраняется в обычный локальный recovery. При двойном отказе запись явно
завершается с ошибкой. Статус recording после жёсткого прерывания означает
незавершённую запись, а не достижение цели. Защита от kill/потери питания/отказа
всех дисков не обещается. Автоматического удаления пользовательских папок нет.

Reader проверяет формат, имена/выход за каталог, SHA и полные checkpoint,
согласованность Settings/Origin/initial/parent и порядок времён. Единственное
разрешённое равенство времён — конечная остановка на контакте: состояния до
и после события в одном моменте. Нулевой шаг не запускается повторно.
SHA обнаруживает повреждение относительно индекса; это не подпись автора
и не доказательство физической правильности вручную составленной записи.

После проверки reader хранит собственные bytes; frame() возвращает новый
объект опыта. Изменение объекта вызывающей стороной не меняет запись.
В первой версии все кадры загружаются в память; формат хранит полные
состояния с повторением initial/parent. Большие/длинные записи потребуют
отдельного измерения памяти и, при необходимости, потокового чтения.
Индекс/один checkpoint ограничены существующими10МБ writer; общего лимита
длины по времени этот формат не обещает. Кода/dependencies recipe пока нет:
индекс фиксирует кадры/границы/пакет, полное окружение — следующий отдельный этап.

## Критерии и проверки

До реализации: неизменные пакеты и полный round-trip, разные скорости/seek
без solver и записи на диск, ошибки публикации с сохранением готового состояния,
остановка/закрытие на пакете. Научные критерии прежнего nominal-протокола:
каждое тело к независимому эталону <10м/<1e-4м/с, Moon−Earth <.1м/<1e-5м/с;
JPL <10км/тело и <1км/пара с прежними временными запасами10м/.2м.
Критерии не подбирались по новым результатам.

Первоначальные25FAIL отражали отсутствие новой функции. Затем24PASS/1FAIL
(ещё отсутствовала CLI-команда),45PASS13.23с и71PASS16.98с.
Первый GUI-набор2FAIL/59PASS21.63с: subprocess не видел тестовый helper из
другого файла; helper перенесён в собственный тестовый модуль,3PASS4.61с.
Независимый стенд сначала остановился на ошибочном `.norm()` вместо существующего
Vector3.magnitude(); ошибочный лог и первый результат сохранены отдельно.
Эта ошибка относилась к стенду, не к физическому ядру.

Отдельная проверка выявила реальный недостаток первоначального нового формата:
он отвергал контакт при t=0 как отсутствие прогресса. Сначала1FAIL,
затем сохранение двух состояний одной эпохи и явный terminal-contact guard.
После исправления72relatedPASS16.85с. До/после и ошибки сохранены локально.

Проверки включают Python/Rust, Strict, свободное вращение, stop/bounce/merge,
начальный контакт, неизменность исходного опыта/parent, продолжение кадра,
отказ manifest/recovery, повреждения/пути/schema/time/settings, Ctrl+C и новый
каталог. Настоящий Tk проверяет фоновую запись, cooperative close, ползунок,
скорость, экспорт и запрет перезаписи оригинала. Во время просмотра advance
подменён исключением; запись и файлы сохраняются, вызовов solver нет.

Итоги окончательного научного и полного аудита добавляются после завершения.
Проверки точности относятся к конкретным эпохам/модели, а не к любому просмотру,
соседним системам, редактированным IC или междуэпоховой непрерывной ошибке.


## Итог научной проверки316

Исходники/data/native были неизменны во время расчётов; доказательство и логи
сохранены локально. Начало JD2461321.5TDB, SI/SSB/EclipticJ2000/DE441,10тел,
GM гигантов — системные барицентры, StrictEIH1PN+fixedSun/EarthJ2/relativeEarthMoon.
Ни новая сила, ни physical parameters fit, ни перенос continuous не выполнялись.

Два новых годовых расчёта:440кадров/439пакетов,438×72000с+21600с.
Вся матрица x/v совпала побитно с закреплёнными legacy_python/legacy_rust.
Кеш независимого RK45 и его3уровня уточнения, первичные JPL-ответы/парсер,
Origin/GM/эпохи/единицы и SHA проверены прежними validate_frozen/validate_data;
старые dependency pins не выдавались за новую верификацию исполняемых бинарников.
Их текущие SHA записаны отдельно.

| Ядро | Прямые пакеты+снимки без записи, с | Пакеты+полная запись, с | Чтение/проверка, с | Файлы, байт | Moon−Earth к RK45, м | Moon−Earth к JPL, м |
|---|---:|---:|---:|---:|---:|---:|
| python | 12.826 | 15.283 | 0.803 | 4202687 | 0.075260816 | 725.514939 |
| rust | 7.582 | 9.976 | 0.794 | 4201836 | 0.075091675 | 725.509709 |

Все прежние по-тельные/относительные численные и JPL timing-aware пороги пройдены.
Таблица — последовательные одиночные замеры текущей среды, не статистический
benchmark/обещание ускорения. Дополнительная запись имеет цену в IO/валидации.
Просмотр на1/25снимков/с достигает того же последнего кадра без solver;
GUI-тест дополнительно запрещает advance исключением и проверяет неизменность файлов.

Проверка второго порядка на ньютоновских двух телах, e=.3, одна орбита,
Kepler-эталон из assess_accuracy.kepler_relative. Грубые сетки200/400шагов:

| Шагов/орбиту | Ошибка конца, м | max abs(ΔE/E₀) | max norm(ΔL)/norm(L₀) |
|---|---:|---:|---:|
| 200 | 1214559758.163 | 0.000537102739 | 3.80984132e-16 |
| 400 | 303289961.245 | 0.00013417471 | 1.52393653e-15 |

Уменьшение ошибки 4.004616× при половинном шаге
прошло заранее заданный диапазон3.5–4.5; энергия<.01, L<1e-12.
Большие ошибки этих грубых сеток сохранены: это проверка порядка, а не
допуск рабочего Strict-профиля. Ньютоновские балансы относятся к этой задаче,
не подменяют 1PN/Noether для планетной модели.

440-эпоховая проверка отличается от125эпох/499пакетов portable315.
Сравнение максимумов этих сеток не является улучшением физической точности.
Не проверены междуэпоховые значения, другие параметры/горизонты/тела;
Noether/sourcevisibility/PN×J2/приливы/Kuiper ограничения остаются прежними.
Новый годовой прогон подтверждает сохранность прежних пакетов при добавлении IO.


## Код и независимые регрессии

- [trajectory.py:record_trajectory](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/trajectory.py:21)
- [trajectory.py:Trajectory](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/trajectory.py:94)
- [playback.py:Playback](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/playback.py:5)
- [trajectory_view.py:TrajectoryViewer](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/trajectory_view.py:15)
- [trajectory_view.py:_export_frame](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/trajectory_view.py:91)
- [trajectory_view.py:launch](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/trajectory_view.py:122)
- [app.py:_build](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:101)
- [app.py:_pause](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:412)
- [app.py:_poll](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:436)
- [app.py:_update_status](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:477)
- [app.py:_stop_and_save](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:684)
- [app.py:_record_trajectory](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:738)
- [app.py:_open_trajectory](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:768)
- [commands.py:main](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/commands.py:13)
- [test_trajectory.py:test_recorded_endpoints_match_independent_free_motion](C:/Users/Admin/Desktop/Solar-simulator/tests/test_trajectory.py:19)
- [test_trajectory.py:test_packets_equal_direct_continuation_with_full_state](C:/Users/Admin/Desktop/Solar-simulator/tests/test_trajectory.py:33)
- [test_trajectory.py:test_failure_preserves_published_frames_and_latest_calculated_recovery](C:/Users/Admin/Desktop/Solar-simulator/tests/test_trajectory.py:82)
- [test_trajectory.py:test_initial_contact_keeps_before_and_after_at_the_same_epoch](C:/Users/Admin/Desktop/Solar-simulator/tests/test_trajectory.py:201)
- [test_trajectory.py:test_different_playback_rates_and_seeking_never_call_solver_or_change_bytes](C:/Users/Admin/Desktop/Solar-simulator/tests/test_trajectory.py:132)
- [test_trajectory_gui.py:test_real_trajectory_journey](C:/Users/Admin/Desktop/Solar-simulator/tests/test_trajectory_gui.py:115)


## Окончательный полный аудит316

--require-native; 243.31с, без пропусков;
source/data/native SHA до/после совпали.

- Project inventory valid: 895 files
- 2067 passed in 239.84s (0:03:59)
- test result: ok. 19 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- Documentation file/line links valid: 2949

Научная проверка после contact/labelfix повторена в новой папке science-final;
первые успешные данные и исходные ошибки сохранены. Результаты совпали с прежними
порогами без их изменения. Логи .tools/trajectory316 (личный рабочий кеш).
Это новый режим исходного проекта; portable315 не пересобиралась и остаётся
последней проверенной поставкой. LATEST/старый ZIP/SHA сохранены. GitHub/commit/push нет.


## Открытие записи344

Открытие из GUI/отдельного viewer проверяет SHA и готовит координаты в рабочем
потоке. Прогресс считает кадры: проверка файлов, затем подготовка просмотра;
это не прогресс физического интегрирования. Отмена проверяется между кадрами,
файлы записи не меняет. Ошибка закрывает загрузчик без пустого viewer.
Tk/Matplotlib принадлежат главному потоку. Viewer переиспользует PlotArtists.
Формат1, всеcheckpoint/parent/времена прежние. Полные байты и координаты всё ещё
хранятся в памяти, индекс записи всё ещё переписывается целиком: масштаб
длинных354-тельных записей этим не решён. Страничный reader/новый индекс отложены.
Измерения только отображения: [все прогоны](review-followup-cost.json).
Повтор: python scripts/measure_playback.py --output <новый файл.json>; baseline
dda0238 должен быть доступен вGit.6повторов×4draw/вариант,120синтетических кадров,
10/354тел, синхронный canvas.draw. Не benchmark физики/чтения/записи.
