# Source/native/GUI acceptance406: NO-GO

Начало 9 ноября, завершение 10 ноября2026, Europe/Moscow. Полный обязательный
Python-прогон выполнен: **2972 PASS,63 FAIL,10 setup ERROR,0 SKIP** из3045узлов.
Техническая приёмка кандидата405 не пройдена. Исправления production, тестов и
исторических привязок в этом этапе не выполнялись. Это не73независимых дефекта
физического runtime: ниже выделены шесть подтверждённых групп причин.

[Машинный отчёт](q2-release-source-acceptance-406.json) содержит все3045статусов,
полные73tracebacks, SHA, исходные receipts и результаты контролей.
[План и исполнители](../scripts/qualification406/README.md) сохранены отдельно
от неизменного кандидата. Завершённый execution receipt с FAIL не означает PASS.

## Проверенный объект и метод

- Dev перед работой: `e5575cb1341b556361766e59f5b8e2349aaf0381`.
- Кандидат: `8fe01304e502f55e879addb0a4b6f3e062832e37`, родитель404
  `0985860f1776594a565f5754275fd110a00e29f2`.
- Tree: `f65701c8576e53882771e9f1b6633c92866f46f3`.
- Source/environment fingerprint:
  `f31aa35a6f4b1e504c1ce34b620a7ca7fe7e5ecf3ca5b4d5d8f2a86d0fe52091`.
- Прежний native0.3.3 SHA256:
  `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`.
- Sealed plan SHA256:
  `659e3481eef64e769ff7e6f932f06ac9830a5d949633eb8c1b125d85c5c9cde0`.
- Inventory3045узлов SHA256:
  `45c84f633273cf8615a08ea28b9d17b939509bdc6f80ae975e6bf98a3b14fede`.

Отдельный полный linked checkout того же commit находится в
`.tools/acceptance406-20261109/source`. Исходный кандидат405, квалифицированная
среда384 и другие кандидаты не переключались и не изменялись. Снимок241тестового
Python-файла закреплён до запуска; selection, pytest configuration и критерии
не менялись. Запущен штатный `scripts/check_project.py --require-native`.
После отказа pytest драйвер останавливается до Rust; обязательная Rust-часть
выполнена отдельной фазой с теми же исходниками и без исключений.

Изолированная test venv получает4207файлов зависимостей побитным копированием
из384; установленный старый `solar_simulator` исключён. Простые `.pth` указывают
на source candidate даже в дочерних `python -I`. Проверены prefix, origins и
SHA всех копий. Pip/install и пересборки PyO3 не было. Опциональная REBOUND5.2.2
скопирована только как уже закреплённая тестовая зависимость; IAS15 не стал
интегратором приложения и новая REBOUND scientific series не запускалась.

Среда: Windows x64, Python3.14.2t/MSVC1944, SOABI `cp314t-win_amd64`,
NumPy2.5.1, SciPy1.18.1, Matplotlib3.11.0, Tcl/Tk8.6.15;
rustc1.99.0 `b940084d7`, host `x86_64-pc-windows-gnu`, cargo1.99.0.
Ограничение потоков OMP/OpenBLAS/MKL=1. Полный профиль в JSON. Это source
acceptance конкретной среды, не wheel/portable или герметичный образ ОС.

## Все непройденные проверки

| Группа | FAIL | ERROR | Подтверждённая непосредственная причина | Минимальное будущее действие |
|---|---:|---:|---|---|
| responsive_layout | 1 | 0 | Окно900×720 с открытыми настройками: canvas167px при требовании >170px. То же167px на старомe9. | Локальное исправление компоновки с прежним критерием. |
| legacy_poll_count_assertion | 1 | 0 | Старый тест требует роста общего числа Tk timers после ручного `_poll`; fix404 заменяет один собственный poll без дубликатов. | Проверять владение одним timer, замену ID и продолжение обработки. |
| historical_control_row_binding | 51 | 0 | Старые receipts требуют исходник control_row до404; архивный mapping его не восстанавливает. | Добавить точную историческую копию только для соответствующего replay. |
| historical375_cargo_fixture | 0 | 10 | historical_checkout не восстанавливает весь source closure375; первый барьер Cargo metadata. | Восстанавливать все7точных исходников и проверять SHA. |
| historical032_cargo_metadata | 4 | 0 | Исторический032validator проверяет текущие Cargo0.3.3 против SHA0.3.2. | Разделить точные версии исторических metadata, не ослабляя live audit. |
| private_ancestor_setup | 6 | 0 | Наш source/TEMP под `.tools`: проверки абсолютных Path.parts считают публичные fixtures приватными. | Следующий запуск в обычных source/temp roots либо отдельное обоснованное исправление root-relative проверки. |
| **Всего** | **63** | **10** | Исходные результаты сохранены. | Ни одна группа не закрыта waiver. |

