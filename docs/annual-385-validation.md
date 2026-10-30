# Годовая EIH+J2 квалификация кандидата0.3.3 — этап385

31 октября2026. **GO для ограниченной новой годовой научной области Strict375;
полный release0.3.3 не квалифицирован.** Кандидат не менялся, main/tag/LATEST/
принятая032 сохранены. [Заранее фиксированный протокол](annual-385-protocol.md).

## Реальное исполнение и provenance

| Привязка | Значение |
|---|---|
| Candidate Git | `fe0f456f2c7ba3a077eac21fc8413937d6e84fac` |
| Observing/assessment tools Git | `c51c99ba34c90dc8e18c90781c9770f4c25baa83` |
| Freeze SHA256 | `5ea5278e2f45181aaf6450475a419f8db58998f23b826ffdeff86d764a7e29a2` |
| Protocol SHA256 | `b868729f227d0fd25677211450245bb9b18d8d88e7d04f293a9be2ed801e198e` |
| Actual environment SHA256 | `056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a` |
| Native0.3.3 `.pyd` SHA256 | `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091` |

394 runtime/data/Rust/driver source SHA перечислены в
[freeze](../scripts/validation/annual385/freeze.json). Это исходники неизменного
кандидатного worktree, не dev0.3.2. Новые tools исполнялись отдельно и имеют
свои SHA. Их исходный commit находится в Git; .tools invoker/monitor recipes
сохраняются с raw в reviewed Project-Archives. Driver375 не редактировался.
Полная среда та же, что в384: Python3.14.2 free-threaded/cp314t-win_amd64,
NumPy2.5.1/SciPy1.18.1/Matplotlib3.11.0, собственная кандидатная venv,
OMP/OPENBLAS/MKL_NUM_THREADS=1. Нет утверждения hermetic OS/portable isolation.

Для fresh reference отдельно закреплены actual rustc1.99.0(b940084d7)/GNU,
SHA compiler/shim, исходник/flags oracle и SHA свежего DLL. Compiler check
до/после совпал. Независимый scalar EIH/body-axis J2 + AU/year/interleaved
RK45 использует прежние два уровня1e-13/1800s и3e-14/900s, atol1e-17.
Production остаётся PerBodyDOP853 без max_step, с прежней физикой и допусками.

Все14inputs и40raw JPLresponses375 проверены по SHA. IC/G/массы, DE441,
JD2461321.5TDB, SSB/EclipticJ2000/SI,10тел,31557600s,125epochs/9holdout
сохранены. Scientific JSON намеренно сохраняет исходные поля375 дословно;
stage385 задаёт новый freeze/assessment и разрешённые provenance fields.
Нет переноса старого receipt/fingerprint на новый runtime.

Выполнены6annual jobs (оба backend ×Strict20/Strict10/Standard20),2holdout,
12прежнихsandbox cases,2annual и2holdout independent RK45 levels.
Восемь runtime grids содержат768кадров/7680состояний тел, не считая
дополнительных точных restart suffix. Все завершённые пакеты записаны в raw
журнал; nfev/actual native calls сохранены. Внутренние accepted/rejected steps
и controller history не записывались и неизвестны.

## Результаты относительно свежего независимого reference

Максимумы по фиксированным эпохам, а не непрерывные верхние границы. Max r
и max v берутся независимо по всем телам; они могут относиться к разным телам.
Wall ниже включает запись/диагностику и restart дляStrict20, не чистый benchmark.

