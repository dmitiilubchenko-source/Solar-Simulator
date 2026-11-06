# Q2-395: независимый review и изолированный кандидат

**GO к отдельно разрешённой source-bound Q2-квалификации после её preflight.**
Новый кандидат подготовлен, но scientific qualification/production deployment/
release acceptance не выполнены. Три FAIL380 сохранены; A+D1 не утверждена,
release0.3.3 остаётся **NO-GO**. Никакого merge в main или изменения portable032.

## Что проверялось независимо

Dev до этапа `043d3b7f805e8eae11628030ebfc42c06500e70f`; исходный CI42249928544
завершён success. Чистота baseline/prototype/private trees проверена перед работой.
Baseline `fe0f456f2c7ba3a077eac21fc8413937d6e84fac` не изменён.
Prototype `896030c3206b1010175d6a491e1f5d7063abdcf5` доступен локально и в
проверенном Git bundle394. Нет matching origin ref; GitHub commit API вернул422:
положительного доказательства публичной доступности этого commit нет.

Новый branch `codex/candidate-0.3.3-q2-395`, отдельный worktree,
**commit `f723a2162b4e115378959e244f428529be2d4516`**, parent точныйfe0f456.
Применён только [patch394](../scripts/validation/q2-r-reuse394.patch), SHA256
`df958f9f4c41ad9f3ed57ec2851c30de8b55e608287bd4ebeecfb2f902abbdc6`.
Два source files и весь Git tree равны prototype; commit отличается metadata Git.
Новый кандидат не является обновлением frozenfe0f456 и не перенесён в dev runtime.

Полные394source SHA, actual environment/native fingerprint, все input/result SHA,
raw-source review и измерения: [машинный отчёт395](q2-optimization-review-395.json).
Фактическое environment нового кандидата:
`d1a2e827e6edcf43ceedacbfc3f62ad72b624c2f0f03332326aa0cf6185695c7`;
baseline `056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a`.
Новый фактически вычисленный fingerprint совпал с394prototype именно потому,
что source/dependencies те же; он отличается отfe0f456, не подделан под receipt.

Native SHA256 `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`.
Python3.14.2t/cp314t, NumPy2.5.1/SciPy1.18.1; BLAS OMP/OPENBLAS/MKL=1,
VECLIB/NUMEXPR/PYTHONHASHSEED unset. Dependencies/native используются read-only
из исходной candidate venv с явной активацией новых source bytes. Это не новая
portable/wheel установка и не доказательство переносимости среды на другой ПК.
Python/Rust version metadata и394source-scope files, кроме двух py, неизменны.
Старый `verify_freeze` **отказал** новому commit: `Candidate Git commit/tree changed`.

## Code review: результат и границы private helpers

Проверен весь exact diff, original source, callers и обработчики, не только PASS394.

- RHS берёт q из текущего y для каждой фигуры, строит owned R через прежний
  `rotation_matrix`; tuple локален этому вызову. Никакого R между stages/RHS.
- `_corrections` передаёт ту же R в `_correction`; angular velocity использует
  тот же matrix в прежнем `R @ ((R.T @ validated_S)/moments)`. Field/tensor/force/
  reaction/torque/potential operations и их суммирование сохранились.
- `rotation_matrix`, `_vector`, RigidFigure, quaternion_rate, RotationDOP853,
  validate/validate_experiment/invariants остались теми же по AST. Field geometry/
  masses/source/finite-output guards и математический tail совпали буквально.
  Public correction/corrections/integrate signatures прежние; standalone omega
  public signature и return expression тоже прежние.
- Private prepared-R helpers **не валидируют произвольную стороннюю матрицу**:
  это внутренний precondition «свежая R из проверенного текущего q». Проверены
  все production callers. Public matrix keyword вызывает TypeError, внедрение
  matrices в checkpoint отвергается codec. Не считать underscore API песочницей
  для недоверенного Python-кода. JSON не исполняется.