Точные nodeid, величины, traceback и распределение по файлам находятся в JSON
`failure_groups.failures`. Часть отрицательных тестов остановилась на более раннем
историческом барьере: их задуманные corruption checks здесь не подтверждены.
После устранения первых барьеров возможны дополнительные отказы; это неизвестно.

### Доказательства и воспроизводимые контроли

1. `tests/test_app_usability.py`, `_check_responsive_controls`: натуральный Tk
   layout на405 иe9 при тех же размерах/масштабе1.3333 воспроизводит167px.
   Результат не доказывает новую регрессию404. PNG контролей сделаны после
   закрытия панели настроек и **не являются изображением момента отказа**.
2. `tests/test_app_workflows.py`, `_check_worker_error`: исходный failing helper
   повторён без замены результата. На контрольной точке10timers до и после:
   восемь layout, canvas idle и один принадлежащий приложению poll. ID poll
   заменён; worker/future очищены, два ожидаемых сообщения об ошибке выданы.
   Отдельный natural-event контроль подтверждает один poll и чистое закрытие.
   Это показывает устаревшую проверку, но исходный обязательный FAIL остаётся.
3. `control_row.py`: ожидаемый старый SHA
   `0dbf30d3fc5212a3a58abc326fdda6d3f120be5f269827253d3ecffff85b2742`,
   фактический405
   `33c289f8716fb8a7e45f5d9775e3482a49c74650faa908a024d80358a3ee8026`.
   Старые байты существуют вe9 Git; registry их не выбирает. Текущий strict
   отказ корректен. Нельзя разрешать старые receipts для изменённого runtime.
4. `tests/test_sandbox_acceptance.py`, fixture `historical_checkout`: три
   доступных before383/381/380архива не содержат полного нужного closure375.
   Найдены7недостающих точных файлов: ERFA-LICENSE.txt, корневой pyproject.toml,
   solar_core Cargo.toml/lock, solar_native Cargo.toml/lock/pyproject.toml.
   Все7исходных SHA доступны в dev working tree и воспроизводятся из accepted032
   с исходным CRLF-представлением. Это неполная fixture, не потеря научных данных.
5. `release_history.py`: текущие Cargo metadata действительно0.3.3; отказ
   исторического032SHA не свидетельствует об ошибке физических расчётов.
6. `scripts/build_portable.py`, документарные unit tests: шесть пустых публичных
   seeds под `.tools` отклонены, в отдельном обычном каталоге скопированы6/6.
   JPL bundle test прошёл replay/metrics и упал на финальной абсолютной path
   проверке. Portable **не собиралась**. Это зависимость от нашего размещения;
   original6FAIL не переименованы в PASS по результатам контроля.

Полные контроли: raw `diagnostics/failure-groups.json`, `layout-405.json`,
`layout-e9.json`, `worker-original.json`, `poll-contract.json`,
`path-control.json` в новом архиве406; имена и SHA также связаны аудитом.
Исходники инструментов: [diagnose.py](../scripts/qualification406/diagnose.py).

Отдельный composition blocker: warning в frozen405 ссылается текстом на
`docs/q2-application-acceptance-402.md`, которого нет в этом checkout.
Поддерживающий отчёт404 тоже отсутствует, но это не вторая literal UI-ссылка.
Оба есть в dev. Нельзя молча подмешать dev docs к проверяемому кандидату.
Проверка1402Markdown line-links не проверяет такой обычный строковый литерал.

## Что прошло

Rust fmt core/native: PASS. Самостоятельный core собран `--release --locked
--offline`; Cargo core **19PASS/0FAIL/0ignored**. Doc/binary targets без тестов.
Все80тестов прямого compiled native API/dispatch прошли; перечень восьми файлов
в JSON. Это не включает упавшие historical replay guards. ABI проверен на
реальном `.pyd`, не на Python fallback. Rust source совпадает с qualified384,
SHA `.pyd` прежний; это не новая побитно воспроизводимая PyO3-сборка.

