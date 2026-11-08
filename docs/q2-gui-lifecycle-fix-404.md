# Исправление завершения GUI — этап 404

2026-11-08. **Технический GO отдельного GUI-кандидата в проверенной среде.**
Полный прикладной допуск D1 и выпуск 0.3.3 остаются **NO-GO**.
[Машинный отчёт](q2-gui-lifecycle-fix-404.json) содержит исходные привязки и результаты.

## Кандидат и границы изменения

Ветка `codex/candidate-0.3.3-gui-teardown-404`, commit
`0985860f1776594a565f5754275fd110a00e29f2`, точный родитель
`e9ddd352ac3dbff2eb8e2c5e37370aecd59fb5db`.
Изменены только `src/solar_simulator/app.py` и `control_row.py`: 50 добавленных,
2 удалённые строки. Это изменение поведения GUI, а не только текста.
Исходные e9ddd352, a99f73a, f723a216 и fe0f456 не изменены.

Новый actual runtime fingerprint:
`81f9b67806a0b258a4a4b5ec0f8d535f56e23c0ab4bf81125f3375fa090de805`.
Исходный fingerprint `d53f18828b57cb63a7a5c9eab92d4ee1d264fe31b44174ffa00806f5759b06a4`
не присваивается новому кандидату. Профили различаются только двумя GUI-модулями.
Python 3.14.2t, NumPy 2.5.1, SciPy 1.18.1, Matplotlib 3.11.0,
solar-native 0.3.3; зависимости из квалифицированной среды 384, импорт — из нового worktree.
Native SHA-256:
`651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`.
Tcl/Tk 8.6.15. Это source-кандидат, не квалификация wheel или portable.

## Причина и исправление

При destroy Tk удалял зарегистрированные Python/Tcl-команды, но в очереди
оставались их afterID. Неизменённый минимальный reproducer 403 на точном e9
получил **10 ошибок invalid command name**: poll — 1, layout — 8, idle_draw — 1.
После исправления та же функция с тем же assertion получила **0 ошибок**.
После закрытия продолжалась обработка событий сохранённого Tcl-интерпретатора;
успешное завершение процесса само по себе не считалось доказательством.

- `Laboratory` хранит afterID poll. Ручной `_poll()` отменяет ожидающий собственный
  timer и заменяет его одним новым; обычный интервал 40 мс сохранён. При активном
  worker запрос закрытия продолжает ждать пакет. Окончательный destroy отменяет timer.
- `ControlRow` отменяет свой pending idle на самом владельце, запрещает новые
  регистрации при destroy и допускает повторный destroy. Уже исполняющийся
  callback не отменяется как pending. Геометрия, Configure/Map и resize сохранены.
- Embedded TkAgg не проходит через `FigureManagerTk.destroy`. Cleanup canvas
  отменяет его `_idle_draw_id` и `_event_loop_id` через соответствующий widget.
  До любых отмен проверяются поля, типы ID, имя команды и принадлежность
  `widget._tclCommands`. Неизвестный или чужой контракт отклоняется до destroy:
  окно и состояние остаются доступны для исправления причины и повторной попытки.

Нет глобальной отмены очереди, подавления TclError, патча Matplotlib или закрытия
чужих figures. Используются private API Matplotlib/Tkinter: это явный риск.
Проверен контракт Matplotlib 3.11.0/Python 3.14.2t; совпадение полей в будущей
версии не гарантирует совпадение семантики. После обновления зависимостей нужна
повторная относящаяся GUI-проверка. Произвольное внешнее embedding не аттестовано.
Backend SHA-256: `ce1142ad3a384ebc491a1543f7a499f6203624f24fe7caccdd60d1396c63c23f`.

## Проверки без новых орбит

[План](../scripts/qualification404/plan.json) заморожен до запуска, SHA-256
`b187f4f4519df51ae1c86a51b613f7fd8eb7bb90ea3fe7a8aa4445628fa0416d`. Исходный FAIL сохранён в baseline, не скрыт skip/xfail.
[Исполнитель](../scripts/qualification404/check_gui.py) выполнил 18 случаев:

