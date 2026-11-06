# Q2-393: локальная причинная диагностика

2026-11-06. **Ограниченный этап завершён; STOP.** Изолированной ошибки
production не установлено. Изменение координатной системы вносит измеримый
локальный вклад, но причины трёх исторических FAIL380 полностью не разделены.
Физика, интегратор, native, кандидат, исторические результаты и критерии прежние.
Это не новая квалификация и не доказательство истинной точности порядка1e-15.
**Release0.3.3 NO-GO; A+D1 из391 ещё требует решения владельца.**

## Происхождение и границы

- Dev до этапа: `50eeadddc48491efa1476d7f52573d672c164348`.
- Замороженный кандидат: `fe0f456f2c7ba3a077eac21fc8413937d6e84fac`.
- nbody_rotation.py SHA256:
  `7cdbf09b398aa467ec5badabcf4428c88dfc62ac81f49b73c988ae8c81c9ce7c`.
- Native SHA256: `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`.
- Environment SHA256: `056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a`.
  Python3.14.2t/cp314t, NumPy2.5.1, SciPy1.18.1; OMP/OPENBLAS/MKL=1.
- Sealed plan SHA256:
  `8cb4d756d68150d1a182d40dacb10e35d7b393746deba28ca69ab3b5e21ab942`.
- Исторический NPZ380 SHA256:
  `51e7c79d7a36547df92959a8614d9d5804232d39c0ebfe5c4a143ecdd6da696a`.
- Сохранённый392 ZIP:1035373B,
  `a390cf1339251dd41511ca85592b968c50caf67ca11e439a8290b92f3020c777`.
  Проверены manifest/member SHA и исходные380 journals; полный audit392 не повторялся.

Машинный отчёт [JSON](q2-causal-investigation-393.json) содержит все15строк,
точные input/raw SHA, per-body/relative differences, E/P/L и qnorm,
80-digit invariants, meshes/counts и source/execution bindings.
Полные входы/trace/checkpoints/логи/план сохраняются отдельно в Project-Archives.
Наличие Git-отчёта не заменяет raw и аттестацию окружения другого компьютера.

Использована прежняя синтетическая Newton total-degree-two M–Q модель:
монополи всех тел и monopole–quadrupole каждой динамической фигуры,
без Q2–Q2, приливов, диссипации, EIH и контактов. SI: r[m],v[m/s],
S[kg m²/s], E[J], P[kg m/s], L[kg m²/s], время[s]. Кватернион переводит
body frame в inertial; S задан в inertial. Реальная Земля–Луна не аттестуется.
G exact binary64 закреплён в плане как `0x1.2589effed8accp-34`.

## Предварительно выбранные контрасты

Для coarse/standard/fine взяты точные сохранённые физические состояния
непосредственно до ранее локализованных максимумов392. Новые удобные IC
не искались. Все settings/rtol/atol/error-control/relative_pair прежние.

|Роль|Система/backend|Входные индексы380|Глобальные интервалы,s|
|---|---|---|---|
|Основной|two/Python|63|3937.5→4000|
|Контроль|two/Rust|56,57|3500→3562.5;3562.5→3625|
|Контроль|three/Python|53,62|3312.5→3375;3875→3937.5|

По3уровня на каждый интервал:15ABC-сравнений,30локальных A/B integrations.
Дополнительно2source-clone controls на основном standard и короткий
синтетический unit test. Контроли разрешил заранее заданный trigger:
основной standard показал изменение внутренних q/S и accepted mesh после
успешных exactA/source/equivalence checks. Выбор не зависел от получения PASS.

- **A:** прежний холодный пакет через настоящий `advance(state,1)`.
- **B:** тоже новый холодный solver; фиксированный исходный COM frame,
  `center=c0+u0*t_start`, `drift=u0`. Relative-pair encode/decode остаётся.
- **C_A/C_B:** соответствующий encode/decode без физического интегрирования.

Локальное время обоих solver [0,62.5], одна конечная эпоха; API input r/v/q/S
побитно одинаковы, время/force backend/settings совпадают. B не является warm
continuation, не устраняет все преобразования и не восстанавливает контроллер.

Источник B — [source-bound clone](../scripts/q2_fixed_frame393.py:33):
проверяется полный SHA доверенного локального модуля и binding функции,
AST меняет **только значения center/drift**. RHS, коэффициенты DOP853,
настройки solver и состав сил не изменены. JSON не содержит исполняемого кода.
Замороженная функция [integrate](../src/solar_simulator/nbody_rotation.py:171)
не редактировалась; две исходные строки —198/199.

