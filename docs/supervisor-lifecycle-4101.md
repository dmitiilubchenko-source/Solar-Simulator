# 410.1 — supervisor lifecycle: NO-GO / PARTIAL

2026-11-17. Изолированная ветка `codex/tooling-4101-supervisor-lifecycle`,
base `ebde749d11405c0fdeca640d9d515be6db61a59b`. Полная410 не запускалась.
[Машинный отчёт](supervisor-lifecycle-4101.json),
[независимый аудит](../scripts/qualification4101/independent-audit.json),
[diff](../scripts/qualification4101/monitor-diff.txt),
[недопущенный amendment](../scripts/qualification4101/admission-amendment410.json).

## Причина и границы исправления

Старый монитор409 неизменён. Он заканчивает цикл по root и пропускает cleanup,
когда root уже вышел. Исходное ложное complete=true воспроизведено вновь внутри
внешней тестовой Job: старый guard оставил известного потомка живым, новый
обнаружил остаток, очистил группу и сохранил FAIL. Исторические410 raw не изменены.

Polling не гарантирует обнаружения потомка короткоживущего родителя. Поэтому
проверен отдельный Windows Job Object, без breakaway, с KILL_ON_JOB_CLOSE:
root создаётся suspended, назначается Job, затем ResumeThread. Отказ назначения
не запускает работу root. Воздействие направлено на собственный job handle,
не на PID/имена Python. Обнаруженные процессы имеют retained handles и FILETIME;
перед использованием проверяется членство в Job. Перечень процессов sampled,
не объявляется исчерпывающим. CPU берётся один раз из Job, отдельно от supervisor.

Это изменение launcher. Impact: существующие acceptance wrappers/parsers не
трогались; новый CreateProcess-путь ещё не имеет stdout redirection и явного
sanitized environment block. Использовать его вместо frozen monitor в410 нельзя.
Это блокер совместимости, а не незаметная замена запуска в acceptance.

Microsoft описывает наследование Job и учёт завершённых процессов в
[Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject),
[Basic Accounting](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information).
Документация API не заменяет измерения текущего ПК.

## Проверки и сохранённые неуспехи

Четыре попытки по20 проб сохранены отдельно. Первая имела ошибочный `-m __main__`:
это отказ стенда, не проверка поведения worker. Усилено сопоставление конкретной
причины отказа. Во второй обнаружены недостаточные SYNCHRONIZE-права retained
handles; в третьей — асинхронность завершения после TerminateJobObject: нулевой
ActiveProcesses ещё не заменяет ожидание process handles. Исправлены права и
bounded wait, финальный CPU считывается после ожидания. Все версии сохранены.

В последней попытке20/20 ожидаемых **исходов проб**, не20/20 обязательных областей
квалификации. Root0/joined проходят; child/grandchild/venv/short-parent и исходный
старый ложный complete приводят к cleanup и FAIL; nonzero/crash, interrupt,
wall/CPU/private/disk stops, injected access/identity/acquisition/receipt-write
errors отклоняются. Все записанные PID/creation_time независимо проверены: завершены.

Не выдаём условные hooks за полную проверку гонок. Пробы13/14/15/19 недостаточны
для детерминированных exit-during-cleanup/discovery, настоящего PID reuse и
повторного termination. Проба20 воспроизводит старый FAIL, но не заменяет
обязательный unrelated-process control. Потеря supervisor, ошибка cleanup,
missing receipt/finalCPU и вся интеграция launcher ещё не квалифицированы.

**Независимый CPU audit остановил допуск.** В short-parent Job CPU=0.828125s,
retained-handle CPU sum=0.84375s, расхождение0.015625s. Это измеренное различие;
его причина UNRESOLVED. Предположения о tick resolution или времени обновления
kernel accounting не доказаны. Допуск и threshold не вводились; новой попытки
ради PASS нет. Первичный assert auditor сохранён, итоговый аудит сохраняет
расхождение как блокер вместо маскировки. Последние20 ожидаемых verdict не
доказывают корректность финального CPU accounting.

## Ресурсы и дальнейший допуск

Четыре synthetic suites: charged25.1875CPU (включая четыре allowance по1CPU
для намеренно несохранённых write-failure receipts),27.348524wall.
Review15CPU/30wall, finalization10CPU/20wall, backup reserve20CPU/40wall:
всего70.1875CPU/117.348524wall, ниже early96/240 и hard120/300.
Это смешанный учёт измерений и консервативных allowances, не полностью измеренный
operational CPU. Sampled fixture private peak147820544B; peak всей сессии неизвестен.
Memory/disk sampled, не OSquota. Raw локально Solar4101-20261117; backup отдельно.

Старый ledger41037.46875CPU/71.332329wall не обнулён. С предыдущим backup410
консервативно53.4375/114.919286; до early остаётся666.5625CPU/845.080714wall.
От исходного forecast650CPU остаётся лишь16.5625CPU на новый запас; новый monitor
overhead ещё не аттестован, новый forecast=null. Разрешения продолжать410 нет.

Следующее действие: независимо разобраться с CPU discrepancy и закрыть launcher
impact/непроверенные негативные контроли в отдельном плане; затем пересчитать
ресурсный forecast. Не править физику, ZIP, native, историческиеFAIL или caps.
Все научные ограничения399/380/402 и fullD1 NO-GO сохранены. Main/tag/LATEST/
accepted032 не менялись. После отчёта STOP; релиза нет.
