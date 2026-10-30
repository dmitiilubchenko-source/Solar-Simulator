# Первая Newton-квалификация кандидата0.3.3

30 октября2026. **Ограниченная научная проверка завершена; релиз0.3.3 не готов.**
Main/portable0.3.2/LATEST сохранены. Годового EIH/JPL, повторной полной Q2
матрицы, full release acceptance, IAS15 и новой portable не было.

## Точно идентифицированный кандидат

Отдельный worktree и ветка `codex/candidate-0.3.3-384`, commit
`fe0f456f2c7ba3a077eac21fc8413937d6e84fac` доступны в origin. Это настоящий
Git-коммит с Python/Cargo/native metadata0.3.3, не рабочий overlay.
Разработческий dev остаётся0.3.2; физические Python/Rust исходники не менялись.
Шесть metadata-файлов совпадают с after-SHA383. Атрибуты Git закрепляют
metadata и legal notice побайтно; сам текст лицензии и научные данные прежние.

| Связь | SHA-256 |
|---|---|
| Native0.3.3 `.pyd` | `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091` |
| Source manifest | `9a4f0158b3ff16b23b6c29e9478864fbd47b7d2876a160f587420825a63fc250` |
| Actual environment | `056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a` |
| Протокол нового исполнения | `0ef90a75b8acb8158bb114e31687d54326ef7c3624a3fdbacaa0b245d347b240` |
| Freeze | `b53d39028e20f1b107dcd68702ce085883db698bd9e7056ebecd04a319558bb6` |

Python3.14.2t/cp314t-win_amd64, NumPy2.5.1, SciPy1.18.1, Matplotlib3.11.0.
Все17 runtime/test distributions скопированы в отдельную venv с проверкой
4180 файлов, без общей dependency-site, symlink или `.pth` исходного проекта.
Тот же OS/base interpreter остаётся общим: это не hermetic OS/portable qualification.
Native перенесён из проверенного383 wheel, а не заново собран. Его Rust/Cargo
input bytes совпали точно; provenance: rustc1.99.0 GNU, maturin1.15.0,
PyO3.29.3/release. Полученный отдельно psutil7.2.2 используется для надзора.

Первый preparation freeze остановился на legal notice:383 export имел CRLF,
новый Git worktree — канонический LF. Неверное предположение о полном равенстве
fingerprints исправлено: фактический новый fingerprint сохранён целиком.
Нормализованное сравнение применялось только к тексту лицензии при диагностике,
никогда к научному environment gate. Исторический383 и его SHA не переписаны.

## Заранее фиксированный опыт

Использован [протокол376 с новым provenance](../scripts/validation/newton384/protocol.json):
36 jobs,4cases: e=.5/.95/.99 peri/.99 apo; Python/Rust × Standard1e-13/
Strict3e-14 × absolute/relative variables; дополнительно4high99 one-packet
контроля. Grid jobs содержат все49 прежних эпох за один номинальный период;
exact binary IC, массы, G и эпохи сохранены. SI, наклонные инерциальные оси,
заданный COM offset/drift, elapsed seconds от0; не эпоха реальной JPL-системы.
atol=.001m/1e-9m/s, per-body; никакого dynamic max_step d32.

Реальные вызовы проходят Experiment → accuracy → PerBodyDOP853/SciPy.
Внешний наблюдатель только считает RHS/solver/native и пишет завершённые
пакеты. Его невмешательство проверено точным сравнением состояний. Счётчики
не являются внутренними accepted/rejected steps: таких сведений нет.
Итого265028 RHS evaluations,132562 реальных Rust force calls; Python jobs
дают0native calls. Счётчики включают повторные suffix для same-packet restart.
Чтение исторических NPZ в процессе acquisition запрещено; reference вычислен
заново для каждого случая, output-каталог создан exclusive.

