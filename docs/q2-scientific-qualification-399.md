# Q2-399: научная квалификация R-reuse

2026-11-08 (Europe/Moscow). **Исполнение завершено: 58/58 jobs, обязательный offline-аудит завершён, облачные копии подтверждены.**
**SOURCE EQUIVALENCE PASS / STRICT CONVERGENCE FAIL / RELEASE NO-GO.**
Оптимизация сохранила численное поведение в зафиксированной выборке. Три прежних FAIL строгой сходимости воспроизведены, критерии не менялись. После отчёта STOP.

## Происхождение и воспроизведение

- Dev/origin до запуска: `8a49600846c9daede1a0c35534c61d61129799ab`.
- Baseline: `fe0f456f2c7ba3a077eac21fc8413937d6e84fac`; tree `6d5cfd2dcafed37e781d05f913b677080965700d`.
- Candidate: `f723a2162b4e115378959e244f428529be2d4516`; tree `b441aea60d6f291db10fd0a8d63f1829b8cd1794`.
- Tool commit: `78fe4cac8873914e5d1fa084d510f3f279b33c68`; все pinned tools совпали с sealed SHA.
- [Sealed plan](../scripts/q2-qualification399-plan.json): SHA256 `3e1ceb821514a770632f7f5c0ac37260a869198d94e5adc60d81bfaa69bbe644`.
- [Исходный scientific contract](../scripts/q2-qualification398-plan.json): SHA256 `b6131f0abeeec63ee2e324a34b22f6c96008e67e747fa94e9ee52b2795c0bd28`.
- Qualified384 venv: Python3.14.2t, NumPy2.5.1, SciPy1.18.1, psutil7.2.2; OMP/OPENBLAS/MKL=1. Interpreter/prefix, реальные импорты и source/native fingerprints проверены до запуска и внутри групп.
- Native SHA256 `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`; baseline/candidate environment LF SHA — соответственно `056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a` / `d1a2e827e6edcf43ceedacbfc3f62ad72b624c2f0f03332326aa0cf6185695c7`.
- [380 reference](../scripts/validation/two-q2-380.npz) SHA256 `51e7c79d7a36547df92959a8614d9d5804232d39c0ebfe5c4a143ecdd6da696a`; [397 reference source](../scripts/q2_reference397.py) SHA256 `52b2d4efebad15fc25739776d3a8939015a6be42be1b88d9b3d5f999271e9338`.

Проверены чистые деревья обоих кандидатов и присутствие tool commit в истории. Штатный `--check-plan` PASS. Новый output root: `.tools/qualification399-20261108`; исходные IC, настройки и временные сетки проверены через frozen bindings каждого результата. Полные job IDs, SHA, счётчики, настройки, fingerprints и массивы наблюдений E/P/L находятся в [машинном отчёте](q2-scientific-qualification-399.json). Raw состояния — в отдельных архивах ниже.

Команда для каждой группы: qualified384 Python `-I -X utf8 -B scripts/run_q2_qualification399.py --plan scripts/q2-qualification399-plan.json --sha <sealed SHA> --output <fresh root> --group <group> --execute-399`. Команды внутри данных не исполнялись. Завершённые jobs повторно не запускались.

## Модель и состав

Newton monopoles + total-degree-two monopole–quadrupole для динамических фигур, без Q2–Q2, приливов, диссипации, EIH и контактов. SI; инерциальные p/v/S, body-to-inertial quaternion; `G=float.fromhex("0x1.2589effed8accp-34")`.

Две исходные конфигурации с двумя Q2-фигурами: two-bodies и three-bodies, по 65 эпох 0…4000 с (62,5 с), coarse/standard/fine, cold и continuous. Legacy one-Q2: 81 эпоха 0…4000 с (50 с), cold/continuous. Каждый набор выполнен для Python/Rust и baseline/candidate: 56 runtime jobs. Ещё два baseline/Python RK45 reference для one-Q2, rtol 3e-11/3e-13. Допуски и оригинальные cold-пакеты неизменны.

[Controller](../scripts/run_q2_qualification399.py:219) и [verify_group](../scripts/run_q2_qualification399.py:192) сохранили отдельные run/launch/guard/attempt/verified/final receipts. [Executor](../scripts/q2_execution398.py:267) проверял codec, dispatch и counters; [assess_all](../scripts/q2_execution398.py:330) применил исходные критерии. Ссылки и номера строк проверены по выполнявшимся файлам.

