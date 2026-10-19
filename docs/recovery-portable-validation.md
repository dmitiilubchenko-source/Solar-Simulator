# Восстановление готового результата и подготовка portable

Изменение315, 19 октября2026. Физические модели, начальные данные,
допуски и границы пакетов не меняются. Новый контракт — в
[описании остановки](controlled-stop.md).

## Воспроизведённые отказы и причины

`run-until` защищал только цикл расчёта; успешное завершение solver не
защищало последующую финальную запись. Отсутствующий каталог назначения
давал ошибку без результата и recovery. Защита теперь охватывает также
report и финальный save; сохраняется последнее завершённое состояние,
включая достигнутую цель и неизменённого непосредственного родителя.
При отказе recovery рядом с output используется локальный каталог GUI.
При двойном отказе команда явно сообщает обе ошибки и не заявляет успех.

Реальная подготовка документов выявила8 битых относительных ссылок:

- USER-GUIDE: controlled-stop, runtime-stabilization, reproducibility,
  profile-selection ссылались на корень вместо docs/.
- Не копировались de441-reader-inputs.zip, nominal-jpl440-inputs.zip,
  runtime-sources-before301.zip и tests/data/jpl-verification.zip.

Причина — ручной список замен путей и отсутствие ZIP в замыкании документов.
Экспорт руководства теперь переносит все относительные ссылки, включая
фрагменты; копирование ZIP разрешено только для четырёх публичных архивов.
Оригинальные байты архивов сохраняются. Личные документы и кеши исключены.
Общая prepare_documents используется сборкой и тестом подготовки;
check_portable проверяет ссылки именно распакованного ZIP до запуска runtime.
ERFA-лицензия в runtime поставляется wheel, а не этапом документов.

## Проверки

До исправления8 новых тестов завершились отказом за10.00с. Первый пробный
прогон остановился на неперехваченном тестом KeyboardInterrupt после2FAIL;
перехват в регрессии добавлен, все8 отказов воспроизведены отдельно.
После исправления20PASS17.67с и расширенный набор56PASS26.42с.

Проверяются отсутствующий каталог, отказ доступа, прерывание финальной записи,
fallback и двойной отказ; input/прежний output не повреждаются. Два отдельных
GUI-процесса проверяют сохранение, закрытие, новый запуск, выбор копии,
продолжение и повторное сохранение на Python/Rust с DOP853. Child, parent,
settings и продолжение сравниваются с тем же исходным опытом без прерывания.
Повреждённая копия остаётся видимой, её открытие не заменяет текущий опыт.

Это регрессии хранения и управления: совпадение продолжения не является
независимой квалификацией физической точности. Полный аудит и результаты
приёмки конкретного ZIP добавляются после фактического завершения.

## Ограничения

Список GUI охватывает локальный каталог приложения; CLI-копии рядом с output
открываются через «Открыть JSON». Поиск по дискам и автоматическая очистка
не выполняются. Список читает пути/mtime, а не все сохранённые состояния.
Открытие копии заменяет текущий опыт; перед этим его нужно сохранить.
Нет гарантии записи при отказе всех дисков, kill или потере питания.
Текущий пакет по-прежнему завершается до остановки; batch не стал скоростью
независимого воспроизведения. Эта задача следующая, отдельная от данного исправления.


## Полный аудит315

Режим --require-native, без пропусков; source/data/native SHA до/после совпали.
Общая длительность 321.97с; это стоимость проверки, не benchmark ускорения.

- Project inventory valid: 889 files
- 2035 passed in 317.25s (0:05:17)
- test result: ok. 19 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- Documentation file/line links valid: 2884

Подготовка документов:552 относительные ссылки,0битых;306файлов в публичном
замыкании,4архива byte-exact. Настоящий ZIP требует отдельной приёмки после сборки.


## Код и регрессии (проверенные определения)

