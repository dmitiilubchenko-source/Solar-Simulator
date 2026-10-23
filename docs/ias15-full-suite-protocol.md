# IAS15 full-state: проспективный протокол364

Зафиксирован 24 октября2026 до просмотра результатов расширенного опыта.
Продолжает [basic pilot363](ias15-full-state-validation.md) и его
[full-state протокол](ias15-full-state-protocol.md). Это исследование,
не обещание включить IAS15 в выпуск0.3.2.

1. Все девять случаев353, без отбора по результатам: holdout_circular,
   holdout_moderate, holdout_original, holdout_permuted, holdout_apocentre,
   holdout_eccentric_phase, original_0.0, original_0.5, original_0.95.
   Использовать прежний `load_cases`, исходные binary64 masses/IC,
   input-request SHA, Decimal actual-IC oracle100 и его проверенную
   неопределённость (<1e-6м/<1e-12м/с). Никакой новой подгонки орбиты.
2. Newton two point mass, SI, инерциальные3D, модельное t0=0; без PN,
   смягчения, вращения, контактов, COM shift. Старый интервал
   63114866.86220014с и packet_dt631148.6686220014с для всех случаев;
   точные прежние выходные epochs:82для holdout,60для original.
3. Два epsilon1e-9/1e-11, PRS23/min_dt0, initial dt=packet_dt/200,
   exact_finish_time1. Для каждого варианта: basic warm, полное binary
   восстановление после КАЖДОГО committed пакета, прежний physical JSON
   cold every-packet. Не дробить пакеты и не выбирать удобные restore points.
4. Использовать неизменные `FullStateGuard`/`CommittedFullState` и `paired`
   из363: SHA/ABI/header/model/structure/physical guards до C-load,
   отсутствие всех10unsupported callback slots, оба raw C mask=0,
   отсутствие Python warnings. Первоначальные56negative guards для каждого
   case/epsilon выполнить до его орбитального расчёта. Только trusted own
   snapshot/same pinned REBOUND5.2.2/64-bit ABI/process.
5. Все17IAS15 written fields, N_allocated6, dt/dt_last_done, physical/model
   поля должны быть побитовыми warm↔full на каждой границе и после C-load.
   Внутри restore проверять также rand_seed; только между независимыми
   контроллерами исключать их неиспользуемые basic seeds. Walltime и pointer
   addresses исключены из численной идентичности по363.
6. Прежние независимые gates для относительного движения: maxΔr<0.1м,
   maxΔv<1e-6м/с, относительные E/L и масштабированный P drift<1e-10.
   Вычислить прежним `metrics` для warm/full/cold; gates не ослаблять.
   Требуется18/18PASS для принятия полного восстановления в этой области.
   Warm/cold outputs и packet endpoints должны совпадать побитно с353.
   Пять известных cold FAIL остаются данными, не блокируют отдельный full
   gate и не переименовываются в PASS. Новые FAIL также сохранить.
7. Сохранять каждый полный warm/full stream с physical JSON, epochs/states,
   oracle и cold-контроль. Fresh .tools output/source ZIP и файлы каждого
   committed пакета; старые результаты не перезаписывать/удалять. При
   исключении variant фиксировать причину/путь partial streams, затем
   проверять остальные варианты. Завершение списка попыток отличается от
   полноты каждого варианта и от научного PASS. При изменении источников/
   входов/library во время опыта прекращать run, не квалифицировать его.
8. Отдельно измерять integration/capture+preflight/read+strict validation,
   byte sizes и запись всего опыта. Это single instrumented runs, без
   performance/speedup claims. SHA sources/inputs/library до/после.
9. Offline replay без REBOUND/C-load/integration: все сохранённые пары,
   physical/binary поля и17буферов, контроль epochs/oracle/IC/353 и повтор
   независимых metrics; явная проверка всех случаев/вариантов/массивов и
   aggregate PASS/FAIL. Отдельные отрицательные проверки повреждения
   evidence, списка случаев, gates и model metadata.

Primary writer/reader/state источники закреплены в
[source-аудите362](ias15-archive-source-validation.md); их не заменять
свежей версией библиотеки. Успех означает сохранение численного результата
данной модели на этих входах/эпохах. Не точность DE441/произвольных систем,
не переносимый Solar checkpoint, не новый integrator runtime. Native-force
callbacks и новый процесс — отдельные последующие этапы после этого gate.
