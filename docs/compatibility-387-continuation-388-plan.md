# Продолжение387 после startup388 — подготовленный план, не выполненный запуск

4 ноября2026. Этот документ не меняет [контракт A/B/C387](compatibility-387-plan.md).
Только новое явно ограниченное окружение для actual accepted032 и frozen033.
Результаты: [startup388](startup-memory-388-validation.md). Самих8орбит не было.

1. Создать NEW output, например `.tools/qualification389`; не перезаписывать387/388.
   Проверить dev/remote/dirty trees, candidatefe0f456 и native651e346…091,
   accepted ZIP7c578220…c49/native0cbc389…0601. Старый worker2102fba8…38f immutable.
2. Использовать действительную portable032/runtime/python.exe и отдельный candidate
   .venv/Scripts/python.exe. Для обоих **all1-current**: OMP_NUM_THREADS=1,
   OPENBLAS_NUM_THREADS=1,MKL_NUM_THREADS=1; VECLIB_MAXIMUM_THREADS,
   NUMEXPR_NUM_THREADS,PYTHONHASHSEED unset. LOCALAPPDATA/MPLCONFIGDIR в новом output,
   -I/-B/external pycache prefix. Не очищать three thread controls внутри prepare.
3. Снять и проверить runtime_fingerprint обоих собственными процессами, сохранить
   SHA/ABI/compiler/dependency/library/source provenance и start/end equality.
   Исторические acceptance recipes с variablesunset — отдельные evidence.
   Не подделывать старый fingerprint и не приравнивать старую среду к новой.
4. Draft `.tools/qualification388/continuation-worker-revised.py`,
   SHA3c2e67c7ed53b149d26e801113dcf5a85886d4f859d1e1379ab3cd11c298e01a,
   требует `--numerical-profile all1-current --developer-root <Solar-root>`.
   Он создан из preserved387; меняет launch variables и делает source-root
   явным, поскольку локальное положение .tools отличается от исходного scripts/.
   Initial draft09c049…44e0 сохранён: самопроверка обнаружила неверный __file__.parents[1]
   при переносе. В388 проверен AST; acquisition **не исполнен**.
   До применения пересмотреть diff, отдельно проверить args/profile/native/candidate
   guards и source/SHA привязки; отсутствие ошибок неизвестного worker не доказано.
   Если draft недоступен — восстановить из verified388bundle, не из догадок.
5. До первого advance actual032 создаёт входные документы ровно прежних8cases:
   Sun–Earth Verlet/DOP853, Sun–Earth–Moon DOP853, один synthetic Q2 DOP853,
   каждый Python/Rust. Не менять masses/IC/dt50/epochs0,50,100,150/3packets по1/
   rtol1e-11/atols1e-7m,1e-11m/s/relative-pair из387. Заморозить inputSHA и
   planSHA отдельным binding до workers. Никаких новых IC/параметров по результатам.
6. Возобновить все прежние A/B/C проверки: legacy1–10, exact same-packet resume,
   oldJSON→033, branch/recovery/recipe integrity, expected cross-env strictreplay
   refusal, GUI cancel/corrupt/schema/native и oldtwo-Q2 explicitload rejection.
   ДвеQ2 только сериализация для negative test; без application интегрирования.
7. Existing read-only observer387 сравнивает отдельные settings,statesbits,r/v,
   model-specificE/P/L. Ненулевая разность сохраняется и объясняется; никакого
   post-hoc tolerance, измененияphysics/отсеваcases. Exact на8cases не globalproof.
8. Бюджет будущего **отдельно разрешаемого** этапа как387: max180CPU/360wall/
   1GiBsampledprivate/128MiB, early900MiB остаётся, live combined parent/tree,
   retainedCPUhandles, sourcebound50msmonitor плюс self/equivalentguard для
   коротких bursts. Предварительная оценка startup ниже180MiBworker по388,
   но integration/GUI peak ещё не измерен — никакой гарантии по одному startup.
   PreflightFAIL/STOP → сохранитьpartial и остановиться без поднятиялимитов.

GO здесь означает готовность такого preflight в документируемой текущей среде,
не разрешение вычислений после STOP388 и не qualification A/B/C/release033.
Кандидат/main/oldreceipts не меняются; при runtimepatch нужен отдельный impactaudit.
