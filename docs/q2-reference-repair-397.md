# Q2-397: recovery audit и отдельный K=1/K=2 reference

**GO к отдельно разрешённому preflight398.** Подтверждённый дефект распаковки
исправлен в новом reference. Полная серия58jobs и квалификация оптимизации
не выполнялись; release0.3.3 остаётся NO-GO, три исторических FAIL380 сохранены.
Дата этапа:2026-11-07. [Машинные результаты](q2-reference-repair-397.json).

## Что удалось установить после сообщения о выключении

Dev и origin перед работой совпали: `13d1a3106dcb1be734ad35a015b56e392201bf87`.
Все4public worktrees и private context чистые; Git merge/rebase/cherry-pick/
index.lock residue отсутствовал. Baseline `fe0f456f2c7ba3a077eac21fc8413937d6e84fac`
и candidate `f723a2162b4e115378959e244f428529be2d4516` доступны и неизменны.
Сверены394source bindings обоих кандидатов, actual native/dependency profiles;
новый fingerprint не выдавался за старый. Native SHA256
`651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`.
Python3.14.2t, NumPy2.5.1, SciPy1.18.1; OMP/OPENBLAS/MKL=1, read-only384venv.
Environment LF-JSON SHA: baseline `056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a`,
candidate `d1a2e827e6edcf43ceedacbfc3f62ad72b624c2f0f03332326aa0cf6185695c7`.
Различие LF/CRLF файлов, объяснённое396, не является изменением среды.

ZIP395748537B/SHA`8911007703ef40a36b7701deb6f5ba32e1cc75203f2e60c3e3868ed0b9a7d243`
и ZIP396399878B/SHA`6b48186871d9d25ad45dd9764093e2a67ae4e76f1f9f1e99f551e5c84e3f5b76`
проверены CRC/size/SHA: все182+39members совпали и с архивными манифестами,
и с локальными файлами. В395 найден и проверен Git bundle с ref f723a21,
требующий публичныйfe0f456. Повреждения/пропажи **в этой зафиксированной области**
не обнаружены. Невозможно доказать отсутствие потерь файлов вне манифестов.
Оставшиеся pytest test-temp являются воспроизводимыми fault-fixtures; они
сохранены. Неожиданных `.partial/.tmp/.next` вне этих fixtures в396 нет.
Существующие outputs/logs/bindings и оба historical FAIL attempts396 сохранены.

Доступные Windows System events: последний boot2026-11-05T21:50:51Z,
Kernel-Power41 и EventLog6005/6008 относятся к этому запуску. Архив396 создан
позже,2026-11-06. Эти доступные записи не подтверждают новый reboot после396;
они не доказывают отсутствия питания/hibernate/неполноты журналов.
Причина пользовательского выключения остаётся неизвестной. Статический
`range(2)` и сохранённый traceback396 независимо объясняют K1 failure;
выключение причиной этой ошибки не объявляется. Solver не возобновлялся.

## Новый reference и точная граница изменения

Исторический [reference380](../scripts/two_q2_reference380.py:7) не изменён,
SHA256`174c6529d010bc652f6ec5e5b6dd8aed5202a98b4cbc1c18d4b27d2b5fbbf78a`.
Новый [reference397](../scripts/q2_reference397.py:7), собственный SHA256
`52b2d4efebad15fc25739776d3a8939015a6be42be1b88d9b3d5f999271e9338`.

В397 скопирована исходная функция reference380; вся подготовка начальных
условий, преобразование COM, scalings, nested RHS и вызов solve_ivp до получения
solution **тождественны по AST**, включая G, RK45, `atol=rtol*.01`,max_step50,
t_eval и все группировки арифметических операций. Уравнения и константы
не изменялись. Старый независимый evaluator380 остаётся в своём исходном файле.

После solve_ivp добавлен [выходной unpacker](../scripts/q2_reference397.py:50).
Layout:6N физических orbital components в масштабированных p/v и12K для9R+
3body-momentum на фигуру. Восстановление r/v в SI и S=`R@Pi` сохраняет прежние
выражения и порядок вычислений. Вместо фиксированного range(2) используется K
из rotations. Порядок R/S соответствует порядку rotations, физические тела
сопоставляются по body ID; проверены также фигура B и перестановки тел/фигур.

Новые выходные проверки: K1/2, shape(6N+12K,T), finite binary64 state, точная
сетка эпох, положительные finite scales, origin/drift shape, уникальность body/
rotation IDs и соответствие masses. Неуспех RK45 по-прежнему отклоняется.
Валидация относится к **output/unpack context**; presolve assumptions и error
paths380 оставлены прежними. Это не новый универсальный валидатор произвольных
начальных условий. Матрицы не проецируются на SO(3), q не нормируются, конечные
off-manifold R не исправляются скрыто. Новая обработка сил/интегратора не нужна.

Воспроизводимый diff: `git diff --no-index -- scripts/two_q2_reference380.py scripts/q2_reference397.py`.
Новый файл не копирует ненужную вторую функцию independent_invariants: прежняя
остаётся доступна из380. Source/execution SHA запечатаны перед тестами в plan397/
binding397, полные файлы и commands сохраняются отдельно в reviewed raw archive.

