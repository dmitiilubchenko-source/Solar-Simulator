# Q2-394: изолированный прототип повторного использования R

2026-11-06. **GO TO REVIEW** по заранее заданному инженерному критерию.
На данном ПК измерено ускорение короткого RHS/расчёта при exact совпадении
проверенных численных результатов. **В production не внедрено.**
Это не исправление3FAIL380, не новая научная квалификация и не разрешение релиза.
Кандидатfe0f456, native, main, LATEST, теги и принятая0.3.2 не изменялись.
A+D1 остаётся предложением владельцу; **release0.3.3 NO-GO**.

## Происхождение и точный diff

Dev до этапа: `127561a54e9464e697661cc7d619238d921c67aa`.
Baseline: `fe0f456f2c7ba3a077eac21fc8413937d6e84fac`.
Отдельный локальный branch `codex/q2-r-reuse-394`, commit
**`896030c3206b1010175d6a491e1f5d7063abdcf5`**; исходный кандидат не переключался.
В dev сохраняются только отчёт, проверочные helpers/tests и
[точный patch](../scripts/validation/q2-r-reuse394.patch), не изменённые runtime files.
Patch SHA256 `df958f9f4c41ad9f3ed57ec2851c30de8b55e608287bd4ebeecfb2f902abbdc6`.

|Файл|Baseline SHA256|Prototype SHA256|
|---|---|---|
|rotation.py|245087dc0b1f5cc64e8c3fbbd1c34fe9e8f80266069ceafb8081906f8dfd4f80|0cec73448d8bbd3a29656d04be7f74aa04338be6df40055548910557f29412c6|
|nbody_rotation.py|7cdbf09b398aa467ec5badabcf4428c88dfc62ac81f49b73c988ae8c81c9ce7c|9126ae10a8f41849f09acc83ae152fe8aea0abe85f99f79f183db5f86b79a6a2|

Sealed plan SHA256:
`9a950cd72f00f9402461029e0136b5300e37fbe424eab9b35ce80ba9e9e22786`.
Фактическое baseline environment SHA256:
`056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a`.
Фактическое prototype environment SHA256:
`d1a2e827e6edcf43ceedacbfc3f62ad72b624c2f0f03332326aa0cf6185695c7`.
Два свежих fingerprint отличаются **только** package SHA двух файлов выше;
это настоящий новый fingerprint, не присвоение старого receipt.
Python3.14.2t/cp314t, NumPy2.5.1, SciPy1.18.1; OMP/OPENBLAS/MKL=1,
VECLIB/NUMEXPR/PYTHONHASHSEED unset. Тот же проверенный native SHA256:
`651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`.
Версии, исходные IC/SHA/settings, все timing samples и результат оценки — в
[машинном отчёте](q2-performance-prototype-394.json).

## Что именно изменено

Один R=rotation_matrix(q) на каждую фигуру из **актуального stage q** внутри
каждого вызова RHS. Локальный tuple matrices передаётся в private `_corrections`
и `_angular_velocity_with_matrix`. Между RHS ничего не сохраняется.
Нет глобального изменяемого cache, body-Q cache, новых threads/GPU или Rust-переноса.

Public `angular_velocity`, `correction`, `corrections` сохранили сигнатуры.
Две field wrappers ведут к тем же private kernels; отдельный готовый matrix
не стал пользовательским параметром, позволяющим обойти q validation.
`rotation_matrix` и `_vector` не менялись: q finite/type/zero checks и
нормирование прежние. Spin проверяется прежним `_vector`; все geometry/mass/
source/external-sphere/finite-output checks остаются в общем kernel.
Public field validation order прежний. В RHS q проверяется при общей подготовке
R до field geometry; при одновременно некорректных q и геометрии порядок ошибки
может отличаться, но отказ сохраняется. Это не ослабление физической границы.

AST audit отдельно подтвердил: RigidFigure/quadrupole, rotation_matrix,
_vector, quaternion_rate, standalone pair/free solver и RotationDOP853
побитно прежние по AST; return expression angular velocity тот же;
тело field после единственной условной подстановки R совпадает по AST.
В integrate после нормализации только известных preparation/call-site правок
весь AST совпал. Силовые суммы, Hamiltonian, back-reactions, моменты,
solver, rtol/atol, error-control, times/packets/коэффициенты не переставлялись.
Создание R перемещено до field evaluation; это единственная намеренная
перестановка работы. body-frame Q продолжает создаваться в каждом поле.

Обоснование эквивалентности: матрица зависит только от одного и того же q.
Она не меняется между Q=R Qbody Rᵀ и ω=R(I⁻¹(RᵀS)); группировка обеих
формул прежняя. В рамках RHS оба потребителя только читают R.
Проверены readonly R, input buffers, сохранённые snapshots и изменённые stage q;
устаревший R не мог пройти эти derivative contrasts.