Математическая проверка: r=x+c+uτ,v=w+u при постоянных c/u,
следовательно x'=w,w'=a({x_j−x_i},q), а q'=f(q,S),S'=τ({x_j−x_i},q).
Перенос и boost не меняют относительную геометрию, гравитационные силы,
моменты, ориентации и S. Автономность Newton M–Q позволяет локальное время.
Энергия и орбитальный L сравниваются **после возврата в исходный inertial frame**.
Это проверяемый аргумент для данной усечённой модели, не EIH-инвариантность.

Однако одинаковые настройки не означают одинаковую численную задачу контроля:
компонентный scale зависит от представленного y. [SciPy DOP853 documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.DOP853.html)
описывает atol+rtol*abs(y); фактические RotationDOP853 weights/source
сохранены без изменений. A/B объединяет влияние представления, округления
и выбора адаптивной сетки; это не изоляция только одного из этих механизмов.

## Наблюдения и независимая проверка

Все15 endpoint A **побитно совпали** с прежними380 r/v/q/S.
Отключённый clone и clone с прежними center/drift на основном standard
тоже дали exact A. До/после `advance` input document неизменен.
Невмешательство trace observer подтверждено этим историческим endpoint control;
отдельное повторение каждого B без trace не выполнялось.

Новый [scalar Decimal observer](../scripts/q2_frame_observer393.py:48)
не импортирует production evaluator и не интегрирует. Exact-binary64→Decimal,
80/110 digits для E/P/L; их согласие и сравнение с runtime diagnostics проверены.
Hamiltonian использует principal-I scalar contraction, translational+spin energy
и M–Q potential; L включает оба S. Общие модель/IC/математические предпосылки
с Solar сохраняются: это независимая арифметическая проверка, не внешняя рецензия.

Угол — [relative quaternion atan2](../scripts/q2_frame_observer393.py:28),
без trace/acos; отдельно сверен с392 chord/asin. Знаки q/−q эквивалентны,
raw и sign-aligned q differences записаны отдельно; raw qnorm не скрывается
перенормировкой сохранённых состояний. Большие E/P/L вычитаются до float conversion.
Высокоточный observer не является высокоточным IVP reference.

Ниже нормы **A−B**, не абсолютная ошибка относительно истинной орбиты.
Полные компоненты/другие тела/relative-vector vs distance differences — в JSON.

|System/backend/input index|Level|max Δr,m|max Δv,m/s|max angle,rad|max ΔS,kg m²/s|ΔE,J|
|---|---|---:|---:|---:|---:|---:|
|two-bodies/python/63|coarse|9.16573e-13|3.46945e-18|0|0|0.0649418|
|two-bodies/python/63|standard|9.16573e-13|0|2.77183e-17|0.125|0.0568197|
|two-bodies/python/63|fine|1.13687e-13|2.22478e-16|0|0|-0.0597343|
|two-bodies/rust/56|coarse|7.10543e-15|0|0|0|-3.56756e-05|
|two-bodies/rust/57|coarse|2.27485e-13|0|0|0|-0.0149404|
|two-bodies/rust/56|standard|2.27374e-13|0|1.9331e-16|0|0.0158932|
|two-bodies/rust/57|standard|9.09495e-13|4.44089e-16|7.85007e-17|0|-0.0726047|
|two-bodies/rust/56|fine|2.27374e-13|3.14018e-16|3.15085e-16|0|-0.136052|
|two-bodies/rust/57|fine|1.13687e-13|2.22045e-16|1.70792e-16|0|-0.0685151|
|three-bodies/python/53|coarse|9.16573e-13|0|0|0|-0.0624725|
|three-bodies/python/62|coarse|3.21555e-13|5.56195e-17|0|0|-0.030133|
|three-bodies/python/53|standard|2.27485e-13|0|1.08723e-16|0|-0.0119837|
|three-bodies/python/62|standard|9.09495e-13|2.22478e-16|6.18369e-17|0|-0.0467914|
|three-bodies/python/53|fine|9.09495e-13|1.73472e-18|0|0|-0.038149|
|three-bodies/python/62|fine|1.82254e-12|4.96701e-16|2.02555e-16|0.125|-0.381212|

Основной standard: относительная позиция отличается9.16573e-13m,
скорости совпали, rawq bodyB отличается1.38778e-17, физический угол2.77183e-17rad,
S_B отличается0.125kg m²/s. E_A−E_B=+0.0568197J; полные P совпали,
ΔL=[−31.0687,−57.3010,+248.5495]kg m²/s. Это абсолютные малые разности
больших состояний, а не дополнительный разрешённый физический бюджет.

