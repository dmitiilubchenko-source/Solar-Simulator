# Продолжение DOP853: результаты и ограничения

15 октября2026. Добавлен отдельный **экспериментальный расчёт интервала**.
Обычные advance/GUI/strictпрофиль/JSONschema сохраняют прежнее поведение.
Общий аналитический gate151 не пройден; режим не стал новым стандартом.
Профильные проверки Солнечной системы прошли отдельно.

[Предварительный протокол](continuous-integration-protocol.md),
[полные метрики и SHA](continuous-integration-validation.json),
[публичные траектории и независимые эталоны](continuous-integration-reference.npz).
NPZбезpickle,663576байт,
SHA`e1cb054f6d5f2ca9b0e983e7f824fcd3e03e99c471266d8bfc3200bd74d67b55`.

## Метод и стоимость

Один DOP853 сохраняет y/f/h_abs между пакетами; каждый пакет заканчивается
на прежней границе времени. Нет расчёта за кадр и dense interpolation.
Центр/drift исходного снимка постоянны, EIH получает инерциальные скорости.
Те же nativeNewton/EIH силы, Q2 и per-body контроль; контакты/динамическое
вращение явно отклоняются. Управление status/t_bound зависит от installed
SciPy1.18.1: другая версия отклоняется, fallback отсутствует.
[Первичный SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.DOP853.html),
[оригинальный DOP853 Hairer](https://www.unige.ch/~hairer/software.html).

Intel i5-13400F/CPython3.14.2/NumPy2.5.1/SciPy1.18.1.354тела,
EIH+fixedSunJ2+prescribedEarthMoonQ2,rtol3e-14/x1e-7м/v1e-13м/с,
720000с, **те же10packet20 и11снимков сt0**. Прогрев+3чередующихся повтора,
сериализация/профилировщик вне таймера:

| Измерение | Рестарты | Продолжение | Уменьшение времени |
|---|---:|---:|---:|
| Расчёт с формированием снимков | 7.8717с | 2.1415с | 72.79% |
| Расчёт + отчёт каждого пакета | 8.7779с | 3.3252с | 62.12% |
| Вызовы RHS отдельно | 1982 | 530 | — |

Gate≥15% полной стоимости прошёл. Повторные массивы точные;
расхождение сlegacy≤2.930мм/all и0.1105мм/pair. Послеsave/load новойsession
≤1.465мм/all и0.000000246м/pair. Численный путь другой, bitexactlegacyне обещается.

## Независимые проверки

354тела/8⅓суток/11эпох: отдельныйscalarRustEIH/principal-axisQ2,
RK45/AU/year с независимой картой Earth–Moon, уровни1e-13/max1800с и
3e-14/max900с. Эталон22.515с; различие уровней0.010753м/all и
0.000030518м/pair. Кандидат≤0.009481м/all(Uranus),0.000031457м/pair.
Порог10м/all,0.1м/pair прошёл. Это численная проверка с неопределённостью
самогоэталона, не доказательство сантиметровой физической точности.

Strict10тел/год/125эпох/499пакетов: SHA-verified independentRK45 reference139/141.
Кандидат≤0.069474м/all(Neptune),pair0.040073м; referenceuncertainty
0.098723м/all,0.003040м/pair сохраняется. Numeric10м/body+0.1м/pair passed.
После свободного расчёта проверены40rawHorizons/DE441 и125эпох,
SI/SSB/EclipticJ2000/JD2461321.5TDB. Goals10км/body+1км/pair passed,
Moonrelative718.840242м. Legacy718.824785м остаётся прежним результатом;
модельный остаток не уменьшился. Баланс EIH+fixedJ2~2.24e-15.
MixedPNfigureterms/приливы/ограничения исходной физики остаются.

## Сохранённый отказ

Наклонные Kepler/2оборота/60эпох, independentbisection/scalarE/L/P,
rtol3e-14/defaultabs1e-3м/1e-9м/с: e0:0.003849мpassed;
e.5:0.100677мFAILED0.1м; e.95:7.145756м/9.11233e-5м/сFAILED.
Отдельный tightabs1e-7м/1e-13м/с: e.5:0.029071мpassed;
e.95:4.390841м/5.59934e-5м/сFAILED. Порог не менялся.
Legacyизтого жеt0на каждой эпохе/tightabs:e.95:4.381937мalsoFAILED.
Отказ не уникален continuation; tightabs помогает, но не устраняет его.
Хороший баланс E~1e-13 не доказывает точность положения. Декомпозиция
initialroundoff/phaseaccumulation/truncation пока не установлена.

ПервыйJSONwriter numpy.bool_ оставил partial; полныеповторы сохранилиотказ.
Первоначальные2testassumptionошибки Vector3eq/Bodyfrozen исправлены.
LegacyincrementalKepler отказывал на floatинтервалах, не представимых
точно какcurrent+duration; егоguardне обходился/runtimeне менялся.
Новый boundclamp предотвращает одинulpovershoot. Generalrelease=false,
ordinaryGUIне переводится автоматически на этот engine.

## Запуск

В новойportable **Continuous Catalog Experimental.cmd** считает354тела
на720000с/packet20 без анимации. Новаяпапка результатов:
`%LOCALAPPDATA%/SolarSimulator/experiments/continuous-...`, путь в консоли.
`snapshots.csv`: все11снимков/3894строки; `final.json` можно открыть кнопкой
«Загрузить». После загрузки работает прежний GUIметод.
`initial.json/final.csv/receipt.json` фиксируют engine/настройки/epoch/SHA/границы
и ограничения. Буферыsolverне сериализуются. Ошибка/прерывание сохраняет
только последнюю завершённую границу вinterrupted.json и failure.json.
Новый output обязателен; input не изменяется. Qualificationпроизвольного
inputне присваивается: experimental=true/qualified=false.

```powershell
.venv/Scripts/python.exe -X utf8 -B -m solar_simulator.continuous_cli --input INPUT.json --target 720000 --packet-steps 20 --output .tools/new-continuous-run
```

Target — абсолютное elapsedвремя опыта вSIсекундах.23новыхтеста прошли:
lifecycle/fractionaltarget/aliases/mode/version/CSV/provenance/outputguards/
failure/KeyboardInterrupt. Полнаярегрессия иactualZIP — вdeliveryreceipt.
Годовая354physicalqualification, RAM/GPU/FPS и другойПК не измерены.
Следующий научный шаг — разобрать e.95фазовуюошибку; модельSolHigh.

Реализация: [ContinuousRun](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/continuous.py:31),
[запуск и сохранение](C:/Users/Admin/Desktop/Solar-simulator/src/solar_simulator/continuous_cli.py:26),
[границы/пауза/aliases](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuous.py:20),
[сохранение прерванного опыта](C:/Users/Admin/Desktop/Solar-simulator/tests/test_continuous_cli.py:48).
