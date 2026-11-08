# Q2: достоверная маркировка и GUI lifecycle —403

2026-11-08. **GO только для отдельного truthful text candidate. GUI teardown defect
подтверждён и не исправлен; полная D1 application acceptance и release0.3.3 — NO-GO.**
[Машинный отчёт](q2-ui-lifecycle-403.json), [план](../scripts/qualification403/plan.json),
[инструменты/минимальный reproducer](../scripts/qualification403/README.md).

## Источники и presentation-only результат

Dev start2fd4424; исходный exacta99f73a4adce95be9d264d8c403e0e6768a54cd7
не изменён. Новый отдельный worktree/branchcodex/candidate-0.3.3-q2-marking-403,
commit **e9ddd352ac3dbff2eb8e2c5e37370aecd59fb5db**, строго отa99. Единственный diff — текст литерала
TWO_Q2_EXPERIMENTAL_WARNING в inspection.py (12added/8removed lines).
Остальные байты файла и AST точны; полная Git blob inventory отличается лишь
этим файлом. Physics/force/torque/Hamiltonian/R-reuse, Rust/native/ABI,
integrators/error control,IC/G/settings,storage/schema,Start/target/save/load/
calculation callbacks и eventloop побитно прежние. Whitelist не расширялся.

Actual source fingerprint **d53f18828b57cb63a7a5c9eab92d4ee1d264fe31b44174ffa00806f5759b06a4**;
прежний1a5b054241a628dc6d4ade30a978726166d001dbb0f25ad9a971cd7fc9f21122
не присвоен новому кандидату. Профиль — свежие штатные LFbytes recipe,не wheel/portable.
Imports из нового src, зависимости/интерпретатор из qualified384venv;
Python3.14.2t,NumPy2.5.1,SciPy1.18.1,solar-native0.3.3.
Native SHA651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091.
За исключениемinspection.py package hash, actualenvironment равен401.

Проверены4состояния:0/1/2фигуры и загруженная переименованная/изменённая
двухфигурная система. Предупреждение есть только для2, видно в model_info,
rotation_text и обеих read-only inspector вкладках. Произвольная система
не получает PASS/сертификацию; q/S/settings,файлы и numerical diagnostics
не меняются. Evolution/RHS вызовов0; static diagnostics остаются прежними.
current_trajectory_certified=False и отсутствие globalerrorbounds не менялись.
Текст содержит утверждение A+D1 **как цели**, numerical11/11PASS, effects10/11,
distance_AB0.244795mвместо10mFAIL, полнуюapplicationNO-GO, всеFAIL и ограничения.
ОбычныйStart не ограничен200s, arbitraryloadedtwoQ2 вне frozen402scope.

Source-bound399/401/402receipts не переписаны и не приняты под новым SHA.
Доказанная неизменность вычислительного кода обосновывает применимость прежних
результатов только в их fixedscope, без новой общей численной квалификации.
Новые орбиты,74теста400,401численные contrasts и22jobs402 не запускались.

## Что воспроизведено в Tcl

Все lifecycle пробы — на originala99, с запрещёнными evolve/solve/integrate.
Использован сохранённый402frame100; настоящий executor/poll в worker control
возвращал этот же снимок. Исторический лог402 содержит12сообщений, timestamps
в нём отсутствуют. Новые пробы записывают реальные commandnames/afterIDs,
Python registration stacks,Tcl errorInfo и monotonic registration/error times.
Придумывать старые timestamps не требуется и не допускается.

| Проба | Background errors | Подтверждённые callbacks |
|---|---:|---|
| active_close_recovery | 1 | FigureCanvasTk.draw_idle.<locals>.idle_draw |
| completed_worker | 2 | FigureCanvasTk.draw_idle.<locals>.idle_draw, Laboratory._poll |
| correct_cancel_all | 0 | — |
| correct_only_idle | 1 | FigureCanvasTk.draw_idle.<locals>.idle_draw |
| correct_only_layout | 8 | ControlRow._layout |
| correct_only_poll | 1 | Laboratory._poll |
| fresh_process_reopen | 0 | — |
| multi_three_roots | 0 | — |
| multi_with_events | 3 | Laboratory._poll |
| single_no_pump | 0 | — |
| single_with_pump | 10 | ControlRow._layout, FigureCanvasTk.draw_idle.<locals>.idle_draw, Laboratory._poll |

