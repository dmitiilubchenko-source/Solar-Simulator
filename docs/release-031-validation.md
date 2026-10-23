# Приёмка Solar Simulator 0.3.1

23 октября 2026. Статус: финальные исходники и конкретный ZIP прошли приёмку.
Подготовлено в dev; main/tag/GitHub Release не менялись.
[Состав и ограничения](releases/v0.3.1.md).

## Зафиксированные критерии

Полная check_project.py --require-native без skip, реальные native/core
версии 0.3.1, cargo fmt/tests, pip check, неизменность исходников/данных/binary
во время приёмки. Настоящий новый ZIP: SHA/CRC, свежая распаковка в путь
с пробелами, изолированные runtime/Tcl/LOCALAPPDATA, прежние desktop/CLI/
recovery/record/playback/replay/continuous проверки и годовой Strict расчёт.
Дополнительно в поставке проверить новые переходы и фоновую загрузку/отмену.
LATEST менять только после успеха. Старый ZIP 0.3.0 и пользовательские данные
сохраняются. Новые измерения физической точности этим patch не обещаются.

## Проверка истории

Перед изменением метаданных сохранены точные байты шести product manifests/
locks и трёх offline replay scripts в scripts/validation/release030-sources.zip.
Архив — снимок dev d5898de до смены метаданных, а не полный снимок тега v0.3.0.
Явная карта release031-history.json закрепляет исходный и текущий SHA;
новый release_history.py принимает только эту переходную пару. Изменение
неизвестного исходника, Cargo content, карты или архива отклоняется. Cargo
допускает только прежнюю CRLF→LF нормализацию. Старые научные JSON/NPZ и их
пороги не меняются; исторический replay не квалифицирует runtime 0.3.1.

## Результаты

Исходный python CI subset: 108 PASS, 2 намеренно deselected Rust cases,
4.53 с. Это предварительный subset, не финальная приёмка без пропусков.
GitHub CI d5898de: Windows desktop-native и Linux python SUCCESS;
optional adaptive skipped. Последующие результаты будут записаны по факту.


## Первая приёмка исходников 0.3.1 — PASS

check_project.py --require-native: 2427 Python PASS за461.15с, 19 Rust,
fmt обоих production crates, 0skip; wall464.325729с. Реальный PyO3,
установленные solar-simulator/solar-native0.3.1, standalone core0.3.1.
SHA всех проверяемых code/data/metadata до/после совпали. Дополнительный
контроль установленного pyd выполнен отдельно от package __init__.py.
Никаких runtime/формул/src изменений поверхd5898de при подготовке не внесено.
Предварительные32history-tests44.10с и16packaging/GUI-tests30.02с PASS.

Обычная изолированная pip установка прошла без обновления зависимостей;
pip check PASS. Первая попытка --no-build-isolation отказала, поскольку
setuptools отсутствует в основном venv. Отказ сохранён, прямого изменения
состава numerical dependencies для его обхода не было.

## Совместимость с настоящей 0.3.0

Старый runtime принятой portable создал новые checkpoint/parent и три кадра
0/20/40с для Python DOP853 и Rust Verlet. 0.3.1 читает все поля/parent,
воспроизводит те же пакеты и побайтно совпадает с отдельным продолжением
в старом runtime. Сравнение дополнительно выполнено по байтам канонического JSON полного
состояния, включая знак нуля, а не только равенством float.
Исходные файлы не изменились. Строгий replay ожидаемо
отклоняет application_version/package_files, также native для Rust, до
создания output; старый recipe не переписывается.

Первый локальный тест сравнивал один длинный advance с двумя пакетами
DOP853: третий кадр отличался. Диагностика установила разные вызовы solver,
а не ошибку чтения. Проверка исправлена на прежние границы advance_towards;
продукт/допуски/исходные записи не менялись. Сохранены прежний тест и FAIL.

## Приёмка ZIP

На момент сборки: ожидает нового ZIP и relocation. Итог конкретного ZIP
добавляется в внешний отчёт после завершения; этот отчёт не используется
как самоподтверждение SHA собственного архива. Старый ZIP0.3.0 сохраняется.


## Сохранённые отказы первой поставки360

Первый ZIP SolarSimulator-0.3.1-20261023-193349.zip,112338916байт,
SHAe6d9641d19696d14bf52ff4e7431ee38bf4b030dad631f8b5945d0f91d804166:
сборка26.513729с, но ZIP-приёмка остановилась до годового расчёта. Новый
patch031 probe требовал LOCALAPPDATA внутри cwd, а общий checker использовал
соседний изолированный каталог. Caller теперь передаёт новому probe отдельные
LOCALAPPDATA/MPLCONFIGDIR внутри relocated workspace; защитная проверка не
ослаблялась. Это ошибка связки проверочных процессов, не физических уравнений.
ZIP, лог, первые исходники и предыдущая успешная source-приёмка сохранены.

