# Исполняемая подготовка0.3.3: этап383

30 октября2026. Это техническая подготовка, не выполненная scientific qualification.
Принятые main/portable0.3.2 и LATEST сохраняются.

## Контракт

[План382](qualification-033-plan.md) сохраняет исходные научные критерии.
[prepare_qualification383.py](../scripts/prepare_qualification383.py) экспортирует
точный Git commit в новый каталог, меняет только шесть package metadata на0.3.3
и записывает before/after SHA. Это commit плюс явно объявленный overlay,
а не чистый checkout с придуманным SHA. Большие historical docs/*-samples.npz
пропускаются как восстанавливаемые Git-данные: перед full acceptance вернуть
их по candidate-staging.json. Изоляция native/Python-пакета отдельная;
численные зависимости разделяются read-only с исходной средой, пути и реальные
хеши фиксируются. Это ещё не аттестация независимой установки portable.

375 получает --work, --protocol и --protocol-sha256; reducer также --report/--arrays.
376 получает --protocol/--protocol-sha256 и прежний --output; reducer принимает
--run-directory/--work/--protocol/--report/--arrays/--guard-file. Новая попытка
не наследует старые failures, guard CPU или grid-MRE. Отсутствующие метрики
обозначаются measurement_available=false, не нулевым измерением.
380 сохраняет --plan/--output и добавляет явный --plan-sha256; новый sealed plan
может включать уже существующий continuous_control без reuse старых arrays.
Везде старые defaults сохранены. Существующий output отклоняется; новые планы
проверяют SHA, вычислительные source и фактическое environment. Не исполняется
код/команда из JSON. Исторические source доступны только offline resolver;
актуальный375 gate не получает разрешение из архива.

## Границы текущей работы

Общий preflight cap:180CPU s,360active wall s,1GiB private,256MiB новых файлов.
Включены red/fault/regression проверки, копирование ограниченного candidate,
wheels/native build и короткая synthetic two-Q2 save/resume probe; время
редактирования и облачного резервирования не является временем вычислений.
Старый50ms monitor с early margins; CPU worker tree и supervisor отдельно.
Выборка и короткий интервал фиксируются до запуска, критерий — техническая
совместимость, неизменность q/S/settings и точное same-packet продолжение,
не научная точность. Нет годового EIH/JPL, полного380/check_project/portable.

Три исторических380 FAIL сохраняются. Packet-convergence scope требует
отдельного решения до основной two-Q2 квалификации. Кандидат с новым native
также не удовлетворяет автоматически старому375 accepted032 same-environment
контракту; этот отказ нельзя обходить fake fingerprint или заменой receipt.
Выбор корректного нового comparison scope — отдельное решение до annual jobs.
Технически параметризованный driver не означает одобрение такого решения.

## Фактически выполнено

Source commit9065c77ce1197aefd0315d0dc1b7c4b5d967d2e6 плюс шесть явных
metadata overlays0.3.3. Разработческий dev/установка остаются0.3.2.
Новый native0.3.3 SHA651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091;
Python3.14.2t/cp314t-win_amd64, NumPy2.5.1, SciPy1.18.1, Matplotlib3.11.0;
rustc1.99.0 GNU, maturin1.15.0/PyO3.29.3 release. Native заново собран
в отдельном target с копией warm cache; старый установленный бинарник не тронут.
Python/native wheel versions и Cargo/lock metadata согласованы.
Подробные SHA/наблюдения: [машинный отчёт](qualification-033-preflight.json).

70 targeted tests с обязательным native,0skip; source Python CI687PASS после разделения native-контракта,
4 прежних deselect,0skip. Прежние8cases/24canonical snapshots byte-exact
в исходной среде; offline380 независимо воспроизводит3FAIL. AST семи
численных helpers совпадает с сохранёнными исходниками. Src/Rust physics,
старые protocol/receipt/arrays/native/LATEST не менялись.

В отдельной candidate venv, включая запуск wheel package через -I, оба
backend прошли synthetic two-Q2 .125s prefix и .125s suffix, точные file
roundtrip/continue, неизменность seed/settings при read-only report.
Реальные375/376/380 sealed планы проверены без интегрирования: valid plan
доходит до отказа reuse output; bad SHA и изменённое реальное OMP окружение
отклоняются до создания output. SI/DE441/JD2461321.5TDB/рамка/atol и все
закреплённые входы375 проверены; математические блоки новых планов равны старым.

Сохранены все preparation FAIL:11 red tests;7 setup errors исторической fixture
до добавления точного нового архива; отсутствие setuptools.build_meta;
затем отсутствие maturin script. Попытка добавить PATH не помогла: прочитанный
maturin.__main__ ищет sysconfig Scripts, поэтому скопирован настоящий
SHA-совпадающий maturin.exe только в candidate. Build-only setuptools84.2.1 и
wheel0.48.0 получены по PyPI metadata/SHA, установлены только в candidate.
Полный frozen recipe и logs локальны в .tools/qualification383 и резервном ZIP.

Суммарно по всем запускам, включая неуспехи:142.156250 измеренных CPU s,
92.176484 active wall s; sampled worker-tree peak560496640B (~534.5MiB),
новые файлы229626275B (~219.0MiB) до compact report/archive.
Supervision CPU включён. RAM пиков supervisor и исчерпывающего inventory
временных файлов вне stage нет; короткие процессы/пики между выборками могут
быть пропущены. 50ms — пауза monitor, не гарантированный фактический интервал
при обходе файлов. Это измерение с ограничениями, не доказанный OS hard bound.

## Решение и следующий шаг

GO техническая подготовка; Newton376 технически исполним после отдельного
старта его бюджета. **NO-GO основной квалификации0.3.3 сейчас**: не согласованы
новый comparison scope375 и packet-monotonicity scope380; нет финального
clean candidate commit/portable isolation. Старое375 environment отличается
application_version/native и thread settings, а не повреждением данных.
Не заменять старый receipt, не объявлять сравнение одинаковой средой.

Перед дальнейшей scientific qualification выбрать final source+metadata+native
freeze, явно решить два scope-вопроса, затем запускать отдельные фазы по
плану382. Сейчас работа останавливается; годовых/full380/full check_project/
portable jobs, main/tag/release/LATEST не было. Проверка новой portable может
потребовать именно нового связанного с ней исполнения: версия сама по себе
не доказывает идентичность native SHA.


Удалённый Linux CI41084797957 сохранил2FAIL/686PASS/1прежнийnativeSkip/4deselect:
два новых test_380 контракта требовали настоящий native в Python-only job.
Это ошибка назначения новых тестов, не отказ runtime. Они перенесены без
ослабления в обязательный desktop-native subset отдельным файлом; новых
skip/xfail нет. Локально19 контрактных проверок после разделения проходят
с native audit; Python subset заново687PASS/4прежнихdeselect.
