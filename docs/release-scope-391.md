# Состав 0.3.3: предложение владельцу после этапа 391

5 ноября 2026. **Рекомендация A; решение владельца — OWNER_REQUIRED.**
GO к утверждению конкретного состава и плана ниже. NO-GO запуску новой
квалификации и выпуску, пока решения не приняты. Предпочтение A из задания
не записано как согласие. Машинные факты и предложения разделены в
[release-scope-391.json](release-scope-391.json).

## Проверенная основа

Dev/origin: `0a2c744742d1c3f2788fb78f8cb81eb5981cd701`, исходное дерево чистое;
принятая main/commit тега 0.3.2: `cf653c9ca4b60649e70658b002a5e70669411266`.
Кандидат `fe0f456f2c7ba3a077eac21fc8413937d6e84fac` остался чистым и неизменным.
Повторно проверены 394 source SHA, actual source activation, prefix/dependency
paths и environment gate существующим `verify_freeze` без интегрирования.

| Привязка кандидата | SHA-256 |
|---|---|
| Native 0.3.3 | `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091` |
| Source environment JSON | `056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a` |

Python 3.14.2t/cp314t-win_amd64, NumPy 2.5.1, SciPy 1.18.1, Matplotlib 3.11.0;
OMP/OPENBLAS/MKL=1, VECLIB/NUMEXPR/PYTHONHASHSEED unset. Текущий dev сохраняет
metadata 0.3.2: нельзя собирать его и назвать результат 0.3.3. Между dev и
кандидатом различаются только шесть product metadata-файлов в src/Rust/build
срезе; Python/Rust runtime source bytes равны. CI исходного dev: Python и
desktop-native success, adaptive-research штатно skipped, run 41918068269.
Это инженерный CI, не полная release acceptance.

Первый offline launcher не нашёл psutil в developer venv до создания worker.
Использована существующая candidate venv без установки зависимостей. Затем
строгая проверка отвергла wheel-копию при `-I`: отличается ровно SHA
`data/ERFA-LICENSE.txt` (installed `18e2c04c…60047`, source `c72781d8…25018`).
Такое LF/CRLF различие уже описано в [384](newton-384-validation.md).
После явной активации candidate/src, как в квалификации 385/390, полный
fingerprint совпал. Никакая лицензия, receipt, native или SHA не исправлялись.
Это не численный дефект, но **wheel/portable должны получить собственный
фактический fingerprint**, а не заимствовать source fingerprint.

## Что остаётся фактом, независимо от выбора

- [380](two-q2-380.md): автономная Newton total-degree 2 модель, монополи
  всех тел плюс оба M–Q вклада, обратные силы/моменты, оба q/S. Q2–Q2 имеет
  degree 4 и отсутствует; у общих тел возможны также пропущенные degree 3
  моменты. Нет высших мультиполей, деформации, приливов, диссипации, EIH,
  контактов. Внешняя область d > R_A+R_B не ограничивает величину ошибки
  усечения реального тела. I и bounding radius не определяют всю плотность.
- Непрерывные уравнения сохраняют полные H/P/L модели; одно сохранение
  инвариантов не доказывает правильность траектории. Независимые gradients
  и проверки реализации описаны в 380/386, а не выполнены заново в 391.
- Три packet-convergence FAIL380 остаются **FAIL**: two/Python
  4.32105e-15 → 7.08677e-15; two/Rust 7.34181e-15 → 9.63342e-15;
  three/Python 5.62528e-15 → 6.21502e-15. Здесь прежние нормированные
  max(coarse–fine) → max(standard–fine), не метры и не углы в радианах.
  Их немонотонность не получила единственного доказанного объяснения.
- [384](newton-384-validation.md) и [385](annual-385-validation.md)
  квалифицируют только собственные модели, IC, сетки, native/source/environment.
  Rust Standard20 385 сохраняет diagnostic FAIL 0.113353 m > 0.1 m;
  Strict не даёт автоматического допуска Standard или dynamic Q2.
- [387–390](compatibility-387-390-assessment.md): A/B/C PASS в ограниченной
  области, 8 short cases/16 restarts не повторять. Это не global accuracy,
  историческая ОС, все пользовательские сохранения или новая portable.

## Два варианта состава