| Job | max r всех тел,м | max v,м/с | Earth–Moon r,м | Earth–Moon v,м/с | Wall,с | Numeric gate |
|---|---:|---:|---:|---:|---:|---|
|Python Strict20|0.0621831|1.41710e-7|0.0581642|1.40729e-7|25.629|PASS|
|Rust Strict20|0.0628898|1.03687e-7|0.0438178|1.04181e-7|15.228|PASS|
|Python Strict10|0.435583|1.07197e-7|0.0391138|1.09017e-7|23.552|PASS|
|Rust Strict10|0.456082|8.27515e-8|0.0307250|8.46719e-8|14.746|PASS|
|Python Standard20|0.0726806|4.50016e-8|0.0205014|4.63565e-8|13.478|PASS diagnostic|
|Rust Standard20|0.115215|2.87696e-7|**0.113353**|2.88214e-7|8.029|**FAIL diagnostic**|
|Python holdout20|0.0107496|1.41240e-9|0.000512919|1.42854e-9|1.199|PASS|
|Rust holdout20|0.00977783|2.09448e-9|0.000736911|2.11874e-9|1.071|PASS|

Критерии исходные:10m/1e-4m/s per body, .1m/1e-5m/s Earth–Moon.
Rust Standard снова не проходит .1m. Он заранее диагностический и не входит
в обязательный Strict gate; прежние Standard FAIL также не изменялись.
Лучший отдельный Python Standard результат не даёт оснований менять профиль.
Меньший rtol или пакет не гарантирует монотонного улучшения в binary64.

Reference level sensitivity: annual0.0987226m/тело и0.00304042m Earth–Moon;
holdout0.00881320m/0.0000341202m. Прежние1m/.1m gates PASS. Эта разность
уровней — эмпирическая sensitivity, не строгая верхняя граница ошибки эталона.

Packet sensitivity Strict20↔Strict10: Python0.441444m/тело и
**0.0949477m Earth–Moon**, Rust0.481479m/0.0735219m. Gate10m/.1m PASS,
но у Python относительная пара близка к исходному пределу. Это ограничение
robustness данного профиля, не повод ослаблять критерий или менять пакет.
Tolerance sensitivity Standard20↔Strict20: Python0.0607255m/0.0605330m,
Rust0.0701983m/0.0695439m; исходные sensitivity gates PASS.

## JPL и инварианты — раздельная интерпретация

Strict20 JPL max: Python747.744m/тело и718.811m Earth–Moon;
Rust747.755m/718.825m. Strict10:747.826m/718.899m Python,
747.816m/718.890m Rust. Прежние10km/1km goals PASS.
Эти остатки включают ограничения физической модели; они существенно больше
численного расхождения с независимым solver той же усечённой модели.
Все40primary responses сверены с dense matrix, начальное SI/frame/time
перекрытие проверено. Новые JPL эпохи/подгонка параметров не выполнялись.

Модельная E — Noether through1PN + Newton fixedJ2 potential; остаток содержит
O(c^-4) и отсутствующие mixed PN–figure terms. Max runtime E residual для
Strict jobs7.3391e-14 при gate1e-10; отдельный scalar fsum replay согласован.
Scaled canonical P changes не более3.904e-15 дляStrict grids; orbital L
изменялся до3.893e-14. При fixed-axis J2 полный orbital L не обязан сохраняться,
и его изменение не превращено в фиктивный conservation gate. Совпадение backend
не является независимой физической теорией или доказательством полноты модели.

## Независимый saved-data audit и совместимость

Отдельный процесс заново прочёл новые arrays и пересчитал все r/v и JPL
метрики scalar math.dist, E/P/L отдельными scalar fsum формулами. Проверены
source/native/environment/IC/массы/эпохи/actual packet grids/settings,
fresh oracle source/binary SHA, finite shapes и реальные native/RHS calls.
125/9epochs не заменялись похожей сеткой. Both backend Strict20 checkpoint
save/load/resume дают exact canonical documents и exact saved suffix arrays.
Middle checkpoint принадлежит точному сохранённому кадру.
12sandbox cases прошли прежние проверки, branch roundtrip/file continue/parent
preservation. Это новая проверка candidate, а не повтор accepted032.

Все**25 обязательных gates** successor375 PASS; failed_criteria пуст.
Compatibility с принятой032 **UNRESOLVED**: её source/environment-bound запуск
здесь не повторялся. Это не утверждение отсутствия всех старых компонентов.
Оригинальный375 environment имел unset thread variables, новый фиксирует1;
новый запуск в иной среде нельзя назвать byte-exact повтором старого.
Никакого произвольного численного cross-version допуска не введено.
Исторический375 CURRENT_RECEIPT_SHA и его строгая защита сохранены.

