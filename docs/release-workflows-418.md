# Матрица418 —33сценария

Короткие синтетические IC этапа380: A=1e15kg,B=2e14kg,r=12000m, шаг выдачи50s, горизонт100s. Для1Q2 используется только фигураA; rtol1e-11,atol_x1e-7m,atol_v1e-11m/s; Newton/relativepairA–B. Это изменение состава учебной модели, не подмена старого сохранения.

| Динамических Q2 | Действие | Backend | Ожидание | Факт |
|---|---|---|---|---|
| 0 | create | python/rust | 0 rotations | PASS |
| 0 | save | python/rust | exact checkpoint | PASS |
| 0 | load | python/rust | exact state | PASS |
| 0 | start | python/rust | time50s | PASS |
| 0 | stop | python/rust | committed stopped checkpoint | PASS |
| 0 | continue | python/rust | same-packet exact100s | PASS |
| 0 | checkpoint | python/rust | exact restored q/S | PASS |
| 0 | export | python/rust | orbital CSV and full JSON | PASS |
| 0 | native | rust | real compiled point_acceleration calls | PASS |
| 0 | legacy | rust | load old0Q2 without write | PASS |
| 0 | invalid | python/rust | ValueError | PASS |
| 1 | create | python/rust | 1 rotations | PASS |
| 1 | save | python/rust | exact checkpoint | PASS |
| 1 | load | python/rust | exact state | PASS |
| 1 | start | python/rust | time50s | PASS |
| 1 | stop | python/rust | committed stopped checkpoint | PASS |
| 1 | continue | python/rust | same-packet exact100s | PASS |
| 1 | checkpoint | python/rust | exact restored q/S | PASS |
| 1 | export | python/rust | orbital CSV and full JSON | PASS |
| 1 | native | rust | real compiled point_acceleration calls | PASS |
| 1 | legacy | python | load old1Q2 without write | PASS |
| 1 | invalid | python/rust | ValueError | PASS |
| 2 | create | python | отказбезинтеграции | PASS |
| 2 | save | python | отказбезинтеграции | PASS |
| 2 | load | python | отказбезинтеграции | PASS |
| 2 | start | python | отказбезинтеграции | PASS |
| 2 | stop | python | отказбезинтеграции | PASS |
| 2 | continue | python | отказбезинтеграции | PASS |
| 2 | checkpoint | python | отказбезинтеграции | PASS |
| 2 | export | python | отказбезинтеграции | PASS |
| 2 | native | rust | отказбезинтеграции | PASS |
| 2 | legacy | python | отказбезинтеграции | PASS |
| 2 | invalid | python | отказбезинтеграции | PASS |

Положительные APIслучаи реально рассчитывают два50sпакета. Отдельно записаны три кадра0/50/100s и воспроизведён exactrecipe; stopAPIфиксирует recoveryна границе, а настоящий GUIостанавливает/дожидается пакет через штатные кнопки. Nativeвызовы point_acceleration перехвачены счётчиком с вызовом реального compiledоригинала.
Legacy0: schema9из исходной portable; Legacy1: принятая checkpoint389 time50s (SHA bdb3ec1147785014646a8656bc38a5762c85d0ad5fb6c3f9d127b2a70f18c1dc). Старые файлы до/после побитно равны. CLIположительные сценарии покрывает полныйtest_cli; новые5отрицательных команд проверяют общийloadguard.
GUI:4видимых normalTkокна/сценария, настоящие ttk.Button.invoke и обработчики. Filechooser/error-dialog ответы инструментированы; это не ручная приёмка владельца. Снимки окна сохранены локально. Cancelне меняет опыт/q/S/допуски. Негативныйload2оставляет текущий100sопыт и исходный файл без изменений.
Полные входы/ожидания/факты/логи находятся в локальномworkflow-matrix.json и архиве418; публичный отчёт не включает личные recoveryпути.

Независимый Decimal80пересчёт0/1при100s: maxrelativeΔE=1.120e-14, maxnormalizedΔP=6.543e-17, maxrelativeΔL=5.366e-16, max|qnorm−1|=5.132e-17. Это дрейф инвариантов, не глобальная ошибка траектории.

## Итог распакованного кандидата
4положительных0/1backendсценария PASS;15APIотказов и5CLIотказов(-Xutf8) PASS;4видимых GUIсценария PASS. Подтверждён defaultredirectedCLI Unicodeescape без-Xutf8. Это не снимает NO-GO полногоcheck_portable: строгийстарыйгодовойdriver отказал доинтегрирования, continuousпоздняяфаза NOT_RUN. ZIPSHA8253c586…81dc6.
