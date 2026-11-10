# Прикладная квалификация двух Q2 — этап402

2026-11-08. Владелец **утвердил A+D1 исключительно для точного синтетического
демо A/B,0–200s**. Это новое решение не переписывает draft386/391, не снимает
три FAIL380 и не разрешает выпуск/main/tag/LATEST/portable.

**Численные условия D1 — PASS для всех11наблюдаемых. Полное заявленное учебное
демо — NO-GO: скалярное расстояние не показывает утверждённый10mэффект.**
Это не исправление или исключение неудобного результата. В GUI остались
технические after-предупреждения, их production impact unresolved.

[Полный машинный отчёт](q2-application-acceptance-402.json) содержит все e/U_ref/
N_sens на пяти эпохах, максимумы/времена, эффекты, источники, SHA и raw receipts.
[План](../scripts/qualification402/plan.json) заморожен до запуска:
`f5445ec4f5a5b9da508e660d0f49a46e2c4bd6ef02540d2dea5f82d7a9444fbe`. [Назначение инструментов](../scripts/qualification402/README.md).

## Source, IC и модель

Исходный dev4fa57a2; расчёт **exacta99f73a4adce95be9d264d8c403e0e6768a54cd7**,
отдельная candidate branch. Actual source imports не developer src; зависимости
и Python из384venv. Python3.14.2t/NumPy2.5.1/SciPy1.18.1/native0.3.3.
Actual LF source fingerprint
`1a5b054241a628dc6d4ade30a978726166d001dbb0f25ad9a971cd7fc9f21122`;
native SHA`651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`.
Это source-bound проверка, не аттестация wheel/portable.

Runtime resource SHA
`3f6fa9b5883db9e14653c43ddc7359e4cf795744e42d3345baf9ea018772428b`;
plan380 SHA`26eaaf67878e34bd292682b90e07b0df5e3ad9b096f8ee9d0f5a0cf6e9b94d68`.
Ресурс полностью равен /cases/0/initial. Все массы,I,q,S,G,COM/drift сохранены.
SI, elapsed0, произвольный инерциальный базис, q body→inertial, S инерциальный.
Newton monopoles + total-degree2 M–Q; без Q–Q, высших multipoles, EIH/Q2,
диссипации, приливов и контактов. Реальные Земля–Луна/JPL не аттестуются.

## Фиксированная серия и настоящий GUI

Все22jobID COMPLETE:16main(2backend×4level×2recipe),2GUIrepeat,
2same-packet suffix,2новых RK45reference. Epochs0/50/100/150/200s;
GUIbaseline rtol1e-11,xatol1e-7m,vatol1e-11m/s,qatol1e-13,
Satol_i=|S_i(0)|1e-13,relativeA/B; три уровня380 неизменны.
Cold —4пакета dt50/1step; continuous — один существующий integrate, не cold continuation.

Четыре GUIjourneys вызвали настоящие ttk demo/target/save/load buttons,
штатные Tk poll, ThreadPoolExecutor,advance_towards/Experiment.advance.
Диалоги получили заранее заданные пути; численные callbacks/IC не подменялись.
Read-only hook записывал committed frames; checkpoint100s сохранялся обычным storage.
GUI финальное save/load и q/S/settings совпали. Это функциональный UIпуть,
не только прямой программный вызов advance и не ручная оценка удобства интерфейса.

