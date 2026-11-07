# Q2-398: partial preflight, NO-GO к запуску399

**Обязательный preflight не завершён. Запуск58trajectories399 — NO-GO.**
Вычисления остановлены на34.53125CPU s перед early35; предел не повышался.
Две Rust-cohort и сквозной controller/recovery admission ещё не проверены.
SealedGO execution plan399 **не создан**. Все58scientificjobs не запускались.
Дата:2026-11-07. [Машинный отчёт](q2-qualification-preflight-398.json).

## Источники и неизменный контракт

Dev/origin перед работой `c8b62128e2f2663a9bd55ba6548886f22d745e63`, worktrees чистые.
Baseline `fe0f456f2c7ba3a077eac21fc8413937d6e84fac`, candidate
`f723a2162b4e115378959e244f428529be2d4516` остались неизменными.
NativeSHA`651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`;
newreference397SHA`52b2d4efebad15fc25739776d3a8939015a6be42be1b88d9b3d5f999271e9338`.
Python3.14.2t/NumPy2.5.1/SciPy1.18.1, общий read-only dependency env384,
OMP/OPENBLAS/MKL1. Реальные Python imports обоих кандидатов проверены в отдельных
процессах; metadata dev0.3.2 не использовалась вместо их0.3.3.
Фактические LF-JSON environmentSHA baseline056c455…795a/candidated1a2e827…695c7
сохранены в identities; native/dependency profiles совпали с frozen395.

До первого probe проверены full394source bindings, candidate parentfe0f456,
ровно два R-reuse source delta, exactpatch394SHA df958f9f…abbdc6. Эти проверки
завершились **до** первого adapter failure; их код, binding и traceback сохранены.
Повторного ROOT/source substitution не было.

[Plan398](../scripts/q2-qualification398-plan.json) не менялся,
SHA`b6131f0abeeec63ee2e324a34b22f6c96008e67e747fa94e9ee52b2795c0bd28`:
48two-Q2+8one-Q2runtime+2RK45refs,58uniqueIDs, те же IC/epochs/levels/recipes/G/SI.
Scientific критерии395/380, savedK2reference380 и три strictFAIL не изменены.

## Что реализовано и что действительно проверено

Добавлены [узкий executor](../scripts/q2_execution398.py) и
[resource-controlled command399](../scripts/run_q2_qualification399.py).
Это отдельные validation tools, не новый integrator/evaluator или runtime.
Они вызывают существующие Experiment.advance/nbody_rotation.integrate,
reference397, represented/difference380, scalar invariants380 и SO3 observer393.
Научные gates используют **runtime** E/P/L с независимой cross-check1e-12,
исходные нормировки380 и raw quaternion norm; новая body-ID адаптация не заменяет
исторические математические определения. Валидация incomplete/NaN/badshape/zero
normalization/checkpoint mismatch вызывает STOP, а не нулевую ошибку.

Сохраняются raw r/v/q/S/R, epochs, точные settings/IC, source/tree/env и toolSHA,
actual RHS/nfev/solver calls/compiled native calls и checkpoint history.
Cold/continuous имеют проверяемое число solver invocations. Финальный manifest
с SHA публикуется последним, файлы fsync+atomic no-replace link; incomplete,
corrupt, чужой binding и повторная запись отклоняются. Неподдерживающая hardlink
файловая система вызывает отказ. На другом ПК нужны новый environment preflight
и реальные roots; эти локальные пути не являются portable-контрактом.

Текущий399command не принимает отсутствующий/blocked sealedGO plan, worker
требует owned supervisor. Завершённые jobs при явно разрешённом resume только
читаются и проверяются; partialjob/missing budget account не возобновляется
молча. Это **draft implementation**: полный controller/admission/recovery
end-to-end здесь не запускался, поэтому готовность к58jobs не объявляется.
Программные SHA/JSON не являются защитой от злоумышленника, переписывающего всю
историю; это provenance/integrity для фиксированного научного запуска.

### Подтверждённый дефект scalar observer

`independent_invariants380` использует enumerate(rotations) как индекс тела.
Для единственной фигуры B это неверно. До исправления сохранён zero-integration
reproducer: E relative discrepancy с Decimal393 **0.0007103709664241898**.
Новая `independent_by_id` только переставляет p/v/mass так, чтобы источники
шли первыми в порядке rotations, затем вызывает **неизменный** scalar kernel380.
Для первоначального A/B order редукция побитно прежняя; для B отдельно сверена
с Decimal observer. RHS/forces/candidates и старые научные результаты не менялись.

### Подтверждённый дефект нового адаптера на continuous t=0

Affine coordinate roundtrip DOP853 может вернуть приt=0 r/v, отличающиеся от
входных на rounding. Старый continuous evaluator380 использовал эти raw samples.
Попытка нового адаптера сохранить такой sample как Experiment(initial==current)
правильно отвергнута storage. Failure/traceback/partial/rawsource версии сохранены.

Исправлено только представление записи: genuine IC checkpoint хранится отдельно,
raw numerical readout0 остаётся прежним. Его проверяет **zero-RHS decoder replay**
существующего initial encoder/decoder; fake solver возвращает только initialy,
не вычисляет силы/шаги. Никакой подгонки r/v/q/S или замены rawt0 на входные
значения нет. Replay single-thread/validation-only, не механизм приложения.
Последующиеt>0 checkpoints сохраняются обычным codec. Тип checkpoint0 обозначен
явно, continuous controller state не считается сохранённым.