## Фиксированный опыт и проверки чисел

Исходные synthetic SI данные [fixture380](../scripts/two_q2_fixture380.py:12),
не реальная Земля–Луна. Newton total-degree-two M–Q без Q2–Q2, EIH, приливов,
диссипации/контактов. G exact binary64 `0x1.2589effed8accp-34`.
Две фигуры используют прежние A/B; для одной остаётся только rotation A,
массы/орбитальные IC обоих тел не меняются.
Free: одно сферическое тело A, I=(2e20,2e20,2e20), прежний S, relative_pair=None.
ZeroQ: оба I заменены на spherical mean каждого прежнего I, всё остальное прежнее.
Все8точных input documents, в том числе q/S/atols, сохранены до интегрирования.

Cases: one/two/free/zeroQ × Python/Rust. Два **cold** пакета по50s,
эпохи0/50/100s, rtol1e-11, position_atol1e-7m, velocity_atol1e-11m/s,
q/S atols из прежней фигуры; max_step не ограничивался. Для one/two/zeroQ
relative_pair=(A,B). Для каждого backend сравнивались baseline и prototype;
совпадение Python с Rust отдельно не заявляется.

- **24парных сохранённых состояния** (initial/mid/end по8cases) совпали по
  dtype/shape/bytes r/v/rawq/S. Checkpoint file SHA baseline/prototype тоже совпали.
  Реальные save→load→advance дали тот же final endpoint, input/snapshots неизменны.
- **24фиксированных RHS contrasts:** initial, изменённые q/S stage и q→−q
  для8cases. Полные производные совпали по битам, y не изменился.
  Смена stage q проверяет отсутствие переноса R между вызовами.
- Независимый scalar Decimal80/110 observer393 вычислил E/P/L и rawqnorm
  на всех saved epochs. Значения обоих вариантов совпали; agreement двух
  точностей энергии проверен. Это observer, **не высокоточный IVP reference**.
- One/two field проверены через независимый scalar principal-I potential:
  position finite differences h=.02m, attitude h=1e-6rad, прежние пределы
  relative2e-6; reaction1e-13, полный orbital+spin torque balance2e-12.
  Дополнительно covariance прежних380 limits, q/−q exact field equivalence,
  analytic spherical free rotation1e-9 matrix limit и constant S.
- Bool/nonfinite/zero q, bool S, zero stage q и sphere overlap отвергаются
  обоими вариантами. Kernel принимал readonly prepared matrices без записи.

|Variant/figures|Force gradient relative|Torque gradient relative max|Reaction relative|Torque balance relative|
|---|---|---|---|---|
|A/1|1.78901e-10|7.24408e-10|8.55859e-17|1.67986e-16|
|B/1|1.78901e-10|7.24408e-10|8.55859e-17|1.67986e-16|
|A/2|9.89186e-11|6.68457e-10|1.14873e-17|6.96708e-17|
|B/2|9.89186e-11|6.68457e-10|1.14873e-17|6.96708e-17|

Абсолютные SO(3) углы baseline/prototype равны0 на проверенной выборке,
сравнение устойчивым relative-quaternion observer. Все численные отличия равны0
там, где требовалась exact identity; файлов с неожиданными delta не возникло.
Это конечная проверенная выборка, не универсальное доказательство float64 equality
для любой платформы/initial state и не оценка истинной ошибки траектории.

## Реальные счётчики

Считались вызовы функции, а не только строки исходника. Counter/profiler hooks
использованы отдельно от timed sections и полностью восстановлены.

|Case|RHS each|R in RHS A→B|Native each|
|---|---|---|---|
|one-python|112|224→112|0|
|two-python|112|448→224|0|
|free-python|112|224→112|0|
|zeroQ-python|124|496→248|0|
|one-rust|112|224→112|112|
|two-rust|124|496→248|124|
|free-rust|112|224→112|112|
|zeroQ-rust|136|544→272|136|

В последнем столбце — число реальных native force calls **каждого** варианта.
RHS и nfev совпали внутри каждого backend; один R/figure/RHS подтверждён
для всех вызовов instrumented коротких расчётов. R вне RHS (validation/report)
считался отдельно и не выдаётся за оптимизированный. Constant-Q не оптимизировался.

## Измерение времени: пять отдельных процессов

