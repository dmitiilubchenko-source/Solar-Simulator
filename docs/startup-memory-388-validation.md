# Startup388: причина STOP локализована, орбиты не запускались

4 ноября2026. Dev исходный1a1f23b6b45b5c15d2fa614bf78d1e1b3798288b.
**GO только к новому compatibility preflight с явным текущим launch profile.**
Прежний387 PARTIAL_RESOURCE_STOP сохранён; A/B/C и выпуск033 не получили PASS.
[План до проб](startup-memory-388-plan.md),
[машинные результаты](startup-memory-388-validation.json).

## 1. Подлинность и исходная последовательность

Original387worker найден: `.tools/qualification387/executed-worker.py`,
SHA2102fba85c7a25c147ebc6fda2af8d0b1c995409c236ca9f116df076901e138f.
Monitor385 не изменён: SHAfe0f4e83a5b1473a23404e813f3f98693fac8099181d936ca5980e3e1f80a508.
Original032ZIP SHA7c578220ec77e792aa9589f32a30352e88277d0d096bff0ad3ca5aae9c014c49,
112312650bytes;5979members повторно CRC/SHA verified against existing distribution.
Native0320cbc389f139854628f287c04a7cea52c530a18294c2c3a0670faa48bf53c0601.
Candidatefe0f456f2c7ba3a077eac21fc8413937d6e84fac, native651e346…091:
actual verify_freeze394entries/environment056c455…795a PASS;13protectedSHAunchanged.

Probe исполнял только import nodes исходного модуля387 и prepare() до первого
присваивания seeds: dataclasses → numpy → scipy.spatial.transform.Rotation →
experiment/storage/rotation/nbody_rotation/simulation/vector3. AST не допускает
последующие prepare/advance calls. Прямой Win32 logger/nested import hook —
явное инструментирование, поэтому его footprint/тайминги не объявляются точной
копией неинструментированного387. Никаких IC и восьми compatibility орбит.

## 2. Что измерялось