- На16новых fixed RHS probes (4cases×4stage variants) записаны реальные R calls
  и полученные q. R counts2K→K, каждый R соответствует latest q; readonly R
  не изменён потребителями, с y не разделяет память. Derivatives exact, y unchanged.
  Это дополнение к кратким394probes, не повтор benchmark.
- Валидация S, масс, geometry, конечности и initial q norm не удалена. Нет Qbody
  cache, новых переменных physical model/force order/controller/settings/schema.

Модель остаётся прежней Newton total-degree-two M–Q без Q–Q/tides/EIH coupling.
R(q) детерминирована и только читается; перенос повторного вычисления R не меняет
формулы. Собственный review/math/data audit не является внешней рецензией.

## Изменение порядка исключений

Проверены совместно некорректные stage q/geometry/S, first/second figure,
coincident positions, public invalid source+q, bool S и injection private matrix.

|Случай|Baseline|Новый код|Интерпретация|
|---|---|---|---|
|q=0 и r внутри sphere|ValueError: внешняя sphere|ValueError: нулевой q|Заявленный перенос подготовки R раньше field|
|q второй фигуры=0 и sphere первой нарушена|Внешняя sphere|Нулевой q|Тот же приоритет, обе причины недопустимы|
|S=NaN и sphere нарушена|Внешняя sphere|Внешняя sphere|S validation не обходится на допустимой geometry|
|r=0 и q=0|Coincident-position ValueError|Та же ошибка|Монопольный guard раньше подготовки R|
|q=0 и bad S при допустимой geometry|Нулевой q|Нулевой q|Public/field q guard сохранён|
|Public field bad source+q / matrix keyword|Отказ|Тот же класс отказа|Public validation/injection contract сохранён|

Оба варианта отклоняют все эти данные без изменения y/snapshots. Изменён только
первый текст ошибки в оговорённых случаях; GUI `_guard/_poll` не выбирают
ветку по этому тексту, а сохраняют предыдущий committed опыт. Это не скрытый
расчёт на некорректной geometry и не основание для ревизии benchmark patch.

## Timing394: отдельный offline пересчёт

Прочитан verified349109B archive394,
SHA256 `4182055bebe7214eadaf3ed4cc234de5fd675f0eafdd3c589e2583c05f466520`;
проверены все84manifest members, исходный plan/source binding и raw samples.
Новый reviewer не вызывает394paired_summary и не доверяет флагам PASS:
exact-binary→Decimal80 sums, медианы и sign probability вычислены заново.
Проверены реальные ABBA/BAAB orders,512microcalls/8macro rollouts и case order.

|Уровень|Median paired speedup|Range|Median paired wall saving,s|
|---|---|---|---|
|RHS|1.06104994|1.03099047–1.08290340|.0585123 на4096calls/series|
|Short calculation|1.06225298|1.02621636–1.08516666|.1217205 на64two-packet rollouts/series|

Сохранена проигравшая one/Python macro series: ratio.99476349, около0.53% медленнее.
Aggregate положителен5/5 в обоих уровнях. One-sided p=1/32 верен **условно**
независимым series/симметричному null sign; общая Windows машина/caches не доказывает
эти предположения. Micro/macro не независимы, p не перемножаются. Не обещается
1.06× для всех сценариев/всего GUI. CPU-квантование~15.625ms сохранено как caveat.

Аллокации перечитаны из raw: peak+120B(one)/+344B(two), retained0 после128calls.
Новый tuple и одновременная жизнь подготовленных R объясняют небольшой peak рост,
несмотря на меньшее число R constructions. Нет доказательства отсутствия всех
C/OS allocations/утечек на любом горизонте; joint process private не per-variant
working-set difference. Основания повторять benchmark не обнаружены; новых0.

## Targeted candidate regressions

Фиксированный execution plan и input SHA записаны до запуска; критерий — exact
binary64 на арифметически идентичных путях, никаких rtol/IC/phase изменений.
Epochs0/50/100s, два cold packets50s, два backend.