[GUI journey](../scripts/qualification406/gui_journey.py) выполнил два настоящих
пакета существующего DOP853 для свободного тела, реальные Start/Pause/Stop,
Python→Rust backend switch и178вызовов compiled point forces. Event задерживает
worker **перед** исходным расчётом; состояние и численный результат не замоканы.

Проверены отказ записи recovery до публикации, сохранение committed state,
успешный retry, сохранение/загрузка/reopen, закрытие активного окна после пакета,
две лаборатории и независимый callback host. Второе окно загружает точный
исторический402frame-100 с двумя Q2: q/S/settings неизменны при inspector,
save/load; нового Q2-интегрирования нет. Инспектор работал штатными Tk events.
После закрытия нет owned callbacks, foreign cancellations или фоновых ошибок
Tcl/Python. Свободное движение сверено аналитически до1e-12m только для этого
короткого функционального случая. PASS этого пути не закрывает GUI-suite FAIL.

Независимый аудит:61модуль скомпилирован,11импортов проверены по actual origin;
1227файлов кандидата и1402line-links проверены. Все3045JUnitузлов точно совпали
с sealed inventory. Git blobs и working SHA проверены раздельно по
аутентифицированному снимку405. Все использованные399–405input SHA неизменны.

## Ошибки самого стенда и ресурсы

- Путь JUnit в `PYTEST_ADDOPTS` с Windows backslashes разобран shlex неверно.
  Отчёт найден под непредусмотренным именем и перемещён с неизменным SHA;
  `junit-relocation.json` сохраняет оба пути и размер. Все3045узлов сохранены.
  В будущем использовать POSIX paths/корректное quoting. Executed source не
  переписан задним числом и полный прогон ради пути не повторён.
- `.tools` ancestor вызвал6описанных setup-dependent FAIL.
- Первый independent auditor ошибочно потребовал равенства Git LF bytes и
  checkout CRLF bytes восьми текстовых файлов. Его код/лог/стоимость сохранены.
  Исправленная версия проверяет Git object identity отдельно от прежних405raw
  SHA; все восемь совпали с предыдущим raw reference. Численные исходники и
  исторические SHA не нормировались и не заменялись.

| Учёт | CPU s | Active wall s |
|---|---:|---:|
| Preflight + initial allowance | 29.718750 | 21.794595 |
| Core build + отдельное завершение Rust | 41.812500 | 16.059723 |
| Полный stock driver | 1067.937500 | 568.714930 |
| Диагностика | 31.281250 | 17.604520 |
| GUI/recovery | 12.343750 | 7.291231 |
| Две попытки independent audit | 20.578125 | 13.060139 |
| Закрывающие SHA receipts | 2.578125 | 2.495213 |
| **Итого** | **1206.250000** | **647.020351** |

Прежние hard2400CPU/2700wall/3GiB/2GiB и early1920/2160/2.7GiB/1.8GiB
не повышались и не достигнуты. Sampled worker-private peak1153331200B,
data-tree peak1354492229B плюс отдельный консервативный1MiB для tiny path control.
Combined parent+worker private threshold контролировался, но его peak отдельно
не сохранён: worker peak нельзя выдавать за всю память этапа.

На полном прогоне worker550.984375CPU, supervisor515.640625CPU; надзор
существенно дорог из-за повторных обходов диска/дерева процессов.50ms — sleep,
а не гарантированная частота сэмпла. Это основание отдельно улучшить измеритель
до будущего повторения, не менять его исторические receipts. Memory/process
samples не continuous OS quota; учитываются .25s tail allowances и initial
2CPU/5wall allowance. Git/editor/cloud/remote CI здесь не измерены.
Оставшихся713.75earlyCPU меньше1067.94измеренной стоимости полного повторения:
повтор в этом бюджете NO-GO. Сравнение565.42wall pytest со старыми прогонами
не является speedup: исторические барьеры прерывают часть проверок раньше.

## Решения и дальнейшие действия

