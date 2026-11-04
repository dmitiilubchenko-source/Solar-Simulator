# Контракт совместимости 387 — до вычислений

4 ноября 2026. Исходный dev e2d96647df941218458d9d928afd965f98c47867.
Принятая версия: main/v0.3.2 cf653c9ca4b60649e70658b002a5e70669411266,
оригинальная portable SolarSimulator-0.3.2-20261025-121729, ZIP 112312650 bytes,
SHA256 7c578220ec77e792aa9589f32a30352e88277d0d096bff0ad3ca5aae9c014c49.
Native032: 0cbc389f139854628f287c04a7cea52c530a18294c2c3a0670faa48bf53c0601.
Кандидат: fe0f456f2c7ba3a077eac21fc8413937d6e84fac,
native033: 651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091.
Не заменять оригинал установленным developer-runtime с metadata0.3.2.

## Предварительный барьер и ресурсы

Проверить SHA ZIP и потоковым чтением CRC/SHA всех его членов против существующей
поставки; без новой распаковки и изменения оригинала. Неисполняемые лишние
__pycache__ допустимы только с -B и новым внешним pycache_prefix. Остальные
лишние файлы — отказ. Исходный бинарный Python/stdlib/dependencies/native из ZIP,
изолированные пользовательские/Matplotlib-каталоги; текущая Windows, не образ
исторической ОС. Команды, SHA инструмента и monitor фиксируются до исполнения.
Кандидат проверяется существующим verify_freeze384 до/после своего worker.

Один этап с общим лимитом 180 CPU s, 360 wall s, sampled private 1 GiB,
128 MiB новых файлов. Ранний стоп 160 CPU/330 wall/900 MiB/112 MiB.
Включить проверку ZIP, подготовку IC, два worker, observer, тесты и повторный SHA-аудит.
Backup/публикация и редактирование текста не являются научными вычислениями.
Монитор прежний, 50 ms, retained Windows CPU handles; это не OS hard quota.

## Фиксированная выборка

Восемь случаев, Python/Rust каждого: sun-earth Verlet, sun-earth DOP853,
sun-earth-moon DOP853, существующий test_nbody_rotation.model с одной Q2.
Sun–Earth eccentricity .0167; остальные исходные preset без изменения.
SI, G=6.67430e-11; инерциальные декартовы состояния учебных preset, t=0,
без заявления эпохи JPL. Q2: m=(1e15,2e14) kg, r=(12000,0,0) m,
v=(0,2.55,0) m/s, I=(2e20,2.5e20,3e20) kg m², bounding radius1000 m,
rotvec(.3,-.2,.4), body omega(.0001,-.0002,.002) rad/s,
q scalar-first/body→inertial; quaternion_atol1e-13,
momentum_atol=|S|*1e-13. Один динамический Q2 — старый общий режим.
Все случаи dt50 s, rtol1e-11, position_atol1e-7 m, velocity_atol1e-11 m/s,
error_control per-body, Newton, point contacts disabled by zero radii;
Q2 relative_pair=(figure,point), остальные None. Три неизменных пакета по1шагу,
эпохи [0,50,100,150] s. Эти параметры — проверка совместимости, не критерий
абсолютной физической точности. Версия032 создаёт точные JSON IC один раз;
plan.json с их SHA замораживается до первого advance в любом worker.

## Три независимых контракта

**A — данные.** Поддерживаемые старые схемы1–9: синтетические fixtures,
полученные обратным применением явных миграций storage к zero-spin Newton/Verlet.
Это не найденные пользовательские файлы из прошлых лет. Схема10 — один Q2.
032 сама валидирует каждый fixture до запуска; 033 читает исходные и сохранённые
032 JSON. Сравнить значения/настройки/parent отдельно от упаковки и fingerprint.
Same-packet save/resume после50s в каждой среде должно точно воспроизвести150s.
Сохранённые input bytes не изменяются. Branch/recovery и запись двух пакетов
с сохранённым recipe проверяются существующими API.

**B — численное поведение.** Независимый observer без импорта Solar считает
binary64 bits, max|Δr| в m, max|Δv| в m/s и Newton/MacCullagh E/P/L через fsum.
Точные состояния/настройки/эпохи дают EXACT только для выбранных случаев.
Любое различие сохраняется с величиной, без post-hoc tolerance; причина
неизвестна → UNRESOLVED. E/P/L — диагностические сравнения, не эталон орбиты.
Нет новой оценки JPL, сходимости или глобальной ошибки.

**C — действия пользователя.** Настоящий Tk Laboratory в обоих interpreter,
мокируются только выбор файлов: отмена load/save, corrupt/unsupported schema,
открытие ветки032, один пакет, pause, save, recovery/restore. Состояние и parent
не должны теряться. UI закрыт после теста; исходные файлы не перезаписываются.
Wrong-native: известные ошибки missing force entrypoint и noncompiled provenance
отклоняются существующими guards в disposable процессе. Это не обещание, что
runtime проверяет SHA каждого ABI-compatible native. Точный SHA — preflight guard.
Старая версия обязана явно отказать новому checkpoint с двумя Q2; создаётся
только файл, без интегрирования. Recipe старой записи должна быть целой, но
strict replay в ином окружении должен отказать, а не выдавать повреждение.

## Решение и исключения

Отдельные A/B/C PASS/FAIL/UNRESOLVED. Нужны успешные барьеры provenance,
полная заявленная короткая выборка, сохранённые ошибки и независимый observer.
Не распространять результат на контакты/mergers, EIH/J2, долгие орбиты,
произвольные JSON или portable033. Annual385/Newton384 не повторять.
Кандидат/main/tag/LATEST/evidence не менять. Q2 policy A и B_app не утверждены;
этот этап не application experiment200s и не release waiver.

Инструмент: [check_compatibility387.py](../scripts/check_compatibility387.py).
После этапа остановиться; runtime-изменения требуют отдельной оценки.