## Проверки до и после

1. **До:** прежний K1 распаковщик падает на сохранённом396state24×2.
   **После:** replay тех же initial_y/final_y новым reference дал shape R(2,1,3,3)
   и S(2,1,3), без нового интегрирования. Старый reproducer396 всё ещё подтверждает
   прежний ValueError; старый source/результат не переписан.
2. K1 t=0 reconstruction и отдельная фигура B проверены synthetic exact initialy:
   размерность6N+12K, R/body momentum/scales, r/v/S и отсутствие мутации.
3. K2 одинаковый synthetic y сравнен побитно для N2/N3 и перестановок ID, включая
   конечное отклонение R от ортогональности: никакой скрытой проекции нет.
4. В проверенных380NPZ сохранены **физические** referencearrays, а не исходный
   K2solution.y;396 сохранил только K1internaly. Не реконструировали предполагаемый
   исторический K2y. Поэтому после synthetic tests выполнен ровно один короткий
   oldK2 RK45 test0..0.001s/8RHS. Его фактический y36×2 подан обоим распаковщикам:
   все r/v/R/S bytes, shapes и nfev совпали. Для newoutput дополнительного solver
   не запускали. Это short same-y equivalence, не повтор квалификации4000s.
5. Один новый short analytic control: круговая Newton орбита двух масс1e15/2e14kg,
   separation12000m, сферическая фигура I=(2e20,2e20,2e20)kgm², omega_z=.002rad/s,
   epochs0/1/2s, independent RK45 rtol3e-13,26RHS. Аналитика: n=sqrt(GM/r³),
   r вращается по cos/sin(nt), R=Rz(omega*t), S постоянен. Скалярный I даёт zeroQ
   и нулевой внешний torque; введённые COMoffset/drift учтены явно.

|Короткий analytic control|Измеренная максимальная ошибка|
|---|---:|
|position / initial separation|1.5158245029548803e-16|
|velocity / circular relative speed|3.4379325746400523e-16|
|R Frobenius|2.805060466068872e-16|
|S / initial spin|0|

Все ниже заранее заданного технического1e-10. Binary64 rounding IC/cos/sin
остаётся; это короткий контроль структуры/уравнений и SI, не строгая IVP bound
и **не улучшение физической точности**. Независимый offline selfcheck пересчитал
эти ошибки из сохранённых arrays другим скалярным reduction, без readyPASS flags.

41unique pytest PASS:22новых +19регрессий396/392;0skip/xfail. Проверены bad K0/3,
rows/columns/type, NaN/Inf, epochs, failedsolver, IDs/mass/scales и немутирование.
[AST test](../tests/test_q2_reference397.py:32), [K2 bytes](../tests/test_q2_reference397.py:42),
[K1/body B](../tests/test_q2_reference397.py:55), [fault tests](../tests/test_q2_reference397.py:70).
Saved-data audit392 повторно сохранил3historical strict-convergence FAIL и
Rust/three-body PASS-control. Старые критерии/NPZ/receipts неизменны.

## Стоимость и решение

Все4controlled attempts recovery/tests/controls/selfcheck завершились без
неуспешных вычислительных попыток: **10.765625CPU s /10.898793active wall s**,
worker+supervisor. Sampled worker private peak190255104B, RSS154939392B;
supervisor OS peakcommit37449728B. Консервативная сумма отдельных пиков227704832B
не синхронный peak. Guard50ms/final Windows CPU handles; краткие пики/descendants,
outerlauncher/последний record-tail CPU могут быть не полностью учтены.
Caps45CPU/120wall/512MiB/16MiB,early35/95/450MiB/14MiB сохранены; resourceSTOP нет.
Последний guard sample145801B output, финальные report/archive отдельно в16MiB.
Read/edit/Git/CI/обязательный backup отдельно; это не время всего чата.
Повторена только одна K2shorttrajectory, одна новая K1analytictrajectory;
K1saved396 replay не интегрирует. Production DOP853/native,4000s58matrix,
full380/Newton384/annual385/fullcheck/portable не запускались.

**GO к повторному preflight398**, не GO к автоматическому запуску58jobs.
[Точный proposed binding plan398](../scripts/q2-qualification398-plan.json)
сохраняет исходные58jobs396, IC, grid, recipes, backend, thresholds395;
заменяет только обязательный K1reference на новый SHA397. Старые380reference0/1
для K2 остаются прежними. Actual tool Git commit нужно запечатать в отдельном
398execution binding после публикации; нельзя сделать self-referential commit.
Специфический execution adapter58jobs всё ещё требуется; готовность его или
ресурсов полной серии397 не аттестует. Будущий бюджет180/360/1GiB/128MiB только
предложен из395, требует отдельного задания и проверки стоимости перед серией.

Оба candidate source/env, рабочее productionядро, main/tags/LATEST/portable032
не изменены. A+D1 не утверждена, release0.3.3 NO-GO. После397 STOP.