Installed psutil7.2.2 `_pswindows.py::memory_info`: private берётся из
PrivateUsage, rss — WorkingSetSize, vms — PagefileUsage. Это **bytes**;
MiB=bytes/1048576. PrivateUsage/PagefileUsage — private committed memory,
не physical working set и не только фактически выгруженные страницы.
[Microsoft PROCESS_MEMORY_COUNTERS_EX](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex)
и [таблица счётчиков](https://learn.microsoft.com/en-us/windows/win32/memory/memory-performance-information).
RSS — резидентный working set; USS дополнительно измерен psutil через private
working-set pages. Реальный полный virtual address size здесь не измерялся:
Windows psutil.vms — alias commit, а не сумма reserved+mapped address ranges.
Сверялся именно [psutil7.2.2](https://github.com/giampaolo/psutil/blob/release-7.2.2/psutil/_pswindows.py),
не изменённые имена новых версий API.

Независимая ctypes реализация GetProcessMemoryInfo подтвердила private в209/209
внешних наблюдениях: psutil значение лежало между прямыми API before/after.
Quiet-child regression также подтвердил private/pagefile/vms и RSS.
В trace уникальные PID/create_time, повторного суммирования root в children нет.
Память суммируется только у живых процессов текущего sample; CPU exited children
сохраняется отдельно через retained handles, не добавляется повторно к памяти.
Supervisor исключён из worker_private, но concurrent hook проверяет их сумму.
peak_pagefile supervisor — исторический peak commit, не физическая RAM.

## 3. Контролируемые профили и результаты

Для всех: genuine portablePython3.14.2t, NumPy2.5.1/SciPy1.18.1,
-I/-B/external pycache prefix; user/Matplotlib paths в новом388output.
Порядок и profiles заданы до исполнения. Пробы дополнительных modules только
у двух low-thread profiles: solver modules,Matplotlib/Tk,app,actualnative032,
native_forces.prepare([1,2]) без вызова силы/создания опыта. Tk-окна не открывались.

| Profile | Thread variables | NumPy BLAS threads | Self peak private MiB | External peak private MiB | CPU s / wall s | Результат |
|---|---|---:|---:|---:|---|---|
|blas1-only|только OPENBLAS=1, остальные5unset|1|148.7891|170.4258|4.84375 /9.32827|native/runtime imports завершены |
|all1-current|OMP/OPENBLAS/MKL=1, остальные3unset|1|136.4063|138.3789|3.859375 /7.32968|native/runtime imports завершены |
|cleared387|все6unset, как attempted387|16|1019.7344|551.2344|1.546875 /2.98688|exit90, private-memory-self |

Разница self/external peaks ожидается: разные моменты/частоты наблюдений.
У cleared387 self API зафиксировал1069268992private bytes при RSS75841536bytes
(72.328125MiB), затем немедленно os._exit(90). Внешний50ms sampler не успел
увидеть этот короткий burst и сохранил только551.2344MiB. Его limit_reason=None
**не означает PASS**: primary stdout содержит self900MiBguard и exit90, raw
resource-summary остаётся PARTIAL_RESOURCE_STOP_OR_FAILURE. Других startup после
этого STOP не запускали. USS checkpoint peaks114.6445/107.0938/41.9023MiB —
отдельная физическая метрика, не replacement private guard.

Пик возник при from scipy.spatial.transform import Rotation, в цепочке
scipy.linalg, **до первого Solar import**. После NumPy alone у cleared387
private549.7852MiB, при low-thread67.6406MiB. В NumPy DLL readonly query показал
16 против1 BLAS threads. У двух завершённых probes уже загруженные разные
NumPy/SciPy OpenBLAS DLL обе сообщили1; OS thread counts4–8 не равны числу
BLAS threads. На stop число потоков второго SciPy pool не получено.
Последняя nested отметка numpy._core._multiarray_umath не доказывает, что
повторный импорт NumPy выделил память: другие native threads могут выделять её
асинхронно. Точная C allocation site и разбивка на buffers/stacks unresolved.

**Подтверждённый механизм:** default многопоточная BLAS initialization в данной
startup-конфигурации создаёт большой commit. Изменение только OPENBLAS_NUM_THREADS
при той же последовательности импортов даёт low-memory startup и фактический
BLAS pool1. Назначение переменной согласуется с
[OpenBLAS usage](https://github.com/OpenMathLib/OpenBLAS/blob/develop/USAGE.md).
Результат не доказывает точный объём каждой внутренней аллокации или влияние
на численные орбиты. Ошибка измерения/двойной подсчёт/private-vs-RSS подмена
не подтверждены. Production Solar здесь не оказался причиной startup peak.

## 4. Историческая среда: найдено новое свидетельство

BUILD-INFO не содержит thread settings. Однако найдены два original portable
acceptance-workflow parent recipe (Python/Rust), по4frames. Их payloadSHA,
manifestSHA и всеframeSHA проверены, stable start/end fingerprint совпали;
79package files совпали с accepted portable, Rustnative0cbc exact.
Оба recipe сохраняют **все6variables=null**. Полные имена/SHA и Python-бинарные
hashes в machine report. Это уточняет unknown387 конкретными сохранёнными
свидетельствами старых запусков; старый отчёт не переписывался.
Самосогласованный local receipt не является подписанной аттестацией ОС,
доказательством всех исторических запусков или прежнего количества CPU/BLAS
потоков. Unset допускает иное default поведение на другой машине.

## 5. Минимальное решение и продолжение

У supervisor387 были выставлены1/1/1, но original worker затем их удалял.
Для будущего сравнения реальных версий в **явно текущей общей среде** убрать
это неявное переключение и требовать explicit all1-current в обоих processes.
Кандидат имеет уже такой frozen profile. Original worker/387results не править;
подготовлен только отдельный source-bound draft, не production patch.
Это изменение процедуры запуска, не новый integrator/physics и не точное
воспроизведение исторических unset-runs. Снижение RSS вместо private или
увеличение900MiBguard не предлагается.

[Новый план продолжения](compatibility-387-continuation-388-plan.md) сохраняет
прежний A/B/C контракт и все8cases. Здесь они **не исполнялись**.
**GO** к его отдельно ограниченному preflight; **NO-GO** объявлению A/B/C,
полной033/portable квалификации или исторической byte-exact эквивалентности.
Нужно проверить actual old/new fingerprints при all1-current и их стабильность,
создать/заморозить IC один раз до science, затем только по новому поручению
выполнить прежние cases/observer/GUI. Q2application200s и waiver386 отдельно.

## 6. Проверки, ресурсы и пределы

6исходных diagnostic tests PASS/0FAIL/0skip,0.56s, включая quiet-child Win32/psutil.
Их точный source SHA7cccf088…ca0bb сохранён вместе с логами. Для публичного CI
отдельно6stdlib-only tests PASS/0.35s: profiles,AST,PIDs/bytes,явный отказ API
внеWindows; без нового psutil requirement/skip или изменения dependencies.
Sourcebound SHA и
209API observations проверены отдельным offline reducer без Solar imports.
Тесты не аттестуют физику/орбитную точность.
Controlled stage+offline reducer+publictests43.828125CPU s/47.71911active wall s,
1880509bytes до отчёта/упаковки. Вне monitor были две readonly summary-инспекции
около1.67s tool wall, CPU не измерен;3CPU reserve учтён remaining-stage guard,
это не приписанное им измерение. Документы/сеть/Git/backup отдельно.
Supervisor peak commit37740544bytes; external worker max578011136bytes,
но self captured1069268992bytes. Индивидуальный self peak ниже1GiB;
combined peak в этот момент unknown. Не заявляется соблюдение hard RAMquota:
900MiBearlySTOP сохранён, sampling допускает overshoot.

Ни один runtime/force/integrator/native/принятая portable/candidate/main/tag/LATEST
не изменён. Старые387STOP и3FAIL380 сохранены. После отчёта STOP.
Следующий этап — ограниченное продолжение387 по новому плану. Модель Sol High.
