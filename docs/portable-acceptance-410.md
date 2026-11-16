#410 — допуск полной portable acceptance остановлен на мониторинге

2026-11-16. **PORTABLE ACCEPTANCE NO-GO / PARTIAL. Полная410 не начиналась.**
Причина — подтверждённый дефект lifecycle/cleanup зафиксированного supervisor,
а не численный FAIL Solar. [Машинный отчёт](portable-acceptance-410.json),
[execution plan](../scripts/qualification410/execution-plan.json),
[исходные результаты](../scripts/qualification410/README.md).

## Проверенный объект и выполненная работа

ZIP `SolarSimulator-0.4.0-20261116-4095.zip`,114633711B,
SHA256 `33114f5ac2234e01e1e248fae757187a50a81020e2b225ee6b746e28e1073e33`.
6005members CRC/SHA совпали с sealed asset contract. Runtime237f736/tree5cf43fd9,
FPf8429486…, nativea2b7e075…/wheel5c2db314…, packagingd04dc9a, currentmanifest9251bc2e…,
verifierefa1a533… и acceptance-toole332fca0… совпали с заданием и frozenplan409.5.
Квалифицированные worktrees чистые. ZIP/native/tooling не изменялись.

Перед дорогим запуском проверена применимость exact monitor
`6ec4c2ac55ff1a56e0a4b229760ae594fa61c00ca864f5b54ac62bf3aca6642b` к
выходу родителя при живом дочернем процессе. Это отдельный bounded synthetic
тест, без Solar imports, орбит и GUI. Родитель создаёт ребёнка и выходит через0.8s;
ребёнок имеет5s self-limit,16MiB allocation и внешнюю cleanup-защиту.

## Подтверждённый FAIL

Монитор вернул `exit_code=0`, `complete=true`, хотя известный ему потомокPID24632
с тем же creation_time оставался жив. Он присутствует в собственном списке
retained process handles. Наблюдался также его interpreterPID10040 сCPU0.953125s.

Причина видна в неизменённом коде: [цикл](../scripts/qualification409/monitor200.py:90)
завершается по состоянию только root; [cleanup](../scripts/qualification409/monitor200.py:117)
убивает дерево только если root ещё жив. При уже вышедшем root эта ветка
пропускается, а [complete](../scripts/qualification409/monitor200.py:146) не требует
завершения потомков. RetainedCPU handles сами по себе не обеспечивают lifecycle.

Независимый read-only auditor сопоставил raw supervisor, PID/creation-time,
фактическую liveness-пробу и исходники; отдельно пересчитал ZIP/nativeSHA/CRC.
Это не вывод по одному PASS/FAIL-флагу.

У первого внешнего cleanup-harness тоже есть ограничение: он убил прямой
venv-launcher, а его interpreter мог доработать до5s self-limit. Последующая
проверка всех известных PID/creation-time подтвердила, что тестовые процессы
завершены. Дополнительный CPU после возврата guard точно не измерен; ему
назначен консервативный allowance6CPU/10wall. Не выдаём это за измеренный CPU.
Оригинальный harness и его реальный отказ сохранены без исправления задним числом.

## Что не выполнено

Свежая relocated-распаковка, GUI/recovery/legacy/CLI/recording workflows,
historical replay410, current040 fresh-year, continuous-year и каталог354:
**NOT_RUN** из-за admission failure. Ошибки положения/скорости/энергии,
Moon–Earth residual, число orbital packets и duration неизвестны, в JSON стоят
null, а не нулевые ошибки. Предыдущий409.5preflight не выдан за scientific PASS.

Не доказаны дефект физического runtime, утечка SolarGUI при штатном закрытии или
аналогичная ошибка в прошлых408/409.5. Доказана непригодность текущего guard к
данному обязательному cleanup-сценарию. Оставшийся worker мог бы продолжать
потреблять CPU/писать результаты после окончания учёта — это риск для полной410.

## Ресурсы и минимальное исправление

[Ledger](../scripts/qualification410/resource-ledger.json): charged37.46875CPU /
71.332329activewall с initial/preflight/cleanup/final allowances; это не полностью
измеренный operationalCPU. Hard900/1200/2GiB/2GiB иearly720/960/1.8GiB/1.8GiB
не менялись, ledger не обнулялся. Монитор sampled, не OSquota. Предсказание650/450
для полного процесса не проверено, поскольку он не запускался.

По условию задания frozen tooling не исправлялся внутри410. Минимальный
следующий этап — отдельная квалификация supervisor revision: после выхода root
проверять известных потомков по PID+creation-time/handles, завершать и ждать их,
снимать finalCPU после cleanup, сохранять receipt и считать неожиданного orphan
отказом. Нужны root0/nonzero/crash/interrupt/timeout и child/grandchild tests,
включая короткоживущие процессы. Kernel job accounting рассматривать при
подтверждённой необходимости, не создавать общий framework автоматически.

После исправления потребуются новый toolingSHA/admission amendment и продолжение
с сохранением уже потраченного410budget. Сам ZIP33114f5a, source237, nativea2b7,
IC/reference/thresholds менять не требуется. Автоматического rerun нет.

Scientific39928/28; D1numerical11/11/effects10/11/distance0.244795m vs10mFAIL,
3historical380+4short402FAIL иfullD1NO-GO неизменны. TwoQ2 экспериментален,
безQ2–Q2/приливов/диссипации/EIHmixed/универсальной ошибки. Выпуск040 — NO-GO.
Main/tag/LATEST/принятая032 не менялись. Новый evidence410 backup готовится
отдельно; уже проверенный ZIP409.5 повторно не загружается. После отчёта STOP.