| Случай | Статус | Background errors | Registrations | Cancellations |
|---|---|---|---|---|
| `zero_figures_close` | PASS | 0 | 10 | 10 |
| `one_figure_close` | PASS | 0 | 10 | 10 |
| `two_figures_pending_all` | PASS | 0 | 10 | 10 |
| `manual_and_scheduled_poll` | PASS | 0 | 16 | 6 |
| `controlrow_owners_and_repeat_destroy` | PASS | 0 | 2 | 1 |
| `executing_layout_destroy` | PASS | 0 | 2 | 0 |
| `canvas_event_loop_cleanup` | PASS | 0 | 12 | 11 |
| `completed_worker` | PASS | 0 | 13 | 1 |
| `active_programmatic_close` | PASS | 0 | 11 | 1 |
| `active_request_close` | PASS | 0 | 11 | 1 |
| `stop_keeps_window` | PASS | 0 | 21 | 1 |
| `worker_failure` | PASS | 0 | 21 | 1 |
| `save_failure_retry` | PASS | 0 | 10 | 10 |
| `active_worker_save_failure_retry` | PASS | 0 | 13 | 1 |
| `two_windows_and_foreign_callbacks` | PASS | 0 | 36 | 11 |
| `canvas_contract_and_foreign_owner` | PASS | 0 | 36 | 11 |
| `resize_layout_draw` | PASS | 0 | 40 | 1 |
| `user_save_load` | PASS | 0 | 10 | 10 |

Каждый случай содержит реальные afterID, имена Tcl-команд, владельцев, времена
регистрации/отмены и очереди до/после destroy. Отмена выполняется тем widget,
который зарегистрировал callback. После закрытия принадлежащая окну очередь пуста.
Матрица включает отдельные Tcl-интерпретаторы при последовательном открытии окон
и два одновременно живых окна в одном host: чужие timer/canvas остаются активны.
Проверены manual/scheduled poll, исполняющийся layout, event loop canvas, resize/draw,
0/1/2 Q2, сохранение/загрузка и отмена пользовательского действия без изменения опыта.

Worker использует настоящий executor с инертным управляемым результатом — сохранённым
кадром 402; вызовы физических solver запрещены. Проверены stop, close, request_close,
ошибка worker, ошибка сохранения и повторная попытка, включая активный worker.
Семантика: завершить текущий пакет → committed state → atomic recovery → destroy.
Ошибка записи сохраняет окно, состояние и poll. После подтверждённого закрытия
новое вычисление не начинается; существующий `shutdown(wait=False)` не менялся.

Recovery байты совпали с исходным 403, SHA-256:
`f678795c5ef0839722639ec7a0ee91df70a1609a2541a261dd689169edf5ee5e`.
Происхождение frame-100 подтверждено receipt 402 и SHA, а не только временем/именем.
Все q/S, настройки, пользовательские документы и recovery проверены без мутаций.

[Независимый аудитор](../scripts/qualification404/audit.py) проверил raw файлы,
completion/SHA, владельцев отмены, отсутствие ошибок и точность recovery; он не
ограничился чтением PASS-флагов. [AST/byte guard](../scripts/q2_lifecycle_delta404.py)
сверил полный Git diff и неизменность всех остальных исходников. После удаления
только новых lifecycle-операций тела dispatch, recovery, обработки ошибок и геометрии
побитно/структурно прежние. Newton/EIH/Q2, силы, моменты, Hamiltonian/R-reuse,
Python/Rust интеграторы, IC, допуски, ABI/native и storage неизменны.
[Четыре портативных контроля](../tests/test_q2_lifecycle404.py): **4 PASS, 0 skip**;
запрещённые изменения методов, imports и остальных байтов отклоняются.
Точный reproducer 403 после исправления тоже PASS. Inventory и ссылки проверены.

Delta-only достаточна для этого ограниченного GUI-допуска: численные пути неизменны,
затронутые переходы проверены. Это не новая научная квалификация. Старые source-bound
receipts не перенесены на новый fingerprint. **Новых орбит — 0**; scientific matrix,
JPL, performance benchmarks и full portable acceptance не запускались.