|Case|Backend|Rotations|Epochs,s|Exact p/v/q/S + restart|
|---|---|---|---|---|
|one|python|1|0/50/100|YES|
|two|python|2|0/50/100|YES|
|free|python|1|0/50/100|YES|
|zeroQ|python|2|0/50/100|YES|
|one|rust|1|0/50/100|YES|
|two|rust|2|0/50/100|YES|
|free|rust|1|0/50/100|YES|
|zeroQ|rust|2|0/50/100|YES|
|point|python|0|0/50/100|YES|
|eih-j2|python|0|0/50/100|YES|
|point|rust|0|0/50/100|YES|
|eih-j2|rust|0|0/50/100|YES|

Итого **12cases /36paired saved epochs**, полные документы/checkpoint SHA,
r/v/rawq/S совпали. Same-packet save→load→advance exact; input/midpoint unchanged.
Два standalone rotation controls (free/pair) с прежним solver на тех же эпохах
тоже exact. Сравнение source внутри одного backend, не ложная cross-backend identity.

Для Newton/rotating cases независимый ScalarDecimal observer393 вычисляет
орбитальную+spin E, P, L, rawqnorm и устойчивый SO(3) угол; source angles0.
Для EIH+fixedJ2 новый read-only observer берёт p_i=∂L/∂v_i complex-step,
E=Σv_i·p_i−L и L=Σr_i×p_i из scalar EIH Lagrangian — другой путь, чем
production vectorized Noether. Лагранжиан сверен с
[Justin Vines, EIH action, стр.3](https://fiteoweb.unige.ch/~maggiore/GWVol1/EIHLagrangian.pdf)
и ранее проверенным independent variational test. Новый observer имеет analytic
free-particle/Newton-limit и invalid-input tests. SI; rest-mass energy исключена.
Fixed J2 добавляется как прежний Newton potential; mixed PN–J2/higher orders
остаются вне модели. Полный L при внешней fixed axis **не** заявлен инвариантом.
Максимальное relative agreement independent/runtime diagnostics:7.47351e-15
при заранее заданном контрольном1e-12. Это rounding check, не orbital error bound.

**76unique pytest PASS**:12offline helper+7Noether observer+57existing regressions.
Последние57выполнены отдельно на baseline и на canonical candidate source,
то есть133test executions, не133unique;0skip/xfail. Существующие gradients,
reaction/torque/covariance/q-sign/free/zeroQ/invalid/storage/native/1PN tests
сохранили собственные пороги. Никаких full380/year384/385/fullcheck/portable.

**6реальных Tk journeys** (point/one/two ×Py/Rust): actual load/save button
callbacks, start/pause, explicit planned batch1, stop/recovery/reload/continue,
cancel, corrupt JSON, actual OS save-to-directory error, readonly inspection;
invalid-q/unsupported mixed-mode load в rotating cases. Сохранённые q/S и настройки
не меняются, GUI epochs совпали с независимо сохранённым baseline.
LOCALAPPDATA выделен внутри нового scientific output; личные файлы не затронуты.

## Два неуспеха стенда: не скрыты

1. Первый baseline worker завершил8rotating cases, затем observer393 получил
   обычный checkpoint без поля rotations и выдал KeyError. Codec/runtime корректны:
   для0rotation поле исторически отсутствует. Новый owned observer-only dict
   явно задаёт пустой список; original documents/observer393 не менялись.
   Завершённые8results reused после SHA/metadata проверки, остальные4case выполнены
   отдельно, source/criteria/budget сохранены. Failed log/partial checkpoint сохранены.
2. Первый GUI draft не выставил batch1. Existing GUI default20 нарушал planned
   one-packet recipe. Отдельный actualTk submission-only reproducer (0integrations)
   записал steps20/dt50, то есть **расчётную запрошенную** duration1000 вместо50.
   Post-step numeric snapshot failed draft не был записан; его не реконструировали
   и не выдаём как сохранённую1000s trajectory. Новый harness перед стартом явно
   выбирает существующий batch1 по исходному плану; oldattempt/data оставлены.

Оба исправления относятся только к новым diagnostic scripts. Исходные execution
plans/bindings/scripts и SHA не переписывались, supplements/source SHA отдельные.
Ни скрытой ошибки patch, требующей молчаливой ревизии, ни unexplained candidate
numerical delta не обнаружено. Source from no-checkout сначала не materialized;
штатный read-tree только свежего пустого worktree завершил подготовку до patch.
Новый Noether observer выделен в отдельный helper; executed review helper restored
byte-exact по прежнему binding, старый binding не менялся.

## Impact/source-bound audit

|Компонент|Фактическое воздействие|Проверка/оставшееся|
|---|---|---|
|Dynamic one/two-Q2|Новый RHS preparation/call structure|Exact finite probes/packets, gradients/invariants; нужна новая scientific qualification|
|Standalone rotation|Public omega делегирует тот же return expression|Free/pair exact, old mathematical tests; source fingerprint новый|
|Point Newton|Условие rotations пусто → прежний accuracy/Verlet path|Unchanged dependency source SHA+short exact Py/Rust; Newton384 не повторён|
|EIH+fixedJ2|Динамическое вращение здесь недопустимо; relativity/oblateness/forces не менялись|Exact short Py/Rust+independent Noether; annual385 не повторён|
|Native interface|Все Rust/PyO3/wrapper/ABI sources/deps/binary прежние|Actual compiled module path/SHA, invalid/missing-native/thread tests|
|Storage/recovery/GUI|Source/schema/callbacks прежние; вращательный readout зависит от omega|Canonical candidate actualTk/data tests; полной release acceptance нет|

В machine JSON — равные SHA experiment/accuracy/error_control/coordinates/
simulation/relativity/oblateness/native_forces/rust_backend/diagnostics/storage/
branch_io/recovery/app/inspection_view/convergence/spin_initial. Import graph
не принимается за доказательство branch coverage: point/PN ветви `advance`
проверены реально, rotating inspection loops исполняются только при rotations.
Новые source fingerprints не наследуют384/385/387–390 receipts. Route391 для
presentation-only delta **не** подходит изменённым physical Python modules.

## Ресурсы и решение

Все **11controlled attempts**, включая2harness failures: **65.28125 CPU s /
54.916663 active wall s**, worker+supervisor; caps180/360/1GiB/128MiB,
early144/288/900MiB/112MiB неизменны. ResourceSTOP нет.
Worker sampled private peak242143232B (230.93MiB), RSS182603776B;
supervisor OS peakcommit37650432B. Консервативная сумма раздельных private peaks
279793664B (266.83MiB), не синхронный пик. Частота50ms,
retained Windows final CPU handles. Возможны короткие пропущенные пики/children;
outer venv launcher/последний record-tail CPU не полностью охвачены. Не hard OS quota.
Scientific output на последнем sample2342013B, sampled filecount peak183.
Финальные reports/bundle отдельно в пределах128MiB. Recoverable source-only sparse
checkout нового кандидата6392147B и существующая dependency venv не смешиваются
с experimental artifact bytes. Чтение/редактирование/Git/CI/обязательная backup
отдельно; activewall не длительность всего чата. Никакого benchmark rerun.

Полная scientific qualification не исполнялась. Изменены только новые review/
observer tools/tests/docs в dev; оптимизированный candidate остаётся отдельно.
Code/verified lines: [offline audit](../scripts/q2_review395.py:14),
[timing arithmetic](../scripts/q2_review395.py:42),
[Noether observer](../scripts/q2_noether_observer395.py:5),
[offline tests](../tests/test_q2_review395.py:14),
[observer tests](../tests/test_q2_observer395.py:5).

Следующий конкретный этап — [новая ограниченная source-bound квалификация](q2-optimized-qualification-protocol-395.md).
План готов; нужен небольшой технический source/output-binding preflight adapter,
поскольку старый380run нельзя просто объявить квалификацией нового source.
**GO к этому отдельному этапу, NO-GO автоматическому запуску/внедрению/release.**
Сохранение3FAIL не становится waiver. Main/tag/LATEST/portable032 неизменны.
После отчёта STOP. Рекомендуемая модель: GPT-6.1 Sol High.
