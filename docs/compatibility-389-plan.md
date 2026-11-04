# Совместимость389 — execution contract до запусков

4 ноября2026. Devce277f4, acceptedmain/tag032cf653c9, candidatefe0f456 immutable.
Использовать [контракт387](compatibility-387-plan.md) и
[план продолжения388](compatibility-387-continuation-388-plan.md) без изменения
физической выборки, численных параметров и A/B/C критериев.

Новый output .tools/qualification389. Original032ZIP112312650bytes,
SHA7c578220ec77e792aa9589f32a30352e88277d0d096bff0ad3ca5aae9c014c49;
native0320cbc389…0601; candidate033native651e346…091. Проверить полные SHA
и источник package/native/NumPy/SciPy/Python/ABI. Подлинную032 не заменять dev.

CURRENT profile доNumPy/SciPy: OMP/OPENBLAS/MKL=1, VECLIB/NUMEXPR/PYTHONHASHSEED
unset. Не сбрасывать первые3 переменные внутри worker. Проверить actual BLAS
threads и loadedDLL paths/SHA в каждой фазе. Это не historical unset replay.

Один общий active preflight/acquisition/observer/test budget180CPU/360wall/
1GiBsampledprivate/128MiB, ранние160CPU/330wall/900MiB/112MiB. Monitor385SHA
fe0f4e83…508 неизменён; retainedCPUhandles и concurrent parent/treeprivate,
внутренний10ms selfguard+boundarysamples с тем же900MiB. При failure/STOP
не продолжать последующие jobs. Сохранить исходную ошибку/завершённые casefiles;
не сбрасывать расход после попытки. Backup/Git/редактирование/сеть отдельно.

Порядок: source/ZIP audit и unit guard tests → **оба startup preflight** →
prepare в032 без advance → freezeIC/inputSHA/planSHA →032worker→033worker→
old032 two-Q2load negative → independent saved-state observer → SHA postflight.
До успеха обоих startup не создавать орбит. Все команды и toolSHA в binding.
Actual fingerprints до/после каждой фазы; candidateverify_freeze до/после.

Использован draft388SHA3c2e67c7…01a как основа локального389worker. Diff сохранён.
Только тестовые усиления: явныйroot/profile, bitsresume, сохранение frames/resume/
progress до assertion, чтение старого продвинутого checkpoint в033, настоящий
GUIStart/submit/pause/commit ровно одного пакета. Три50s научных пакета и solver
settings не меняются. Profile events считают реальные PyO3/Verlet/RHS calls,
не подменяя numerical functions. Acquisition .npz/.npy access запрещён audit hook;
новые состояния JSON, старые научные массивы не используются.

8cases строго original387, создаются actual032: Sun–Earth(.0167)Verlet/DOP853,
Sun–Earth–MoonDOP853, original single-Q2 syntheticfixture, каждыйPython/Rust.
SI/G6.67430e-11,dt50,rtol1e-11,atols1e-7m/1e-11m/s,per-body;
relative_pair только Q2=(figure,point);epochs0/50/100/150s/3packets по1.
Остальные I/q/S/масс/IC definitions — сохранённый387prepare, не новые варианты.

A: original JSON legacy1–9/schema10Q2, own/cross old checkpoint load, exact
same-packet save/resume, branch/parent/recovery/recipe/frame integrity.
C: actualTk load/save/start/pause/cancel/corrupt/unsupported, knownwrongnative
entrypoint/noncompiled provenance rejection, old2Q2load явный отказ. Mock только
file selectors/native-negative; inputs/oldoutputs не изменяются. Unsupported
ABI-compatible native SHA — preflight guard, не обещание universalruntimeSHAcheck.
Strict oldrecipe replay в новом fingerprint должен отказать до интегрирования.

B: independent read-only observer387+extension389, binary64 states/settings,
Δr/Δv и model-specificE/P/L,rawq/S differences. Все разности сохранять. Exact
только выбранных finite cases; nonzero unexplained→UNRESOLVED без posthoc tolerances.
Дрейф E/P/L не глобальная орбитная ошибка. Ни JPLгод, ни2Q2application200s,
ниполнаяacceptance/новыйintegrator/productionchanges не разрешены этим планом.

GO gate389: все8cases и все обязательные A/C checks выполнены, источники/inputs/
outputs/fingerprints целы, independentobserver согласован. EXPECTED metadata/native/
feature differences отдельно. Отказы инструментария не выдавать за runtimebug;
runtimebug → reproducer+impactproposal, frozen candidate не патчить. После389STOP.
