# Установка без прежнего рабочего кеша

Проверенный профиль: Windowsx64, CPython3.14t, RustGNU,18версий зависимостей
в requirements/validated-windows-cp314t.txt. Это профиль для воспроизведения
измерений, не проверенная матрица всехPython>=3.11/платформ/ABI.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -X utf8 -m pip install -e ".[dev,native]" -c requirements/validated-windows-cp314t.txt
.\.venv\Scripts\python.exe -X utf8 -m pip check
.\.venv\Scripts\python.exe -X utf8 -B scripts/setup_gnu_tools.py
.\.venv\Scripts\python.exe -X utf8 -B scripts/build_native.py
& "$env:USERPROFILE\.cargo\bin\cargo.exe" build --release --manifest-path rust/solar_core/Cargo.toml
.\.venv\Scripts\python.exe -X utf8 -B scripts/check_project.py --require-native
```

GNUbootstrap нужен только при отсутствии binutils: загружает официальные
MSYS2пакеты сSHA. Если инструменты уже есть, вместоbootstrap используй
`scripts/build_native.py --gnu-bin C:/path/to/bin` с as.exe/dlltool.exe
и ихDLL. PATH меняется только дочернему процессу; глобальные PATH/реестр
не меняются. Portable включает runtime, Rust нужен для разработки/сборки.
StandaloneRustrelease нужен для4integrationtests; без него они явноskip.
В режиме `--require-native` такие пропуски завершают аудит ошибкой, поэтому
отдельный `cargo build --release` выше необходим. `pip check` проверяет
согласованность установленных зависимостей, а не точность модели. Constraints
закрепляют выбранные версии пакетов, но не Python/Tk, ABI, Rust/toolchain,
изолированные build-зависимости, колёса всех платформ или системные библиотеки.
Это проверенный профиль, не полный hermetic lock и не гарантия битового
совпадения расчётов на любом компьютере. ContinuousRun отдельно требует SciPy1.18.1;
локальный PerBodyDOP853 использует внутренний hook SciPy. Обновление этих
зависимостей требует относящихся численных проверок до обновления профиля.

Pytest sessionsetup проверяет публичный tests/data/research63-inputs.zip
и manifest, восстанавливает только7отсутствующих файлов в.tools. Это
замороженные исследовательские входы, не прежнийprivatecache и не новый
расчёт. ПовреждённоеexistingSHA отклоняется без перезаписи. Ручной вызов:
`python -B -m scripts.prepare_test_inputs`. Старые15тестов/38provenanceSHA
сохранены; физическийPNперенос не сертифицирован.

Чистаякопия: до6failed/15errors/4skip и1303passed; послеpublicinputs и
freshRustrelease1334passed безskip. Freshnative собран изкопии тоже.
Это копия нынешних tracked+untracked исходников, не последний опубликованный
commit: при будущей публикации необходимо включить все публичныефайлы.
Личные документы/готоваяvenv/targets/privatecache не копировались.
Ссылки проверяются поROOT текущейкопии. [Критерии](reproducibility-protocol.md).


## Стабилизация установки и остановки312–314

Основные инструкции теперь используют constraints/pipcheck/native+standalonebuild
и --require-native. Локальные18версий/CPython3.14t/Windowsx64 совпали;
чистая установка снуля повторно не выполнялась, прежние clean-copy измерения — история.
Управляемые GUIstop/close и CLIinterrupt сохраняют завершённое состояние вместе
с parent; ошибка worker пишет копию до уведомления. Исправлен сброс parent в
конструкторе при первоначальном открытии. [Поведение и восстановление](controlled-stop.md).
Полный 2023Python/19Rust/fmt/skip0 PASS, source/data/native frozen.
Численные формулы/пакеты/допуски прежние; новой годовой квалификации/portable нет.


## Быстрая диагностика343

`python -X utf8 -B scripts/check_environment.py` только читает среду: импорты
зависимостей, ABI, Tk, Cargo/native, SHA публичного test-bundle и наличие
контекста. Не устанавливает зависимости, не восстанавливает rawcache и не
запрашивает сеть. --gui требует реальный дисплей; --require-native требует
настоящий PyO3/ballistic probe, Cargo и standalone release; --validated требует
записанный Windows3.14t профиль пакетов. --json даёт структурированный результат.
Отсутствующий личный контекст/Cargo/native без требующего флага — OPTIONAL;
отсутствие обязательных Python-пакетов или публичного bundle — FAIL. Успех
doctor не заменяет научную или portable-приёмку. GUI-child тесты явно используют
UTF-8 у обоих процессов и сохраняют первичную ошибку при пустом stdout/stderr.
