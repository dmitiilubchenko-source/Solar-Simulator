# Сохранность веток, CLI и время: исправления301–309

18 октября2026. Исправлены пункты1–3 независимого ревью: потеря родителя
при сохранении ветки, несовместимость основных CLIкоманд с bundle и
перескок точной временной цели при дробном шаге и ненулевом радиусе.
Изменения локальны; формулы сил и последовательность шагов интегратора
сохранены. [Машинный отчёт и SHA](runtime-stabilization-validation.json).

## До и после

|Сценарий|До|После|
|---|---|---|
|GUI продолжить ветку и сохранить в тот же файл|Родитель теряется|Родитель и ребёнок сохраняются|
|GUI сохранить после измененияdt|Обычный checkpoint теряет историю|Bundlev2 сохраняет обе части|
|gui/inspect/run для корректной ветки|Ошибка формата,exit2|Успех,GUI получает parent_snapshot|
|converge для ветки|Загрузчик отвергаетbundle|Сравнивает ребёнка,вход не меняет|
|run-until для ветки|Результат без родителя|Результат с родителем|
|Радиус1,dt=.1,20шагов до2с,Python/Rust|2.0000000000000004с,повтор цели отвергается|Ровно2с,повтор идемпотентен|
|Контакт сфер на1.95с при цели2с|Корректный фактический контакт|Сохранён,не округлён к цели|

14новых пользовательских сценариев до исправления дали12FAIL/2PASS,
после прошли все14. Сам исходный независимый audit_probe также повторён:
история сохранена,CLIуспешен,обе цели ровно2с; внешний файл evidence
не перезаписывался. Добавлены6проверок архивного происхождения.

## Минимальные изменения

`branch_io.save_experiment` атомарно сохраняет обычный checkpoint, если
родителя нет, или полный bundle, если родитель есть. GUI «Сохранить JSON»,
«Вернуть родителя…»,CLIrun иrun-until используют этот путь. Восстановление
родителя происходит только после успешной записи; отмена/ошибка записи
оставляют текущий опыт. Явный `branch --part child` экспортирует отдельный
checkpoint. Storage.load сохраняет прежний контракт обычного checkpoint;
для обоих форматов предназначен branch_io.open_experiment.

`solar-experiment-branch`v1 остаётся прежним: настройки родителя и ребёнка
одинаковы; прежние guards/checksum/bodychanges проверяются. При разных
текущих Settings ребёнка записываетсяv2 с теми же полными parent/child.
V1 продолжает читаться; старой программеv2 не подходит и она отвергнет его.
SHAродителя неизменен, origin ребёнка остаётсяNone. Ограничения на
prescribedQ2/динамическое вращение и размеры файлов сохранены.
V2 — снимок текущих настроек и состояния, **не журнал всех промежуточных
переключений** и не дерево всех предков.

В бесконтактном проходе Python/Rust завершённый префикс имеет время
completed_steps×dt, как граница, вычисляемая time_control. При контакте
возвращается этот префикс плюс фактическое время внутри шага. Epsilon,
подрезания события до цели или изменения пространственного состояния нет.
Формулы Verlet/сил не изменены; ускорение вычислений не заявляется.

## Почему понадобилось обновить происхождение

Первый полный прогон:1983PASS/4FAIL,безskip. Три отказа обнаружили старый
SHAконтракт sandbox-limits после изменения сериализации, один — требование
старого app.py при проверке уже замороженной JPL440траектории. Это реальные
отказы происхождения, сохранённые в отчёте, а не скрытые успешным повтором.

Для текущего sandbox заново выполнены12прежних независимых сценариев:
изменение массы/скорости,выходная траектория,e=.95,вторая звезда,
удаление главного тела;по6наPython/Rust. Kepler/RK45/инварианты/пороги
прежние. Все научные метрики **точно совпали** с прежним отчётом,кроме
исключённых из сравнения walltimes. [Старыйreceipt](sandbox-limits-before301.json)
сохранён отдельным неизменным файлом;текущийsandbox-limits-validation.json
содержит действительно новые измерения иsourceSHA,не подменённые хеши.

В [SHApinnedархиве](runtime-sources-before301.zip) сохранены8точных старых
исходников. Только verifier замороженной JPLтраектории допускает их
использование длястарого sourcebinding. Архив целиком и каждый entry
должны совпасть сSHA;выход пути заROOT,повреждение архива,неизвестный
source или неверныйdigest отвергаются. Проверка input и опциональная
проверка установленных dependencies остались строгими. Это проверка
**исторически исполненных байтов**,не квалификация нынешнего runtime.

У аудитов273–300 часть широких sourceclosures включает изменённые
contacts/sandbox/assess_nominal_jpl. Их прежние receipts/NPZ не менялись,
старыеsourcebindings разрешаются точными байтами архива. Строгие guards,
сравнивающие их только сliveисходниками,могут справедливо отвергать
повторное использование:для исторического повтора нужен прежний snapshot
или новый научный прогон. Эти результаты не переименованы в новые
измерения с пересобранным native. Новый JPLгод/роторгод не интегрировался.

## Проверки и стоимость