| | A — рекомендованная экспериментальная учебная модель | B — исключить две Q2 из релиза |
|---|---|---|
| Допустимое утверждение | Согласованная усечённая модель и отдельно проверенный конкретный учебный recipe, если будущая application acceptance пройдена | Поддержка 0/1 фигур; две Q2 намеренно недоступны в выпускаемом runtime |
| Недопустимое утверждение | «Полностью квалифицировано по 380», точность Земля–Луна, абсолютная ошибка произвольного опыта, допуск после редактирования/за 200 s | «Дефект 380 исправлен», либо «две Q2 исключены», если скрыта только кнопка |
| Обязательные условия | Явное изменение release scope вместо невыполнимого обещания полного PASS380; предупреждения; утверждённый B_app/reference/sensitivity; отдельный короткий application run | Явный отказ двум фигурам при create/load/advance, включая CLI и сохранённые файлы; отсутствие потери второй фигуры; регрессии 0/1; новый состав package/docs |
| Минимальный diff | Только presentation: app.py, inspection.py, inspection_view.py и документы/тесты | Одной маркировки недостаточно. Общая cardinality-валидация nbody_rotation.validate плюс вызывающие create/storage/continuation пути должны безопасно отклонять две фигуры; убрать demo resource/entry из состава, пересмотреть closure |
| Fingerprint | Новый, хотя численные исходники и native можно сохранить побайтно | Новый; меняется runtime dispatch/validation, а не только текст |
| Квалификация | Delta audit ниже + application + полная release/portable acceptance | Повторная 0/1 validation/storage/GUI/CLI qualification и source/native/portable acceptance; основание сокращения научных повторов устанавливать по реальному diff |
| Блокеры/риск | Владелец должен явно принять экспериментальный scope, исходный FAIL и предложенное разрешение; пользователь может неверно обобщить демо | Новый релизный ограничитель и проверка всех входов; риск скрытой доступности и отказов прежних пользовательских two-Q2 файлов. Оригиналы файлов не изменять |

B здесь означает **выпуск без режима**, как в задании 391. Более ранний
вариант B в draft386 «оставить выпуск с режимом заблокированным» остаётся
историческим текстом, а не автоматически выбранной современной политикой.
Ни A, ни B сейчас не применены. Не нужен новый physics framework или solver.

## Предложение учебного разрешения, а не утверждённые допуски

Цель рекомендуемого профиля D1: различать поступательное движение на масштабе
десятков метров, изменение направления осей порядка 0.01 rad и обмен spin
порядка 0.01% начального |S|. Это предлагаемое требование к демонстрации,
а не объективно известное требование пользователя. Оно не обещает, что именно
такой эффект обязательно произойдёт за 200 s, и **не требует различать малую
орбитальную поправку Q2 от монополя**. Для последней потребуется отдельно
определить эффект и контроль; новый monopole contrast в 391 не запускался.

Физические масштабы взяты из frozen IC, не из ошибок380: separation 12000 m,
relative speed 2.5578311125 m/s, радиусы 1000/900 m, surface gap 10100 m.
|ω(0)| = 0.00201246 / 0.00169115 rad/s; |ω(0)|×200 ≈ 0.4025 / 0.3382 rad.
Начальные |τ| ≈ 5.13832e11 / 7.25166e11 N m дают
|τ(0)|×200/|S(0)| ≈ 1.70592e-4 / 1.82018e-3.
Это размерностные начальные оценки, **не интегрированные изменения и не
границы ошибок**: ω, τ и их направления меняются. Они лишь делают обсуждение
разрешения осмысленным. Spin измеряется в SI, направление — в инерциальном базисе.

