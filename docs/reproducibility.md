# Установка без прежнего рабочего кеша

Проверенный профиль: Windowsx64, CPython3.14t, RustGNU,18версий зависимостей
в requirements/validated-windows-cp314t.txt. Это профиль для воспроизведения
измерений, не проверенная матрица всехPython>=3.11/платформ/ABI.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -X utf8 -m pip install -e ".[dev,native]" -c requirements/validated-windows-cp314t.txt
.\.venv\Scripts\python.exe -X utf8 -B scripts/setup_gnu_tools.py
.\.venv\Scripts\python.exe -X utf8 -B scripts/build_native.py
& "$env:USERPROFILE\.cargo\bin\cargo.exe" build --release --manifest-path rust/solar_core/Cargo.toml
.\.venv\Scripts\python.exe -X utf8 -B scripts/check_project.py
```

GNUbootstrap нужен только при отсутствии binutils: загружает официальные
MSYS2пакеты сSHA. Если инструменты уже есть, вместоbootstrap используй
`scripts/build_native.py --gnu-bin C:/path/to/bin` с as.exe/dlltool.exe
и ихDLL. PATH меняется только дочернему процессу; глобальные PATH/реестр
не меняются. Portable включает runtime, Rust нужен для разработки/сборки.
StandaloneRustrelease нужен для4integrationtests; без него они явноskip.

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