- [commands.py:main](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/commands.py:13)
- [commands.py:_run_until](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/commands.py:123)
- [recovery.py:save_recovery](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/recovery.py:10)
- [recovery.py:recovery_directory](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/recovery.py:22)
- [recovery.py:list_recoveries](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/recovery.py:27)
- [app.py:_restore_recovery](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:731)
- [app.py:_show_recoveries](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/app.py:780)
- [build_portable.py:build](C:/Users/Admin/Desktop/Solar-simulator/scripts/build_portable.py:116)
- [build_portable.py:prepare_documents](C:/Users/Admin/Desktop/Solar-simulator/scripts/build_portable.py:296)
- [build_portable.py:copy_public_rotation_documents](C:/Users/Admin/Desktop/Solar-simulator/scripts/build_portable.py:356)
- [build_portable.py:export_guide](C:/Users/Admin/Desktop/Solar-simulator/scripts/build_portable.py:399)
- [check_portable.py:check_recovery](C:/Users/Admin/Desktop/Solar-simulator/scripts/check_portable.py:228)
- [check_portable.py:check_document_links](C:/Users/Admin/Desktop/Solar-simulator/scripts/check_portable.py:331)
- [test_recovery_journey.py:test_final_output_failure_recovers_finished_result](C:/Users/Admin/Desktop/Solar-simulator/tests/test_recovery_journey.py:23)
- [test_recovery_journey.py:test_final_output_recovery_falls_back_to_local_data](C:/Users/Admin/Desktop/Solar-simulator/tests/test_recovery_journey.py:55)
- [test_recovery_journey.py:test_final_output_and_both_recoveries_fail_explicitly](C:/Users/Admin/Desktop/Solar-simulator/tests/test_recovery_journey.py:73)
- [test_recovery_journey.py:test_recovery_inventory_is_local_and_keeps_damaged_files_visible](C:/Users/Admin/Desktop/Solar-simulator/tests/test_recovery_journey.py:88)
- [test_recovery_journey.py:test_save_close_restart_restore_continue](C:/Users/Admin/Desktop/Solar-simulator/tests/test_recovery_journey.py:154)
- [test_portable_rotation_documents.py:test_actual_prepared_portable_has_complete_relative_document_links](C:/Users/Admin/Desktop/Solar-simulator/tests/test_portable_rotation_documents.py:51)
- [test_portable_rotation_documents.py:test_exported_guide_rebases_new_links_and_keeps_anchors](C:/Users/Admin/Desktop/Solar-simulator/tests/test_portable_rotation_documents.py:69)
- [test_portable_rotation_documents.py:test_packaged_document_validator_rejects_missing_and_escaping_targets](C:/Users/Admin/Desktop/Solar-simulator/tests/test_portable_rotation_documents.py:77)
- [test_portable_rotation_documents.py:test_unlisted_archives_cannot_join_public_closure](C:/Users/Admin/Desktop/Solar-simulator/tests/test_portable_rotation_documents.py:85)


### Первый отказ приёмки ZIP и исправление стенда

Первый настоящий check_portable завершился отказом за85.82с: старый стенд
сравнивал GUI Strict по умолчанию с готовым Standard. Теперь Standard выбирается
явно, default Strict и его открытие кнопкой проверяются отдельно. Второй пробный
запуск выявил попытку чтения сохранённого bundle обычным storage.load после
возврата родителя. Проверка переведена на load_branch и усилена сравнением parent.
При чтении обнаружен также устаревший импорт application.save: используется
действующий save_experiment с parent. Физическое ядро и runtime не менялись.

Оба исходных отказа сохранены локально; они не объявлены успешной приёмкой.
Исправленные GUI/recovery пробы в изолированной распаковке прошли за19.29с:
Python и Rust сохранили parent и дали точное продолжение; финальная запись CLI
в отсутствующий/недоступный каталог дала корректную recovery/fallback.
Далее полный frozen аудит текущего стенда и новый полный запуск на чистой
распаковке того же неизменённого ZIP. До успеха LATEST оставлен прежним.


