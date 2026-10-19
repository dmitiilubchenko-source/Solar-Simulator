# Команды и сохранённые ветки песочницы

[Стоп и копия, закрытие GUI и Ctrl+C в run-until](controlled-stop.md)
сохраняют последний завершённый пакет отдельно от исходного опыта.

Новые команды работают безGUI. SI и время в секундах от начала опыта:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator solar-sandbox initial.json --profile strict --backend rust
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator run-until initial.json year.json --time 31557600 --batch 20
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator branch branch.json parent.json --part parent
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator branch branch.json child.json --part child
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator export-state year.json positions.csv
```

`--profile strict` выбирает настройки закреплённого строгого старта;
без флага сохраняется прежний Standard. Это не универсальная точность
любых систем. [Выбор профиля и границы проверки](profile-selection.md).

run-until принимает обычныйcheckpoint или child файлаветки. Для ветки
сохраняет также неизменного непосредственного родителя. Сохраняет
Settings, сокращает конечный интервал и показываетrequested_target_seconds
иtarget_reached. Контакт может остановить опыт раньшецели. Размерпакета
не меняет допуски, разныеDOP853разбиения могут давать разныеокругления.
Новыеоперации требуют отдельныйoutput, чтобы сохранялсяисходныйJSON/bundle.
`gui/inspect/run/converge` также принимают ветку. `run` сохраняет её родителя,
включая смену backend. `branch --part child` явно экспортирует только ребёнка.

ВGUI «Вернуть родителя…» доступно после открытияфайлаветки/правки/добавления/
удаления. Сначала сохраняетсяcurrentJSON, затем восстанавливаетсяполный
родитель сего временем/настройками/событиями. Отмена/ошибка записи сохраняет
опыт. Толькоimmediateparent, дерево предков не хранится. Сохранённая текущая
ветка также содержит родителя, в том числе при перезаписи файла. Послевозврата UIсвязь
с предком очищается. Resetchild сохраняет доступ к родителюветки.

Если Settings ребёнка изменились, bundle сохраняется какv2; прежниеv1
читаются. Старой программеv2 не подходит. [Совместимость и проверки](runtime-stabilization.md).

«Удалить тело…» сохраняетparent+child и открываетновыйстартt0. Последнее
тело, источникфигуры или обязательнойпары нельзя удалить при техжеSettings.
Выбери другой подходящийопыт или явно измени модель наt0; фигуры/пары
не отключаютсяавтоматически. Длядинамического/prescribedвращения редактор
по-прежнему недоступен. УдалениеСолнца вpointNewtonсистеме оставляет
движение прежнихтел поуравнениям; однаоставшаясяпланета движетсясвободно.

CSV содержит текущийорбитальныйсрез r/v/mass/radius, frame/center/time_scale,
epoch, полныеSettings иcanonicalcheckpointSHA. float64вывод roundtrip;
Unicode/кавычки/запятые сохраняются. Длявозобновления сохраняйJSON: spin/q,
события/история остаютсявнём. CSVэкспорт не рассчитываетновуюорбиту.
Дляпользовательскихначальныхусловий center/frame отмеченыкакзаданныепользователем,
календарнаяэпоха пустая; данныеJPL сохраняют настоящийEclipticJ2000/SSB/TDB.

Новые функции не расширяют [область физической точности](sandbox-demo-validation.md).
[Воспроизводимая установка](reproducibility.md), [демонстрация](sandbox-demo.md).