| Величина, отдельно по телам | Минимальный предлагаемый эффект Δ_j | Предложение D1: B_app,j = Δ_j/10 | U_ref ≤ B/10; N_sens ≤ B/10 |
|---|---:|---:|---:|
| r_A, r_B: Euclidean position | 10 m каждое | 1 m каждое | 0.1 m каждое |
| Относительный вектор r_B−r_A | 10 m | 1 m | 0.1 m |
| Дистанция ρ=|r_B−r_A| | 10 m | 1 m | 0.1 m |
| v_A, v_B и v_B−v_A | 0.01 m/s каждый вектор | 0.001 m/s | 0.0001 m/s |
| Ориентация A, B, physical angle | 0.01 rad (~0.573°) каждая | 0.001 rad (~0.0573°) | 0.0001 rad |
| S_A: inertial vector difference | 1e-4 norm(S_A0) ≈ 6.02412e13 kg m²/s | ≈ 6.02412e12 kg m²/s | ≈ 6.02412e11 kg m²/s |
| S_B: inertial vector difference | 1e-4 norm(S_B0) ≈ 7.96806e12 kg m²/s | ≈ 7.96806e11 kg m²/s | ≈ 7.96806e10 kg m²/s |

Точные S бюджеты: коэффициенты 1e-4/1e-5 от начальной binary64 нормы,
значения сохранены в JSON. Не менять их по текущему S(t). Требования для
relative vector и distance проверять независимо: два body errors по 1 m
сами по себе гарантируют только 2 m, а не предложенный 1 m для пары.
Положение зависит от выбранного инерциального базиса/COM; fitting запрещён.
Для SO(3) угол физический, q и −q эквивалентны; raw q сохранять для exact restart.

График autoscale/zoom и условная длина главных осей не задают минимального Δ.
При гипотетическом span 14 km и 1000 px получается 14 m/px, а угол 0.001 rad
на оси длины 1000 m даёт ~1 m: такой допуск нельзя подтвердить «на глаз».
Это иллюстрация, не замер GUI. Проверка проводится по сохранённым SI данным.
17 печатных цифр также не обещают 17 цифр физической точности.

**OWNER_REQUIRED:** утвердить D1 либо иной учебный смысл. Вариант D2 — все Δ/B
D1 уменьшить в 10 раз, если нужен более мелкий количественный эксперимент;
проверка станет строже, возможен UNRESOLVED из-за reference/sensitivity.
Отказ от численного учебного разрешения оставляет B_app=null и NO-GO отдельной
application acceptance; это не разрешение назвать один визуальный smoke квалификацией.
Ни один вариант не выбран на основании уже измеренной ошибки380.

## Предлагаемое правило application acceptance

Это дополнение-предложение к неизменному [draft386](two-q2-application-protocol.md),
не его утверждение/редактирование. Перед исполнением отдельный sealed plan.
IC: точный demo380 resource SHA `3f6fa9b5883db9e14653c43ddc7359e4cf795744e42d3345baf9ea018772428b`,
равный cases/0/initial plan380 SHA `26eaaf67878e34bd292682b90e07b0df5e3ad9b096f8ee9d0f5a0cf6e9b94d68`.
SI, elapsed t=0 в инерциальном базисе, без JPL epoch. Оба backend, времена
0/50/100/150/200 s, dt=50 s, четыре cold packets по одному шагу; GUI rtol1e-11,
x_atol1e-7 m/v_atol1e-11 m/s/q_atol1e-13, S_atol=|S_i(0)|1e-13.
Сохранить также все три прежних tolerance levels без выбора «лучшего».

16 runtime jobs = 2 backend × 4 levels × {cold,continuous}; оба cold GUI
baseline получить через actual GUI, остальные — существующими Experiment/integrate.
Плюс 2 baseline repeats и 2 exact suffix из точных кадров t=100 s; 2 свежих
независимых RK45/R/body-Pi reference по неизменным уровням draft386. Это
20 runtime jobs (suffix включены) + 2 reference, не повтор 4000 s матрицы380.

На пяти эпохах для каждого компонента сохранить e_j относительно fine reference.
Предлагается U_ref,j = level-difference плюс наблюдаемый projection defect
для ориентации; не трактовать сумму как строгую верхнюю границу. Reference R
проверять на SO(3); polar projection только в observer, с сохранением raw R,
его defect и обоих углов. Для точных SO(3) ||R1−R2||F=2sqrt(2)sin(θ/2).
Предложение для малого projection defect: U_ref,θ = угол между двумя polar R
плюс сумма двух ||R−polar(R)||F / sqrt(2). Последний член — условная локальная
угловая шкала дефекта, не строгая граница физической ошибки; её смысл должен
быть принят владельцем. det≤0, nonfinite или projection contribution больше
U_ref budget → UNRESOLVED. Стабильное вычисление physical angle проверить
независимо; не использовать acos около 1 без контроля ортогональности.
Неопределённый угол → UNRESOLVED, не ноль.

