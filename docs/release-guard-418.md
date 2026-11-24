# Граница динамических Q2 —418
Кандидат0.4.0 поддерживает ноль или одну динамически вращающуюся несферическую фигуру.
Две и более временно недоступны. Старые файлы не удаляются и не переписываются;
режим не заменяется однофигурным автоматически. FixedJ2 не являются динамическими rotations.

Общий [guard](../src/solar_simulator/rotation.py:22) вызывается в
[Experiment](../src/solar_simulator/experiment.py:89), [create](../src/solar_simulator/experiment.py:101),
[advance](../src/solar_simulator/experiment.py:149) доadvance(0)/halted,
[validate](../src/solar_simulator/nbody_rotation.py:49),
[публичной поправке сил](../src/solar_simulator/nbody_rotation.py:113),
[проверке initial/current](../src/solar_simulator/nbody_rotation.py:145),
[контроллере](../src/solar_simulator/nbody_rotation.py:164) и
[recoveryдоmkdir](../src/solar_simulator/recovery.py:10).
Storage/from_document/to_document и record/replay используют эти границы.
[Старый GUIprofile](../src/solar_simulator/application_profiles.py:7) явно отказывает;
кнопка удалена. Тесты не выполняют solver для проверки отказа.
Преднамеренный вызов приватных низкоуровневых функций/обход Pythonконструктора не является поддерживаемым API.

Формулы M-Q, ориентаций/q/S, сил и моментов не изменены. Ограничение не относится к архивному
read-only демонстратору416 и не отменяет эксперимент413.
[Старые исходники](../scripts/release_history.py:110) разрешены только для offlineпроверки provenance,
не для аттестации актуального кода. Подмена/отсутствие архива не даютPASS.
Полные прежние двух-Q2тесты сохранены в scripts/validation/product-before418-tests.zip
SHA256 f3a4dc88b8f7e3fc78f6c83a3598612780129c87c9ab201a7aff511ab20102c2.