До запуска зафиксированы5серий, case order one-Py/two-Py/one-Rust/two-Rust,
ABBA/BAAB/ABBA/BAAB/ABBA. В каждой серии два Python namespaces загружены из
двух проверенных worktrees в один interpreter, с теми же зависимостями/native;
различные серии — разные worker processes. Это позволяет чередовать варианты
без включения import/startup в каждую пару; global bindings между namespace
не смешиваются, origin каждого модуля проверен.

На case/variant: прогрев8RHS и1rollout; каждый из4ordered blocks содержит
512microcalls либо8rollouts, где rollout — два advance(...,1), horizon100s.
Micro включает одинаковую byte-equality проверку результата каждого RHS.
Macro — только два advance, без disk/save/load; после блока проверен последний
endpoint и его повторное совпадение. Все промежуточные повторения timed macro
не сохранялись: persistence проверена отдельно с обоими endpoints.
Warmup/import/attestation/quality входят в общий ресурс, не в timing samples.

Ниже wall секунды: отдельно median A и median B; paired speedup — median
пяти **отношений сумм двух blocks** A/B внутри series. Отношение отдельно
взятых медиан может отличаться; paired saving тоже вычислено внутри series.
ABBA суммируется, результаты не отбирались по быстроте.

|Case|Level|Median A,s|Median B,s|Median paired saving,s|Median paired speedup|Speedup range|
|---|---|---|---|---|---|---|
|one-python|micro|0.195789|0.189054|0.0090145|1.05017|1.0031…1.13432|
|one-python|macro|0.38966|0.365401|0.0125844|1.03444|0.994763…1.07697|
|two-python|micro|0.337678|0.317795|0.0213413|1.06764|1.03714…1.07694|
|two-python|macro|0.652912|0.624488|0.0287493|1.04604|1.0216…1.14655|
|one-rust|micro|0.169931|0.160554|0.011697|1.07285|1.02028…1.10009|
|one-rust|macro|0.35397|0.338671|0.0245641|1.07253|1.01361…1.09382|
|two-rust|micro|0.31902|0.302706|0.0145341|1.04773|1.04142…1.08284|
|two-rust|macro|0.687422|0.652026|0.0465177|1.07134|1.03212…1.09267|

|Aggregate equal-count workload|Median A,s|Median B,s|Median paired saving,s|Median speedup|Range|
|---|---|---|---|---|---|
|micro|1.01695|0.965971|0.0585123|1.06105|1.03099…1.0829|
|macro|2.07698|1.99814|0.12172|1.06225|1.02622…1.08517|

У one/Python macro одна серия дала A/B=0.9947635 — prototype примерно на0.53%
медленнее, хотя median этого case полезен. Этот результат сохранён.
Нельзя объявлять каждую отдельную серию/case статистически улучшенной.
Aggregate на обоих уровнях положителен5/5; exact one-sided sign p=1/32
**при предположении независимых series и равновероятного знака при null**.
Общий Windows scheduler/caches не гарантирует независимость. Micro и macro
не независимые исследования, их p не перемножаются. Это ограниченные данные
одного ПК, без общего performance promise.

CPU samples приведены в JSON. Наблюдается coarse quantization~15.625ms;
для one/Python micro median CPU даже одинаковый0.1875s. Основной decision
использовал wall и заранее заданный engineering minimum ratio1.02,
5положительных aggregate series на каждом уровне, отсутствие case-median
slowdown>2% и необъяснимого роста памяти. Выборка/порог не менялись после запуска.
Результат **1.06105× RHS /1.06225× short-rollout**, не обещанные заранее6%.
Измеренное уменьшение времени порядка5.8%, а не равное проценту speedup−1.

## Память и качество архитектуры

|Case|A peak,B|B peak,B|Extra peak,B|Retained A/B,B|
|---|---|---|---|---|
|one-python|13272|13392|120|0/0|
|two-python|14176|14520|344|0/0|
|one-rust|13784|13904|120|0/0|
|two-rust|14648|14992|344|0/0|

Это tracemalloc после прогрева в отдельных baseline/prototype windows,
128одинаковых RHS, после gc; retained0 у обоих. Рост peak120B/344B согласуется
с дополнительным локальным tuple/передачей R. Это цена прототипа, не нулевая
allocation overhead. Полной трассы всех C/OS allocations и доказательства
отсутствия утечек на любом горизонте нет. Совместный OS private/RSS измерен
guard, оба namespaces резидентны: нельзя приписывать его отдельному варианту.

Diff только2files,30insertions/11deletions. Три private helper kernels и два
public field wrappers увеличивают call structure, но сохраняют одну копию
физических формул. Матрицы3×3 локальны, массивы всей системы дополнительно
не копируются для cache. Public validation/interface, checkpoint/recovery/GUI
не меняются. Полученный выигрыш оправдывает **review**, не автоматическое
добавление optional matrix в публичный API или дальнейшее усложнение.

