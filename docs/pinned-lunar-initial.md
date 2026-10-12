# Источник начального входа и проверяемая запись — изменения67–68

Две небольшие задачи завершены без смены уравнений H57, runtime, данных или
старых форматов. Это продолжение [условного входа66](lunar-initial-boundary.md),
с прежними [физическими ограничениями64](rotation-time.md).

## 67: источник координат и скоростей

[source_inputs](C:/Users/Admin/Desktop/Solar-simulator/scripts/pinned_lunar_initial.py:34)
читает закреплённый SI-набор10тел с SHA
`d58227299b10b217246aa5c63f33da51b0fd331b5c7a75bee400d577d6d1f702`.
Проверяются SHA, parent профиля51, эпоха/базис/центр, DE441, единицы,
vector_correction, Earth/MoonGM и точный исходный порядок тел.
GM/G, c, I и bounding radius переводятся в прежние SI similarity units;
координаты и скорости берутся только из этого источника.

[from_pinned_dataset](C:/Users/Admin/Desktop/Solar-simulator/scripts/pinned_lunar_initial.py:66)
требует явную conditional-research цель, сам строит все параметры/x/v и
вызывает неизменённую обёртку66. Вызывающая сторона не передаёт сюда свои
массивы. Диагностика содержит идентификатор/SHA орбитального источника,
порядок тел, units и отдельные отпечатки модельных x/v.
[array_digest](C:/Users/Admin/Desktop/Solar-simulator/scripts/pinned_lunar_initial.py:26)
включает форму и little-endianfloat64 bytes: signed zero не теряется.
Это детерминированный технический отпечаток, не новая точность природы.

11новых внутри26относящихся тестов прошли2.44s: результат
[bitwise direct66](C:/Users/Admin/Desktop/Solar-simulator/tests/test_pinned_lunar_initial.py:13),
[отказ purpose/changed bytes](C:/Users/Admin/Desktop/Solar-simulator/tests/test_pinned_lunar_initial.py:25),
[metadata/order/GM](C:/Users/Admin/Desktop/Solar-simulator/tests/test_pinned_lunar_initial.py:35),
[shape/signedzero/nonfinite/bool](C:/Users/Admin/Desktop/Solar-simulator/tests/test_pinned_lunar_initial.py:55).

## 68: строгая запись происхождения

[make_receipt](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_initial_receipt.py:45)
создаёт отдельный kind `solar-simulator-research-lunar-initial-receipt`, schema1:
purpose, representation, state SHA, полные metadata, SHA используемых
исходников, NumPy/SciPy версии и checksum канонического JSON.
В файле **нет интегрируемого состояния или времени продолжения**.
Он не является checkpoint и не обещает переносимость между версиями.
Checksum обнаруживает изменения; это не подпись автора.

[verify_receipt](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_initial_receipt.py:50)
отклоняет неизвестные поля/schema/kind/representation/physical purpose,
проверяет checksum, заново строит pinned initial и сравнивает весь договор
и отпечаток состояния. Пересчитанный checksum не отменяет сравнение с
источником. Canonical JSON различает False/0 и целые/дробные числа.
SHA проверяются относительно загруженных кодовых версий до и после
инициализации. Дубликаты ключей и NaN/Infinity отклоняются при чтении.
[save](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_initial_receipt.py:71)
пишет только проверенный JSON в новый файл; [load](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_initial_receipt.py:76)
выполняет повторную проверку. Прежние Cartesian/Jacobi loaders этот kind отвергают.

22новых теста68, включая
[файловый round-trip и точные metadata floats](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_initial_receipt.py:27),
[independent full-H gradient v/W](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_initial_receipt.py:40),
[пересчитанный checksum/семантика](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_initial_receipt.py:53),
[source guard](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_initial_receipt.py:86),
[сохранность файлов](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_initial_receipt.py:94).
Полный относящийся поднабор: **95passed,3.70s, включая33новых67–68**.
Один предыдущий успешный прогон68 до добавления independent-gradient теста:
94passed4.12s. Неудачных запусков этих двух итераций нет.
Производные восстановили исходные v и заданную W до прежнего1e−13.

Реальная запись `.tools/boundary67-68/initial-receipt.json` сохранена и
заново загружена; state SHA
`de59110dae8d9213218a77a75ae0674b2386cb3fb0cdb850861d30004cdedad2`.
Проверка сохранности `.tools/boundary67-68/verification.json`.
Полный check_project не повторялся; последний после63 —835Python/17Rust+fmt.

Источник x/v теперь закреплён, но его harmonic-эфемеридные значения только
назначаются conditional canonical boundary. Физический harmonic→ADM/SSC,
local tetrad/clock и PN-I/Q2 перенос не выполняется. Effective rigid I
остаётся условной; inertia/radius timeprovenance unqualified, physicalfalse.
Новая запись не используется прежним runtime и не включает приливы/ядро.
Следующий69: научная квалификация происхождения I/radius/time/basis/SSC;
PN-runtime требует отдельного сквозного аудита. Личные файлы локальны,
commit/push/portable не выполнялись.

## Исправление source manifest в71

В исходном CODE_SOURCES68 отсутствовал импортируемый spin_initial.py.
При уже загруженном коде его дисковая правка могла не замечаться, хотя
initialstate пересоздавался и проверялся. Пробел воспроизведён в изолированной
копии. В71 [loader включён в SHA-контроль](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_initial_receipt.py:21);
real diskmutation теперь отвергается до initialization/flow. Это исправление
происхождения, без изменения формул/profile/initialstate. Старые receipts
этой версии кода явно отвергаются, остаются сохранёнными и не мигрируют
автоматически. Новый начальный файл создаётся через init команды70.
Приведённые выше95passed относятся к68 и не доказывали полноту manifest.
Квалификация69 и [сквозной researchрежим70](lunar-research.md) выполнены;
полная физическая квалификация по-прежнему false.
