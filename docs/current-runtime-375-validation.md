# Текущая научная квалификация 375

26 октября 2026. [Протокол до новых результатов](current-runtime-375-protocol.md),
[точные настройки и SHA входов](../scripts/current-runtime-375-protocol.json),
[машиночитаемый результат](current-runtime-375-validation.json),
[фактические массивы](../scripts/validation/current-runtime-375.npz).

Научные критерии пройдены. Проверено существующее вычислительное ядро
commit499b27b; отдельно исполнялись точные исходники принятой 0.3.2 cf653c9.
После измерений меняется только проверка доказательств и тесты. Формулы,
интеграторы, физические коэффициенты, старые данные и отчёты не менялись.
Результат относится к зафиксированному desktop-окружению; это не новый выпуск.

## Профиль и выполненные расчёты

10 тел DE441, Sun/8планет/Moon; внешние планеты представлены барицентрами
систем. SI, SSB/Ecliptic J2000, JD2461321.5 TDB; 31557600 с.
Newton + point-mass EIH1PN + фиксированные J2 Sun/Earth с обратными силами.
SciPy DOP853/per-body, Earth–Moon relative variables, rtol3e-14,
atol1e-3 м/1e-9 м/с; dt3600 с. Strict20:125 эпох,499 фактических пакетов.
Контроль Strict10:948 пакетов на тех же эпохах; holdout:9 эпох/43 пакета.
Все границы пакетов записаны, настройки/порядок/начало проверены точно.

Фактически выполнены шесть годовых текущих runs (Python/Rust × Strict20,
Standard20, Strict10), два годовых accepted032, четыре holdout runs
(два текущих и два accepted032), четыре свежих независимых RK45-интегрирования
(два уровня × год/holdout), 24 sandbox-case (12 текущих +12 accepted032).
Для обоих текущих Strict20 выполнен также файловый restart в середине года
с продолжением по тем же пакетам. Его состояния и канонические документы
совпали с непрерывным исходным расчётом точно. Для всех sandbox-case проверены
file branch roundtrip, save/load/continue и сохранность родителя.

Rust исполнял настоящий solar_native0.3.2, pyd SHA
0cbc389f139854628f287c04a7cea52c530a18294c2c3a0670faa48bf53c0601,
совпадающий с принятым 0.3.2. Для Rust Strict20 зарегистрировано103344
force calls (включая повторный suffix), Strict10 94908, holdout4763.
Python-варианты не вызывали production-native force. Переключения backend
или fallback не было.

## Независимая численная проверка

Эталон рассчитан заново: RK45, AU/year, interleaved EMB + Moon−Earth,
независимая scalar EIH реализация и body-axis J2 вместо runtime tensor force.
Скалярный Rust oracle собран в новом каталоге, а не взят из старого DLL-cache:
rustc1.99.0, sourceSHA47ffd86634e23c9b76f8a9f9b39da39136c9f10e70a7a331410e4ef2415073ca,
binarySHA600b919e42e48bfad76671ecdbdf65514fbf6b71e71924f15fbd4980a7e12921.
Уровни rtol1e-13/max_step1800 с и3e-14/900 с, atol1e-17.

Разница двух годовых reference уровней:0.098722587 м/тело и0.003040421 м
Moon−Earth; holdout:0.008813202 м/тело и0.000034120 м Moon−Earth.
Прежние reference-критерии <1 м/тело и <0.1 м относительной Луны пройдены.
Сходимость — оценка чувствительности, а не строгая математическая граница.
Свежие массивы обоих уровней также совпали с исходными reference139/141
побитно; это дополнительное свидетельство, а не замена свежего расчёта.

Максимальное согласие Strict20 с независимым reference и остатки к JPL, метры:

| Тело | Численное Python | Численное Rust | JPL Python | JPL Rust |
|---|---:|---:|---:|---:|
| Sun | 0.000004 | 0.000007 | 218.805 | 218.805 |
| Mercury | 0.026545 | 0.037174 | 207.701 | 207.691 |
| Venus | 0.028273 | 0.024215 | 257.470 | 257.468 |
| Earth | 0.013440 | 0.011098 | 174.549 | 174.550 |
| Moon | 0.060651 | 0.045023 | 747.744 | 747.755 |
| Mars | 0.025980 | 0.025325 | 571.340 | 571.341 |
| Jupiter | 0.009423 | 0.009710 | 273.267 | 273.266 |
| Saturn | 0.018997 | 0.023256 | 31.081 | 31.080 |
| Uranus | 0.062183 | 0.062890 | 17.167 | 17.165 |
| Neptune | 0.021534 | 0.028425 | 64.722 | 64.701 |

