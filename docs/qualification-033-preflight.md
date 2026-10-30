# Исполняемая подготовка0.3.3: этап383

30 октября2026. Это техническая подготовка, не выполненная scientific qualification.
Принятые main/portable0.3.2 и LATEST сохраняются.

## Контракт

[План382](qualification-033-plan.md) сохраняет исходные научные критерии.
[prepare_qualification383.py](../scripts/prepare_qualification383.py) экспортирует
точный Git commit в новый каталог, меняет только шесть package metadata на0.3.3
и записывает before/after SHA. Это commit плюс явно объявленный overlay,
а не чистый checkout с придуманным SHA. Большие historical docs/*-samples.npz
пропускаются как восстанавливаемые Git-данные: перед full acceptance вернуть
их по candidate-staging.json. Изоляция native/Python-пакета отдельная;
численные зависимости разделяются read-only с исходной средой, пути и реальные
хеши фиксируются. Это ещё не аттестация независимой установки portable.

375 получает --work, --protocol и --protocol-sha256; reducer также --report/--arrays.
376 получает --protocol/--protocol-sha256 и прежний --output; reducer принимает
--run-directory/--work/--protocol/--report/--arrays/--guard-file. Новая попытка
не наследует старые failures, guard CPU или grid-MRE. Отсутствующие метрики
обозначаются measurement_available=false, не нулевым измерением.
380 сохраняет --plan/--output и добавляет явный --plan-sha256; новый sealed plan
может включать уже существующий continuous_control без reuse старых arrays.
Везде старые defaults сохранены. Существующий output отклоняется; новые планы
проверяют SHA, вычислительные source и фактическое environment. Не исполняется
код/команда из JSON. Исторические source доступны только offline resolver;
актуальный375 gate не получает разрешение из архива.

## Границы текущей работы

Общий preflight cap:180CPU s,360active wall s,1GiB private,256MiB новых файлов.
Включены red/fault/regression проверки, копирование ограниченного candidate,
wheels/native build и короткая synthetic two-Q2 save/resume probe; время
редактирования и облачного резервирования не является временем вычислений.
Старый50ms monitor с early margins; CPU worker tree и supervisor отдельно.
Выборка и короткий интервал фиксируются до запуска, критерий — техническая
совместимость, неизменность q/S/settings и точное same-packet продолжение,
не научная точность. Нет годового EIH/JPL, полного380/check_project/portable.

Три исторических380 FAIL сохраняются. Packet-convergence scope требует
отдельного решения до основной two-Q2 квалификации. Кандидат с новым native
также не удовлетворяет автоматически старому375 accepted032 same-environment
контракту; этот отказ нельзя обходить fake fingerprint или заменой receipt.
Выбор корректного нового comparison scope — отдельное решение до annual jobs.
Технически параметризованный driver не означает одобрение такого решения.

Фактические результаты текущего ограниченного исполнения добавляются после
измерений; до этого план не считается выполненным.
