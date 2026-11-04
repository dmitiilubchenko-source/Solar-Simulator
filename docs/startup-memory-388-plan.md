# Startup388 — план до проб

4 ноября2026. Dev1a1f23b, candidatefe0f456 immutable. Никаких IC/орбит.
Цель — тот же900MiB private guard387, не уменьшение показателя подменой метрики.
Originalworker SHA2102fba85c7a25c147ebc6fda2af8d0b1c995409c236ca9f116df076901e138f,
monitor SHAfe0f4e83a5b1473a23404e813f3f98693fac8099181d936ca5980e3e1f80a508.

Один bounded stage: максимум60CPU/120wall/1GiB sampled private/32MiB новых файлов;
ранние50CPU/110wall/900MiB/28MiB. Монитор50ms неизменён. Учитывать controllerCPU
и combined private на одном sample. При memory-stop не запускать другие пробы.
Подготовка текста/сеть/Git/backup отдельно от активного измеряемого preflight.

Порядок заранее: (1) ZIP+5979members read-only CRC/SHA и freeze033;
(2) малые synthetic/API tests; (3) portable blas1-only;
(4) portable all1-current; (5) portable cleared387 — последней, если guard сработает,
остановить исполнение, сохранить наблюдения и анализировать offline.
Использовать собственный portablePython, не developer metadata032.
Три profiles перед импортами очищают6thread variables; blas1-only ставит только
OPENBLAS_NUM_THREADS=1; all1-current — OMP/OPENBLAS/MKL=1; cleared387 оставляет
все6unset, как attempted387. Историческая эквивалентность не предполагается.

Сначала исполнить ровно stdlib-imports исходного module387, затем только Import/
ImportFrom prefix originalprepare до первого присваивания seeds. AST ограничивает
исполнение импортами, не вызывает prepare/main/создание объектов/advance.
Прямой WindowsAPI logger и nested-import tracing — явное инструментирование,
не идентичное неинструментированномуstartup по расходу/таймингам. На checkpoints
80ms окна для внешнего observer. Extra imports только для двух low-thread profiles:
scipy.integrate,matplotlib,tkinter,solar_simulator.app,actualnative032. БезTkокна,
GUI-сессии/новыхопытов и изменения исходных файлов. -I/-B/externalpycache_prefix,
LOCALAPPDATA/MPLCONFIGDIR вновом388каталоге; nohistoricaloverwrite.

Сохранять private/working-set/peakcommit Win32-self; внешний psutil private/rss/
USS/threads/descendantidentity и независимый GetProcessMemoryInfo до/послеsample.
Не называть psutilWindows.vms полным виртуальным адресным пространством.
Readonly BLASthread query использует GetModuleHandle только уже загруженныхDLL,
не загружает новыеDLL и не вызывает setters. Trace+profile+process+time+CPU+exit
и limitreason обязательны, output exclusive. Self900MiBguard дополняет external,
не заменяет/не ослабляет его. Sampling допускает overshoot, это не OS hardquota.

Критерии: метрика объяснена по установленномуpsutil7.2.2 и MicrosoftAPI;
исходный387sourceSHA сохранён; первичныйSTOP не переименован вPASS. Различия
памяти/числа потоков измеряются, а не оцениваются по RSS. Исторические рецепты
валидировать SHA payload/manifest/frame, отделить сохранённое свидетельство
конкретного запуска от полного hermeticOS snapshot. Для продолжения387 нужен
явный frozen launch profile и source/IC/settings/8cases прежнего A/B/C;
эти случаи здесь не выполнять. Итог GO/NO-GO относится только к подготовке
нового compatibility preflight, не кscientific/release qualification.
