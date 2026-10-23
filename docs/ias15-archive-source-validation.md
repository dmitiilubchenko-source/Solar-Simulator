# Полный snapshot IAS15: исходники допускают отдельную проверку

23 октября 2026, этап362. **Можно переходить к ограниченному pilot, но
корректность численного продолжения ещё не доказана.** Рабочий DOP853 Solar,
выпуск0.3.1, силы, данные и допуски не изменялись.

[Машиночитаемый аудит, SHA и строки первоисточников](ias15-archive-source-validation.json),
[протокол следующего опыта](ias15-full-state-protocol.md).

## Что установлено по первичным исходникам

Проверен закреплённый sdist REBOUND5.2.2 с прежним SHA, девять файлов.
Все18 полей структуры IAS15 учтены: 17 имеют дескрипторы сериализации,
одна длина allocation выводится читателем из размера данных.

| Состояние | Что делает archive writer/reader |
|---|---|
| epsilon, min_dt, adaptive_mode, iterations_max_exceeded | Сохраняет четыре скаляра |
| at, x0, v0, a0, csx, csv, csa0 | Сохраняет семь массивов длины N_allocated |
| g, b, csb, e, br, er | Сохраняет шесть массивов длины 7×N_allocated |
| N_allocated | Восстанавливает из field.size_data/element_size |
| t, G, dt, dt_last_done, steps_done, particles, model flags | Отдельные глобальные дескрипторы |
| Python callback, его счётчик/исключение и Solar origin | Требуют явной повторной привязки/sidecar |

Основания: [структура](https://github.com/hannorein/rebound/blob/5.2.2/src/integrator_ias15.h#L27),
[дескрипторы](https://github.com/hannorein/rebound/blob/5.2.2/src/integrator_ias15.c#L79),
[writer/reader](https://github.com/hannorein/rebound/blob/5.2.2/src/binarydata.c#L627).
Проверена запись содержимого массивов, а не их адресов. Выделение памяти
происходит при чтении. Для этих буферов получается49×N_allocated double;
при N_allocated=3N и восьмибайтовом double это1176N байт. Это вывод о составе данных, не измеренный размер файла.

Physical JSON и один dt из353/355 не содержат этого полного состояния.
Однако аудит не отделяет влияние каждого пропущенного буфера и не доказывает
причину пяти старых отказов. Они остаются FAIL в прежних отчётах.

## Выбор пути чтения и реальные ограничения

`Simulation.__reduce__` экспортирует binary stream через ту же C-функцию,
которую использует первый `save_to_file`. Конструктор `Simulation(bytes)`
создаёт объект без запроса на движение вперёд. Существующий файл, напротив,
дополняется snapshot/delta цепочкой; будущий pilot ограничен свежими файлами.
`getSimulation(close/exact)` может сам интегрировать, а snapshot-режим
вызывает synchronize. Поэтому он не выбран для проверки неизменённого состояния.
[Python API](https://github.com/hannorein/rebound/blob/5.2.2/rebound/simulation.py#L269),
[archive API](https://github.com/hannorein/rebound/blob/5.2.2/rebound/simulationarchive.py#L179).

Reader способен предупреждать о повреждении и частично прочитать архив.
Сверка версии в C игнорирует git hash. Совпадение номера не заменяет SHA
библиотеки, ABI, предварительную проверку структуры и model/physical sidecar.
Никаких переносимых между платформами snapshot этим не квалифицировано.
Python-конструктор показывает цепочку чтения, но не является готовым строгим
loader: для полного raw warning mask в pilot требуется исследовательская
обёртка C API with_messages. Её реализация и владение памятью ещё не проверены.

Найдены две границы предупреждений: Python-таблица не содержит объявленный
в C bit2048 CUSTOM_INTEGRATOR; это не наблюдавшийся отказ IAS15. Общий
POINTERS flag покрывает шесть hooks, включая additional_forces, но не
pre_timestep_modifications. Отсутствие предупреждения не доказывает отсутствие
всех callbacks. До экспорта неподдерживаемые hooks должны быть отклонены.
Для будущего native загрузка допустима только с проверенной привязкой силы
до integrate; предупреждения нельзя подавлять.
[C warning flags](https://github.com/hannorein/rebound/blob/5.2.2/src/binarydata.h#L30),
[проверка function pointers](https://github.com/hannorein/rebound/blob/5.2.2/src/binarydata.c#L653).

## Привязка к установленной исследовательской библиотеке

Все68 файлов её прежнего raw SHA-инвентаря359 совпали. Первое побайтное
сравнение Python wrappers со sdist далоFalse: установленный Windows wheel
использует CRLF. После явной нормализации только для сравнения оба файла,
simulation.py и simulationarchive.py, совпали целиком; AST тоже совпадают.
simulation.py уже имел такую оговорку в352, теперь проверен второй wrapper.
Оригинальные файлы и старые SHA не переписывались. Бинарная эквивалентность
компиляции sdist установленному shared library не утверждается.

## Проверки и воспроизведение

Аудитор использует стандартную библиотеку Python: проверяет SHA до чтения tar,
принимает только единственные regular members и ничего не извлекает/исполняет.
Это узкий анализ закреплённого C-формата, а не универсальный C-parser.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.audit_ias15_archive_source --source .tools/ias15165/rebound-5.2.2.tar.gz --output fresh-audit.json
```

Output должен отсутствовать. Сравниваются поля и source SHA; elapsed_seconds
ожидаемо меняется. Расширенный публичный JSON содержит также проверку wheel,
ограничения и результаты тестов. Файл sdist является отдельно закреплённым
источником; встроенного скачивания/установки/сети нет. Чужие C-исходники
не добавлены в Solar или portable; лицензия/adoption остаются отдельным решением.

Первый запуск: 14PASS/1FAIL2.05с и SyntaxWarning. Parser не распознавал
вложенный member integrator.name; исправлены грамматика member и raw regex
строка. Первый source run отказал на отсутствии обязательного глобального
поля. Оба лога/старый helper сохранены, критерии не ослаблялись.
Затем15 новых тестов PASS6.20с; расширенный набор33PASS43.20с/0skip,
включая прежние offline replays353/355/356. Исходный python CI subset:
116PASS16.89с,2 намеренно deselected Rust cases; это не полный native-аудит.
Source audit занял около0.043с, без интегрирования. Оптимизация не выполнялась.
Финальный python CI subset:132PASS9.20с,2 намеренно deselected Rust cases;
включены16 новых тестов с проверкой SHA аудитора/теста/протокола.
Это проверка source/helper, не повтор полной native-приёмки0.3.1.

Результат362 — подтверждённая возможность **поставить следующий опыт**.
Ни binary restore, ни девять орбит, ни native restart этим не приняты.
Следующий шаг — pilot363 по зафиксированному протоколу; все неуспехи сохранять.

[Аудитор](C:/Users/Admin/Desktop/Solar-simulator/scripts/audit_ias15_archive_source.py:86),
[структурные проверки](C:/Users/Admin/Desktop/Solar-simulator/tests/test_ias15_archive_source.py:40).