## Exact source equivalence

**28/28 пар PASS**: побитово одинаковые binary64 raw p/v/q/S, канонические checkpoint и counters внутри одного backend/recipe/IC/epochs. Независимый аудит сравнил отдельные struct-packed binary64 последовательности. Максимальный устойчивый физический угол baseline/candidate — 0 rad. Побитового равенства Python и Rust друг другу не требовали.

## Исходные scientific criteria

Все 56 runtime jobs прошли свои применимые инвариантные и reference-критерии. Строгая сходимость отдельно: **10 PASS / 6 FAIL** (три исходных случая по два идентичных кандидата). Исторические файлы380 и их SHA сохранены.

| Cold-конфигурация | max(Coarse−Fine), normalized | max(Standard−Fine), normalized | Baseline / candidate |
|---|---:|---:|---|
| two-bodies / python | 4.321053763e-15 | 7.086768133e-15 | FAIL / FAIL |
| three-bodies / python | 5.625282158e-15 | 6.215018179e-15 | FAIL / FAIL |
| two-bodies / rust | 7.341808831e-15 | 9.633424121e-15 | FAIL / FAIL |
| three-bodies / rust | 1.001853256e-14 | 3.222516759e-15 | PASS / PASS |

Все восемь continuous convergence comparisons прошли. Это не разрешение заменять cold на continuous. Значения cold порядка1e-15 и эмпирический разрыв reference объясняют ограниченность интерпретации строгого критерия; не доказывают единственную причину FAIL и не отменяют его. Подробные четыре компонента и независимый scalar-fsum пересчёт — в JSON.

| Максимум по 56 jobs | Значение | Исходный предел |
|---|---:|---:|
| energy_drift | 3.131053119e-10 | 1e-08 |
| angular_drift | 5.579533524e-13 | 1e-08 |
| linear_drift | 6.997496666e-16 | 1e-12 |
| quaternion_norm | 1.514095516e-10 | 1e-08 |

E включает кинетическую, монопольную, M-Q и вращательную энергии; L включает орбитальную часть и S. ΔE/|E₀|, |ΔL|/|L₀|, |ΔP|/(Σm max|v₀|), raw ||q||−1 имеют исходные определения380. Сохранение инвариантов не доказывает абсолютную физическую точность.

| Наблюдение | Максимальный runtime−reference | Максимальный разрыв двух reference |
|---|---:|---:|
| position | 3.631312269e-13 | 8.144181587e-14 |
| velocity | 8.046957345e-13 | 3.292159407e-13 |
| orientation | 9.416462596e-10 | 7.191622080e-11 |
| spin | 1.352856195e-11 | 2.877031995e-12 |

Максимумы включают coarse; это диагностическая сводка, а не новые пороги. Position/velocity нормированы на исходный максимальный межтельный масштаб; spin — на исходный модуль S каждой фигуры; orientation — Frobenius-норма матриц, не угол в радианах. Проверен прежний reference-level criterion <1e-8. Разрыв двух RK45 уровней — **эмпирическая разрешающая способность**, не строгая граница ошибки и не независимая внешняя рецензия. С JPL эти величины не сравнивались.

## Независимый offline-аудит

Проверены все58 IDs/owners/SHA, исходные IC/settings, shapes/epochs, complete/guard/launcher/attempt/final receipts и неизменность файлов после чтения. RHS=nfev, compiled calls=RHS только для Rust; cold имеет число solver calls=число интервалов, continuous=1. Partial/corrupt/unowned результатов нет.

[393 observer](../scripts/q2_frame_observer393.py:48) вычислил E/P/L в Decimal80 и110 для заранее заданных initial/final каждого из56 runtime jobs — **112 состояний**. Отдельная Fraction-арифметика пересчитала P/L непосредственно из исходных binary64 чисел; готовые PASS-флаги evaluator не использовались. Raw qnorm проверены через math.fsum по всем эпохам, source-pair углы — [устойчивой quaternion-формулой](../scripts/q2_frame_observer393.py:28). Строгая сходимость независимо пересчитана scalar-fsum и дала те же16 verdicts.