Across15 максимум per-body r=1.82254e-12m, relative r=2.06136e-12m,
v=4.96701e-16m/s, угол3.15085e-16rad, S=0.125kg m²/s.
Разности энергии имеют оба знака: от−0.381212 до+0.0649418J.
Нет основания назвать B более точным; отсутствует разрешающий такие величины
независимый IVP reference. Не складывать эти числа по64пакетам.

Для всех A/B coarse4accepted/56RHS, standard5/68, fine6/80;
rejected0. Native calls равны RHS только у Rust, у Python0.
Счётчики rejected получены по12stage RHS на attempt и числу вызовов
error estimator; инициализация/dense-output RHS учитываются отдельно.
Это наблюдение данной версии SciPy, не выдуманный публичный счётчик.
Начальные h0 A/B совпали: основной coarse0.07343537335834777s,
standard0.04129574517018001s,fine0.026640689700115336s.

Accepted meshes отличаются у10/15случаев (все standard/fine), несмотря на
равное число шагов. Основной standard penultimate time отличается примерно7e-15s;
это не свидетельство значимой физической ошибки. `h_next` — предложение
следующего шага, последнее после завершения пакета не используется. JSON
разделяет accepted_mesh_equal и next_step_proposals_equal; исходный
`adaptive_path_equal` включает оба и не должен трактоваться только как mesh.
Внутренний последний y1 отличается по смыслу от возвращённого dense snapshot;
q/S internal comparison не выдаётся за сохранённый API endpoint.

## Что именно установлено

|Гипотеза|Статус|Доказательство и предел вывода|
|---|---|---|
|Encode/decode изменяет представленные r/v без движения|CONFIRMED|C, независимая точная арифметика и binary64 comparison; не весь4000sFAIL|
|Выбор COM frame влияет на локальный расчёт|CONTRIBUTES|A/B; часть q/S и accepted meshes меняется; истинное улучшение не показано|
|Прямой reset/потеря q/S на границе|NOT_SUPPORTED|C переносит их без изменений, exactA сохранён; только исследованные случаи|
|Изолированный вклад cold restart|UNRESOLVED|оба A/B cold, warm controller checkpoint отсутствует|
|Локальная truncation error отдельно от roundoff|UNRESOLVED|нужен независимый разрешающий IVP; observer его не заменяет|
|Единственная причина всех3FAIL380|UNRESOLVED|локальные контрасты не реконструируют полную накопленную ошибку|

Pure C max per-body position difference до2.03687e-12m. Даже точный real
affine map с **реальными округлёнными** pair coefficients не exact inverse:
α=0.8333333333333334,β=0.16666666666666669,
α+β−1=2^-54 в rational arithmetic (binary64 сумма округляется к1).
Encode R=x1−c+βρ; decode x1=R−βρ+c,x2=R+αρ+c даёт
x2_input+(α+β−1)ρ. Проверено Fraction для r/v; этот общий bias
**одинаков у A/B**, не объясняет их разность сам по себе.

В floating arithmetic добавляется зависимое от frame округление. Это
подтверждённое свойство [PairCoordinates](../src/solar_simulator/coordinates.py:19),
а не автоматически нарушение контракта: [relative coordinates](relative-coordinates.md)
не обещают bit-exact inverse. Переписать decode через x2=x1+ρ — возможное
будущее численное изменение с другими cancellation/roundoff; оно затронет
Newton/EIH/Q2 и не является доказанно необходимым исправлением.

Три FAIL380 сохраняют точный смысл: строгая монотонность прежнего packet
coarse/standard/fine сравнения не выполнена. 392 исключил некоторые ошибки
observer,393 показал sensitivity локального численного пути. Ни одно из них
не превратило FAIL в PASS и не доказало нарушение физических уравнений.
Warm392 имеет другую входную ошибку/историю; его нельзя подставлять как
контроль с тем же incoming state. Дефекта production, требующего patch, нет.

## Производительность: решение без оптимизации

Использован только [профиль392](q2-numerical-investigation-392.md), новых
benchmarks нет. Примерно4300cold против450continuous RHS на4000s — цена разных
recipes; пропускать cold restart как готовую оптимизацию нельзя: меняются
адаптивная история, save/resume и numerical results.

- Обязательны state-dependent geometry, силы/реакции/моменты, quaternion→R
  и выбранная точность; меньше RHS само по себе не критерий правильности.