## Итог315: проверенная локальная portable

Повторный полный аудит после исправления приёмочного стенда: --require-native,
без пропусков, source/data/native SHA совпали; 313.96с.
- Project inventory valid: 889 files
- 2035 passed in 309.74s (0:05:09)
- test result: ok. 19 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
- Documentation file/line links valid: 2906

Проверен настоящий ZIP `SolarSimulator-0.2.0-20261019-010144.zip` (112,274,993байт).
SHA-256: `25c60fe67b846a35965b7a35a618402ee63b1c531f2684b56eadd848ee14a4d0`.
Сборка 42.36с, полный check_portable
87.36с. Чистая распаковка с пробелами и
изолированным runtime/LOCALAPPDATA: `C:\Users\Admin\Desktop\Solar-simulator\.tools\portable relocated 20261019-011136\SolarSimulator-0.2.0-20261019-010144`.
Относительные ссылки в реальной поставке: 562, битых0.
Все 70 файлов Python-пакета и данных совпали
с текущими исходниками побайтно; четыре публичных ZIP также exact.
Личные документы исключены, включая содержимое четырёх вложенных архивов.

GUI, цикл save→close→новый процесс→выбор recovery→continue→save и parent
проверены на Python/Rust. Финальная запись CLI и fallback проверены настоящими
отсутствующим/недоступным каталогами, а не только mock. JPL replay прошёл
без solver; отдельный новый годовой расчёт Strict прошёл с solver.
Continuous воспроизвёл прежние контрольные данные, но general_release_passed
остаётся false: его общий научный критерий не объявляется пройденным.
Это воспроизведение прежних профилей/сеток, не новая универсальная точность.

LATEST обновлён только после этих проверок и SHA. Прежняя сборка155 и её ZIP/SHA
сохранены. Публикации GitHub/коммитов нет. Исходные отказы не удалены.
Дальше — отдельный этап независимого воспроизведения траектории; затем общая
сетка parent/child, удобные единицы и рецепт повторения. Не расширять сейчас
состав тел/вращение/приливы/Rust под видом завершения интерфейсного цикла.

Исправленный приёмочный стенд: [check_gui](C:/Users/Admin/Desktop/Solar-simulator/scripts/check_portable.py:348).


### Измерения годового повторения из ZIP (отдельная сетка125эпох)

Свободный расчёт10тел на31557600с: 125эпох, 499пакетов,
batch20/dt3600с, ядроRust, DOP853/EIH1PN+fixedSun/EarthJ2, Strict3e-14 и прежние
позиционный/скоростной допуски. SI/SSB/EclipticJ2000/TDB/DE441; исходники
научных модулей проверены по прежним SHA, первичные ответы и сетка — replay.
Наибольший позиционный остаток к JPL: **747.755283м (Moon)**;
Moon−Earth: **718.824785м**.
Заданные ранее10км/тело и1км/пара пройдены на этих эпохах.
Отличие от сохранённой Strict-траектории в данном окружении:0м и0м/с.
Сам solver-цикл занял 7.896с; полный приёмочный процесс
включал другие сценарии и занял87.36с. Это не benchmark оптимизации.

[Метод recompute](C:/Users/Admin/Desktop/Solar-simulator/scripts/recompute_jpl.py:13)
использует прежние входы/пакеты/критерии. Это воспроизведение production,
а не новый независимый интегратор; независимая RK45-проверка относится к
предыдущему аудиту141. Эта сетка125эпох отличается от исторической440 и границами пакетов:
максимумы747.76/718.82м нельзя выдавать за улучшение прежних772.16/725.57м.
Ни междуэпоховая гарантия, ни неопределённость наблюдений, ни квалификация
изменённых пользователем систем из этих чисел не следуют. Смешанные PN–figure
члены и приливы остаются вне данной модели; общий критерий continuous false.