Audit разделяет уравнения, G/IC, binary64, SciPy и saved reference. Он независимо
проверяет arithmetic/reductions и иной integrator/coordinate/force implementation,
но не является внешней рецензией или независимым измерением природы.

## Неуспехи, ресурсы и проверки

Первый старт отказал **до годового интегрирования**: observing wrapper импортировал
physics до обязательного375activate. Защита драйвера сработала корректно.
Rows пусты, исходный freeze/trace/empty output/journal/logs/resources сохранены.
Минимальное исправление tools вызывает прежний guard первым, затем freeze и
observation; candidate и scientific protocol не менялись. Реальная activation
probe и regression test подтвердили порядок. Новый freeze ссылается на старый.
Первая попытка3.234375CPU s включена в общий счёт; бюджет не сбрасывался.

Общая стоимость**213.609375CPU s**: retry worker174.718750,
retry supervision35.656250, первоначальная попытка3.234375.
Консервативный wall**308.489920s** включает первый старт, исправление и5s margin.
Wall anchor восстановлен из exclusive execution-binding file timestamp до
первого запуска; затем применяется monotonic clock. Это консервативная оценка,
не сохранённое точное значение первоначального perf_counter.
Worker private sampled peak281440256B, supervisor OS peak37691392B;
консервативная сумма319131648B (~304.3MiB). Артефакты на закрытии science
18668458B (~17.8MiB), включая первоначальные и retry данные. Hard caps
1200CPU/1800wall/2GiB/512MiB и ранние пределы не повышались.
Tree/RAM sampling50ms может пропустить очень короткие children/peaks;
это не OS hard quota. Подготовка окружения/software tests/backup отдельно.
Короткие launcher rustup/compiler-identity probes до/после monitor phase
не входят в213.61CPU s и отдельно не измерены; это не полный CPU всего сеанса.

Технические tests:40PASS, включая arithmetic limits, corrupt/missing/nonfinite
archives, immutable saved evidence, actual activation restoration и прежние383/384
контракты. Actual preflight отклонил6подмен source/tool/native/environment/
protocol/candidate; два backend1h observer contrasts побитно совпали с baseline.
Начальный тестовый отказ list вместо tuple исправлен только в новой фикстуре.
13protected historical input/evidence/native/LATEST SHA после science неизменны.
Full check_project/source-native acceptance, full Q2 matrix и portable не запускались.

## Восстановление и решение

[Compact manifest](../scripts/validation/annual385/manifest.json),
[all8 CSV](../scripts/validation/annual385/all8.csv) и
[машинный assessment](../scripts/validation/annual385/assessment.json) сохраняют
все исходы. Протокол/freeze/environment и states.npz позволяют read-only replay
показателей; regression tests выполняют его без native и без интегрирования.
Это не аттестует текущий произвольный checkout. Полный source-bound assessor
требует восстановления указанного candidate/venv и tools commit, raw job tree,
fresh compiled reference DLL, original invoker/monitor и проверки всех SHA.
Точные non-Git raw/journal/checkpoints/logs/recipes сохраняются отдельно через
Project-Archives; status cloud сообщается только после independent readback.

**GO** годовой научной квалификации Strict в описанной области/среде;
**UNRESOLVED** cross-version compatibility; **NO-GO** заявлению полной готовности033.
До выпуска: решение по3FAIL380 и scope двухQ2, отдельный compatibility этап,
полные source/native+GUI/recovery и реальные portable checks по новым бюджетам.
Main/tag/release/LATEST требуют отдельного решения. После385 новые научные
jobs не запускать автоматически. Следующий полезный шаг — согласовать scope
двухQ2 для033, сохраняя прежние FAIL; рекомендуемая модель GPT-6.1 Sol high.