Предлагается N_sens,j как envelope **всех** pairwise tolerance contrasts на
том же recipe, cold/continuous contrasts на каждом уровне, same-environment
repeats и независимого пересчёта сохранённых наблюдаемых. Требовать отдельно
U_ref≤0.1B, N_sens≤0.1B и e+U_ref+N_sens<B. Изменение рецепта здесь только
измеряется, пользовательский baseline им не заменяется. Это эмпирическая
инженерная проверка устойчивости на сетке, не global-error theorem и не
измерение абсолютного runtime roundoff. Exact repeat/restart обязаны совпасть.

В draft386 упомянут precision contrast. **Отдельное решение владельца:**
достаточно ли для этого узкого допуска двух reference levels, operational
sensitivity и независимого observer arithmetic (например Decimal80/120).
Это не повышенная точность самого DOP853. Если требуется именно независимая
оценка его глобального roundoff, её пока нет: соответствующий пункт unresolved,
NO-GO такому утверждению; не добавлять молча новый численный backend.

Применимые gradient/reaction/E/P/L/qnorm gates380 остаются неизменными,
как и три старых FAIL. В новой прикладной проверке немонотонность снова
показать отдельно; исключение её из release gate требует явного решения A.
Domain d>R_A+R_B обязателен в RHS; loss of domain → явный отказ/last completed
packet recovery. Численный допуск модели не ограничивает ошибку реальных тел.

## Конкретный будущий diff интерфейса и тесты

Сейчас **ни одна runtime строка не изменена**. Предлагаемые места:

1. [Кнопка демо](../src/solar_simulator/app.py:115):
   «Две Q2 — экспериментальный учебный опыт». Не менять callback/IC/settings.
2. [model_info](../src/solar_simulator/app.py:388), только len(rotations)==2:
   «Экспериментальная учебная модель. Newton total-degree 2: M–Q;
   без Q2–Q2, высших мультиполей, приливов, диссипации, EIH и контактов.
   Три FAIL сходимости380 сохранены. Глобальная ошибка произвольного опыта
   не установлена. Прикладная проверка относится только к точному демо A/B,
   0–200 с и указанному recipe; до её выполнения прикладной допуск не установлен».
3. Там же пояснить: «Расчёт до времени — остановка на выбранной цели;
   обычный Запуск не ограничен 200 с. Изменённые IC/пакеты и t>200 с вне
   прикладной области». Не вводить скрытый hard-stop/изменение интегрирования.
4. [rotation_text](../src/solar_simulator/inspection_view.py:47) и
   [inspection.report](../src/solar_simulator/inspection.py:89): тот же conditional
   смысл для двух фигур; отдельная константа текста, не менять общий one-Q2
   ROTATION_SCOPE. В [qualification message](../src/solar_simulator/inspection.py:30)
   сохранить current_trajectory_certified=False и global errors=None.
   Не добавлять выдуманный certified=True по именам A/B или времени снимка.

После выбора scope формулировка должна отражать реальный статус application
receipt, а не заранее «проверено». Если receipt создан после freeze и текст
требует правки — новый fingerprint и повтор delta audit. Заранее нейтральный
текст со ссылкой на отдельный отчёт позволяет не править package повторно.

Тесты будущего diff: existing test_laboratory_rotation_gui/test_laboratory_rotation,
test_two_q2_gui, tests с reliability report. Добавить точечные assertions для
видимости предупреждения после open/load, 0/1 без two-Q2 маркировки, read-only
q/S/settings и SI, отмены/сохранения/ошибки/recovery; verify target и обычный
Start семантически различаются. Новые расчёты только в согласованном коротком
application бюджете. Никакого изменения schema или старого CLI JSON.

## Новый fingerprint и допустимость delta qualification

recipe.runtime_fingerprint хеширует все package .py/.json/.txt, поэтому даже
строка интерфейса создаёт новую привязку. Freeze384/385 и receipts неизменны.
Не переписывать CURRENT_RECEIPT_SHA, не ослаблять verify_freeze, не давать
новому commit старое имя. Новый delta receipt должен ссылаться на точный fe0f456
и новый commit с полным новым фактическим environment.