| Job | Status | Solver calls | RHS/nfev | Native | Path |
|---|---|---:|---:|---:|---|
| main__python__gui__cold | COMPLETE | 4 | 236 | 0 | actual Tk |
| main__python__gui__continuous | COMPLETE | 1 | 71 | 0 | headless |
| main__python__coarse__cold | COMPLETE | 4 | 224 | 0 | headless |
| main__python__coarse__continuous | COMPLETE | 1 | 71 | 0 | headless |
| main__python__standard__cold | COMPLETE | 4 | 260 | 0 | headless |
| main__python__standard__continuous | COMPLETE | 1 | 83 | 0 | headless |
| main__python__fine__cold | COMPLETE | 4 | 296 | 0 | headless |
| main__python__fine__continuous | COMPLETE | 1 | 98 | 0 | headless |
| main__rust__gui__cold | COMPLETE | 4 | 248 | 248 | actual Tk |
| main__rust__gui__continuous | COMPLETE | 1 | 71 | 71 | headless |
| main__rust__coarse__cold | COMPLETE | 4 | 224 | 224 | headless |
| main__rust__coarse__continuous | COMPLETE | 1 | 71 | 71 | headless |
| main__rust__standard__cold | COMPLETE | 4 | 272 | 272 | headless |
| main__rust__standard__continuous | COMPLETE | 1 | 83 | 83 | headless |
| main__rust__fine__cold | COMPLETE | 4 | 320 | 320 | headless |
| main__rust__fine__continuous | COMPLETE | 1 | 95 | 95 | headless |
| repeat__python | COMPLETE | 4 | 236 | 0 | actual Tk |
| repeat__rust | COMPLETE | 4 | 248 | 248 | actual Tk |
| suffix__python | COMPLETE | 2 | 124 | 0 | headless |
| suffix__rust | COMPLETE | 2 | 124 | 124 | headless |
| reference__0 | COMPLETE | 1 | 104 | 0 | headless |
| reference__1 | COMPLETE | 1 | 224 | 0 | headless |

Счётчики отражают фактический backend. GUIrepeat совпал побитно по p/v/q/S,
documents и counters. Suffix начинается из сохранённого100s и двумя исходными
пакетами точно воспроизводит150/200s; его первые0/50s в сводке имеют явное
происхождение authenticated parent. Никаких новых solves для этих двух эпох.

Первая попытка continuous GUI/Python завершила интегрирование, но reporting
ошибочно сериализовал decoder readout при t=0: storage корректно отказал.
Уже завершённый GUIjob сохранён и аутентифицирован, не повторялся. Только
неподтверждённая попытка continuous выполнена заново в новом каталоге с теми же
IC/settings. Поэтому **22логических завершённых jobs,23integration attempts**;
лишняя незафиксированная попытка и её CPU не скрыты. Raw partial не реконструирован.

## Пообъектные D1 и наблюдаемый эффект

Для каждого observable/epoch/job: U≤B/10,N≤B/10,e+U+N<B.
Единицы: r/rho/distance —m, v—m/s, theta—rad, S—kg·m²/s.
В таблице раздельные максимумы по всем зафиксированным jobs/эпохам;
max(e+U+N) вычислен по совпадающим эпохам, не суммой несогласованных максимумов.
Изменение — относительно собственного настоящего t0, без COM/phase/rotation fitting.

| Observable | B | max e | max U_ref | max N_sens | max(e+U+N) | min observed effect | Delta | numerical / effect |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| r_A | 1 | 2.0815e-12 | 9.26462e-13 | 2.10293e-12 | 4.26482e-12 | 87.3553 | 10 | PASS / PASS |
| r_B | 1 | 9.6649e-12 | 7.34646e-12 | 1.07476e-11 | 2.22757e-11 | 424.296 | 10 | PASS / PASS |
| rho_BA | 1 | 1.16381e-11 | 8.27162e-12 | 1.2712e-11 | 2.62887e-11 | 511.534 | 10 | PASS / PASS |
| distance_AB | 1 | 5.77743e-12 | 8.21701e-12 | 6.35578e-12 | 2.02615e-11 | 0.244795 | 10 | PASS / FAIL |
| v_A | 0.001 | 2.19368e-15 | 1.05407e-15 | 2.18972e-15 | 4.77144e-15 | 0.0185788 | 0.01 | PASS / PASS |
| v_B | 0.001 | 1.09598e-14 | 5.2784e-15 | 1.09854e-14 | 2.38823e-14 | 0.0928942 | 0.01 | PASS / PASS |
| v_BA | 0.001 | 1.31495e-14 | 6.33004e-15 | 1.31751e-14 | 2.86063e-14 | 0.111473 | 0.01 | PASS / PASS |
| theta_A | 0.001 | 1.24376e-12 | 7.57499e-12 | 1.28551e-12 | 1.01043e-11 | 0.402462 | 0.01 | PASS / PASS |
| theta_B | 0.001 | 2.39165e-12 | 3.71702e-12 | 2.47171e-12 | 8.58038e-12 | 0.338347 | 0.01 | PASS / PASS |
| S_A | 6.02412e+12 | 4180.41 | 388239 | 4527.32 | 396947 | 1.19405e+14 | 6.02412e+13 | PASS / PASS |
| S_B | 7.96806e+11 | 5359.61 | 123613 | 5007.81 | 133981 | 1.38741e+14 | 7.96806e+12 | PASS / PASS |

