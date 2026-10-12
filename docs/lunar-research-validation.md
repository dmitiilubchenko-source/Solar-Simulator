# Сквозной аудит лунного research-расчёта

Изменение71, 11 октября2026. [Машинный отчёт](lunar-research-validation.json),
[предварительная политика](../scripts/lunar-research-policy.json),
[API/команда](lunar-research.md), [квалификация источника](lunar-source-qualification.md).
Все численные критерии и девять подтверждений прошли. Это подтверждение
вычисления заданного H57; физическая точность относительно DE441 не заявляется.

## Что проверено

Весь путь от pinned x/v/R/Rdot через совместную p/S-инверсию и Earth–Moon
Jacobi до файла, загрузки, эволюции, restart в отдельном процессе и dx/dt-export.
Все десять тел,32суток,129эпох. Newton rotor/Q2 + ADM point1PN/LOSO,
одна жёсткая Луна и нулевые pointspins остальных тел. Новые p/S не подбирались
по будущей траектории. Futureephemerides/orientation не читались.

Production per-blockDOP853 rtol1e-11; tighter3e-13,atol×0.03 и max_step10800с.
Независимый scalarEIH/Jacobi complex-step и rawmatrix/bodyEuler RK45,
rtol3e-13/3e-14, max_step21600с. Все траектории рассчитаны заново, без кеша.
Productioninitial оказался побитово тем же, что ранее закреплённый59;
гипотеза возможного различия ULP здесь не подтвердилась. Это не новая физика.
Исходники/входы/политика/тесты29файлов закреплены SHA доjobs и сверены после.
NPZ и checkpoint hashes записаны в отчёт; raw q/S и прямая относительная
координата не нормировались и не пересоздавались при продолжении.

| Величина | Измерение | Предварительный предел |
|---|---:|---:|
| Относительный дрейф H |2.052e-15|1e-9|
| Масштабированный дрейф P |2.115e-16|1e-10|
| Относительный дрейф J |6.134e-16|1e-9|
| Дрейф нормы q |4.441e-16|1e-9|
| Agreement всех тел, максимум |10.791мм|1м|
| Agreement Earth–Moon |0.252мм|1м|
| Разность уровней эталона, все тела |9.581мм|1м|
| Разность уровней эталона, Earth–Moon |2.090мм|1м|
| Чувствительность tighter, все тела |2.191мм|1м|
| Чувствительность tighter, Earth–Moon |0.0879мм|1м|
| Restart, все тела |0.0940мм|1м|
| Restart, Earth–Moon |0.0219мм|1м|
| Agreement S/исходный масштаб |1.414e-15|1e-8|
| Agreement R, норма Фробениуса |1.073e-13|1e-8|
| Независимый H, относительная разность |7.242e-16|1e-12|
| Независимые v/W, масштабированная разность |5.103e-16/3.987e-16|1e-12|

H/v/W независимо проверены на девяти выбранных заранее эпохах, не непрерывно
во времени. Контроль ошибочного p=m v дал7.477e-8 по v, NewtonS=I W
дал1.245e-9 по W; оба больше заданного1e-10. Значит новый путь чувствителен
к этим неправильным подменам и использует полные производные H.
Orthogonality/det независимого rawR:2.172e-12/1.534e-12 <1e-8.
Покомпонентные максимумы для каждого из10тел и все критерии S/R для
tighter/referenceuncertainty/restart сохранены в JSON, тела не исключались.

Два уровня эталона расходятся больше agreement Earth–Moon. Это эмпирическая
чувствительность эталона, не доказанный интервал истинной ошибки. Сохранение
H/P/J не доказывает истинность модели Луны. Годовой остаток121.84″ остаётся
необъяснённым; физический harmonic/ADM/SSC/tetrad/PN-I перенос не квалифицирован.
Кольцо Койпера здесь отсутствует; прежняя проблема KBO/SB441 не решена этим аудитом.

## Найденная ошибка provenance и непринятый прогон

В ручной CODE_SOURCES68 пропущен импортируемый spin_initial.py. Старый
тест подменял результат code_hashes и проверял вызов guard, но не проверял
покрытие конкретного импортируемого файла. При уже загруженной функции
его diskedit не менял вычисленный initial; guard/checksum его не замечали.
Причина воспроизведена на изолированной копии старого кода.

Первый прогон71 остановлен после production34.30s,tighter60.74s и
reference0 72.81s, во время reference1. Он не принят. NPZ, старые исполняемые
исходники и failure.json оставлены в `.tools/rotation71-incomplete-source-closure`.
Процесс остановлен перед правкой: выполняемые исходники не редактировались.

[Исправленный manifest](C:/Users/Admin/Desktop/Solar-simulator/scripts/lunar_initial_receipt.py:21)
включает loader. Тест в изолированной копии действительно меняет diskfile:
новый receipt/evolve отвергает изменение до initialization/integration.
Старый strictreceipt явно отвергается даже с пересчитанным checksum;
автоматической миграции нет, исходные файлы сохранены. Формулы, pinneddata,
численные критерии и initialstate не менялись. После этого выполнен полностью
свежий принятый аудит в `.tools/rotation71`, оба независимых эталона завершены.

## Код и воспроизведение

- [Строгая оценка всех критериев](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_research.py:34),
  [независимые v/W](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_research.py:47),
  [неправильные p/S controls](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_research.py:56),
  [полный аудит](C:/Users/Admin/Desktop/Solar-simulator/scripts/assess_lunar_research.py:73).
- [Каждый непройденный критерий](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research_audit.py:21),
  [запрет скрытых/пропущенных метрик](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research_audit.py:32),
  [actualboundary независимые derivatives](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research_audit.py:42),
  [real diskmutation](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research_audit.py:56),
  [oldreceipt rejection](C:/Users/Admin/Desktop/Solar-simulator/tests/test_lunar_research_audit.py:76).

12новых audit/sourceguardchecks; вместе с22новыми70 и48прежними —
82relatedpassed17.87s. Для нового полного исследования используйте
`audit(output=NEW_REPORT,work=NEW_DIRECTORY)` из scripts.assess_lunar_research;
оба пути внутри проекта, существующие пути отклоняются. Исходники во время
jobs сохраняйте неизменными. Стандартная команда повторно не перезаписывает
закреплённый отчёт: `.venv/Scripts/python.exe -X utf8 -B scripts/assess_lunar_research.py`.

Полный scripts/check_project.py после аудита:933Python passed402.57s,
17Rust passed, fmt обоих crates;1010file/line links на момент проверки.
Старые127JSON/74runtime-Rust файла и все304прежние statusentries сохранены;
в старом sourcecode изменена только одна строка receiptmanifest, с сохранённой
копией до правки.34новых теста70–71 включены в полный набор,82related —
его поднабор. После закрытия журнала ссылки и provenance сверяются ещё раз.
Commit/push/portable не выполнялись.
