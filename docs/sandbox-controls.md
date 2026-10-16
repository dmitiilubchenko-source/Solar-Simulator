# Команды и сохранённые ветки песочницы

Новые команды работают безGUI. SI и время в секундах от начала опыта:

```powershell
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator solar-sandbox initial.json --backend rust
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator run-until initial.json year.json --time 31557600 --batch 20
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator branch branch.json parent.json --part parent
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator branch branch.json child.json --part child
.\.venv\Scripts\python.exe -X utf8 -B -m solar_simulator export-state year.json positions.csv
```

run-until принимает обычныйcheckpoint или child файлаветки. Сохраняет
Settings, сокращает конечный интервал и показываетrequested_target_seconds
иtarget_reached. Контакт может остановить опыт раньшецели. Размерпакета
не меняет допуски, разныеDOP853разбиения могут давать разныеокругления.
Новыеоперации требуют отдельныйoutput, чтобы сохранялсяисходныйJSON/bundle.
Старыеnew/run/inspect/converge/gui/fit-orbit поддерживаются прежнимCLI.

ВGUI «Вернуть родителя…» доступно после открытияфайлаветки/правки/добавления/
удаления. Сначала сохраняетсяcurrentJSON, затем восстанавливаетсяполный
родитель сего временем/настройками/событиями. Отмена/ошибка записи сохраняет
опыт. Толькоimmediateparent, дерево предков не хранится. ОбычныйcurrentJSON
не содержитродителя; сохраняй исходныйbundle. Послевозврата новаяUIсвязь
с предком очищается. Resetchild сохраняет доступ к родителюветки.

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
