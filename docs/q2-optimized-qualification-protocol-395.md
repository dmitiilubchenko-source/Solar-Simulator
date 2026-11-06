# Следующая source-bound Q2-квалификация: проект395

**PROPOSED / NOT EXECUTED.** Нужны отдельное задание на исполнение и технический
preflight нового запуска. Это не принятие A+D1 и не разрешение релиза.
Кандидат `f723a2162b4e115378959e244f428529be2d4516`, baseline
`fe0f456f2c7ba3a077eac21fc8413937d6e84fac`. Оба immutable/отдельные worktrees.
Единственный delta — exact patch394, SHA256
`df958f9f4c41ad9f3ed57ec2851c30de8b55e608287bd4ebeecfb2f902abbdc6`.
Фактические fingerprints и scope: [review395](q2-optimization-review-395.md).

## Узкая цель и фиксированный состав

Проверить перенос ранее исследованных numerical recipes на новый source.
Не доказывать универсальную точность/монотонность float64, не искать новый rtol,
не добавлять модели сил, body-Q cache или persistent solver в приложение.

1. Две фигуры: **оба исходных физических IC380** (two-/three-bodies),
   оба backend Python/Rust, три прежних уровня, два recipes, два source.
   Итого48runtime trajectories. Все четыре cohorts включены:3исторических
   convergence FAIL и Rust/three-body PASS-control; неудобные ветви не исключаются.
2. Legacy одна фигура: exact one-Python/one-Rust IC394 (SHA в395 JSON),
   единственные исходные settings rtol1e-11/atolr1e-7/atolv1e-11/oldqSatols,
   два recipes ×два source:8runtime trajectories. Это legacy controls,
   не новая произвольная сетка допусков.
3. Для two-Q2 использовать только **проверенные сохранённые** независимые
   matrix/body-momentum RK45 reference0/reference1 из380 NPZ. Проверить IC,
   G, единицы, epochs и оба reference SHA, перед использованием повторно
   проверить uncertainty прежним evaluator. Ничего не перезаписывать.
4. Для one-Q2 два новых reference4000s старым independent
   `two_q2_reference380.reference`, rtol3e-11/3e-13, после короткого K=1
   dimension/math preflight. Это2reference trajectories, не production solver.
   Калибровка references не означает rigorous IVP error bound.

Всего **56runtime +2reference =58фиксированных trajectories**. Выполнение этой
серии в395 не разрешалось и **не происходило**. Не повторяются исходные
compatibility/annual/Newton matrices, portable или весь исторический380 pipeline.
Не добавлять новые случаи по результатам промежуточных ошибок.

## Recipes и пороги

Newton total-degree-two M–Q, SI, q body→inertial, S inertial; no Q–Q/tides/EIH.
G exact binary64 прежний. IC две фигуры — из оригинального380 plan побитно,
одна фигура — из проверенного394 input; q/S не перенормировать и не подгонять.

Two-Q2:4000s, прежние65epochs, шаг выдачи62.5s.
Cold —64последовательных `advance(state,1)` с dt62.5, каждый новый solver.
Continuous — **один** существующий `nbody_rotation.integrate` на тех же65epochs.
Это разные recipes; continuous не заменяет cold и не означает оптимизацию runtime.

|Уровень380|rtol|position_atol,m|velocity_atol,m/s|Множитель q/S atol|
|---|---|---|---|---|
|coarse|1e-9|1e-6|1e-10|100|
|standard|1e-11|1e-8|1e-12|1|
|fine|3e-13|3e-10|3e-14|.03|

Legacy one-Q2:4000s,81epochs/50s,80cold packets либо один continuous solver;
единственные исходные legacy settings. Сравнивать source только внутри
одного backend/recipe/epoch; не объединять epochs или менять пакетизацию.

Два независимых вывода, не один общий искусственный PASS:

- **Source equivalence gate:** exact binary64 p/v/rawq/S на каждой эпохе,
  сопоставимые RHS/native counts, unchanged IC/files/snapshots. Необъяснённое
  отличие → NO-GO принятия патча; сохранить полные векторы и источник.
- **Старые научные criteria380:** energy/angular drift1e-8, linear1e-12,
  rawqnorm1e-8, reference difference1e-7 и uncertainty1e-8, неизменные scales;
  standard-fine < coarse-fine по прежнему max four-component metric.
  Сохранить этот inequality, даже если разность ниже разрешения reference.
  Дополнительный stable SO(3)/Decimal observer не заменяет исходный evaluator.