Эталон — прежний независимый Decimal f/g от exact binary64 relative IC и
mu=exact(G)*(exact(m1)+exact(m2)),70/100digits. Формулы/размерности сверены с
[первичной реализацией Orekit](https://raw.githubusercontent.com/CS-SI/Orekit/develop/src/main/java/org/orekit/orbits/KeplerianMotionCartesianUtility.java)
и постановкой Cartesian propagation [NASA/JPL PROP2B](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/FORTRAN/spicelib/prop2b.html).
Это наш bounded elliptic oracle, не запуск этих внешних программ;70/100
разрядов проверяют чувствительность, не дают строгую теорему об ошибке.

## Измеренные ошибки

Ниже заранее выделенный Strict/relative grid subset. r/v — максимум ошибки
относительного состояния на49эпохах; CPU включает диагностику, journal и
проверку продолжения, а не только solver. [Все36вариантов без отбора](../scripts/validation/newton384/all36.csv).

| Случай | Backend | max r,m | max v,m/s | job CPU,s | RHS |
|---|---|---:|---:|---:|---:|
|e=.5|Python|0.135418|6.11805e-8|0.593750|8256|
|e=.5|Rust|0.137642|6.22281e-8|0.437500|8316|
|e=.95|Python|3.67831|4.69068e-5|0.750000|10404|
|e=.95|Rust|3.94335|5.02864e-5|0.531250|10416|
|e=.99 peri|Python|39.3522|0.00555418|0.828125|11760|
|e=.99 peri|Rust|37.5339|0.00529755|0.625000|11748|
|e=.99 apo|Python|0.0275927|2.31002e-6|0.812500|11808|
|e=.99 apo|Rust|0.0256827|1.92204e-6|0.562500|11808|

У .95 и .99-peri максимумы r/v приходятся на конец номинального периода.
У .99-apo максимум r — в конце, v — в середине, в окрестности перицентра.
Это локализация на заданной сетке, не непрерывные максимумы.
Низкий energy drift не гарантирует малую позиционную/скоростную ошибку:
для .99-peri Strict/relative dE/|E0| около1.2e-12 при десятках метров r.
Все E/L/P и обе координатные формы сохранены в CSV/полном машинном proof.
Совпадение Python/Rust не считается независимым физическим доказательством;
различие фаз или backend само по себе не устанавливает причину ошибки.

## Независимая проверка и статусы

Свежие arrays независимо перечитаны отдельным Fraction/Decimal120 observer:
все36jobs/1576states, r/v/E/L/P для всех эпох совпали с producer в прежнем
8ULP serialization gate. Он разделяет Newton/G/IC и сохранённый f/g reference,
но не арифметику producer reduction; это не внешняя рецензия и не второй IVP.
[Компактные свидетельства](../scripts/validation/newton384/manifest.json)
содержат freeze, environment, protocol, raw-state summary NPZ, proof и trace.
Полные packet journals, per-job arrays/receipts/checkpoints и логи сохранены
отдельно локально и подлежат Project-Archives backup.

| Требование | Результат |
|---|---|
|Новый immutable candidate/source/native/environment|PASS: реальные SHA до/после, чистая кандидатная ветка|
|Reference t0/70–100 sensitivity|PASS: исходные пределы1e-6m/1e-12m/s|
|8moderate376accuracy gates|PASS: r<100m,v<1e-3m/s,dE<1e-10|
|8same-packet file restart cases|PASS: точные канонические документы|
|Все36jobs и независимые1576state reductions|PASS,без новой интеграции в observer|
|High-e accuracy gate|UNRESOLVED/DIAGNOSTIC:376не задавал новый порог; ошибок не скрывать|
|Исторические три380packet FAIL|FAIL сохранён, не заменён continuous PASS|
|Полная квалификация0.3.3|NO-GO: остальные обязательные этапы не выполнялись|

Основной science+independent audit:42.25CPU s (35.078125worker+7.171875supervision),
36.314431wall s; worker private peak139526144B, supervisor OS private peak
37814272B, консервативная сумма этих максимумов177340416B (~169.1MiB),
artifacts5800284B (~5.53MiB) на закрытии phase. Предел180/360/1GiB/64MiB
не повышался. Worker/tree peaks и поиск коротких процессов sampled, не OS hard
quota; supervisor peak теперь измерен, в отличие от383. Подготовка worktree/
копирование зависимостей и software tests учитываются отдельно от science phase.

Дополнительный расширенный post-audit был предложен уже после закрытия фазы;
его preflight увидел332.616s от исходного старта и отказал по раннему320s окну.
Он не запускался, бюджет не сбрасывался, научные данные не пересчитывались.
Обязательный независимый аудит выше уже завершился внутри36.314s. Нет заявления
дополнительного побитового сравнения с historical376 или независимой векторной
сверки каждого journal entry, которые предполагал этот необязательный скрипт.

30 технических/reference tests,22candidate-native preflight tests и8 новых
observer/evidence checks прошли. Исторические13input/evidence/native/LATEST SHA
сверены после работы и совпали; физический код/старые данные не изменены.

## Восстановление и следующий этап

Создать отдельный checkout указанной кандидатной ветки/commit; developer dev
не переключать. Восстановить точную Python/ABI/dependency/native среду по
freeze/environment и проверить каждый SHA. Native из383 wheel имеет исходный
SHA; заново собранный wheel нельзя автоматически считать тем же бинарником.
Команда producer/ресурсный recipe сохранены в архиве этапа. Для read-only
replay компактного evidence без новой интеграции:

```powershell
.venv/Scripts/python.exe -X utf8 -B -m scripts.assess_newton384
```

Этот replay не аттестует текущее окружение. Полный source-bound existing376
verify выполнять только в восстановленном candidate с явными --protocol,
--report и --arrays на файлы evidence. Другая ОС/ABI требует новой квалификации.

[Решения375/380](qualification-033-scope-384.md): старый375 gate не ослаблен,
новый annual successor scope и cross-version compatibility требуют согласования;
для380 исходная монотонность остаётся обязательным scientific gate с3FAIL,
новый прикладной допуск/экспериментальный release scope не утверждён.
**GO** ограниченной Newton-проверки в описанной области; **NO-GO запуску года,
полной Q2/portable acceptance и выпуску в рамках384**. Следующая задача —
утвердить scope будущего годового протокола; самостоятельно дорогие jobs не запускать.