Во всех ошибках аудитор сопоставил **тот же exact command**: до destroy он
существовал, после destroy TclafterID оставался в очереди, а command уже удалён;
после event processing пришёл invalid-command с тем же именем и afterscript
в errorInfo. Каждая регистрация предшествует ошибке, стеки и ID сохранены в JSON.
У single_with_pump10ошибок (poll1/layout8/idle1), у group controls1/8/1,
при правильной отмене всех owned callbacks —0. Это контролируемое устранение
механизма ошибки в диагностике, **не production fix**.

**Причина установлена:** Laboratory._destroy уничтожаетroot и Python Tclcommands,
не отменяя pending `_poll`; ControlRow хранитpendingafter_idle без cleanup;
embedded Matplotlib canvas оставляетidle_draw. Уничтожение widget удаляет
команды, но не соответствующие afterIDs. Одного root с продолжающим работу Tcl
достаточно: проблема не требует нескольких Tkroots. Завершение standalone
процесса уничтожает интерпретатор и маскирует проявление; обычный запуск/выход
не продемонстрировал видимую ошибку. Long-lived/повторно используемый eventloop
уже воспроизводит production callback-ownership defect. Потери состояния не наблюдались.

В multi_with_events layout/draw успели отработать до закрытия, остались3poll;
последнийroot также явно pumped. Число зависит от pendingqueue и порядка
закрытия, поэтому не обязано равняться историческим12. В402 было2poll/8layout/
2idle_draw; конкретные callbacknames в403 и source регистрации совпадают по
механизму. Точное время destroy отдельно не измерялось: порядок подтверждён
before/afterqueue snapshots; clocks регистрации/ошибки относительны к каждой пробе.

## Ошибка harness, её исправление и расходы

Перваяизолирующая проба only_poll остановилась: harness вызвалroot.after_cancel
для child-owned callbacks. Tclcommand удалился, но имя осталось в дочернем
Python _tclCommands; последующийdestroy попытался удалить его второйраз.
Сохранены failing traceback/исходник/стоимость. Исправлено **только в diagnostics**:
after_cancel вызывается на зарегистрировавшем callback widget; чужие Tclscript
таймеры отменяются без удаления чужих Python ownership records.

Шесть завершённых проб аутентифицированы по SHA и не повторялись. После47.609375CPU
новый отдельный continuation-v2 закрепил оставшиеся изоляции и corrected
multi-event control. Один Python import разделён между отдельными Tk/Tcl
интерпретаторами; очереди изолирующих проб полностью обработаны и проверены пустыми.
Фактическая дополнительная стоимость8CPU; бюджет не повышался.
Первоначальный multi_three_roots не обрабатывал события:0ошибок там **не PASS**,
а недиагностическая проба. Вместо ложного вывода добавлен явно отдельный
multi_with_events. Завершённые probe outputs оставлены неизменными.

State/save/recovery сохранны: при close с inert activeworker штатный stop/finish
сохранил тот же402checkpoint, включая q/S/settings; raw recovery SHA и документ
проверены независимо. Завершение worker также оставляет pendingcallbacks,
поэтому успешное сохранение не доказывает правильность teardown.

## Минимальный failing contract и отдельная будущая правка

[reproduce_close.py](../scripts/qualification403/reproduce_close.py) содержит
single-rootclose→retainedTclupdate и assertnoerrors. Полностью инструментированная
проба уже выполнила этот механизм; convenience script отдельно не повторялся.
Ожидаемый failing contract: послеclose не должно бытьinvalid callbacks; наблюдается10.
Это не skip/xfail и не научный FAIL, скрытый успешным diagnostic exit code.

Минимальная предлагаемая **отдельная** lifecycleправка:

1. Сохранять pollafterID и отменять ownedpendingtimer передrootdestroy, не меняя
   завершение worker/lastpacket/recovery. Учесть directmanual_poll тесты, чтобы
   не удвоить таймер и не удалять выполняемый callback.
