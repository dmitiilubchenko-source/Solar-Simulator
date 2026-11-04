# Совместимость 387: PARTIAL_RESOURCE_STOP

4 ноября 2026. **NO-GO для закрытия межверсионного qualification gate.**
Подлинность принятой portable032 подтверждена; её подготовка остановлена
надзором до создания IC и до первого интегрирования. Межверсионные A/B/C
остаются UNRESOLVED. Это не обнаруженная несовместимость физических результатов.

## Фактически проверенные версии

| Объект | Подтверждение |
|---|---|
| dev до работы | e2d96647df941218458d9d928afd965f98c47867, origin/dev совпадал |
| Принятые main/v0.3.2 | cf653c9ca4b60649e70658b002a5e70669411266 |
| Оригинальная portable032 | SolarSimulator-0.3.2-20261025-121729.zip, 112312650 bytes |
| ZIP SHA256 | 7c578220ec77e792aa9589f32a30352e88277d0d096bff0ad3ca5aae9c014c49 |
| Native032 SHA256 | 0cbc389f139854628f287c04a7cea52c530a18294c2c3a0670faa48bf53c0601 |
| Portable Python executable SHA256 | 410c1771d8d7d3d5ca672b335f4402e73fb1d6b9b4b12f73984e19d5e9ce5f8f |
| Кандидат033 | fe0f456f2c7ba3a077eac21fc8413937d6e84fac, отдельный checkout/venv |
| Native033 SHA256 | 651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091 |
| Environment033 SHA256 | 056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a |

Потоково проверены CRC и SHA всех **5979 файлов** ZIP против существующего
каталога поставки: 318154662 распакованных bytes, лишних файлов нет. Новая
полная распаковка не выполнялась. Отдельный read-only `git archive` main
подтвердил79 runtime/data файлов; восьмидесятый src/solar_simulator/README.md
не установлен wheel, это документация, а не изменённый физический модуль.
Новый source-bound verify_freeze подтвердил394 source entries и действительное
окружение кандидата. Developer metadata0.3.2 не использована вместо baseline.

BUILD-INFO оригинала фиксирует Python3.14.2t/cp314t-win_amd64, NumPy2.5.1,
SciPy1.18.1, Matplotlib3.11.0 и native/core0.3.2. Эти версии подтверждены
байтами поставки/её manifest; полноценный runtime fingerprint032 в новом запуске
**не получен**. Candidate dependency fingerprint проверен фактическими импортами.
Текущая Windows не является восстановленным образом исторической ОС.

## Контракт и остановка

[Предварительный контракт](compatibility-387-plan.md) зафиксирован до исполнения.
Execution binding сохраняет команды и SHA исходного worker/monitor/плана.
Планировались четыре модели × Python/Rust, времена0/50/100/150s, same-packet
resume, схемы1–10, ветка/recovery, GUI cancel/error и старый отказ двум Q2.
JSON с точными IC и их SHA должен был быть создан baseline до первого advance.
Эта фаза **не достигнута**: `inputs/` и `plan.json` не созданы; ни одной
научной орбиты или новой application-траектории Q2 нет.

Ранний sampled-private guard900MiB сработал при подготовке оригинальной032:
exit15, reason `private-memory`,21samples/50ms, rootCPU1.0625s,
wall1.1597975s, private1018.8046875MiB, RSS71.25MiB. Worker был остановлен
надзором, а не завершился с доказанной Python/runtime ошибкой.
Его отдельный sampled private peak ниже верхнего1024MiB; запас лишь5.20MiB.
Пик supervisor36.00MiB; совпадение этих пиков во времени не измерено.
Нельзя утверждать ни соблюдение combined upper в каждый момент, ни доказанное
превышение отдельным процессом1GiB. Ранний900MiB guard не ослаблялся, повторной
попытки acquisition не было. Причина большого private при небольшом RSS unknown.

**Критическая самопроверка:** attempted prepare очищал numerical thread overrides
до NumPy imports. Это было предположение о старом запуске, не подтверждённый
исторический fingerprint. BUILD-INFO не доказывает значения этих переменных.
Поэтому даже успешную подготовку нельзя было бы назвать восстановлением точной
исторической launch-time среды. OpenBLAS/число потоков — только возможная причина
расхода памяти, без причинного теста. Никакие настройки не менялись после
просмотра точности; измерений точности вообще не было. Не запускать single-thread
«замену исторической среды» под прежним названием.