131связанный тест прошёл23.26с;обаcargofmt прошли,19Rustтестов прошли.
Native и standalone release пересобраны из текущих исходников.
Перед каждым полным прогоном обязательны import реального.pyd и
успешный nativeсценарий дробного шага;затемSHAbinary/source до/после.

Повторный полный `scripts/check_project.py`: **1993 passed in 226.97s (0:03:46)**,19Rust/fmt/ссылки прошли;skip0. Wall всего 229.151с.

Это полноценный повтор после сохранённого первогоFAIL,не сумма отдельных
прогонов. Постоянный обязательный nativeрежим checker ещё не добавлен;
в этом прогоне его наличие и исполнение проверены явно.

Свежая публичная копия в пути с пробелами,без старой.tools/личныхdocs:
14пользовательских тестов passed2.32с. Socketсеть запрещена также в
дочерних Pythonпроцессах. Установленные зависимости и.pyd общие,
новая платформа/чистая установка/новыйportable этим не квалифицированы.
Стоимость проверок не является сравнением производительности алгоритмов.

## Что осталось

Пункты4–7 ревью:явный выбор Standard/Strict и реестр областей квалификации;
постоянный обязательный режим проверки native;отмена/сохранение длинных
заданий;согласование основной инструкции установки с проверенными constraints.
Settings рабочего солнечного профиля и научные accuracyflags не изменены.
Физический контракт I/Q2 Луны остаётся исследовательским следующим блоком
после стабилизации. Здесь нет новых приливов,3D,оптимизации или GitHub.

Проверенные участки кода и тестов:

- [branch_io.open_experiment](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/branch_io.py:8)
- [branch_io.parent_experiment](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/branch_io.py:19)
- [branch_io.save_experiment](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/branch_io.py:24)
- [sandbox.to_branch_document](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/sandbox.py:84)
- [sandbox.from_branch_document](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/sandbox.py:111)
- [app.launch](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:806)
- [app.__init__](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:22)
- [app._save](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:318)
- [app._restore_parent](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:599)
- [cli.main](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/cli.py:79)
- [commands.main](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/commands.py:13)
- [contacts.run_until_contact](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/contacts.py:96)
- [assess_nominal_jpl.verify_frozen_sources](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_nominal_jpl.py:34)
- [assess_nominal_jpl.validate_frozen](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_nominal_jpl.py:181)
- [test_review_regressions.branch_file](C:/Users/Admin/Desktop/Solar-simulator/tests/test_review_regressions.py:22)
- [test_review_regressions.test_gui_save_over_original_branch_keeps_parent_after_continuation](C:/Users/Admin/Desktop/Solar-simulator/tests/test_review_regressions.py:30)
- [test_review_regressions.test_legacy_read_only_cli_accepts_branch_and_preserves_file](C:/Users/Admin/Desktop/Solar-simulator/tests/test_review_regressions.py:46)
- [test_review_regressions.test_cli_continues_branch_with_parent_and_explicit_backend_change](C:/Users/Admin/Desktop/Solar-simulator/tests/test_review_regressions.py:56)
- [test_review_regressions.test_gui_cli_passes_parent_snapshot_to_launcher](C:/Users/Admin/Desktop/Solar-simulator/tests/test_review_regressions.py:72)
- [test_review_regressions.test_fractional_step_with_radius_finishes_at_exact_target_and_is_idempotent](C:/Users/Admin/Desktop/Solar-simulator/tests/test_review_regressions.py:82)
- [test_review_regressions.test_fractional_packet_contact_keeps_real_time_before_target](C:/Users/Admin/Desktop/Solar-simulator/tests/test_review_regressions.py:94)
- [test_review_regressions._real_branch_save_and_restore](C:/Users/Admin/Desktop/Solar-simulator/tests/test_review_regressions.py:103)
- [test_review_regressions.test_real_gui_branch_load_continue_save_reopen_restore](C:/Users/Admin/Desktop/Solar-simulator/tests/test_review_regressions.py:122)
- [test_frozen_source_snapshot.setup_snapshot](C:/Users/Admin/Desktop/Solar-simulator/tests/test_frozen_source_snapshot.py:11)
- [test_frozen_source_snapshot.test_exact_archived_source_qualifies_history_while_live_source_is_different](C:/Users/Admin/Desktop/Solar-simulator/tests/test_frozen_source_snapshot.py:20)
- [test_frozen_source_snapshot.test_archival_verification_rejects_corruption_and_unrecorded_sources](C:/Users/Admin/Desktop/Solar-simulator/tests/test_frozen_source_snapshot.py:28)
- [Rust.run_until_contact](C:/Users/Admin/Desktop/Solar-simulator/rust/solar_core/src/contacts.rs:200)


## Дополнительный путь потери родителя, найденный в313

Ранние проверки подтверждали передачу parent_snapshot в launcher и загрузку
ветки в уже созданном GUI. Создание Laboratory сразу с веткой не проверялось
сквозным сценарием: конструктор сбрасывал переданный parent вызовом _set_experiment
без аргумента. Теперь parent передаётся явно; новый тест проверяет конструктор,
завершение пакета и сохранённый bundle. Старые результаты проверок сохранены.
[Управляемая остановка, восстановление и границы](controlled-stop.md).
