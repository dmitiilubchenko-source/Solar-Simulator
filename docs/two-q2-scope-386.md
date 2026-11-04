# Две Q2: область применения и решение по0.3.3

4 ноября2026, этап386. Рекомендуется политикаA с отдельным явно экспериментальным
scope. **Владелец ещё не утвердил waiver; scientific380 по-прежнему FAIL.**
Новых4000s matrices/годовых орбит/full acceptance/portable не выполнялось.

## Что подтверждено

Кандидат `fe0f456f2c7ba3a077eac21fc8413937d6e84fac` не менялся.
Actual native SHA256`651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`,
environment`056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a`.
Frozen source/native/dependency checks385 прошли до/после коротких тестов386.
Newton384 и EIH+fixedJ2 385 остаются своими отдельными научными проверками;
переноса их критериев на dynamic Q2 нет.

| Уровень утверждения | Подтверждение и предел |
|---|---|
| Формальная модель | Autonomous Newton total-degree2 Hamiltonian: monopoles всех тел + M–Q каждой фигуры, вращательная энергия обеих. Симметрии дают полный E/P/L в непрерывных уравнениях |
| Реализация силы/момента | Независимые principal-I potential gradients по позиции/ориентации, reaction и angular balance; повторены короткими tests, не только energy drift |
| Численная точность380 | Два fixed synthetic IC,65epochs0..4000s,12cold packet jobs,6continuous Python jobs,4RK45references; конкретные старые sources/environment |
| Текущий кандидат | Короткие functional/static/GUI tests в его настоящей среде; это не новая полная numerical qualification Q2 |
| Произвольный пользовательский опыт | Глобальная r/v/R/S ошибка неизвестна; локальные atols и E/P/L не доказывают её малость |

