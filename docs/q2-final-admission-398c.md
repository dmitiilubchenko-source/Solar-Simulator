# Q2-398C: технический допуск к независимым группам399

2026-11-07. **Технический GO. Следующий этап — реальные научные группы399,
только после отдельного разрешения владельца.** Никакая из58полных траекторий
в398C не выполнялась. Научная квалификация ещё не получена; release0.3.3 NO-GO,
A+D1 не утверждена. [Машинный отчёт](q2-final-admission-398c.json).

## Зафиксированный исполняемый план

[Sealed plan399](../scripts/q2-qualification399-plan.json), SHA256
`3e1ceb821514a770632f7f5c0ac37260a869198d94e5adc60d81bfaa69bbe644`.
Tool commit`78fe4cac8873914e5d1fa084d510f3f279b33c68`.
После итоговых регрессий выполнен настоящий CLI `--check-plan`:58IDs приняты,
ни controller, ни scientificworker этим вызовом не запускались.
Сначала создан проверенный commit tools, затем план с его SHA; самоссылки нет.
Создание плана и его technicalGO **не являются разрешением выполнить399**.

Исходный dev/origin8a26a96 был чистым. Baseline
`fe0f456f2c7ba3a077eac21fc8413937d6e84fac` и candidate
`f723a2162b4e115378959e244f428529be2d4516` не менялись. В отдельных процессах
повторно проверены только source/native/environment fingerprints, без интеграции.
NativeSHA`651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`,
прежняя read-only384venv Python3.14.2t/NumPy2.5.1/SciPy1.18.1, BLAS1.
Candidate full Git blob/materialized source SHA совпали с frozen395.

Исходный contract398 SHA`b6131f0abeeec63ee2e324a34b22f6c96008e67e747fa94e9ee52b2795c0bd28`,
reference397 SHA`52b2d4efebad15fc25739776d3a8939015a6be42be1b88d9b3d5f999271e9338`,
старые380reference/NPZ/IC/G/SI/эпохи/criteria неизменны. Python/Rust/RK45 prefixes
из398/398B не повторялись. Их результаты используются с исходными bindings.

## Групповой controller и восстановление

[Существующий driver](../scripts/run_q2_qualification399.py) теперь принимает
`--group baseline:python`, `baseline:rust`, `candidate:python`, `candidate:rust`
или `baseline:evaluate`. Один вызов запускает только выбранную фазу.
Плановый порядок приведён выше в JSON `execution_order`; независимые группы
не выбираются по номеру attempt. Evaluator требует полноту всех четырёх.

Общий root содержит immutable `run.json`; каждая группа — собственный каталог,
binding/лимиты, launcher claims, guard/attempt receipts, jobSHA, `verified.json`
и `final.json`. Физические cold/continuous recipes не заменены продолжением
другой группы. Старый all-cohort loop устранён; это было ограничение dispatch,
**не доказательство повторного интегрирования completed jobs в398B**.

Final group повторно не запускается, receipt не перезаписывается. При resume
завершённые jobs проверяются по exact source/input/tool/epoch binding и SHA,
затем пропускаются без `run_job`. Подтверждённый KeyboardInterrupt между jobs
можно продолжить только без partial и при остатке исходного бюджета. CPU/wall
предыдущей попытки сохраняются; startup/launcher нового процесса учитываются.
Resource STOP, partial job, corrupt/missing supervisor или orphan launcher —
STOP с сохранением originals, без обнуления бюджета и автоматической переинтеграции.

Проверены реальные CLI/controller/неизменённый385monitor/дочерние процессы на
**шести явно synthetic control records**, с невозможным для real58 набором IDs.
Только в доверенном тестовом harness заменены admission/runtime/worker command;
физические функции не вызываются. Настоящий sealed-plan admission проверен отдельно.
Прерывание между jobs → resume не повторил первый job; переход между группами
не изменил закрытую группу. Запуск evaluator до полноты отказал; после четырёх
групп control fixture дошёл до evaluator. Повтор closed group отказал read-only.
Это проверка инфраструктуры, не synthetic scientificqualification.