Сокращение научных повторов допустимо **только после доказанного diff**:
три presentation-файла, разрешённые строки/constant returns; прежние
simulation/accuracy/error_control/nbody_rotation/rotation/forces/experiment/storage,
все Rust sources, G/IC/atols, data/native и численные dependency bytes равны.
Прочитать все callers, проверить отсутствие новых вызовов или side effects;
AST/byte SHA вычислительных функций отдельно, затем targeted GUI/state/reliability.
Пакетные handlers не менять. Провести независимый source-diff review и
отрицательные проверки: изменение силы, native, IC или tolerance должно
отвергать delta-only маршрут. Исторический resolver не должен его принимать
как текущую квалификацию.

Тогда старые 384/385 остаются измерениями старого source-bound кандидата, а
новый допуск опирается на явный аргумент неизменности вычислительной реализации
и новую инженерную приёмку. **Не объявлять новое научное исполнение 384/385.**
Если diff выходит за presentation whitelist, compiled/dependency bytes другие
или идентичность не доказана — STOP delta-only. Отдельный план повторяет
затронутый Newton384 и/или EIH+J2 385 на новом freeze, не переносит старый PASS.
Список заранее не сокращать произвольно до удобной одной орбиты. Для B требуется
новая оценка dispatch/validation diff. В 391 никаких таких запусков не было.

## Остаток release acceptance: предлагаемый порядок

Все бюджеты ниже — предварительные потолки **будущих отдельных этапов**, не
текущее разрешение. Monitor CPU worker+supervisor, wall, sampled private tree,
disk; immutable input/output, partial при отказе, early margins до запуска.
Внешние исходники/архивы не перезаписывать; mandatory cloud readback отдельно.

| Фаза и зависимость | PASS / FAIL или STOP | CPU / wall cap | Private / новые данные |
|---|---|---:|---:|
| 1. Решение владельца | Записаны A/B, учебная цель/D1/D2, B/U/N, precision-policy, исключение FAIL380 из узкого release gate и разрешённые утверждения. Нет решения → OWNER_REQUIRED | Анализ, без solver | Компактные документы |
| 2. Presentation patch и provisional C1 после 1 | Отдельный checkout/commit 0.3.3; fe0f456 сохранён, exact diff/численные SHA/native/версии/ABI/полный actual env и negative guards. Неожиданный diff → STOP | 180 / 360 s | 1 GiB / 256 MiB |
| 3. Application A на C1 после 2 | Зафиксированные 20 runtime jobs + 2 refs, все e/U/N и старые применимые E/P/L/q gates; exact resume/repeat, GUI state/recovery, no fallback. Любая обязательная метрика отсутствует/превышена → FAIL/UNRESOLVED | 60 / 120 s | 1 GiB / 32 MiB |
| 4. Final candidate freeze после 3 | Final source = тот же C1, либо повтор delta/app для изменившихся relevant bytes. Утверждён мост к 384/385, receipts на точных источниках. Candidate clean; main/LATEST прежние | 30 / 90 s | 512 MiB / 16 MiB |
| 5. Полная source/native/desktop/GUI/recovery после 4 | check_project.py --require-native, весь относящийся набор, actual PyO3, Rust test/fmt, 0 неожиданных skip/xfail; doc/inventory/SHA/recovery checks. Не заменять subset или историческим PASS | 2400 / 2700 s | 3 GiB / 2 GiB |
| 6. Isolated portable build после 5 | build_portable.py из согласованного C1/env, metadata Python/core/native0.3.3; новый exclusive output, ZIP/CRC/member SHA, package data и тексты. Свой packaged fingerprint и provenance, не source FP | 300 / 600 s | 2 GiB / 1 GiB |
| 7. Полная relocated portable acceptance после 6 | check_portable.py ZIP в новом пути с пробелами, -I/без PYTHONPATH, actual native и packaged data; GUI/save/recovery/record/playback; JPL replay И fresh-year, continuous-year acceptance probes. Любой обязательный FAIL/STOP → NO-GO | 900 / 1200 s | 2 GiB / 2 GiB |
| 8. Финальный review после 7 | Все receipts связаны с окончательными source/ZIP/native/env, ограничения публичны, архивы и cloud SHA проверены. Отдельное разрешение main/tag/release/LATEST | 30 / 90 s | 512 MiB / 16 MiB |