220observable/job rows оценены отдельно. Для distance_AB эффект~0.2448m,
а требовалось10m: **FAIL эффекта во всех20runtime jobs**. При этом изменение
относительного вектора~511.5m; поворот вектора и изменение его нормы — разные
наблюдаемые. Нельзя переносить большой vector effect на scalar separation.
Остальные10эффектов превысили свои Delta; это не разрешает удалить одиннадцатый.
Spin budgets получены Decimal80/120 из точных начальных binary64 компонентов,
не из текущего |S(t)|. Точные нормы/бюджеты-строки сохранены в JSON.

## Reference, observer и независимость

Два свежих scalar-I/R/body-momentum RK45:rtol3e-11/3e-13,
dimensionless atol=rtol*.01,max_step50s,та же5точечная сетка.
AST-prefix,RHS,initial scaling и solve arguments reference397 совпали с380;
production forces не вызывались. Исходные raw R,scaled y,bodyPi/inertialS,
RHS,det,orthogonality и projection defects сохранены.

Observer-only polar projection: основной расчёт eig(RᵀR), независимый SVD;
finite R,det>0,положительные singular values,SO3 checks. Raw R не заменены.
Угол — stable matrix atan2, независимо normalized-quaternion Decimal80/120,
без неустойчивого acos около1. U_theta равен углу projected reference levels
плюс сумме projection defects/sqrt2. Это операционная эмпирическая шкала,
не строгая граница глобальной ошибки.

N_sens — envelope всех попарных уровней внутри recipe,cold/continuous,
GUIrepeat и saved-observer arithmetic80/120. Python/Rust показан отдельно,
без требования межbackend битового равенства. N не объявляется absolute roundoff.
Аудитор заново проверил raw SHA/IC/epochs/source, наблюдаемые/неравенства,
E/P/L/qnorm и checkpoint binding. Он не доверяет ready-made PASS.
Максимальное расхождение observer implementations относительно B:
3.67053e-12.
Независимы арифметика/norm/SO3 parameterization и invariant implementation;
общими остаются Hamiltonian/IC/SciPy/binary64/определения D1. Это не внешняя рецензия.

## Инварианты, domain и все FAIL

Все исходные применимые EPL/q gates380 прошли. Максимумы:
energy drift7.95822e-13,linear drift7.37115e-17,
angular drift1.06683e-15,raw qnorm4.59077e-13.
Отдельная Decimal80/120проверка включает orbital+spin и тот же M–Q Hamiltonian.
Исходный potential-gradient/reaction test двухтел прошёл без новой орбиты.

Минимальная separation на наблюдённых validation/RHS calls:
11999.7552m>1900m.
Настоящий RHS проверяет внешние bounding spheres и их непересечение на каждом
попытанном stage; негативная stage-подстановка отклонена, исходный completed
packet неизменен. Это сильнее проверки пяти выдач, но не математическое
доказательство непрерывного domain между всеми RHScalls. Никакого fallback.
Malformed q/I/mass/NaN/bool,duplicate IDs,mixing/contact/overlap отклонены.

Все4новых коротких strict convergence contrasts FAIL (Python/Rust,cold/continuous:
standard–fine не меньше coarse–fine по исходному правилу380). Они сохранены
отдельно от D1; причины не сводятся автоматически к одному roundoff.
Три historical FAIL380 и fixed58/28exact evidence399 неизменны, не повторялись.

Другие отказы:1)continuous t0serialization harness;2)аудитор переставил
(R@Pi_scaled)*scale в R@(Pi_scaled*scale), получив другие младшие биты;
точное исходное выражение совпало для всех20reference spin vectors;
3)report observer индексировал уже1Dtotal как2D. Исправлены только tools/observer,
старые версии/попытки/SHA/CPU сохранены. После орбит выполнялся только offline audit.