Нормированные расхождения runtime−Decimal110 не больше E 7.570e-15, P 2.657e-17, L 2.323e-16. Decimal80−110: E 3.058e-78, L 2.595e-80, P 0. Fraction−Decimal110: P/L 0 при сохранённом сравнении с120-значным Decimal переводом рациональных чисел. Это согласованность арифметики, не новая научная точность1e-78.

Нормировки P/L используют полные физические масштабы, не относительную ошибку почти нулевой компоненты. Decimal observer разделяет с основной моделью усечённый M-Q Hamiltonian и интерпретацию ориентации; он не является внешней экспертизой. Decimal не проверял все промежуточные состояния и не ограничивает ошибку между эпохами.

Для continuous t=0 использованы именно raw arrays. Подлинный initial_input checkpoint сохранён отдельно; максимальное отличие его p/v от raw readout: 1.818989404e-12 м / 4.440892099e-16 м/с. Подмена checkpoint численным t=0 не выполнялась.

## Ресурсы

| Группа | Jobs | Controller CPU / wall, с | С postcheck CPU / active wall, с | Sampled worker private, MiB |
|---|---:|---:|---:|---:|
| baseline:python | 16 | 26.609375 / 23.909178 | 29.593750 / 26.314869 | 122.92 |
| baseline:rust | 14 | 27.296875 / 24.866490 | 30.343750 / 27.315322 | 126.24 |
| candidate:python | 14 | 27.312500 / 24.833459 | 30.265625 / 27.153603 | 127.76 |
| candidate:rust | 14 | 32.671875 / 29.024550 | 35.890625 / 31.623831 | 125.81 |
| baseline:evaluate | 58 | 7.812500 / 7.404242 | 12.109375 / 10.984253 | 205.70 |

Итого группы+postchecks+evaluator+аудит+report arithmetic: **138.203125 CPU / 123.391877 active wall с**. Evaluator с аудитом и arithmetic report: 12.109375 CPU из early48/cap60; wall 10.984253 из early96/cap120. Каждая runtime-группа осталась внутри original180/360, early144/288, RAM1GiB/900MiB и disk128/112MiB. Нового бесплатного бюджета аудита не было.

Измеряются CPU обнаруженных процессов через Windows final handles и sampled private/RSS; контроль50мс может пропустить короткие процессы и пики. По0,25с CPU/wall на receipt/exit tail начислены как allowance, не измеренная строгая верхняя граница. Эти однократные групповые времена не являются paired benchmark: ускорение полного расчёта данным прогоном не установлено.

Backup отдельно: **24.406250 CPU / 27.213807 local active wall с**, включая неудачную попытку из-за чужого lock. Все backup legs вошли в исходный лимит60CPU/240wall, early48/192 для своей группы. Connector upload/fetch wall сохранён отдельно в JSON; serverCPU, ожидание lock, общение/редактирование, metadata preflight, Git/CI не включены в эти локальные измерения. Initial failed metadata probe не получил resource receipt; его точный CPU неизвестен и не приписан научным группам.

## Ошибки и критическая самопроверка

1. Прямой preflight helper был вызван без controller sanitation BLAS: только OMP/OPENBLAS/MKL оказались unset вместо1. Read-only diff сохранил факт отказа и равенство остальных полей; при точном штатном окружении обе аттестации прошли. Source/native/dependencies/sealed fingerprints не менялись, научных заданий тогда ещё не было.
2. Readback candidate/Rust сначала отклонён активным чужим backup.lock. Общие config/manifest не менялись до освобождения. Затем тот же архив проверен; неудачная операция учтена, до этого следующая группа не запускалась.
3. Один read-only preview `python -c` получил SyntaxError; просмотр JSON выполнен PowerShell. На артефакты и расчёты это не повлияло.

Научных/integration/resource STOP нет. Исторические FAIL не исправлялись и не скрывались. Подтверждение исходных файлов/масштабов, независимая арифметика, exact pairing и отдельные verdicts устраняют вывод только по exit0. Но успешные проверки не доказывают универсальную физическую корректность; причинное объяснение трёх FAIL остаётся в границах ранее установленных свидетельств393.

## Архивы

Аккаунт и owner-only папка Solar-Simulator в Project-Archives проверены заново. Только filtered queue текущего проекта; старые verified395/398/398B dependencies reused, без повторной загрузки. Каждая копия проверена независимым download с SHA/size/parent; локальные оригиналы сохранены. Приватный контекст, SQLite, секреты, окружения и чужие проекты исключены. Распаковка проверена CRC и SHA каждого member.