Дополнительный LF-checkout выявил два отказа для root/native pyproject в новой
карте истории: она содержала лишние raw CRLF-переходы, которыми научные
replayers не пользуются. Они удалены из разрешённых переходов; точные байты
обоих файлов по-прежнему в неизменном SHA-bound архиве. Четыре Cargo-файла
продолжают использовать прежнюю CRLF→LF нормализацию, три Python replay
скрипта — точные байты. Добавлены обе полные LF/CRLF проверки замыкания карты.
Никаких old scientific SHA/JSON/NPZ или алгоритмов не исправляли ради PASS.
После правок требуется новая source-приёмка и новая поставка; первая0.3.1
не отмечается принятой и LATEST не меняет.


## Финальная приёмка — PASS

[Машиночитаемый отчёт, source SHA и все по-тельные результаты](release-031-validation.json).
Финальный check_project.py --require-native: 2429 Python за463.04с,
19 Rust/обе fmt/0skip; wall465.296753с. В отличие от первого
прогона включены LF/CRLF проверки всего замыкания карты. Источники/data/metadata
не менялись; реальный pyd проверен отдельно, исходники и установленный native
в поставке побайтно совпадают. Между проверками изменялись только описанные
проверочные инструменты; src/физические данные/Rust алгоритмы прежние.
В check_portable.py также нормализованы прежние смешанные окончания строк
в LF; смысловая правка — десять строк подключения нового изолированного probe.

ZIP `SolarSimulator-0.3.1-20261023-194752.zip`: 112338887байт.
SHA256: `20c3b150d9edad4598208517a031a225e235d7d5ed5888f49b23e392809f3d5b`.
Сборка26.333704с, новая ZIP-приёмка121.350337с.
Это стоимость стадий, не методически сопоставимый benchmark/обещание FPS.
Свежая распаковка с пробелами; python -I/локальные imports/Tcl/native и
изолированные профили. 79 runtime py/json/txt файлов
и четыре публичных научных ZIP совпали с source; CRC/SHA/исключение личного
и отсутствие REBOUND/solar_adaptive в runtime прошли.
Относительных ссылок в поставке: 570.

Прежние GUI/recovery/CLI final-write fallback/target-time/editor/record/
close/restart/playback/comparison/export/audit/full+stopped replay прошли.
Новый probe отдельно подтвердил 6 сохраняющих переходов и 6 отказов записи,
parent/current сохранность, Tk heartbeat при held reader, отмену открытия,
аналитическое свободное движение, reuse artists и playback без solver.
Не происходит автоматического удаления recovery или исходных записей.

## Годовой расчёт из финальной поставки

Новый свободный production Strict расчёт: 10тел, SI/SSB/EclipticJ2000,
JD2461321.5TDB/DE441, год31557600с, 125эпох/499пакетов;
7.778614с. EIH1PN+fixedSun/EarthJ2 reaction, giant-system GM,
per-body и relative Earth–Moon, прежние rtol3e-14/position_atol1e-3м/
velocity_atol1e-9мс. Все прежние цели10км на каждое тело и1км Earth–Moon PASS.
Максимальный телесный остаток к JPL: Moon
747.755283323м. Earth–Moon
718.824784521м / 0.0019776112364мс.
Earth–Moon отличие от прежнего125-grid cache: 0м.
Новых сетевых запросов JPL нет: прежние исходные ответы и SHA проверяются
из публичного bundle. Сохранённый replay сам solver не запускал; свежий год
запускал. Независимый RK45 относится к прежнему отдельному аудиту, а не
к этому production rerun. Нет гарантии между эпохами/для иных систем.
Continuous проверяет прежние выборки, но общий критерий остаётся false.
Старые Standard/PN/Noether/rotation/Kuiper/IAS15 FAIL сохранены.

LATEST переключён на этот ZIP только после приёмки. Принятый ZIP0.3.0
с прежним SHA и первый отвергнутый кандидат0.3.1 сохранены. Старые теги/main
не менялись. Публикация версии требует отдельного согласования результата.

## Проверенные места кода

[История SHA](C:/Users/Admin/Desktop/Solar-simulator/scripts/release_history.py:16),
[Cargo](C:/Users/Admin/Desktop/Solar-simulator/scripts/release_history.py:45),
[настоящий isolated probe](C:/Users/Admin/Desktop/Solar-simulator/scripts/portable_patch_workflows.py:13),
[реальный процесс в тесте](C:/Users/Admin/Desktop/Solar-simulator/tests/test_portable_patch.py:9),
[коррупция](C:/Users/Admin/Desktop/Solar-simulator/tests/test_release_history.py:37).
