# Compatibility390: последний отрицательный контроль пройден

5 ноября 2026. **PASS: оригинальная portable0.3.2 безопасно отвергает файл
с двумя динамическими Q2-фигурами.** Связанное [итоговое assessment387–390](compatibility-387-390-assessment.md)
закрывает ограниченный A/B/C gate. Это не принятие релиза0.3.3.

[План до выполнения](compatibility-390-plan.md),
[машинный отчёт](compatibility-390-validation.json).

## Подлинные источники и файл

Рабочая база devfcca77646ff5a261cbf46749026403c13d60e9f9, дерево было чистым.
Accepted main/tag032cf653c9ca4b60649e70658b002a5e70669411266,
candidate033fe0f456f2c7ba3a077eac21fc8413937d6e84fac не менялись.
ZIP032112312650bytes, SHA7c578220ec77e792aa9589f32a30352e88277d0d096bff0ad3ca5aae9c014c49
повторно проверен; critical installed package/Python/native files сверены с389ZIPmanifest.
Полная5979member CRC-проверка389 не повторялась. Все394candidate source hashes,
его HEAD/clean tree и13protected historical SHA проверены без орбит.

Использован существующий389two-q2.json,4382bytes,
SHAa56269a82892b6dc740b309e77db2a085dca7ad3ed563e40e1964e3e66461055.
SHA совпал с tracked389report и member уже сохранённого389archive
fced37db7decb52f3475196effeaaced3702c0f75206851a0961b9d2138d3e5c.
Новых IC/сценариев нет. Schema10, originNone, две distinct initial/current фигуры,
оба q/S, конечные значения и отсутствие внешних URL/путей проверены отдельно.
Настоящий кандидат033 успешно выполнил load→to_document: весь документ и bits
q/S сохранились. Проверка его полных constructor/storage contracts не заменялась
ручной проверкой количества элементов.

## Выполненный отказ и сохранность опыта

Старая версия запускалась из originaldist/runtime/python.exe, не developer-runtime.
Baseline — существующий389accepted/one-q2-dop853-python/frame-1.json,
SHAbdb3ec1147785014646a8656bc38a5762c85d0ad5fb6c3f9d127b2a70f18c1dc:
валидный сохранённый опыт с одной Q2 при t=50s. Он не пересчитывался.

| Проверка | Наблюдаемый результат |
|---|---|
|Old032 storage.load(two-q2.json)|ValueError: «Схема 10 требует одну динамическую фигуру»|
|Штатный GUI button/error route|Реальный Laboratory._guard(_load) вызвал messagebox.showerror с тем же сообщением и заголовком «Расчёт не выполнен»|
|Частичное принятие/потеря второй фигуры|Нового опыта не возвращено, исходный объект Laboratory.experiment сохранил identity|
|Настройки, parent, полный документ|Не изменились; before.json/after.json совпали побайтно и по SHA|
|Initial/current q/S старого опыта|Все bits совпали, дополнительно независимо сравнены float.hex|
|Recovery во время отказа|Каталог и его содержимое не изменились|
|Контрольное сохранение после отказа|Корректный старый one-Q2 checkpoint, полностью равный baseline|
|Контрольное recovery после отказа|Загружено и независимо перечитано: валидный one-Q2 checkpoint, q/S сохранены|
|Fallback/численные расчёты|0integration calls; временные sentinels запрещали advance/evolve/integrate|

Мокировались только выбор файлов и доставка модального messagebox, не loader
или результат валидации. Контрольные save/recovery вызваны отдельно **после**
доказательства отсутствия файловых изменений при отказе. После sentinels все
runtime functions восстановлены до проверки конечного fingerprint.
Исходные two-q2.json и baseline сохранили SHA до/после всех действий.
Это отказ от неподдерживаемой cardinality существующей schema10, а не признание
валидного нового файла повреждённым или молчаливое удаление q/S.

## Окружение, независимая проверка и ресурсы

CURRENT profile доNumPy/SciPy: OMP/OPENBLAS/MKL=1, VECLIB/NUMEXPR/PYTHONHASHSEED unset.
Actual prefixes/packages, Python3.14.2t/cp314t-win_amd64, NumPy2.5.1/SciPy1.18.1,
compiled native locations и SHA проверены. Old loaded BLAS NumPy/SciPy сообщили1.

| Файл | SHA256 |
|---|---|
|Old032 native|0cbc389f139854628f287c04a7cea52c530a18294c2c3a0670faa48bf53c0601|
|Candidate033 native|651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091|
|Old032 actual environment before/after|4d8838ca01dc6f9f00f74b97c5142bb2dcaa82b8f7ce355192c735bac0b7f335|
|Candidate033 actual environment|056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a|

Actual FP dictionaries совпали с corresponding389records. Не утверждается
побитовое восстановление исторических unset-запусков/ОС; FP hashes описывают
файлы и настройки, не полную аттестацию загруженного кода/драйверов.
Independent audit не импортировал Solar: перечитал raw before/after, inputSHA,
baseline, post-error save/recovery, initial/current q/S и error payload. Готовые
PASS-флаги не использовались вместо сравнения этих данных. Исходные389TypeError
и CPUSTOP отдельно SHA-проверены и оставлены неизменными.

3guard tests PASS/0FAIL/0skip. Новый390budget независим от389:
**22.546875CPU s /21.84729active wall s**,963812bytes до документов/архива.
External worker peak180408320bytes(~172.05MiB), supervisorpeakcommit37855232bytes;
self old178450432bytes/new177598464bytes. Ни один early-stop не сработал.
Пределы30CPU/90wall/512MiB/16MiB и early25CPU/75wall/450MiB/14MiB не менялись.
Самплирование50ms external/10ms self, retained finalCPU handles; это не OS hardquota.
Controller включён, документы/Git/network/backup отдельно. Интеграций0.

**GO ограниченному compatibility assessment387–390.** Старый389PARTIAL остаётся
исторически верным: недостающий контроль выполнен отдельным390, не задним числом.
Production/core/native/candidate/main/tags/LATEST/научные критерии не изменены.
Следующий шаг — решение владельца по Q2 policy/B_app и план финальной приёмки033,
не новый цикл этих восьми орбит. Отдельный Rust Standard20 diagnosticFAIL385
также сохранён; он не входит в MandatoryStrict gate и не исправлен compatibility.
После390STOP. Модель следующего review: Sol High.
