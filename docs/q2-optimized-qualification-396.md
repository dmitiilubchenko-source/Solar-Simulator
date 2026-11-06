# Q2-396: обязательный preflight остановил квалификацию

**NO-GO до основной серии: выполнено 0 из 58 запланированных траекторий.**
Обязательный one-Q2 reference380 не поддерживает K=1 в распаковке результата.
Это дефект измерительного стенда для нового применения, не установленный дефект
R-reuse или рабочего DOP853. Кандидаты, старые reference/пороги/FAIL и протокол395
не изменялись. Новая квалификация оптимизации не получена.

Дата этапа: 2026-11-07. [Машинные результаты](q2-optimized-qualification-396.json).
Основание: неизменный [протокол395](q2-optimized-qualification-protocol-395.md),
SHA256 `ac0f68d13e04c25a344dcc8831b3f6a4bb1696a951b93d1de5fc7ecf698933a3`.
До запуска запечатаны отдельный plan396, 58 job IDs, inputs, source binding,
пределы и правило остановки при отказе K=1. Никакого подбора IC/rtol/эпох.

## Источники и adapter

Dev/origin перед работой: `4e2614d0f4a8265f91c7202a65bcc00780f8151f`.
Чистые отдельные worktrees: baseline `fe0f456f2c7ba3a077eac21fc8413937d6e84fac`,
candidate `f723a2162b4e115378959e244f428529be2d4516`. Оба остались неизменными.
Exact patch394 SHA `df958f9f4c41ad9f3ed57ec2851c30de8b55e608287bd4ebeecfb2f902abbdc6`.
Повторно проверены все394source bindings каждого кандидата; actual imports
относятся к его src, dependencies/native — к исходной384venv. Baseline проверен
старым строгим freeze; новый кандидат — собственными Git blob/materialized SHA.
Старый fingerprint не подставлялся вместо нового.

Python3.14.2t/cp314t, NumPy2.5.1, SciPy1.18.1; OMP/OPENBLAS/MKL=1.
Native SHA `651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091`.
Actual environment равен сохранённому395 profile по всем полям. Важно различать
SHA сериализаций **одного и того же** JSON profile:

|Source|JSON indent2 + LF + newline|Фактический сохранённый файл CRLF|
|---|---|---|
|baseline|`056c4559f48ef170804d3bc13527bbc30deba2f49e9ebaf04f752d5c6c7f795a`|`2edd7288c1f3e67527930f83b75aa8d22ef734ec451ba7a5b3269e5d3527ca9b`|
|candidate|`d1a2e827e6edcf43ceedacbfc3f62ad72b624c2f0f03332326aa0cf6185695c7`|`b667c5083fe1dba7df6d3de72960f3a3a769052e60fd06a6e6c4cd2eaeb8f23d`|

Оба варианта вычислены заново; это пояснение кодировки, не ослабление проверки.
Полные actual profiles, origins, 380array component SHA — в локальном raw backup;
их привязки и численные результаты приведены в machine JSON.

Новый [узкий adapter](../scripts/q2_source_adapter396.py:14) проверяет SHA,
environment/origins, запрещает reuse output и перезапись результата, связывает
payload с commit/plan/environment и отдельным SHA sidecar. Неполная запись
не считается завершённой. Исторический driver380 и его ROOT не подменялись.
`represented/difference` актуального driver побитно по AST совпадают с точным
историческим driver из SHA-проверенного qualification-before383.zip.
Полный executor58jobs сознательно не реализовывался после preflight NO-GO:
эти provenance/output primitives не объявляются готовой научной инфраструктурой.

## Подтверждённый блокер K=1

Неизменный [reference380](../scripts/two_q2_reference380.py:52), SHA256
`174c6529d010bc652f6ec5e5b6dd8aed5202a98b4cbc1c18d4b27d2b5fbbf78a`,
строит RHS по фактическим rotations, но выходные R восстанавливает через
`for k in range(2)`. Для двух тел и одной фигуры состояние имеет6N+12K=24
компоненты; второй блок R начинается за концом массива.

На **точном one-python IC394**, SHA256
`414ea30d4d28e8d07cfd51330bf4f963bec4bee63bbe723435ac1778c73b2baa`,
разрешённый короткий preflight0..0.001s с двумя эпохами и RK45 rtol3e-11/
atol3e-13/max_step50s дал success,8RHS, solution shape(24,2). Затем на **первой
выходной эпохе** возник `ValueError: cannot reshape array of size 0 into shape (3,3)`.
Это не ошибка разрешения RK45, не энергетический FAIL и не действие R-reuse:
тест с подставленным exact initial state и **нулём интегрирований** воспроизводит
ту же ошибку. При K=2 этот синтетический shape-control проходит.
Сохранены traceback, исходное/конечное внутреннее RK45 y, параметры и SHA.
Wrapper только наблюдал результат solve_ivp, возвращая его без изменения;
reference восстановлен после вызова. IC не изменились.

Таким образом, аналитический K=1 контроль и две4000s reference **не выполнены**.
Сокращение обязательной выборки или молчаливая правка range(2) не разрешены.

## Старые scientific результаты остаются старыми