## Evaluator: стоимость и исправление прежнего описания

В398B ошибочно описан существующий full58synthetic test как двухэпоховый.
В действительности `payload(job)` использовал `job['epochs']`:65/81эпоху;
две эпохи были только default при отсутствии job. Исторический отчёт не редактирован.

В398C новый заранее заданный **static synthetic** набор использовал все58IDs,
исходные IC/settings и полные65/81сетки. Все frozen IC выдержали codec roundtrip.
Actual integrations/RHS=0. Схемные counters fixtures искусственные и не являются
измерением solver/native. Полные fake scientificjob files не сохранялись.

|Измеренная часть|CPU s|Wall s|
|---|---:|---:|
|Генерация synthetic fixtures|4.890625|4.931410|
|Сам существующий `assess_all`|1.578125|1.606996|

28source contrasts дали ожидаемый syntheticPASS,56runtime cases — общий
scientificFAIL,16strict-convergence FAIL на статических данных. Эти16 не имеют
отношения к трём historicalFAIL380. Раздельная классификация работает.
Synthetic K1reference slots не являются настоящим4000sRK45 reference; его два
исходных jobs остаются обязательными в399. Реальные старые K1short/K2reference
proofs сохраняются отдельно; empirical levelgap не является rigorouserrorbound.

Faults: missing job, неверный K1/K2 shape, IC, source, protocol и native counter
отклонены. Независимые380scalar E/P/L сверены с runtime-invariant calculations;
qnorm считается по raw quaternion без проекции. Saved392audit сохранил3historicFAIL.

Обнаружен отдельный дефект validation tooling: прямой `assess_all` не проверял
declared contractSHA. Сохранён воспроизводимый failing test и прежний source.
Добавлен ранний отказ foreign/missing protocolSHA. AST математической редукции
побитно структурно совпал после исключения одного admission predicate; силы,
интегратор, формулы наблюдаемых и scientificcriteria не менялись.

Итоговый current-revision subset: **44PASS/1explicitdeselected**. Старый full58
synthetic test локально заменён более сильным измеренным full58/realIC набором
и остаётся в обычном CI. Было два ожидаемых исходных failing tests, неожиданных
отказов не было. SoftwarePASS не доказывает физическую точность.