2. В ControlRow закрывать свойpendingafter_idle доdestroy и предотвращать
   повторную регистрацию во время teardown; отмена на правильном owner.
3. Для embeddedcanvas явно закрывать его ownedidle_draw до уничтоженияwidget;
   FigureManagerTk cleanup здесь не вызывается. Привязать cleanup к проверенной
   версииbackend и проверитьprivateAPIриски вместо общегоcancelallafter.

Production здесь **не исправлялся**. Нужны отдельный source-bound кандидат,
аудит затронутыхGUIузлов,0/1/2cases,manual/realpoll,close/stop/worker/save/
recovery и проверки независимых окон. Не ослаблять presentation whitelist и
не переносить доказательство text-onlydiff на будущий lifecycle patch.

## Научные результаты и решения владельца

402неизменён:22/22logicalCOMPLETE,23attempts;11/11numerical budgetsPASS,
10/11effects;distance_AB0.244795m<Delta10mFAIL. Все4коротких strictconvergence
FAIL и3historicalFAIL380 остаются. EmpiricalU_ref/N_sens не globalbound/roundoff.
Relative-vector/angular displacement не переименован в scalar distance.

ВариантA: оставить исходныйD1 без изменений — полнаяapplicationNO-GO.
ВариантB: только по будущему отдельному разрешению заранее определить другой
учебный профиль, например relative-vector/orientation, объяснить физический
смысл и зарегистрировать новые критерии до проверки. **Bне утверждён**;
данные402 не дают автоматическогоPASS новому профилю, исходныйFAIL неизменен.

## Раздельные verdicts и сохранение

| Gate | Verdict |
|---|---|
| SCIENTIFIC_UI_TEXT | PASS, достоверная маркировка |
| PRESENTATION_SOURCE_DELTA | PASS одного литерала; GO только textcandidate |
| GUI_LIFECYCLE | FAIL подтверждённого danglingafter; не исправлен |
| APPLICATION_D1_NUMERICAL | Исторический402PASS11/11 в его fixedscope |
| DEMONSTRATED_EDUCATIONAL_EFFECTS | FAILdistance_AB;10/11 |
| RELEASE_READINESS | NO-GO |

Final computationalledger:63.0625CPU /58.7532847activewall s.
Пики/диск и все phase receipts — JSON после closingaudit. Initial2CPU/5wall allowance не measured;
50ms sampledmemory/tree и0.25tail allowance не строгие continuousbounds.
90CPU/180wall caps,early72/144,1GiB/900MiB,32/28MiB не повышались.
Backup отдельно; CLOUD_VERIFIED_SHA256, raw originals сохранены.
После filteredProject-Archives нужны independentdownload SHA/size/parent;
приватный контекст туда автоматически не включается.
Main/tags/LATEST/portable032 и oldcandidates неизменны. После отчёта STOP.
Следующий небольшой шаг — отдельно разрешённый lifecycle fix,не новые орбиты.
Рекомендуемая модель: GPT-6.1Sol High.

Final computational ledger: **63.0625chargedCPU /58.7532847activewall s**,
включая неудачный cancellation probe, continuation и closingaudit.
6portable negativecontrols PASS/0skip; inventory1372files/1455links PASS.
Все наблюдённые lifecycleerrors сохранены; PASStools не означает GUIlifecyclePASS.

Incremental backup: ZIP276496B SHA256
`e09cbb4279781812fce3afcbf5d74acde01c978aaf0553a1e207d742905f7bf4`,
Drive1biSBdzUJXb7A2W8viDQ3rPoWOIE_5uR9. Git recovery recipe582B SHA256
`9c779c289142a14fc964e94121255a6f7cca2405550ee56f12e0e4a2307ec218`,
Drive1TySXO-HkbT1Yg5MssNindUGKvUp3Y0pw. Оба независимо скачаны и проверены
по SHA/size/parent; owner-only права перепроверены. Backup4.84375CPU /
7.812667activewall s отдельно; connectorCPU не measured. Filteredqueue только
Solar-Simulator, старые immutabledependencies reused, без broadrescan.