| Verdict | Результат |
|---|---|
| SOURCE_ACCEPTANCE | NO-GO:63FAIL/10ERROR и отсутствующий документ UI-ссылки |
| RUST_NATIVE_ACCEPTANCE | PASS только проверенного ABI/API/core/source scope |
| GUI_DESKTOP_ACCEPTANCE | FAIL:167px и незакрытый обязательный poll-test gate |
| WORKER_RECOVERY_ACCEPTANCE | Targeted real-runtime PASS; общий legacy gate открыт |
| SCIENTIFIC_EVIDENCE_SCOPE | Сохранён исторический scope; новая глобальная точность не заявлена |
| APPLICATION_D1 | NO-GO без изменений |
| PORTABLE_READINESS | NO-GO; сборка/relocated acceptance не запускались |
| RELEASE_READINESS | NO-GO |

Из399–405переиспользованы только явно связанные исходники/receipts для истории,
scope и точной идентичности; не новая научная аттестация405. Исторические D1:
numerical11/11PASS, effects10/11, distance_AB0.244795m при10mFAIL; три380и
четыре402convergence FAIL сохранены. Полная D1, произвольная Q2-траектория и
release0.3.3 не получили разрешения. Full380/58jobs399/22jobs402/annual385
не повторялись. Штатные короткие physics regressions полного pytest выполнены.

Минимальный **следующий отдельный этап**, без нового изменения физики:
исправить167px; актуализировать poll assertion по реальному ownership contract;
замкнуть точные375/032/history source fixtures; собрать docs-complete candidate;
выбрать нормальные source/temp roots и оценить стоимость disk supervisor.
Для каждого изменения сначала failing regression, затем сохранение старых SHA
и независимый отказ на подменённом live source. После этого нужен новый frozen
candidate/plan/budget и полная приёмка без автоматических waiver. Здесь STOP.

## Публикация и резервирование

В dev отправляются только инструменты, компактный отчёт и карта проекта.
Кандидат8fe, accepted main/v0.3.2, теги, LATEST, portable и квалифицированные
бинарники не изменяются. Личные документы — только отдельный приватный контекст.

Новый filtered406backup **CLOUD_VERIFIED_SHA256**: свежий независимый download,
SHA256/size/parent сверены для обоих файлов; аккаунт/папка проверены заново,
доступ owner-only. DriveFS отсутствует: использованы prepare queue и коннектор,
а не предположение о завершении синхронизации.

| Файл | Размер B | SHA256 | Drive ID |
|---|---:|---|---|
| Новый reviewed-v2 ZIP406 | 19482148 | `969960976ab1301f20bd80b47a0a6f804cdd3358c4f9364f7bdfffba19b2e649` | `1VqU-JXBI8nOXRNxoThFp5Ues-X1ZNX12` |
| Git restore recipe d891b3a | 582 | `84c06d6a4bb0664365e4b8db1120b069c6b5886bb780b286a34f0d29bb24ab78` | `19knvBu1NLOvGnZYhXbNUrFQJ33t2SDUm` |

819уникальных payload members,3274source aliases/точных Git restore references;
49546989B до сжатия. Локальный ZIP CRC и каждый member SHA проверены. Candidate8fe,
родитель098 и его родительe9 подтверждены до/после упаковки.399–405архивы не
выгружались повторно;404требует прежний append-only manifest erratum.

Первая упаковка отклонена nested-archive review: шесть намеренно повреждённых
NPZ-fixtures не проходят review как ZIP. Первый архив/код/ошибка сохранены
локально. Reviewed-v2 исключает эти6байтовых payload и ещё5защищённых/неоднозначных
имён, перечисляя исходный путь/размер/SHA/причину в manifest. Они не выдаются за
cloud-backed; все оригиналы остаются на ПК. Полные test logs/tracebacks и
GUI/recovery сохранены в облаке. Environment/source copies, кеши, зависимости,
SQLite, личный контекст и секреты в архив не включены. Чистые Git-файлы
восстанавливаются по точному commit/path/SHA, не загружаются повторно.

Операционный backup отдельно:48.1875CPU/47.0533384activewall; включая неудачную
упаковку и review, в пределах заранее заданных120CPU/900wall/1GiB/512MiB
(early96/720/900MiB/400MiB). Connector/editor CPU не измерен. Полные operational
receipts включены в машинный отчёт. Новых source/scientific запусков в этом
бюджете нет. Доказательства опубликованы в dev commit `d891b3a`; последующее
уточнение backup меняет только отчёт. Main/tags/LATEST/portable прежние. STOP.
