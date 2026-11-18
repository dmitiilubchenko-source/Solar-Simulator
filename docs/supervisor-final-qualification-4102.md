# 410.2 — Windows supervisor: NO-GO/PARTIAL

2026-11-18. Новая изолированная ветка `codex/tooling-4102-supervisor-qualified`
от34d0766. Название ветки не является результатом квалификации. Full410 не запускалась.
[Raw audit](../scripts/qualification4102/independent-audit.json),
[machine report](supervisor-final-qualification-4102.json),
[невыданный amendment](../scripts/qualification4102/admission-amendment410-v2.json).

## Реализовано

Новая копия monitor4102 сохраняет suspended CreateProcessW → AssignJob → Resume.
Добавлены STARTUPINFOEX с HANDLE_LIST только stdin=NUL/stdout=stderr=log, Unicode
environment block, явный cwd, очищенные PYTHONPATH/PYTHONHOME и threadvars1.
Нет shell fallback. Job handle не наследуется. Assignment failure теперь отдельно
завершает suspended root, даже когда Job пуста; это подтверждённый недочёт прототипа410.1.
Старые monitor409/4101, физика, native, ZIP и acceptance scripts неизменны.

Ресурсные receipts расширены раздельными user/kernel100ns, FILETIME процессов,
Job membership, exit status, timestamps и тремя post-termination snapshots:
Job before → retained process CPU → Job after. CPU группы считается один раз,
CPU supervisor отдельно. Индивидуальный список sampled; неизвестные процессы
не выдуманы. Job остаётся источником агрегатного CPU по контракту Microsoft.

Первичные API:
[Job accounting](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information),
[CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw),
[STARTUPINFOEX/handle list](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute).
Шкала100ns не доказывает фактическую точность счётчика или равенство разных API.

## Фактические проверки

20/21 ожидаемых исходов одного нового фиксированного набора; прежние четыре
полные suites410.1 не повторялись. Проверены argv с кавычками/backslash/Unicode,
пути с пробелами, cwd, stdin EOF, threadvars, отсутствие Python env, stdout/stderr,
Tk startup/update/destroy без орбит. Root0/joined, orphan/grandchild, nonzero/crash,
CPU/wall/private/disk stops, interrupt, Create/Assign/Resume/access errors и
ошибка записи receipt дали ожидаемые результаты. Логи действительно сохранены.

Одна обязательная проверка **не пройдена**: finalCPU injection сработала на более
раннем accounting call, получен monitor-error, а не доказанный final-only отказ.
Внешний writer failure отмечен отдельно; штатный completion для него не выдуман.

9/9 дополнительных контролей: foreign handle не наследован; настоящий
IsProcessInJob=false path с foreign handle не убивает посторонний процесс;
repeated terminate пустой Job; новый reader отклоняет missing/invalid/noCPU/wrongSHA;
после abrupt supervisor os._exit(23) внешне подтверждено завершение известных
owned processes, completion отсутствует; посторонний процесс сохранился.
Это не реальный OS PID reuse и не тест всех существующих acceptance consumers.

Ошибки стенда сохранены: первый echo предполагал UTF8 при redirected stdout,
получил UnicodeEncodeError с системной cp1252; fixture теперь пишет ASCII JSON
с Unicode escapes. Launcher encoding не подменялся. Первый control runner
ошибочно вызвал -m __main__; исходник/traceback сохранены, это не successful
supervisor-loss control. Исправленный targeted control выполнен отдельно.

## CPU: что доказано и что неизвестно

Исторические0.828125Job vs0.84375retained410.1 сохранены. Старые handles уже
закрыты; исторические раздельные user/kernel для пропущенных процессов восстановить
невозможно. Новые полные snapshots получены без повторного worker интегрирования.
В неинъецированных случаях три финальных Job снимка устойчивы, но расхождения с
process sums сохраняются в обе стороны. Например joined3.09375 vs3.109375,
orphan0.609375 vs0.625; grand0.609375 vs0.546875. Последний пример также включает
процессы между samples. Совпадение времени чтения не устранило различия.

Microsoft определяет Job totals для всех активных и завершённых процессов;
математическое равенство с суммой sampled process counters не заявлено.
Однако конкретный механизм наблюдаемых различий не установлен. Не вводился
tolerance, не объявлялось округление доказанной причиной. CPU reconciliation
остаётся UNRESOLVED для полного admission. Стабильность счётчиков не является
доказательством отсутствия всех accounting/ownership ошибок.

## Незакрытые области и ресурсное решение

Нужны корректный final-only CPU fault, детерминированные exit/discovery races,
nested restrictions/breakaway, compatibility со штатным acceptance consumer,
аудит исключений при finalization/close/save. PID mismatch смоделирован реальным
foreign handle, но реального reuse не происходило. Нельзя выдать полный GO.

Видимый Job CPU8.9375s и harness parent0.21875s; suites13.288172wall.
С консервативными allowances и резервом backup25CPU/150wall:84.15625CPU /
288.288172wall, нижеearly144/480 иhard180/600. Данные не являются полностью
измеренным CPU всей сессии; peak всей сессии неизвестен. Fixture sample108122112B.
Раздельные allowances сохранены в machine audit. CPU аварийно потерянного
supervisor и несохранённых receipts не объявлен нулём, покрыт10CPU/15wall.

Ledger41053.4375CPU/114.919286wall с прежним backup неизменен. Early headroom
666.5625CPU/845.080714wall. Старый forecast650CPU оставляет16.5625CPU на новую
неопределённость. Short-test overhead не является стоимостью полного portable.
Квалифицированного нового forecast нет; amendment **не выдан**. Ни caps, ни
исторические FAIL, ни scientific criteria не изменены. После отчёта STOP.
