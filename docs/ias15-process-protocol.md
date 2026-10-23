# IAS15: проспективный протокол нового процесса365

24 октября2026, до просмотра результатов нового опыта. Продолжает
[364](ias15-full-suite-validation.md), не меняет его источники или критерии.

- Те же9 actual-IC задач353/364, epsilon1e-9/1e-11, Newton2point/SI,
  inertial3D/modelt0=0, basic gravity/PRS23/min_dt0/exact_finish_time1.
  Прежние masses/IC, interval63114866.86220014с, epochs82/60 и packet_dt
  631148.6686220014с. Без новых сил, COM shift, callback или параметров.
- Две заранее выбранные точки: первый committed пакет (index1,
  t3155.743343110007с) и первый committed endpoint>=T/2 (index66для
  holdout/index57дляoriginal, t31557433.43110007с). Оба epsilon;36положительных
  worker запусков. Не выбирать точку по последующему совпадению/ошибке.
- Каждый worker — новый subprocess того же Python executable, без
  переданного Python/C объекта симуляции. Передать только проверяемый JSON
  с metadata/request SHA; raw snapshot читать из SHA-pinned public NPZ364.
  Проверять pid/ppid, фактический Popen.pid, launch_id, SHA запроса/источников/
  входов и отсутствие ранее импортированного REBOUND. Это не проверка
  другого interpreter/OS/компьютера/ABI.
- До орбитальной части stdlib-проба выявила Windows venv launcher:
  Popen.pid относится к launcher, worker.ppid равен ему, а worker.pid иной.
  Допустимы direct S→W или Windows S→L→W, S/L известны supervisor по Popen,
  W/ppid сообщает worker; PID должны соответствовать этой цепочке.
  Supervisor передаёт launch metadata через stdin после создания процесса,
  worker связывает её с request SHA/launch_id до C. Это уточнение измерения
  идентичности процесса до данных, а не ослабление численных критериев.
- В новом процессе независимо построить guard363 из исходных IC и pinned
  REBOUND5.2.2/68librarySHA; сверить ABI/version/origin/masses/epoch/identity/
  physical и binary SHA с frozen364. Ошибочные metadata/hash/paths должны
  отклоняться до передачи stream C-reader. Guard363 не менять.
- Загрузить ровно выбранный полный snapshot через guard.restore, оба raw C
  mask=0, без warnings/synchronize/getSimulation/integrate при чтении.
  Затем один непрерывный контроллер продолжает все прежние packet endpoints
  доT. Не добавлять промежуточных restore/reset или менять dt.
- Сравнивать полные сериализуемые fields с frozen FULL364 (не только x/v):
 17IAS15fields, actual N_allocated6, dt/dt_last_done, steps_done, model,
  x/v/a/masses и rand_seed. Исключены только walltime/pointer addresses.
  Внутри restore также обязательна побитность. Full364 уже был сверён с warm;
  выбор FULL позволяет сохранить и проверить исходный seed.
- Физические результаты continued packet states сохранять. На выходных
  эпохах составить прежний prefix+новый suffix и повторить независимые
  actual-IC analytic/E-L-P gates: Δr<0.1м, Δv<1e-6м/с, E/L/P drift<1e-10.
  Отдельно повторить metrics на suffix. Не подменять проверку одной побитностью.
  Для принятия требуются36/36полных продолжений и прежние независимые gates.
- Raw streams/sidecars и immutable commit markers каждого worker остаются
  локально для анализа отказов. Публичный NPZ хранит новые physical states,
  indices и canonical SHA всех field payloads, без дублирования старого NPZ.
  Canonical SHA включает build header и все payloads кроме clocks/addresses,
  не преобразует числовые значения в текст. Offline replay сравнивает SHA
  с frozen364 и повторяет аналитику; это evidence replay, не новый C-load.
- Исключение/timeout/nonzero exit/malformed result не должны удалять request,
  stdout/stderr или последний committed snapshot. Candidate сравнивается и
  сохраняется перед commit; при ошибке остаются прежние commit markers.
  Supervisor сохраняет отказ и продолжает остальные варианты. Новые файлы
  только в fresh .tools directory, старые результаты не перезаписывать.
- До положительных запусков: pure-Python negative tests (в том числе изменение
  каждого17IAS15payload), subprocess exit/timeout/stale result;4реальных
  отрицательных worker: outer SHA, ABI, embedded binary SHA, source SHA.
  Ожидается reject/no C restore, а не искусственный орбитальный FAIL.
- Отдельно измерить launch/wall, C restore, integration, capture/preflight и
  запись. Одно инструментированное продолжение на точку; не заявлять speedup.
  Sources/inputs/library SHA проверить до/после; во время опыта их не менять.

Пять coldFAIL353/355/364 сохраняются; здесь cold reset не повторяется.
Успех не означает новую точность JPL или новый product backend. Native силы,
лицензия/adoption, standalone Rust, portable/Solarstorage/0.3.2 — вне365.
Primary writer/reader/ownership источники — прежний [аудит362](ias15-archive-source-validation.md).