Перед публикацией выявлена dependency-contract проблема: controller импортирует
psutil, а прежний CI не объявлял эту зависимость. Используется отдельный
[requirements/qualification.txt](../requirements/qualification.txt) с уже
проверенной на основном ПК [psutil7.2.2](https://pypi.org/project/psutil/7.2.2/).
Первоначальное добавление extra в pyproject вызвало10setup errors исторических
375fixtures в desktopCI42388831933 (158PASS): все из-за одного sourceSHA mismatch.
Прежние точные pyproject bytes восстановлены с проверкой исходного375SHA;
зависимость вынесена в отдельный requirements файл. Красный CIlog сохранён,
исторические receipts/архивы/SHA/критерии не менялись. Саму384venv и численные
source files после computational checks не меняли. Повторный CI обязателен.

## Зафиксированные бюджеты399

Все лимиты относятся к будущему отдельно разрешённому399, не расходуются здесь.
Оценки групп наследуют398B whole-prefix scaling с резервами; full4000s throughput
не измерен. Hard-vs-early headroom сохраняет место для sampled STOP и записи.

|Фаза|Jobs|ОриентирCPU s|CPU cap/early|Wall cap/early|
|---|---:|---:|---:|---:|
|baseline Python +2reference|16|102.312|180/144|360/288|
|baseline Rust|14|82.625|180/144|360/288|
|candidate Python|14|90.781|180/144|360/288|
|candidate Rust|14|80.656|180/144|360/288|
|Отдельный evaluator|проверяет58|40.625 с резервами|60/48|120/96|

На фазу RAM1GiB/early900MiB, output128MiB/early112MiB. Группы независимы:
итоговые cap720CPU/1440wall для четырёх групп не означают ожидаемое потребление.
Ориентир~356CPU групп отличается от лимитов. Evaluator40.625CPU — консервативная
модель:8×1.578125 arithmetic,+3startup,+10rawSHA/JSONIO,+10supervision,+5audit.
Его полный58file I/O и post-evaluator diagnostic audit не измерены на будущих
science arrays. Это запас с guardedSTOP, а не гарантия любого времени исполнения.
Ожидаемый scientific output~37.55MB с прежней1.25margin; новые prefixes не нужны.

Восстановление после выключения: проверить точные Git/source/environment/input
SHA, затем launcher/guard/attempt receipts, каждую finished job и finalreceipt.
Без подтверждённого accounting не выдавать новый бюджет. Partial сохранять,
не превращать в completed и не переписывать. При resourceSTOP менять лимиты
после просмотра результатов запрещено; статус остаётся PARTIAL/NO-GO.

Controller учитывает собственный processCPU со startup и child final CPU по
существующему monitor. Wall использует processcreation и monotonicfloor.
Дополнительно списывает0.25CPU/0.25wall на receipt/fsync/exit tail: это allowance,
не measuredbound.50ms polling, краткие unseen descendants/spikes и отсутствие
физического power-cut теста явно ограничивают строгость resource guarantees.

## Независимый итоговый аудит и backup

После guarded evaluator его `final.json` остаётся immutable. Дополнительный
read-only audit выполняется в отдельном каталоге тем же существующим385monitor:
`used_cpu`/прошедший activewall инициализировать chargedзначениями evaluator,
лимиты остаются48CPU/96wall early и60/120 cap. Сохранить отдельный audit receipt,
связанный SHA с закрытым evaluator/всеми группами; не обнулять общий бюджет.
План заранее выбирает все56initial/final runtime frames для диагностического
393Decimal80/110observer. Это существующие проверенные функции, не новый
интегратор и не новые scientificthresholds. Если audit не завершён — не объявлять
итоговый399complete. Повтор `assess_all` сам по себе не называть независимой проверкой.

Проверить все58IDs/owners/epoch/settingsSHA, exact same-backend source arrays,
reference levels, scalarE/P/L/rawqnorm и сохранность3historicFAIL. Не путать
source-equivalence, reference-level agreement, физическую точность и releaseGO.

После каждой группы и evaluator — новая reviewed filteredqueue, archive/manifest,
source/input/raw/output/guard receipts и независимый cloudreadback.395bundle,
398Python/RK45 и398BRust используются как verified dependencies, не дублируются.
Предложенный отдельный localbackup cap60CPU/240wall,early48/192,512/450MiB,
128/112MiB output на этап сохранения; измеренный398Bprepare1.05CPU/archive0.31CPU
и иной объём будущих states обосновывают резерв, но не измеренный throughput.
Connector/server CPU локально не наблюдаем; wall/status записывать отдельно.
Timeout/upload failure = CLOUD_UNVERIFIED, originals сохраняются, доступ не расширять.

## Результат398C

8guardedattempts, **33.578125CPU/25.318565activewall**, включая оба исходных
failing tests и весь supervision. Sampled worker private306298880B,
RSS168534016B, supervisor peak37511168B; пики не синхронные. Последний guard
учёл601593B diagnostic artifacts. Caps45/120/512MiB/32MiB,
early35/90/450MiB/26MiB не менялись; новых computational checks далее нет.
Git/CI/publication и обязательный incremental backup отдельно от этих8attempts.

**Technical readiness GO; scientific readiness — допуск выполнить квалификацию
после разрешения, результатов399 ещё нет; release readiness NO-GO.**
Productionphysics/integrators/R-reuse/native, оба кандидата, historicalevidence,
main/tag/LATEST/portable032 не менялись. Новый подготовительный этап не требуется
без конкретного нового блокера. После оформления отчёта STOP.