- One-Q2 controls: exact source agreement плюс energy/L/P/qnorm limits выше;
  reference normalized position и Frobenius R difference <1e-8 из прежнего
  one-Q2 two-body contract. Velocity/S differences диагностические, без нового
  accuracy gate. Scales: initial pair distance, initial relative speed и initial
  |S|; reference-level gap по четырём components <1e-8. Эти numerical limits
  не сертифицируют истинную ошибку; при reference-resolution floor рядом с
  измеряемым difference интерпретация остаётся UNRESOLVED. Нового более строгого
  absolute accuracy profile этот pilot не вводит.
- **Все три historical FAIL380 остаются historical FAIL.** Их новое повторение
  можно отметить отдельно. Равенство candidate/baseline при тех же FAIL означает
  equivalence PASS и strict-convergence FAIL, а не scientific/release PASS.
  При изменении состава FAIL исследовать расхождение; не править старый отчёт.

Reference uncertainty — оценка согласия двух численных решений/orthogonality,
не сертифицированная граница истинной ошибки. Различия~1e-15 не разрешены
старыми RK45 references; ограничения392/393 сохранить в новом отчёте.

## Исполнение и preflight

Переиспользовать `validate_two_q2_380.represented/difference`,
`two_q2_reference380.reference/independent_invariants` и saved-data observer392/393.
Старые планы/receipts и их `verify` не редактировать. Прямой `run` старого380
драйвера не является запуском новой квалификации: он связывает ROOT/source,
environment и жёсткий старый состав/результат. Не подменять ROOT/SHA ради PASS.

Перед основной серией нужен **небольшой явный source-bound adapter** новых
output/manifest и фиксированного job list: runtime source origin/candidate commit
и actual environment проверяются отдельно от SHA исполняемых tool sources.
Из395 freeze брать actual source files, не заменять новые hashes старыми.
Никакой общей queue/framework или нового solver. Adapter ещё не реализован395.

Технический preflight до58trajectories обязан проверить:

- all frozen Git/patch/native/dependency/IC/reference SHA и actual imports;
- сохранность исходных scientific criteria, wrong SHA/source-root/environment отказ;
- новое пустое output, отказ существующему/частичному/corrupt result;
- короткий K=1 reference и old380 method/scales без смены математических определений;
- ресурсную оценку по реальным RHS/observer/IO costs, а не одному времени интегратора.

Для уменьшения import/fingerprint overhead допустимы4последовательных worker
processes, по одному на (source,backend), каждый выполняет фиксированные14jobs
из свежих IC. Независимый reference отдельно. Source/environment attestation
до/после worker, immutable code на весь запуск; CPU/RAM/disk/wall надзор50ms
сохраняется. Никакого переноса controller state между trajectories.

## Предлагаемый предел и остановка

Новый отдельный budget, **не продолжение и не увеличение395 задним числом**:
180CPU s,360active wall s,1GiB sampled private,128MiB outputs;
early144CPU/288wall/900MiB/112MiB. Включить preflight, все неуспехи и supervisor.
Предварительная оценка60–130CPU/90–260wall, до32MiB outputs/до384MiB worker:
392 даёт~4350cold/~450continuous RHS на4000s;394RHS~0.2–0.33ms,
плюс source/dependency hashing, reference, metadata, observer и файловые операции.
Это оценка с существенной неопределённостью, не гарантированное время.

Если preflight не обосновывает завершение до early limits — NO-GO до основной
серии; не менять выборку/пороги по результату. При stop сохранить completed case
arrays/checkpoints/logs/manifests и точную причину PARTIAL, лимиты не поднимать.
Cold допускает только подтверждённый same-packet prefix resume. Прерванный
continuous case без controller state **нельзя** продолжить cold и выдать за тот
же recipe; сохранить partial и отдельно разрешить повтор только неполного case.

Каждая законченная trajectory имеет собственный immutable payload+SHA, owner
source/backend/settings/epochs/IC/reference provenance. Не перезаписывать старые
планы/результаты, не исполнять команды из JSON. Архивация — Project-Archives,
проверка облачных bytes/SHA отдельно от локальной очереди.

## Выход

Отдельные equivalence/physics-criteria/reference-resolution/resource conclusions.
Только заданная synthetic область и horizon; не real Earth–Moon/JPL/year claim.
Newton384/annual385 не повторяются и не наследуются новым source fingerprint.
Полная release/source/native/GUI/portable acceptance и решение владельца A+D1
остаются отдельно. После исполнения будущего этапа STOP; main/tag/LATEST не менять.
