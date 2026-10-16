# Явный условный вход Луны — изменение66

Добавлен отдельный research API
[from_lunar_profile](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_initial_boundary.py:28).
Он использует прежний закреплённый профиль, инверсию58 и выбранный H57.
Формулы, runtime, старые checkpoint и данные не изменены.

Обязателен `purpose='conditional-research'`. Другие цели, включая запрос
физической сертификации или локальных часов, отклоняются до чтения профиля
и инверсии. Перед инверсией проверяются типы параметров/SIUnits, уникальный
порядок имён с фигурой Moon, точная эпоха JD2461321.5TDB и EclipticJ2000,
G и совместимость массы/GM, моментов I, bounding radius и c с профилем.
[Допуск](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_initial_boundary.py:21)
1e−12 служит проверке округления одинаковых параметров, не оценке их
физической неопределённости. Числа конвертируются только SI similarity;
clock/basis/SSC-преобразования не вычисляются.

q берётся из прежнего проверенного R; W извлекается непосредственно из
globalTDB Rdot, затем переводится в модельное обратное время. Никакая
дополнительная SO-связь к W не добавляется: её учитывает сама инверсия58.
Другие тела в этом API — явно идеальные точки с нулевым спином.
Чужие заданные спины сюда не передаются и не игнорируются.
Диагностика включает SHA профиля, эпоху/базис/GM-time, effective constant
solid-inertia, **unqualified** inertia/radius timeprovenance,
**not applied** clock/basis/SSC и **physical_mapping_certified=false**.

Caller x/v должны уже иметь модельные единицы и заданные эпоху/базис.
Их канонические центры являются явным условным назначением. API не
доказывает происхождение произвольных переданных массивов и не выполняет
harmonic→ADM, local→global или полный extended-body перенос. Даже правильно
согласованные единицы не означают физическую сертификацию.
Это новый отдельный вход: прежние low-level функции и приложение его ещё
не вызывают. Новый формат сохранений не вводился.

Проверки: **15 новых тестов внутри62passed,3.28s**, вместе с canonical_initial,
spin_initial и rotation_time. Source fixture63 закреплён SHA и проверен
через старый verify_sources. [Битовый результат и independent H gradients](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_initial_boundary.py:35)
подтвердили прежнюю инверсию и восстановление заданных v/W до прежнего1e−13.
[Раннее отклонение физических целей](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_initial_boundary.py:57)
проверено с запрещёнными вызовами loader/inversion;
[параметры/соглашения](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_initial_boundary.py:65)
и [источник/неявная цель](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_initial_boundary.py:80)
тоже проверены. Отказов тестовых запусков66 не было. Полный набор не
повторялся; последняя полная проверка после63 —835Python/17Rust+fmt.

Научные основания и ещё нерешённые соглашения — [контракт64](rotation-time.md):
новые физические формулы и новые заявления о точности здесь не вводились.
Истинная лунная точность, объяснение121.84″/год, PN-runtime и приливы ещё
не подтверждены этим входом. Следующий67 — связывание нового договора с
происхождением x/v и metadata в отдельном стенде; SSC/tetrad/PN-I/Q2 остаются
самостоятельными научными задачами. Локальная проверка сохранности:
`.tools/boundary66/verification.json`. Публикация/portable не выполнялись.