Первая попытка запустить supervisor developer-интерпретатором завершилась
ModuleNotFoundError(psutil) до мониторинга и до запуска portable; её tool wall0.1887s,
CPU не измерен. Затем supervisor запущен существующим candidate-интерпретатором,
где psutil уже установлен; окружения не переустанавливались.

## Результаты по направлениям

| Направление | Выполнено | Статус |
|---|---|---|
| Provenance032 | ZIP/member CRC/SHA, native, Python,79main runtime/data files | PASS для файлов поставки |
| Freeze033 | Actual source/environment/native,394entries | PASS |
| A: схемы1–9 и один Q2/schema10, старые JSON | Только статическая карта storage; ни один fixture не исполнен | UNRESOLVED |
| A/C: parent/recovery/save-resume | Не запускались | UNRESOLVED |
| C: GUI cancel/corrupt/schema/wrong native | Не запускались в двух настоящих средах | UNRESOLVED |
| C: старый отказ двум Q2 | По коду ожидается; файл/поведение не проверены | UNRESOLVED |
| B: Sun–Earth Verlet, Python/Rust | 0/2cases | NOT RUN |
| B: Sun–Earth DOP853, Python/Rust | 0/2cases | NOT RUN |
| B: Sun–Earth–Moon DOP853, Python/Rust | 0/2cases | NOT RUN |
| B: один synthetic Q2, Python/Rust | 0/2cases | NOT RUN |

Таблица **реальных численных различий пуста**: сравнимые массивы не получены.
Нули Δr/Δv, совпадение E/P/L или exact restart не приписываются отсутствующим
данным. Изменение version/native/package fingerprint ожидается по файлам,
но strict recipe replay cross-version на этих двух средах здесь не выполнен.

## Инструменты и независимая проверка

Публичный [read-only verifier/observer](../scripts/check_compatibility387.py)
проверяет portable и отдельно сохранённые массивы; **не интегрирует**.
Независимый observer не импортирует Solar evaluators: binary64 bits,
math.dist/fsum, Newton kinetic/pair potential, MacCullagh body-frame inertia,
E/P/L в SI. Он проверен только на синтетических fixtures, не на межверсионных
орбитах. Совпадение своих тестов не доказывает физическую корректность Solar.

[Тесты](../tests/test_compatibility387.py): **10 PASS,0FAIL,0skip**,0.22s pytest.
Проверены аналитическая точечная пара, сферический rotator, осевой Q2-потенциал,
ошибочный ZIP SHA, изменённый/отсутствующий member, лишний .pth, traversal,
exclusive write, signed zero, сохранение обнаружимого расхождения без допуска.
Исходный незавершённый acquisition worker сохранён побитно локально с SHA
2102fba85c7a25c147ebc6fda2af8d0b1c995409c236ca9f116df076901e138f;
в публичный runtime не включён. Исторический execution-binding не переписан.

Machine summary: [compatibility-387-validation.json](compatibility-387-validation.json).
Raw: `.tools/qualification387/{execution-binding,portable-verification,resource-summary,
postflight-resources,static-audit,candidate-postflight,final-resources}.json`,
guard directories/stdout и preserved worker. Прежние evidence/SHA сохранены.

## Ресурсы и решение

Учтённые процессы/supervision: **11.015625 CPU s**, активные интервалы
**12.8479393 wall s**,1090088 bytes до финального отчёта/архива. Дополнительно
неизмеренный ранний launcher0.1887s tool wall; это ограничение учёта, не0CPU.
Postflight112631808bytes sampled worker private; не повторял acquisition.
Редактирование, сеть, Git и резервирование отдельно;50ms sampling не hardquota.

Runtime, силы, интегратор, settings, candidate, oldscience, main/tag/LATEST не менялись.
Изменения runtime **не обоснованы**: численная несовместимость не исследована.
Полноценное принятие033/main/portable — **NO-GO**; закрыты только provenance
и инструментарий. Newton384/annual385 сохраняют свой scope; три FAIL380,
неутверждённые A/B/B_app/reference-uncertainty policy386 остаются открытыми.

Следующий небольшой этап: локализовать startup/private-memory без орбит и
без изменения лимита, установить документируемую launch-time среду032;
после отдельного нового preflight вернуться к уже фиксированным A/B/C cases.
Не объявлять восстановление невозможным в принципе: доказан только этот
ограниченный resource stop. Модель: GPT-6.1 Sol High.