В GUI runner зафиксировано **12 Tcl invalid-command pending-after messages**
после уничтожения/повторного создания Tk roots (poll/layout/idle_draw).
Они не превращены в clean GUI PASS и не скрыты. Все записанные scientific states,
save/load/repeat целы; связь с обычным single-root приложением отдельно unresolved.
Кандидат не исправлялся. Его фраза «A/D1не утверждены» теперь устарела;
нужна отдельная presentation правка/newfingerprint/delta audit после402.

## Ресурсы и сохранение

Учтено **37.828125CPU / 36.248744activewall s**,
включая все три failed computational attempts и2CPU/5wall начальный allowance.
WorkerCPU26.062500s,private sampledpeak
234635264B,stagefiles2205572B при сводке.
Cap60CPU/120wall/1GiB/32MiB,early50/100/900MiB/28MiB не повышались.
50ms polling/tail allowances и несэмплированная начальная подготовка ограничивают
точность измерения; редактирование/Git/cloudCPU не выданы за measured scientific CPU.
Backup — отдельный operational ledger. Status **CLOUD_VERIFIED_SHA256**;
сырьё/checkpoints/logs/manifests сохранены, отсутствие DriveFS не является uploadproof.
Cloud verification требует отдельного скачивания и SHA/size/parent.

## Раздельные решения и следующий шаг

| Gate | Verdict |
|---|---|
| APPLICATION_D1_NUMERICAL_GATE | PASS всех11наблюдаемых,только frozen synthetic scope |
| EMPIRICAL_REFERENCE_RESOLUTION | PASS empirical,не globalbound |
| OPERATIONAL_SENSITIVITY | PASS empirical,не absolute roundoff |
| REPEAT_AND_RESTART | PASS exact |
| PHYSICAL_DOMAIN | PASS RHS guards/checked trajectory;не continuous theorem |
| HISTORICAL_SCIENTIFIC_GATE | FAIL сохранён;4новых коротких FAIL отдельно |
| DEMONSTRATED_EDUCATIONAL_EFFECTS | FAIL distance_AB Delta10m |
| GUI_LIFECYCLE | UNRESOLVED pending-after warnings в multi-root runner |
| LIMITED_DEMO_AS_FULL_D1 | NO-GO полного утверждённого набора эффектов |
| RELEASE_READINESS | NO-GO |

Численно модель разрешает наблюдённые изменения на этой сетке с большим запасом
относительно D1. Но **не продемонстрирован весь утверждённый учебный эффект**;
нельзя заявлять безоговорочный APPLICATION D1 ENGINEERING PASS. Следующий небольшой
шаг — отдельная задача на актуализацию маркировки и локализацию Tk after lifecycle
без новых орбит; решение по отсутствующему эффекту остаётся владельцу.
Не менять Delta/IC/горизонт задним числом и не запускать подбор ради PASS.
Исходный кандидат/main/tag/LATEST/portable032 неизменны. После отчёта STOP.
Рекомендуемая модель следующей небольшой инженерной задачи: GPT-6.1Sol High.

Проверки завершения:5portable observer regression tests PASS/0skip;
реестр1363публичных файлов и1455file/line links PASS. Это проверки tools,
не снятие научных/учебных FAIL. Старые74PASS400 и fixed58/399 не повторялись.

Резервирование завершено: архив569744B SHA256
`0d4c02b043ea09363ee2547a10b2f2b37f29e72bda8f03098195ce3901b9558c`,
Drive1CIPr1EwJ-eUVripURRzqLKSfv77THW08. Git recovery recipe582B SHA256
`413580d0c52f7551c8a95fc7f69619d08a86e54f956a3413b553153598ae9907`.
Оба файла независимо скачаны; SHA/size/parent/owner-only права проверены.
Backup отдельно5.15625CPU/9.0268825activewall s; connectorCPU не измерен.
Prepare использовал только Solar-Simulator reviewedqueue на чистом опубликованном
Git, без broad rescan. Старые immutable401/399/395 dependencies переиспользованы.
Все executed tool revisions сохранены и SHA-проверены; оригиналы не изменены.