Первый coldprobe успел завершиться: он **не повторялся**, сохранён под своей
v1source binding. Для него подтверждена readonly загрузка и неизменность cold
пути. Его сопоставление с новым candidate — короткий numerical contrast через
версии measurement adapter, не full399qualification единого tool fingerprint.

## Выполненные пробы и отказы

Запечатанный preflight предусматривал24runtime shortprefix probes:3IC×2recipes×
2backends×2sources, первые3originalepochs (100soneQ2/125stwoQ2), плюс2shortK1refs.
Это диагностические префиксы, не сокращённая научная матрица399.

Выполнены уникальные **12Python runtime prefixes +2RK45 prefixes**; одна
неоконченная continuous попытка повторена в новом каталоге после исправления
технического дефекта. Уже завершённый coldprobe не запускался заново.
Оба Python sources: two/three-bodies standard cold/continuous, one-Q2legacy
cold/continuous. RK45rtol3e-11/3e-13, epochs0/50/100,62/122RHS.
Шесть matchedPython contrasts совпали побитно по raw r/v/q/S/checkpoint values,
settings/epochs/RHS counts; SO3angles0. Это **не** equivalence58jobs/Rust/4000s.
Rust backends обоих sources в новом executor **не запускались**.

Короткие Python probes дали одинаковые максимумы: Edrift1.615893364213484e-14,
Ldrift7.115823328364689e-16, Pdrift7.377531580265318e-17,
rawqnorm8.881784197001252e-16. Scope125/100s и frozen synthetic NewtonMQ2;
не realEarth–Moon/JPL/годовой accuracy claim. Saved-data audit392 сохранил
три historical convergenceFAIL и originalRust/three-body PASScontrol.

Локальные software проверки versioned:46PASS доt0fix; при добавлении regression
один тест ошибочно получил NameError (1FAIL/2PASS), затем исправленные targeted
tests2PASS. Ещё одна подготовительная ошибка workerIndentationError сохранена.
Итого3контролируемых failed attempts, включая настоящийt0adapterfail; все CPU
учтены. Старые executed unit source/test bytes восстановлены из known diff и
**подтверждены исходным SHA**, не реконструированы приблизительно. Текущие полные
регрессии выполняет обычный CI; локальный all-tests PASS текущей ревизии не заявлен.

Fault injection CPU/wall/RAM/disk/KeyboardInterrupt:5ownedchildren остановлены и
reaped, reason/последний sample/CPU/RAM/logs сохранены. Исходный interruption
traceback записан отдельно. Unit I/O faults проверили fsync-boundary interruption,
badSHA/manifest/partial/foreignbinding/no overwrite. Не проводился physicalpowercut;
device write cache/FS durability за пределами этих synthetic checks.

## Бюджет и осторожная оценка399

9controlled attempts: **34.53125CPU s /29.497902active wall s**, включая failures
и supervisor/descendants. Остановка **до** early35, не превышение лимита.
Worker sampled private peak234176512B, RSS177577984B; supervisor peak37539840B;
консервативная сумма271716352B не синхронный пик. Guard50ms/finalWindowsCPU;
краткие пики/unseen descendants/outer launcher/record-tail CPU могут быть пропущены.
Caps45/120/512MiB/32MiB,early35/90/450MiB/26MiB сохранены. Git/CI/edit/обязательный
backup отдельно от этого computational budget; их цена не объявляется нулевой.

Измерено: один source/env attestation~1.859CPU s доcohort и~0.594 после;
runtime probe с observer/serialization/fsync/readback0.0156..0.1563CPU s,
20–26KB для3frames; coarse CPU quantization~15.625ms существенна.
Python-only conservative horizon-scaling всех исходных jobs даёт~254CPU s до
заранее заданной1.5margin,~381CPU s после неё **без** supervisor и backup.
Это смещённый вверх проектный ориентир (startup/fixed I/O тоже масштабируются),
не валидированное предсказание. Непроверенный Rust и нелинейность adaptive steps
не дают аттестовать ни его, ни прежнюю оценку60–130CPU.
Output projection~31.1MB до1.25margin/~38.9MB после — ниже128MiB;
RAM измерена только для выполненных cases. Wall/CPU всего операционного этапа
дополнительно включают archive prepare/upload/readback; они замеряются отдельно.

**Безопасность первоначальных180CPU/144early не установлена.** Увеличение budget
не принято автоматически. Прежде чем выбирать более высокий предел либо4
independent(source,backend)groups с прежними58jobs, нужно закончить missingRust/
controller checks. Cold не заменяется continuous и matrix не сокращается.

## Итог и минимальное продолжение

|Пункт|Статус398|
|---|---|
|Исходный58job contract/source/reference397|Проверен, не изменён|
|Python short source/backend/recipe probes|Завершены с оговоркой v1cold reuse|
|Rust probe cohorts|NOT RUN|
|Полный current-revision local suite/controller end-to-end|Не аттестованы; отдельные unit/probe части проверены|
|Atomic/integrity и resource fault components|PASS в synthetic scope|
|Готовность scientific399|**NO-GO / partial preflight**|
|Scientific58/release0.3.3|NOT RUN / NO-GO|

Для отдельного задания предлагается **неутверждённый** остаточный preflight
budget20CPU/60activewall/512MiB/32MiB (early16/45/450MiB/26MiB): только две
missingRustcohort, current CLI/admission/resume faults, independent final
evaluator/resource audit. Завершённые Python jobs не повторять. При полномPASS
создать новый sealed399plan; до того не выдавать draft за допуск. Эта работа
и новый бюджет здесь не начаты. Main/tags/LATEST/portable032/оба candidates/
productionphysics неизменны. После отчёта STOP.