Moon−Earth: численное Python0.058164202 м/1.40729e-7 м/с,
Rust0.043817848 м/1.04181e-7 м/с; holdout Python0.000512919 м,
Rust0.000736911 м. Критерии прежние:<10 м/<1e-4 м/с для каждого тела,
<0.1 м/<1e-5 м/с для Moon−Earth. Пройдены также Strict10 и оба holdout.
Энергетический остаток Strict20 Python2.81268e-14/Rust2.51465e-14 при
пороге1e-10. Использован усечённый Noether EIH + Newtonian figure potential;
полный орбитальный L при двух фиксированных осях не является инвариантом.

Чувствительность20→10 пакетов: максимум по телам0.441444 м Python/
0.481479 м Rust, Moon−Earth0.094947688/0.073521857 м. Прежние
границы <10 м/тело и <0.1 м Moon−Earth пройдены. Python имеет небольшой
запас до порога; на другие разбиения пакетов это не переносится.
Чувствительность rtol1e-13→3e-14: Moon−Earth0.060533/0.069544 м.

Исходный Standard Rust numerical FAIL воспроизвёлся на нынешнем runtime:
0.113352679 м >0.1 м. Standard Python дал0.020501394 м. Более строгий rtol
не гарантирует монотонного улучшения float64 траектории. Strict-квалификация
не превращает Standard в квалифицированный профиль и не отменяет старый FAIL.

## JPL и сравнение с принятой 0.3.2

Проверены SHA всех40 первичных ответов Horizons и совпадение их парсинга
с опубликованной125-эпоховой матрицей, lineage/frame/TDB/KM-S→SI и overlap.
Стартовое расхождение текущих состояний с JPL:0 м/0 м/с на заданных данных.
Параметры/сетка не подгонялись, новых сетевых запросов и новых эпох не было.
Moon−Earth к JPL: Python718.811492 м, Rust718.824785 м;
скорость Rust0.001977611 м/с записана как наблюдение, отдельный физический
порог скорости не утверждался. Пройдены прежние цели <10 км/тело и <1 км
Moon−Earth. Это отличие упрощённой модели от эфемериды, не численная ошибка
DOP853. Ошибка преобразований проверена соглашениями/overlap; это не
самостоятельная квалификация читателя коэффициентов DE441 на другие эпохи.

При одинаковых входах, пакетах и сегодняшнем окружении Python/Rust годовые
и holdout состояния, границы пакетов и final documents совпали с новым
исполнением исходников0.3.2 побитно. Все12 sandbox traces и исходные branch
документы также совпали. Текущий и заново рассчитанный0.3.2 Rust Strict20
совпали со stored141 побитно, как и сохранённый fresh-year результат0.3.2.
Исторические OS/toolchain не реконструировались: сравнивались исходники
в одном сегодняшнем окружении и с тем же принятым pyd.

## Sandbox и достоверность доказательств

Масса×2, скорость×0.7/×1.8, e0.95, добавление компаньона, удаление primary —
для Python/Rust. Прежние Kepler-bisection/RK45 двух уровней/free-motion
эталоны и критерии E/P/L/центра масс сохранены. Максимум позиции0.067253144 м.
Все12 текущих случаев прошли, включая реальные файлы parent/child и continuation.
Эти случаи не дают JPL-точности пользовательским системам и не квалифицируют
произвольные столкновения, тесные сближения или экстремальные числа.

Новый отчёт фиксирует78 source/build-config SHA, настройки, inputs,
Python/NumPy/SciPy и зависимости с файлами, CPython executable/library SHA,
production-native и отдельный oracle. Среда CPython3.14.2 free-threaded,
NumPy2.5.1, SciPy1.18.1, Windows AMD64; полные детали в JSON.
Gate требует собственный новый report/NPZ/protocol, текущие source/input SHA
и совпадение измеренного environment/native. Старый grid FAIL и Strict PASS
проверяются как неизменные исторические inputs; archive SHA не разрешает
новый runtime. На другом окружении необходима отдельная проверка.
Fingerprint не является герметичным образом OS/CPU или аттестацией RAM-кода.

Самопроверка: производственный force/DOP853/coordinate class не вызываются
reference RHS. Общими остаются физические константы, исходные данные, SciPy
и float64, а figure reference использует тип/оси фигуры. Это независимая
численная реализация одной модели, а не независимое доказательство всей
физики. JPL и аналитические Kepler/free-motion проверки отвечают на другие
вопросы. Фиксированные оси, omitted tides/asteroids/higher multipoles и mixed
PN-figure terms ограничивают физическую модель. Между эпохами гарантий нет.