| Файл | Bytes | SHA256 | Cloud |
|---|---:|---|---|
| Solar-Simulator-stage399-baseline-evaluate-20261108.zip | 563790 | `ecd35a07275a809221147768e0ecabdc62a1730781f782ae7b24948bafc39c00` | [VERIFIED](https://drive.google.com/file/d/1ffqn_75ZwTb9wgpmgk63pNW3dsj6f1GG/view) |
| Solar-Simulator-stage399-baseline-python-20261108.zip | 1172928 | `9d363f1ce4850d21179c0bbb506e681ffedcaecc5d751a81524ed935898eaa05` | [VERIFIED](https://drive.google.com/file/d/1V7UrZcTQMt-KUU9iYDGPvrZ8pQOXkfS8/view) |
| Solar-Simulator-stage399-baseline-rust-20261108.zip | 889944 | `01e6aee8b61dd20a0b1d4a9813c2b0665c08db99cc91250ed11627cb300f4934` | [VERIFIED](https://drive.google.com/file/d/1K9J4ciMcQl5cUyYzOXHw_obK1b-oevnY/view) |
| Solar-Simulator-stage399-candidate-python-20261108.zip | 890613 | `8591bb75241b529975a42b6ca865612b17314bbe5c52085aed6a5772972e5c4f` | [VERIFIED](https://drive.google.com/file/d/1m-3HGqQ5v2qZs1ewBiMvnzCrQCWa8EYl/view) |
| Solar-Simulator-stage399-candidate-rust-20261108.zip | 890280 | `aaf61a7ad2f8931a0740229b41b605d8792937cef03e3c761a8fc3989be6c8e2` | [VERIFIED](https://drive.google.com/file/d/1RCQrUcnpjv1_QY4oqm_r_CkACnMZtnVI/view) |
| Solar-Simulator-stage399-manifest-20261108.json | 29325 | `bf07eb5452cff7cbbc975fde7e987d2bcb31f62b9be92cb8b08adc0cd2bc9919` | [VERIFIED](https://drive.google.com/file/d/1J9c288huNRo70JBt7WAXmVq8dlAUCJz3/view) |

Raw группы и execution receipts находятся в соответствующих ZIP; evaluator ZIP дополнительно содержит полный независимый audit, его код и resource receipts предыдущих backups. Внешний manifest содержит пять SHA-bound recovery pointers и provenance. Собственное будущее cloud-подтверждение и финальная стоимость manifest не вложены рекурсивно в него: они сохранены в центральном backup manifest и настоящем JSON. Публичные отчёты сохраняются точным Git commit; личные документы — только прежним отдельным private-context процессом.

## Инженерное решение и следующий шаг

**GO для утверждения «R-reuse сохраняет прежнее численное поведение в fixed58 квалификации на этой PC-bound среде».** Не доказаны универсальная точность, улучшение точности или ускорение всех расчётов.

**NO-GO для утверждения полного PASS исходных научных критериев и автоматического release0.3.3.** Три cold FAIL сохраняются, A+D1 остаётся решением владельца; полная актуальная source/native/portable приёмка и согласованный состав выпуска здесь не выполнялись. Main/tag/LATEST и принятая0.3.2 неизменны. Production sources, физические формулы, интеграторы, R-reuse, native и публичные настройки этим этапом не менялись.

Следующий полезный шаг — решение владельца об области допуска Q2/A+D1 по этим результатам, затем отдельное задание на включение оптимизации и относящуюся приёмку кандидата. Не начинать новые серии только ради монотонного PASS. Рекомендуемая модель: GPT-6.1 Sol High. После оформления399 STOP.

## Уточнение публикационной проверки

Первый push `aad21e5` запустил CI42417648577. Python job128539098150 остановился **до pytest**: реестр `docs/project-inventory.json` не содержал два новых отчёта399. Это пропуск обязательного документарного шага, а не отказ научного расчёта. Причина проверена по traceback `scripts/project_inventory.py:47`; полный исходный decoded CI-лог сохранён отдельно с SHA. После просмотра карты проекта обновлены только карта и штатный реестр файлов. Scientific receipts, исходные FAIL, plan, оба кандидата, native и код проверок не менялись; расчёты не повторялись. Новый удалённый CI оценивается отдельно и не подменяет квалификацию399.