Taylor expansion двойного Newton-интеграла через COM даёт degree2 potential
с суммой вкладов I обеих фигур; [Chen,Li,Tao2021 §III.1 и AppendixA](https://arxiv.org/html/2103.12767v2#A1)
проверен как первичный источник. Solar использует свой SciPy DOP853, а не
симплектический integrator GRIT. Вывод и соглашения Solar сохранены в
[380](two-q2-380.md); новая физическая формула здесь не вводится.
Q–Q имеет degree4; у общих нецентросимметричных тел возможны degree3 члены.
Модель не описывает высшие moments/деформацию/приливы/EIH/контакты.
Не пересекающиеся bounding spheres задают внешнюю область, но не малость
физического остатка у поверхности. I не определяет всю плотность реального тела.

## Три FAIL и непрерывный контроль

Offline replay заново редуцировал все12packet jobs и6backend contrasts;
23массива первой остановленной попытки дополнительно сверены dtype/shape/bytes.
Старые protocol/report/NPZ/archive SHA не менялись.

| Случай | Backend | max(coarse–fine) | max(standard–fine) | Исходный gate |
|---|---|---:|---:|---|
|two-bodies|Python|4.32105e-15|7.08677e-15|**FAIL**|
|two-bodies|Rust|7.34181e-15|9.63342e-15|**FAIL**|
|three-bodies|Python|5.62528e-15|6.21502e-15|**FAIL**|
|three-bodies|Rust|1.00185e-14|3.22252e-15|PASS control|

Это max прежних нормированных position/velocity/R/S метрик (в этих строках
доминирует Frobenius R). Критерий строго `standard–fine < coarse–fine`.
Сохранение малых абсолютных ошибок/reference и E/P/L его не отменяет.
Величины согласуются с возможным влиянием roundoff/новой adaptive mesh,
но единственная причина каждой компоненты не установлена.

Single-invocation Python control даёт coarse–fine R9.35/9.42e-10 и
standard–fine1.20/1.02e-11 (двух-/трёхтельный случаи). Это другой recipe,
поддерживающий сходимость на этих задачах;64cold-packet FAIL остаются.
Малый дрейф инвариантов не заменяет comparison координат/ориентаций с reference.
Проверенные состояния относятся к усечённому Hamiltonian, не точности Earth–Moon.

При SHA-аудите выявлено ожидаемое историческое различие evaluator:
`scripts/assess_two_q2_380.py` в manifest имеет SHA0b5ea98c…dec7f0,
нынешний55d0864a…756ba9. Точные старые байты есть в Git638ccf0; commitbc75156
в382 добавил только evidence_path и нормализацию пути continuation. Diff
проверен, numerical reduction/criteria не менялись; остальные manifest artifacts
совпали. Исторический manifest не переписан, отсутствие прямого равенства не скрыто.

## A или B

| Политика | Последствия | Обязательные условия/риски |
|---|---|---|
|**A, рекомендована**|Учебный экспериментальный режим может войти в033 в отдельно названной области. Original380FAIL сохраняется; новая application acceptance оценивается отдельно|Нужно явное решение владельца об исключении из прежнего release gate, numeric B_app, source-bound проверки actual GUI recipe и заметная маркировка. Есть риск переноса пользователем демо-чисел на real/arbitrary системы |
|**B**|Release с этим режимом остаётся заблокирован, пока обязательные scientific criteria не закрыты по утверждённой методологии|Нельзя подбирать более удобный rtol/IC или заменять исходный gate новым PASS. Новые расследования требуют отдельной гипотезы/бюджета, без гарантии устранения немонотонности. Выпуск без режима — отдельное решение/кандидат, не простое скрытие кнопки |

A соответствует назначению доступного synthetic laboratory. Это рекомендация
по управлению scope, а не научный факт и не уже принятый waiver. Полная
квалификация по неизменному380 остаётся FAIL в обоих вариантах. Исходный380
не был полным release protocol, однако план033 перенёс его критерии без waiver.

## Прикладной протокол и B_app

[Отдельный draft](two-q2-application-protocol.md) предлагает сначала actual
двухтельное GUI-демо0..200s, оба backend и заранее заданные contrasts.
Новые IC не подбираются. Числа из старых380 не используются для выбора допуска.

Предлагается B_app,j<=Delta_j/10 для минимального учебного изменения Delta_j,
которое требуется различать: r/r_AB[m],v/v_AB[m/s],orientation[rad],S каждой
фигуры[kg·m²/s]. Это открытое инженерное требование к разрешению эксперимента.
Delta_j не задано пользователем/интерфейсом;17печатных цифр и масштабируемый2D
вид не определяют его. Поэтому **численный B_app остаётся OWNER_REQUIRED**.
Установить произвольный threshold и объявить новую квалификацию было бы подгонкой.
В draft отдельно описаны reference uncertainty, uncertainty от нарушения SO(3),
noise/repeat sensitivity, E/P/L, exact same-packet restart и negative tests.
Все численные budgets/доли надо утвердить до нового исполнения.

## Маркировка приложения и влияние на candidate

Проверены реальные `app.py`, `inspection.py`, `inspection_view.py` и GUI tests.
Кнопка/панель называют тела учебными, не Earth/Moon; окно показывает degree2,
отсутствие Q–Q/высших multipoles/tides/dissipation/relativity. Reliability
явно оставляет global errors=None и current_trajectory_certified=False.
Это честное описание текущей физики. Но слова **«экспериментальный»** и статус
трёх380FAIL в интерфейсе отсутствуют. Для политикиA нынешняя маркировка требует
небольшого усиления; новый оценщик ошибки или редактор тензоров не нужен.

Минимальное **предложение**, не выполненная правка: только при2dynamic figures
добавить experimental/limited qualification wording в model_info app.py,
read-only inspection_view и qualification text inspection.py; сообщить также,
что200s — проверяемый scope, а обычный Start не останавливается на этой цели.
Не переписывать сохранённые q/S/settings и не менять schema.

Важное отличие рецептов: actual demo atol1e-7m/1e-11m/s и4пакета по50s,
standard380 atol1e-8m/1e-12m/s и64пакета по62.5s. Поэтому старые accuracy
числа380 не аттестуют точную GUI-конфигурацию автоматически. Нужен отдельный
короткий application run **после** утверждения draft/B_app, без повтора full380.

Любое изменение даже GUI-текста меняет package fingerprint, который проверяют
384/385. Fe0f456 не правился. Для будущего кандидата нужно заранее согласовать
new source/env receipt/delta qualification: code-diff, unchanged physics hashes,
targeted GUI/state/reliability tests и достаточность повторов384/385. Нельзя
подставить прежний fingerprint или обещать автоматическую аттестацию новых SHA.

## Короткие проверки386 и release-блокеры

43tests PASS/7.645s,0skip на **настоящем fe0f456/native033**: independent gradients,
external boundary (включая касание/nextafter), forbidden physics mixing,
обаq/S persistence/restart/reset,0/1/2figure snapshots, GUI start/pause/stop/
save/load/change scenario/cancel, неизменность состояния при чтении.
Добавлены только7малых domain regression cases; physical code не менялся.
Отдельно в developer032/native0cbc повторены8старых сценариев/24canonical
snapshots — byte-exact. Это **не** сравнение accepted032 с candidate033.

Bounded checks:13.953125CPU s/14.882322wall s; worker private sampled431435776B,
parent OS peak37720064B, консервативная сумма469155840B (~447.4MiB),
артефакты31015B на закрытии worker. Cap60/120/1GiB/32MiB, early50/100/900MiB/28MiB.
50ms sampling/short child caveats: это не OS hardquota. Подготовка/cache,
readback/document packaging/CI/backup отдельно; no large scientific run.
Frozen394source/env385 до/после точны; Newton/EIH hashes не изменялись.

Archives384(939521B,01e0a5b2…8b057d) и385(6766451B,6cdf50ff…84ad3a7)
4ноября заново downloaded и независимо SHA/size/parent проверены:
**CLOUD_VERIFIED_SHA256**. Connected account/root/owner-only Solar-Simulator
folder подтверждены. [Машинные факты386](two-q2-scope-386-audit.json)
содержат полные SHA, FAIL и результаты; очередь других данных этим не закрывается.

Compatibility032↔033 остаётся UNRESOLVED. Для033 также нужны утверждённый
Q2release scope, new candidate provenance при UI-правках, separate compatibility,
full source/native+GUI/recovery и настоящая portable acceptance. Main/tag/LATEST
не менялись. Дешёвые тесты386 не подменяют эти этапы.

**GO** к рассмотрению политики/draft владельцем. **NO-GO** новому application
численному допуску/запуску и включению Q2 под видом полностью qualified режима,
пока не утверждены A/B, узкий scope, B_app и new candidate qualification policy.
Нужные дальнейшие вычисления — только короткий actual-GUI recipe и контроль
uncertainty по draft после этого решения. После386 остановка; без автоматических
матриц/новых лет/смены интегратора. Рекомендуемая модель: GPT-6.1 Sol high.
