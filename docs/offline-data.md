# Локальный запас научных данных

Этапы234–235, 2026-10-16T21:28:27+03:00. Цель — работать без переключения VPN и повторных
запросов к JPL. Runtime, начальные условия, физические силы, интегратор
и прежние научные отчёты не менялись.

Данные лежат локально в `.tools/offline234/sources` (ignored Git/portable).
[Реестр и результаты проверки](offline-sources-validation.json) фиксирует URL,
SHA256, единицы/системы, диапазоны и историю неудачных загрузок.
Основное содержимое16файлов:9663740байт. Частичные загрузки/фрагменты
и HTTP-заголовки также сохранены отдельно; фактический каталог больше.

## Что уже есть без сети

| Источник | Назначение и границы |
|---|---|
| DE441 ASCII,115записей306–420 | Коэффициенты для интервала JD2461321.5–2464974.0TDB:10юлианскихлет от текущей эпохи; фактический охват2461296.5–2464976.5 |
| DE441 header | Константы, EMRAT и расположение коэффициентов |
| pck00011.tpc, исходный GM Horizons | Размеры/оси/GM; старый GM совпал с SHA текущего Origin |
| ERFA ltpequ/ltpecl + лицензия | Исходные таблицы уже используемой ориентации |
| Park et al.2021, Vines EIH action | Первичные формулы и ограничения моделей |
| Horizons manual, batch instructions | Системы времени/координат, параметры запросов |
| DE ASCII format, DE441 tech comments, PCK Required Reading | Формат, происхождение и соглашения данных |

[Официальное описание ASCII](https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/ascii_format.txt)
указывает системные барицентры планет, геоцентрическую Луну и лунные
либрации. В сохранённых записях есть также Солнце/Плутон. Это не каталог
произвольных спутников/астероидов/звёзд. Начальные условия других систем
и отсутствующие тела могут потребовать новой загрузки.

Нативные координаты ICRF, позиции в TDB-compatible километрах,
либрации в радианах; runtime Solar — SI/Ecliptic J2000. Читатель будущих
коэффициентов должен отдельно пройти проверку единиц, преобразования осей,
времени, производных и Earth/Moon через EMB+EMRAT. Самостоятельный
читатель и точность нашей симуляции на10лет **ещё не квалифицированы**.
Сырые данные не используются для подгонки IC или будущего движения силой.

Текущая годовая проверка уже полностью автономна:
[440снимков JPL](nominal-jpl440-validation.md),
архив `docs/nominal-jpl440-inputs.zip`. Для её повторения интернет не нужен.
Новые10лет — запас первичного эталона, не расширение годовой квалификации.

## Доступ и неудачные попытки

Большие файлы DE441/Park оборвались по55секундному таймауту. Сохранились
исходные частичные файлы и оба первоначальных incomplete-manifest/версии
загрузчика. Догрузка блоками262144байта проверяла206/Content-Range/ETag/
длину каждого ответа, затем SHA и полную структуру результата. Старые
348673байта совпали побайтно; проверены115ID/1018коэффициентов на запись,
конечность,32-дневная непрерывность, GROUP1050 и покрытие10лет.
Численные критерии и прежние физические данные не изменялись.