Первичная модель сверена по сохранённому [Park et al.2021, pp5–6, §3.1–3.3](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf):
point-mass PPN β=γ=1, multipoles и обратная реакция; полный DE441 содержит
существенно больше тел/гармоник и приливы. PDF SHA96c3945deb12e0f0843c2bf0703d3542d950cf85ff903b1fe11a501634f68ee0.

## История проверок и ограничения

Первый orchestration job0.3.2 отказал до вычислений из-за совпадения source/output
каталогов. Пробные current/reference jobs остановлены до исправления драйвера;
их массивы/логи сохранены. Затем выполнены новые run-current/run-accepted032/
run-reference на неизменных исходниках. Первый assessor отдельно отказал на
Git CRLF/LF юридического ERFA-LICENSE.txt; разрешена только эта нормализация
legal notice. Численные Python/JSON/Rust bytes сравниваются точно.
Самопроверка дополнила provenance двумя реально использованными analysis/JPL
модулями и build manifests; первые proof-файлы сохранены отдельно, все численные
массивы до/после дополнения побитно одинаковы. Критерии и траектории не менялись.

Времена jobs включают контроль/запись/restart и перекрывались по CPU; их нельзя
трактовать как benchmark или ускорение. Стоимостные повторы141 не повторялись:
оптимизация не является задачей. Полная source/native приёмка — отдельный
следующий контроль. Новая portable и релиз здесь не создаются.

## Регрессии и полная приёмка

Профильный набор:25 PASS/38.34 с, настоящий native,0skip; оба прежних
negative E действительно дошли до целевых подмен после успешного контроля.
Независимые scalar math.dist наблюдения сохранённых массивов сверили численные
метрики, reference convergence и JPL residual. Related:471 PASS/95.78 с/0skip с настоящим native. Короткая приёмка
успешна за6.975 с. Python CI:566 PASS/4 штатных deselect/17.81 с;1402 file/line links.
Полный `check_project.py --require-native`: **2902 Python PASS, 1065.01 с,
19 Rust PASS, обе fmt PASS,0 FAIL/ERROR/skip**. Все878 source/data/protocol/
native отпечатков после прогона совпали со стартом. ГруппаE закрыта:
исходный current positive control и обе целевые подмены проходят свои проверки.
Это локальная полная source/native приёмка, не GitHub CI или новая portable.

GitHub desktop workflow пересобирает native на windows-latest. Отдельный
host/binary/environment не становится квалифицированным автоматически:
при несовпадении fingerprint gate откажет. Для другого окружения потребуется
собственное новое доказательство. Нельзя снимать эту границу моками/skip ради
зелёного CI. Здесь не заявляется успешная приёмка runner или будущей0.3.3.
Существующий portable0.3.2 остаётся прежним; новый выпуск не создавался.


## Повторение без изменения опубликованных доказательств

Нужен свежий checkout коммита этого этапа, Windows/CPython/NumPy/SciPy и
принятый pyd с указанными SHA, а также rustc для отдельного oracle. Установка
окружения описана в [reproducibility.md](reproducibility.md). Сам pyd и OS
не переносятся через Git; для точного повтора нужна проверенная локальная
поставка0.3.2 или её binary-копия. С другим pyd драйвер отказывает; такое
окружение требует отдельной квалификации, а не замены SHA в старом отчёте.

Запускать из корня свежей копии. Каталоги jobs должны отсутствовать; старые
попытки не удалять и не перезаписывать. Подготовить accepted032 source:

```powershell
if (Test-Path .tools/qualification375) { throw 'Используйте свежую рабочую копию' }
New-Item -ItemType Directory .tools/qualification375 -Force | Out-Null
git archive --format=zip --output=.tools/qualification375/accepted032.zip cf653c9ca4b60649e70658b002a5e70669411266 src/solar_simulator
Expand-Archive -LiteralPath .tools/qualification375/accepted032.zip -DestinationPath .tools/qualification375/accepted032
```

Три исторических cache-input можно восстановить из публичных артефактов
этого коммита без скачивания .tools и без расчёта орбит. Проверка в памяти
на измеренной версии NumPy дала точное совпадение всех трёх исходных SHA.
Это восстановление старых inputs; новые reference далее считаются заново.
Запустить этот Python-код через Python окружения проекта:

```python
from pathlib import Path
from io import BytesIO
from zipfile import ZipFile
import hashlib, json
import numpy as np

root = Path.cwd()
protocol = json.loads((root/'scripts/current-runtime-375-protocol.json').read_bytes())
report = json.loads((root/'docs/current-runtime-375-validation.json').read_bytes())
from scripts.sandbox_checks.accept_sandbox import CURRENT_RECEIPT_SHA
assert hashlib.sha256((root/'docs/current-runtime-375-validation.json').read_bytes()).hexdigest() == CURRENT_RECEIPT_SHA
assert hashlib.sha256((root/report['array_archive']).read_bytes()).hexdigest() == report['array_sha256']

def keep(name, raw, expected):
    assert hashlib.sha256(raw).hexdigest() == expected, name
    path = root/name
    if path.exists():
        assert path.read_bytes() == raw, name
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)

bundle = root/'tests/data/jpl-verification.zip'
assert hashlib.sha256(bundle.read_bytes()).hexdigest() == protocol['input_sha256']['tests/data/jpl-verification.zip']
with ZipFile(bundle) as saved, np.load(root/report['array_archive'], allow_pickle=False) as data:
    profiles = json.loads(saved.read('trajectories.json'))['profiles']
    inputs = {
        '.tools/qualification138/reference139.npz': dict(times=data['current_times'], level_0=data['reference_annual_level_0'], level_1=data['reference_annual_level_1']),
        '.tools/qualification138/reference141-holdout.npz': dict(times=data['current_holdout_times'], level_0=data['reference_holdout_level_0'], level_1=data['reference_holdout_level_1']),
        '.tools/qualification138/production139.npz': dict(times=data['current_times'], **{name:np.asarray(value) for name,value in profiles.items()}, reference=data['reference_annual_level_1']),
    }
    for name, values in inputs.items():
        stream = BytesIO()
        np.savez_compressed(stream, **values)
        keep(name, stream.getvalue(), protocol['input_sha256'][name])
    for name, digest in protocol['raw_jpl_sha256'].items():
        keep(name, saved.read('raw/'+Path(name).name), digest)
```

После подготовки выполнить фактические новые jobs. Драйвер не читает
опубликованные current375 trajectories вместо интегрирования:

```powershell
.venv/Scripts/python.exe -X utf8 -B -u scripts/qualify_current_runtime375.py current
.venv/Scripts/python.exe -X utf8 -B -u scripts/qualify_current_runtime375.py accepted032
.venv/Scripts/python.exe -X utf8 -B -u scripts/qualify_current_runtime375.py reference
```

Для повторной оценки задать только новые выходные имена; опубликованные
JSON/NPZ и source-bound gate остаются неизменными. Это перенаправление вывода,
не изменение настроек/критериев:

```powershell
.venv/Scripts/python.exe -X utf8 -B -c "import scripts.assess_current_runtime375 as a; a.REPORT='.tools/qualification375/recheck-validation.json'; a.ARRAYS='.tools/qualification375/recheck-outputs.npz'; assert a.assess()"
```

Новый recheck JSON должен содержать собственные фактические времена и
provenance, поэтому его общий SHA не обязан совпадать с опубликованным.
Сопоставлять критерии, численные поля, epochs, пакеты и фактические массивы.
Не перепривязывать gate к случайному recheck-файлу ради PASS.


## Файлы этапа

Новые доказательства и инструменты:

- [docs/current-runtime-375-protocol.md](../docs/current-runtime-375-protocol.md).
- [docs/current-runtime-375-validation.json](../docs/current-runtime-375-validation.json).
- [docs/current-runtime-375-validation.md](../docs/current-runtime-375-validation.md).
- [scripts/assess_current_runtime375.py](../scripts/assess_current_runtime375.py).
- [scripts/current-runtime-375-protocol.json](../scripts/current-runtime-375-protocol.json).
- [scripts/qualify_current_runtime375.py](../scripts/qualify_current_runtime375.py).
- [scripts/validation/current-runtime-375.npz](../scripts/validation/current-runtime-375.npz).
- [tests/test_current_runtime_qualification.py](../tests/test_current_runtime_qualification.py).

Изменения существующих компонентов (в старом научном описании только ссылки):

- [docs/development/historical-checkpoints.md](../docs/development/historical-checkpoints.md).
- [docs/project-inventory.json](../docs/project-inventory.json).
- [docs/project-map.md](../docs/project-map.md).
- [docs/qualification-extension-validation.md](../docs/qualification-extension-validation.md).
- [docs/verification/README.md](../docs/verification/README.md).
- [scripts/check_suites.py](../scripts/check_suites.py).
- [scripts/sandbox_checks/README.md](../scripts/sandbox_checks/README.md).
- [scripts/sandbox_checks/accept_sandbox.py](../scripts/sandbox_checks/accept_sandbox.py).
- [tests/test_sandbox_acceptance.py](../tests/test_sandbox_acceptance.py).
