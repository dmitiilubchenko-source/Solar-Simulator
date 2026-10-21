# Исправления по инженерному ревью21октября2026

Работа341–345 вdev; [исходное ревью](reviews/2026-10-21/PROJECT_REVIEW.md)
относится к19ed4a5. Изменены пути интерфейса/диагностики/проверок.
Формулы сил, интеграторы, dt/rtol/atol, эпохи и данные прежние.
Продукт остаётся0.3.0; новый ZIP/новая годовая квалификация здесь не заявлены.

## Результат

- Все6путей замены опыта сначала валидируют кандидата и сохраняют полный
  прежний checkpoint/parent в уникальную recovery. Отказ записи сохраняет
  прежние опыт/графики; cancel/невалидный вход не меняет результат. Копия
  создаётся и приt0; автоматического удаления копий нет.
- GUI-test child и parent явно используют UTF-8; исходная русская ошибка
  видна даже при конфликтующем внешнем cp1251. Пустые pipes не дают TypeError.
- Read-only doctor проверяет доступность компонентов, ABI/пакеты и публичный
  bundle; required/optional различаются. Нет установки/сети/научной сертификации.
- Проверка/подготовка траектории работает вне Tk-потока, отмена между кадрами;
  Tk/Matplotlib в главном. Ошибка не оставляет пустой viewer. Все исходные
  байты записи/parent/времена сохранены; viewer переиспользует artists.
- [Явные группы CI](ci-checks.md), полный --require-native не ослаблен.

## Проверки и измерения

28 GUI/recovery/stop PASS48.94с;9 UTF-8/doctor/workflow PASS15.62с;
40 trajectory/artists PASS133.10с; дополненный reader/close3PASS18.17с.
Во всех перечисленных локальных прогонах0skip. Это относящиеся группы,
их количества нельзя складывать как число уникальных тестов.

[Оба измерения отрисовки со всеми samples](review-followup-cost.json):
120одинаковых синтетических кадров,10/354тела,6повторов×4draw сcanvas.draw.
10тел:0.35547→0.27394с и0.62386→0.48825с;354тела:0.55369→0.47051с и
1.03746→0.67025с. Разброс аппаратной/системной нагрузки существенен.
Это benchmark отображения, не интегрирования или скорости чтения.

Первый [настоящий CI](https://github.com/dmitiilubchenko-source/Solar-Simulator/actions/runs/39623640694)
для9632b37: Linux Python90PASS/2явныхdeselectedRust, Windows native78PASS
безskip, productionRust19PASS/fmt. Research job не запускался автоматически;
локальная explicit adaptive group:45PythonPASS3.27с, Rust default12+1 и
feature12+2,0failed/0ignored. Это unit/контракты, не новый Kepler-аудит.

## Сохранённый отказ полного прогона и исправление

Первый --require-native на9632b37:2221PASS/1FAIL/0skip,1010.14с pytest,
1013.013с весь вызов. ЕдинственныйFAIL: JPL440 требовал старые байты
plot_artists.py. После344 ему недоставало исторической копии; это пропуск
подготовки source snapshot, не новая орбитальная ошибка. Все tracked-байты
во время прогона были неизменны. Первичный отказ сохранён в локальном журнале.

Точные2339байт изdda0238 добавлены в
[snapshot](../scripts/validation/plot_artists_before344.py),
SHA256 7ae14fff4f9a97b6869a921c3c4c97b420c2c2d40efae9e5188be5fdd11d0661
совпадает с исходным frozen annualreceipt. Прежний verifier получил явную
привязку; JSON/NPZ/архивы/пороги не менялись.16относящихся тестов прошли3.32с,
включая порчу snapshot; старая440-эпохальная проверка воспроизводится офлайн.
Эта проверка добавлена и в Python CI. Результат полного строгого повтора приведён ниже.

## Ограничения

Все checkpoint-байты и координаты траектории ещё в памяти; запись индекса
по-прежнему переписывает растущий список. Формат хранения/страничный reader
не изменены. Остановка интегрирования ждёт завершённого пакета. Новый
контроллер/общий рефакторинг, приливы/3D и перенос research-runtime не делались.
Исследовательский Rust DOP853 сохраняет5PASS/4FAIL; Decimal9/9 на уточнённых
сетках не доказывает порядок8 и не квалифицируетruntime.
Последняя принятая portable0.3.0 сохранена; для0.3.1 нужна новая сборка и
реальная приёмка ZIP, затем отдельное согласование main/тегов/релиза.


Дополнительный preflight обнаружил зависимость link-scanner отignoredличного
журнала со ссылкой наприватный repo. Он теперь исключает ровно PRIVATE_DOCS,
как public inventory. Обычные публичные outside/unknown ссылки всё ещё
отклоняются.30проверок sourcebinding/link/native-policy PASS8.50с; публичных
file/line links1387. Начавшийся повтор был остановлен до этого исправления
и не выдаётся за полную приёмку. Результат нового полного строгого прогона приведён ниже.


## Итоговая проверка исходников и переносимости

Полный `check_project.py --require-native` на5c725b0 завершён:2224PythonPASS
1060.35с,0skip;19RustPASS, оба production fmt PASS;1387publiclinks и988inventory.
Весь вызов1066.954с. Все tracked-байты до/после совпали. Формулы/данные/
solver/time-control сверены побайтно с19ed4a5; принятыйZIP0.3.0 SHA прежний.

Расширенный [Linux CI5c725b0](https://github.com/dmitiilubchenko-source/Solar-Simulator/actions/runs/39627457821)
выявил2FAIL/105PASS/2deselected: Windows-пути frozenreceipt обрабатывались
нативным Path.name и вPOSIX давали KeyError annual.json. Ошибка воспроизведена
наWindows заменой только Path наPurePosixPath. Исправлена нормализацией
разделителей при выделении имени; исходные receipt/JSON/NPZ/SHA неизменны.
Все9массивов/receipt до/после наWindows иPOSIX rules совпали побайтно.

После этого изолированного инфраструктурного исправления:31относящийся
тест sourcebinding/link/native-policy PASS6.50с,0skip; новый regression
сPOSIX rules добавлен вPython CI. Полный17-минутный Windows-прогон после
однострочной нормализации повторно не запускался: runtime/численные
модули не изменились, проверены сам parser и байты всех9выходныхмассивов.
Python CI теперь также запускает общую проверку публичных file/line ссылок.
Актуальные результаты последнего dev-коммита: [CI](https://github.com/dmitiilubchenko-source/Solar-Simulator/actions?query=branch%3Adev).

Готовность: исправления исходников проверены в указанном объёме. Для нового
выпуска0.3.1 ещё нужны версия-кандидат, новый portableZIP и его приёмка.
Публикация вmain/новые теги/релизы не выполнялись.

[safe transition](../src/solar_simulator/app.py:806).

[background reader](../src/solar_simulator/trajectory_loader.py:17).

[Tk loader](../src/solar_simulator/trajectory_loader.py:30).

[environment preflight](../scripts/check_environment.py:17).

[real recovery regression](../tests/test_experiment_transition_gui.py:95).

[reader/close regression](../tests/test_trajectory_loading.py:87).