Ранние лимиты CPU/wall для исполнения заранее ≤80% потолков, RAM/disk ≤90%;
проверить запас по известному startup перед каждым запуском. Для application
сохранить draft386 early50/100/900MiB/28MiB. Если одного фрагмента не хватит,
сохранить partial и новый план до продолжения; не перекидывать бюджет молча.
Build+portable суммарно сохраняют cap382 1200 CPU /1800 wall /3 GiB disk.
Другие caps взяты из 382/386, не обещают срок выполнения. До начала release
иметь ≥8 GiB свободного места сверх существующих результатов и архивов.

Эмпирические ориентиры: application пока не измерена (draft 5–20 CPU s,
не подтверждённая экстраполяция); targeted GUI381 ~2.34 CPU s, checks386
~13.95 CPU s. Полная source032 ~869 wall s; это не измерение 033.
Новая mandatory annual385 уже выполнена (~213.61 CPU s), повторять её
ради документов нельзя. В [check_portable](../scripts/check_portable.py:227)
fresh-year и [continuous-year](../scripts/check_portable.py:519) реально
интегрируют: они остаются обязательными acceptance probes **упакованного**
runtime, не новым исследованием/матрицей 385. Их нельзя случайно запустить
в 391 или подменить старым NPZ replay. Прогноз оставшейся release работы —
порядок десятков минут wall при warm build/cache, CPU/RAM новой portable
не измерены; ресурсный preflight каждого будущего этапа обязателен.

Для B фаза3 с двумя Q2 не выполняется: вместо неё — заранее ограниченный
rejection/0–1 regression plan; это не permission пропустить фазы4–8.
При недостаточном delta-обосновании дополнительные научные запуски не входят
в таблицу и требуют отдельного плана/бюджета.

## Результат и обязательные решения

Рекомендую **A + D1**, честную experimental маркировку и operational sensitivity
без заявления о доказанном глобальном roundoff. Требуется явное согласование
всего пакета: scope A, Δ/B/U/N, трактовка precision, будущий delta-only маршрут,
короткий application run и затем оставшаяся обязательная acceptance.
Это выбор требований, а не «прощение физической ошибки» или новый PASS380.

391 выполнил только static/source/environment и offline arithmetic проверки,
без орбит и изменения runtime. Исторические отчёты/кандидат/критерии сохранены.
Проверки документов и машинного контракта PASS: 1409 file/line links, 1295
inventory paths, все цели ссылок нового отчёта существуют, исторические SHA
совпали, runtime/Rust diff пуст. Отдельный observer перечитал IC, вычислил
нормы S через exact Fraction + Decimal100, сопоставил scalar ω/τ с существующей
NumPy-реализацией и пересчитал три FAIL из сохранённых метрик380. Эти коды
разделяют уравнения/IC, не являются внешней рецензией или новым reference орбит.

Измерено 11.5625 CPU s внутри пяти monitor invocations, учёт с отдельным
1 s запасом на неинструментированный старт — 12.5625 CPU s и 12.8096 active
wall s. Запас не является измеренным CPU. Worker private sampled peak
144809984 B (~138.1 MiB), 42496 B локальных артефактов на закрытии проверок.
RAM supervisor и его startup/inter-job CPU отдельно не записаны; это не
гарантия полного stage RAM/CPU. 50 ms sampling не hard quota. Подготовительные
отказы, фактические измерения и эти ограничения сохранены. Время чтения,
редактирования, Git/CI и обязательного резервирования учитывается отдельно.
Cap/early не повышались; resource STOP не было.

Критическая самопроверка: предлагаемые Δ/B не стали принятыми критериями;
projection/sensitivity не названы доказанными границами ошибок; source/wheel
различие не скрыто; предположение о единственной причине FAIL380 не сделано;
новой аттестации384/385 нет. Новые физические тесты не добавлялись: программного
контракта, который надо было бы исправлять, в этом этапе не меняли.
После 391 остановка. **0.3.3 release NO-GO; main переносить рано.**
Для следующего согласованного presentation/acceptance этапа: GPT-6.1 Sol High.