- Повторение одинакового R в пределах одного RHS при том же q избыточно;
  можно передавать подготовленные R внутрь вычисления, не кэшировать между RHS.
  Доля R в392~11.5–11.8%; optimistic total speedup~1.06 для устранения половины
  этой работы — оценка Amdahl, не измеренный выигрыш.
- Постоянный body-frame Q из I можно готовить один раз на integration context,
  если объект параметров неизменен и при новом опыте контекст перестраивается.
  Inertial R Q Rᵀ обновляется при каждом новом q. Доля body-Q~3.3–3.5%;
  вместе с R optimistic~1.10x, не обещание производительности.
- Честный отдельный prototype: те же IC/backend/packets/settings/outputepochs,
  pinned before/after source/environment/native; прогрев, фиксированный порядок
  и повторы, CPU/wall/private/RHS/nativecalls, raw r/v/q/S и независимые E/P/L.
  Отчёт включает разброс времени и все расхождения, без подбора допусков.
- Даже algebraically equivalent перестановка операций может изменить trajectory.
  Нужны source fingerprint и one/two-Q2 gradient/free/zeroQ/covariance/persistence
  regressions, затем относящаяся Q2 qualification; прежние receipts не наследуются.
  Если меняются common coordinates/error-control/native, отдельно затрагиваются
  Newton384/annual385. При точном сохранении arithmetic всё равно нужны контроль
  raw numerical bytes и targeted regressions. Полный релиз требует своего gate.

**Сейчас не менять код производительности.** Следующий полезный engineering шаг —
отдельно согласованный маленький R-reuse prototype с before/after, не лечение FAIL.
Уже имеющихся данных достаточно, чтобы прекратить причинные опыты без бесконечного
high-precision follow-up. Для выпуска сначала требуется решение владельца по
честной Q2 scope/маркировке391 и отдельная оставшаяся приёмка, не снятие3FAIL.

## Проверки, ресурсы и воспроизведение

Новые targeted tests: **26 unique PASS,0FAIL,0skip**, по26в двух observer jobs;
preflight10 — их подмножество, не дополнительные уникальные тесты.
Покрыты недопустимые frame/precision/bool/nonfinite/shape/sourceSHA,
двеAST-подстановки/owned vectors/disabled clone, analytic E/P/L limit,
tiny-angle/sign/extreme scale и input immutability.
Код: [frame tests](../tests/test_q2_frame393.py:10),
[observer tests](../tests/test_q2_frame_observer393.py:4).
Тесты включены в существующий Python CI subset; нового framework нет.
Все source/execution bindings,15inputSHA, исторические endpoint bytes,
candidate freeze/native/environment и независимый saved-data observer проверены.

Cap90CPU/180activewall/1GiB/48MiB; early70/145/900MiB/40MiB неизменны.
Все6контролируемых jobs: **19.1875 CPU s / 17.880528 active wall s**,
worker+supervisor, без повторов научной серии. Worker private sampled peak
178597888B (170.32MiB), RSS138477568B; supervisor OS peakcommit37441536B.
Консервативная сумма раздельных peaks216039424B (206.03MiB),
не синхронный пик. Частота50ms, retained Windows final CPU handles;
внешний launcher/последний record-tail CPU отдельно не пойман. Короткие пики
могут остаться незамеченными: это sampled guard, не hard OS quota.
Рабочих scientific artifacts на последнем guard sample1165711B;
пик числа файлов наблюдался:67. Финальные отчёты/backup добавляются отдельно,
в пределах48MiB; архив — другая копия, не новое научное вычисление.
Чтение/редактирование, Git/CI и обязательное резервирование отдельно;
activewall не означает длительность всего чата.

Научных FAIL/STOP этого ограниченного этапа нет; это не отменяет old3FAIL.
Две неудачные preparatory assertions при выделении нового testfile выявили
trailing-LF mismatch до записи; original executed testfile восстановлен
byte-exact, binding и прежние результаты не редактировались.
Full check_project,380matrix,384/385,compatibility,portable/release не запускались.

Локальные acquisition commands: candidate Python `-I -X utf8 -B`,
qualification393/run.py с worker.py main/control; observe.py читает только
сохранённые JSON. Полный sealed plan, команды/source hashes и восстановление
предоставлены в reviewed archive; **не запускать автоматически после распаковки**.
Публичные helper/tests читаются без raw; полный replay требует подтверждённых
raw/исторических journals и точного environment. На другом ПК пути надо проверить.

После отчёта **STOP**. Нет automaticfix/optimization/main/tag/LATEST/portable.
Рекомендация следующей ограниченной инженерной задачи: GPT-6.1 Sol High.