Предпочтительная `ssd-api.jpl.nasa.gov/doc/horizons.html` не скачалась:
две ошибки подключения curl, затем таймаут30с PowerShell. Исходный план234
остался **INCOMPLETE15/16**, не превращён задним числом в успех.
В235 отдельно сохранена
[официальная batch-инструкция](https://ssd.jpl.nasa.gov/ftp/ssd/horizons_batch.txt),
на которую ссылается [страница API](https://ssd-api.jpl.nasa.gov/doc/horizons.html).
Она содержит TIME_TYPE/TLIST/VEC_CORR и другие параметры; недостающая
API HTML явно отмечена в manifest. Основной набор235 с этой объявленной
альтернативой полон; это не утверждение, что недоступная страница скачана.
Три первоначальных и повторная ошибка подключения сохранены в manifest;
PowerShell-таймаут отдельно отражён в JSON отчёта.

## Проверка и порядок работы

Из корня проекта, **без сети**:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.prefetch_physics_sources --directory .tools/offline234/sources --cached
```

`--cached` никогда не догружает отсутствующие файлы. SHA manifest:
`9bb19c96de7c5be71fb97fccff39c4ea8ced1fe8100d19a294a18a91e48a5b75`.
Проверка с запрещёнными socket.connect/create_connection и download прошла
за0.097530с. Наличие кеша не подменяет проверку SHA.

48относящихся тестов passed2.05с,16новых: порча/NaN/пропуск/ID/время/
неверные индексы, неполный кеш, ETag/диапазоны/длина догрузки и раскрытие
замены документа. Последний полный232:1747Python/17Rust; в этом блоке
он не повторялся — исполняемый физический код не менялся.

Сначала искать требуемые данные здесь и в существующих публичных архивах.
Новый сетевой запрос нужен при отсутствии тела/периода/первичного источника;
сначала объяснить конкретный пробел. Не перескачивать сохранённое просто
из-за нового чата. Для новых эпох сначала квалифицировать локальный
DE441-читатель на закреплённых JPL-векторах; не обещать точности до проверки.

## Проверенные определения

- [sha](C:/Users/Admin/Desktop/Solar-simulator/scripts/prefetch_physics_sources.py:32)
- [validate_records](C:/Users/Admin/Desktop/Solar-simulator/scripts/prefetch_physics_sources.py:36)
- [download](C:/Users/Admin/Desktop/Solar-simulator/scripts/prefetch_physics_sources.py:69)
- [verify_reserve](C:/Users/Admin/Desktop/Solar-simulator/scripts/prefetch_physics_sources.py:101)
- [resume_download](C:/Users/Admin/Desktop/Solar-simulator/scripts/prefetch_physics_sources.py:142)
- [run](C:/Users/Admin/Desktop/Solar-simulator/scripts/prefetch_physics_sources.py:195)
- [main](C:/Users/Admin/Desktop/Solar-simulator/scripts/prefetch_physics_sources.py:271)
- [header](C:/Users/Admin/Desktop/Solar-simulator/tests/test_physics_source_reserve.py:10)
- [record](C:/Users/Admin/Desktop/Solar-simulator/tests/test_physics_source_reserve.py:23)
- [records](C:/Users/Admin/Desktop/Solar-simulator/tests/test_physics_source_reserve.py:31)
- [test_full_predeclared_range_has_contiguous_finite_records_and_covers_ten_years](C:/Users/Admin/Desktop/Solar-simulator/tests/test_physics_source_reserve.py:35)
- [test_invalid_records_are_rejected_without_relaxing_range_or_epoch_contract](C:/Users/Admin/Desktop/Solar-simulator/tests/test_physics_source_reserve.py:45)
- [test_bad_pointer_layout_is_rejected](C:/Users/Admin/Desktop/Solar-simulator/tests/test_physics_source_reserve.py:62)
- [test_cached_mode_never_downloads_missing_data](C:/Users/Admin/Desktop/Solar-simulator/tests/test_physics_source_reserve.py:68)
- [test_source_reserve_tampering_is_detected_before_any_coefficient_use](C:/Users/Admin/Desktop/Solar-simulator/tests/test_physics_source_reserve.py:75)
- [test_existing_download_attempt_cannot_be_overwritten](C:/Users/Admin/Desktop/Solar-simulator/tests/test_physics_source_reserve.py:84)
- [test_small_range_recovery_checks_object_range_and_length_and_keeps_original_prefix](C:/Users/Admin/Desktop/Solar-simulator/tests/test_physics_source_reserve.py:94)
- [test_fallback_cannot_silently_claim_preferred_api_page_was_downloaded](C:/Users/Admin/Desktop/Solar-simulator/tests/test_physics_source_reserve.py:127)


## Уточнение после242

Указанное выше отсутствие квалификациичитателя описывает состояние235.
Теперь [отдельныйresearchreader](de441-reader-validation.md) прошёл сверку
440JPLэпох одного года и аналитические/Decimal/стыковые проверки.
Архивdocs/de441-reader-inputs.zip содержит нужные первичныеbytes безстарой.tools;
команда в отчёте работаетбезсети. Десятилетний прогнознашегоядра по-прежнему
не квалифицирован; читательнеподставляетэталонноедвижениевсимуляцию.


## Отдельный primary cache254

Для [реальных spin-масштабов](real-spin-scales-validation.md) потребовался
отсутствовавший полный первичный Hartung–Steinhoff,
[arXiv1011.1179v3, Eq.66](https://arxiv.org/pdf/1011.1179v3), PRD83,044008.
Локально: `.tools/scales254/Hartung-Steinhoff-1011.1179v3.pdf`,286448bytes,
SHA256 `b5daf350e62aa3c95a32ac7ccf9cfb8cf4f7d796f47978044756d1d99e96344e`.
Квитанция URL/bytes/SHA и headers сохранены рядом в primary-source.json.
Это отдельный кеш; прежний manifest16sources/9.66MB и его SHA не менялись.
Исполнение нового аудита не требует PDF/сети, формулы проверяются тестами;
JPL/DE441 не перескачивались. Сначала использовать существующий кеш.