## Ресурсы, проверки и восстановление

Все10guarded jobs: **76.9375 CPU s / 65.574965 active wall s**,
worker+supervisor, включая прогревы, imports, проверки, все timed batches и
сам observer/source audit. Cap120/240/1GiB/48MiB; early90/190/900MiB/40MiB
не менялись. Нет failed scientific workers/resource STOP.
Sampled worker private peak178634752B (170.36MiB), RSS146980864B;
supervisor OS peakcommit37642240B, консервативная сумма раздельных private peaks
216276992B (206.26MiB), не синхронный пик.
Sample50ms/retained Windows final CPU handles; short spikes/неувиденные children,
внешний venv launcher и последний record-tail CPU могут не учитываться.
Это sampled guard, не hard OS quota. Activewall не длительность всего чата.
Последний scientific artifact sample1352571B;
пик числа файлов инструментирован: 83.
Финальный recovery bundle/отчёты отдельно ниже48MiB. Чтение/редактирование,
Git/CI и обязательное резервирование учитываются отдельно от научного budget.
Новый восстанавливаемый Git worktree сначала занимал116541722B, затем был
сужен до src+root metadata (6392147B) штатным sparse checkout; это отдельно
от experimental artifact bytes. Исходный кандидат/данные не удалялись.
Оба варианта использовали существующее dependency environment, новых venv нет.

**10новых unit tests PASS**, плюс прежние **28регрессионных PASS** на baseline
и те же28на prototype:38уникальных, не66. Ни skips, ни xfail для скрытия ошибок.
Регрессии ограничены two-Q2, one-Q2 field/free/persistence-invalid/unsupported
contracts; не запускались full380/384/annual385/compat/fullcheck/portable.
Старые артефакты/SHA/3FAIL380 неизменны. Preflight подтвердил native/environment
и новый source fingerprint, но это не общая аттестация candidate0.3.3.

Код инструментов: [source binding](../scripts/q2_r_reuse394.py:18),
[RHS capture без интегрирования](../scripts/q2_r_reuse394.py:30),
[paired statistics](../scripts/q2_r_reuse394.py:74),
[unit tests](../tests/test_q2_r_reuse394.py:10).
Полный sealed plan, frozen input JSON, timings, quality states/checkpoints,
observers, source/AST checks, логи и guarded resources — в reviewed Project-Archives.
Локальный prototype commit дополнительно сохранён Git bundle с parentfe0f456;
это неопубликованный branch, он не является ancestor публичного dev.
Из Git patch восстанавливаются точные source bytes; bundle восстанавливает
также точный локальный commit. На другом ПК сначала проверить данные и среду,
не выполнять команды из архивов/JSON автоматически.

Подготовительные неуспехи вне scientific workers: PowerShell не разобрал
brace-path до исполнения; Git quoted Unicode filename вызвал WinError123
при подсчёте размера checkout. Исправлены способ вызова и ls-files -z;
физика/данные/численные критерии этим не менялись. Все10guarded jobs успешны.

## Решение и следующий этап

**GO TO REVIEW exact prototype**, но не GO production и не новый scientificPASS.
До потенциального внедрения отдельно:

1. Проверить exact patch/ownership/error paths/private interfaces; не смешивать
   с body-Q preparation или продолжительным solver. Любое новое изменение
   аннулирует тождественность именно измеренного prototype.
2. После разрешения подготовить новый isolated candidate/source/environment
   fingerprint. Повторить0/1/2figure, standalone free/zeroQ, independent field
   gradients/rotation covariance/reaction/E/P/L, packet rawq/S, actual storage/
   recovery/GUI regressions. Сравнивать прежние корректные сценарии без подгонки.
3. Провести отдельную source-bound Q2 scientific qualification по согласованному
   бюджету/протоколу, включая прежние convergence comparisons и сохранение3FAIL,
   а не присвоить старые receipts новому source SHA. Более длинные IC/horizons и
   другие среды не покрыты100s benchmark. Ни одной универсальной accuracy claim.
4. Незатронутость point-Newton/EIH путей обосновать dependency/diff/SHA и
   относящимися регрессиями; правила source-bound gates не ослаблять. Новое
   квалификационное решение не выводится только из равенства коротких q/S.
5. Отдельно требуется решение владельца по Q2 scope391/A+D1 и оставшаяся
   release acceptance; main/LATEST/tag/release этим этапом не разрешаются.

После отчёта **STOP**. Повторных benchmarks/подбора параметров/новой оптимизации
автоматически не делать. Рекомендуемая модель следующего узкого review:
GPT-6.1 Sol High.