## Сохранённые научные ограничения

Результат 402 неизменён: numerical budgets **11/11 PASS**, demonstrated effects
**10/11**, distance_AB **0.244795 м при требовании 10 м — FAIL**.
Полный D1 — NO-GO; сохранены четыре коротких convergence FAIL и три исторических
FAIL 380. Δ/B/U/N, IC, времена и критерии не менялись. A+D1 разрешены владельцем
только как ограниченная учебная демонстрация.

Текст inspection из e9 сохранён дословно. Фраза о нерешённом lifecycle теперь
устарела; нужна последующая минимальная текстовая правка с отдельным source-delta
аудитом и новым actual fingerprint. Она намеренно не смешана с этим исправлением.

## Ресурсы и сохранность

Суммарный ledger всех фаз: **46.359375 CPU-с,
42.635209 active wall-с**; sampled private peak worker tree
**261103616 байт**; текущие локальные диагностические данные
**1254818 байт**. Это не elapsed время общения.
Включены исходный FAIL, 18 проб, независимый аудит, точный повтор MRE и тесты.
Начальные 2 CPU/5 wall и подготовительные 0.5 CPU/1 wall — консервативные allowances,
не прямые измерения. Память/процессы контролировались каждые 50 мс; короткие пики
между samples возможны, tail allowance не является строгой непрерывной границей.
Metadata/edit/Git/cloud расходы исключены, backup измеряется отдельно.
Caps 120 CPU/240 wall/1 GiB/48 MiB и early-stop 96/192/900 MiB/40 MiB не повышались.

Первый helper подготовки получил AssertionError из-за дублирующего варианта LF/CRLF
до любой записи production-файлов; он исправлен, отказ и allowance сохранены.
После production fix проваленных acceptance-попыток не было.

Резервирование завершено: **CLOUD_VERIFIED_SHA256**. Отдельный operational ledger:
**5.421875 CPU-с / 9.161312 active wall-с**;
connector CPU не измерен, окно операций transfer/readback 50.908 с
учтено отдельно. Повторно проверены аккаунт, родитель и owner-only права.
Filtered Project-Archives/Solar-Simulator содержит:

- Raw ZIP: **397823 байт**, SHA-256
  `6c896847d55447cde4531cb40986689f57b8347f05926c4d66832fc49e83cef6`.
- Git recovery recipe для `c66c70ab22efdd9924364f5de2fcd5cd234fe0c2`:
  **582 байта**, SHA-256
  `ad75ae5693f75236c315c46c1f1fc87fea28b4eafef715c6ba280c65cc9a692d`.

Обе облачные копии независимо скачаны заново; размер, SHA и parent совпали.
Архив содержит 82 проверенных raw/служебных файла, manifest и инструкцию восстановления;
зависимости 403/402/401/399/395 повторно не загружались. Исходники доступны по точным
опубликованным commit. Private context/SQLite/secrets/окружения/кеши исключены;
оригиналы не удалялись. Личный контекст сохраняется отдельно в приватном Git.
При оформлении Markdown был отказ кодировки до записи; явный UTF-8 устранил его.
Это metadata-операция, исходники и экспериментальные данные не менялись.


| Решение | Результат |
|---|---|
| GUI_LIFECYCLE | PASS в проверенной матрице и среде |
| CALLBACK_OWNERSHIP | PASS, только собственные callbacks |
| WORKER_RECOVERY | PASS, состояния и recovery SHA неизменны |
| NUMERICAL_SOURCE_IDENTITY | PASS |
| APPLICATION_D1 | Исторический 402: полный NO-GO |
| RELEASE_READINESS | NO-GO |

Следующий небольшой шаг — отдельная корректировка устаревшей GUI-маркировки.
Полная приёмка 0.3.3 остаётся отдельным этапом; main, tags, LATEST и принятая
portable 0.3.2 не изменены. После отчёта STOP.
Рекомендуемая модель следующей ограниченной задачи: GPT-6.1 Sol High.