Проверены manifest380, исходные планы, compatibility/initial archives и NPZ380
`51e7c79d7a36547df92959a8614d9d5804232d39c0ebfe5c4a143ecdd6da696a`.
Два сохранённых RK45 reference каждого IC прочитаны без интегрирования;
максимальный компонентный gap —6.255679007211014e-11 для двух тел и
6.778488043859376e-11 для трёх (orientation Frobenius). Оба ниже старого1e-8,
но это согласие уровней, **не строгая граница истинной ошибки** и не разрешение
различий~1e-15. В machine JSON сохранены все четыре компонента обоих gap.

Независимый saved-array audit392 и assessor380 повторно сохранили старую
strict convergence классификацию. Ни одно значение не является новой396orbit:

|Историческая cold cohort|Coarse–Fine max|Standard–Fine max|Старый строгий критерий|
|---|---:|---:|---|
|two-bodies / Python|4.3210537632440276e-15|7.086768132709826e-15|FAIL|
|two-bodies / Rust|7.341808831039677e-15|9.633424121268789e-15|FAIL|
|three-bodies / Python|5.625282158101942e-15|6.215018178946092e-15|FAIL|
|three-bodies / Rust|1.0018532557700625e-14|3.2225167587052165e-15|PASS-control|

Максимумы **исторических reported** drift380: E1.0124318342494197e-13,
L8.022975817886496e-15, P6.997496665605474e-16, rawqnorm1.3322676295501878e-15.
Старые нормировки/пороги остались прежними; эти drift здесь не переизмерялись.
Независимо пересчитаны saved-reference errors/qnorm/convergence.
Decimal80/110 E/P/L и stable SO(3) дополнительно применены только к трём
**начальным** IC (two/three/one): исходники/документы неизменны; максимальное
относительное E-discrepancy с runtime7.569952456472613e-15. Это проверка
наблюдаемых/размерностей SI, не доказательство точности эволюции. Новых E/P/L
drift или source-equivalence результатов для4000s нет.

## Проверки, отказы и ресурсы

35unique pytest PASS:10новых fault/shape checks и25регрессий saved392/observer393;
0skip/xfail. [K=1 reproducer](../tests/test_q2_source_adapter396.py:59) проверяет
ожидаемый отказ; его PASS не превращает reference в пригодный. Проверены wrong
SHA/source/environment/origins, incomplete/corrupt payload/sidecar, повторная запись,
чтение чужого binding; проверки ошибок не меняют исходные файлы.

Первый baseline preflight остановился: новый harness пытался проверить old380
SHA assessor по текущему файлу. Отдельный v2/supplement использовал существующий
строгий `ui_historical_sha`, проверил archive SHA/old evaluator AST. Первый скрипт,
его binding, отказ и output сохранены; старые SHA/планы не редактировались.
Неисполняемые подготовительные ошибки чтения неверного имени report и SyntaxError
генератора supplement исправлены до запуска; научных результатов они не создали.

Все5controlled attempts, включая исходный harness FAIL и K1 NO-GO:
**18.859375CPU s /17.0383077active wall s**. Worker sampled private peak215322624B,
RSS157278208B; supervisor OS peakcommit37519360B. Консервативная сумма отдельных
пиков252841984B не синхронный peak. Надзор50ms, retained final Windows CPU handle;
короткие пики/descendants, outer launcher и последний record-tail CPU могут быть
не полностью охвачены. Это sampled guard, не hard OS quota.
Caps180/360/1GiB/128MiB,early144/288/900MiB/112MiB сохранены; resourceSTOP нет.
Integration/observer/IO не превращались в benchmark: production DOP853/native
calls0, short independent RK45 RHS8. Подробные worker/supervisor timings и output
bytes — в JSON. Read/edit/Git/CI/обязательный backup отдельно от scientific budget.
Оценка39560–130CPU/90–260wall для58jobs остаётся **не аттестованной**: короткий
reference~2.7ms не даёт обоснования throughput4000s. После K1 отказа серия не начиналась.

## Раздельное решение и следующий шаг

|Статус|Результат396|
|---|---|
|SOURCE EQUIVALENCE|NOT RUN для56runtime trajectories; короткий PASS395 не наследуется|
|SCIENTIFIC CRITERIA|NOT RUN для нового кандидата;3historical strict-convergence FAIL сохранены|
|REFERENCE RESOLUTION|Two-Q2 старые gap проходят прежний порог; mandatory one-Q2 FAIL распаковки|
|RELEASE READINESS|NO-GO; A+D1 не утверждена, source/native/GUI/portable acceptance отдельно|

Оптимизация не отклоняется как ошибочная без доказательства её дефекта, но
внедрять её на основании396 нельзя. Минимальный следующий отдельный этап:
изолированная K=1 адаптация только unpacker reference с новой provenance,
проверка неизменности K=2 output/RHS и аналитических zero-Q/rotation controls K=1,
затем новый sealed preflight/budget перед **прежними58jobs**. Оригинальный
reference380, протокол395, receipts и FAIL сохранить. Здесь эта правка не сделана.

Production Python/Rust, оба кандидата, main/tag/LATEST/portable032 не менялись.
Годовой385/Newton384/compatibility/fullcheck/portable не запускались. После отчёта STOP.
