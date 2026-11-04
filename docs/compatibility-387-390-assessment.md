# Итоговая совместимость0.3.2 ↔ кандидат0.3.3: область387–390

5 ноября2026. **GO / A,B,C PASS в перечисленной проверенной области.**
Это завершение compatibility gate, не принятие0.3.3 и не универсальная физическая
эквивалентность. Источники: [389фактическое сравнение](compatibility-389-validation.md),
[390последний negative check](compatibility-390-validation.md), их машинные отчёты.

## Что именно сопоставлено

Подлинная accepted032cf653c9 из original portableZIP7c578220…c49/native0cbc389…0601
и immutable candidate033fe0f456/native651e346…091 в отдельном checkout/venv.
Общий явно текущий profile OMP/OPENBLAS/MKL1, остальные3variablesunset;
FP0324d8838ca…f335, FP033056c4559…795a. Это не историческая ОС/unset-replay.
Expected fingerprint differences: application_version,package_files,native.
В сравнении389 Python/dependency/platform/numerical-env части совпали.

| Контракт | Фактическое покрытие | Результат |
|---|---|---|
|A — данные|Generated032legacy1–9, singleQ2schema10,8advancedoldcheckpoints→033; point-mass branch/parent/recovery; recipe/frame integrity|PASS в этой области|
|B — численное поведение|8actualcases:SunEarthVerlet/DOP,SunEarthMoonDOP,oneQ2DOP ×Python/Rust; эпохи0/50/100/150s;16samepacketrestarts|EXACT states/settings/q/S;Δr/Δv/E/P/L0 на фиксированной сетке|
|C — поведение пользователя|ActualTk start/pause/load/save/cancel/corrupt/schema/recovery; knownwrongnative negatives; strictcross-envrecipe отказ;390old032 rejectsnewtwoQ2 безпотеристарогоопыта|PASS для выполненных действий|

Ни один из8cases/restarts не повторялся в390. ДвеQ2 только валидировались и
загружались для отказа, без вычислений. Динамические Q2 branches существующим
контрактом не поддерживаются; проверенные parent/child ветки — point-mass.
Нельзя расширять эти результаты на произвольные старые файлы/все native APIs,
долгие орбиты/контакты/EIH+J2/two-Q2application или global accuracy.

## Промежуточные FAIL/STOP сохранены

387: private-memory startup STOP до IC. 388: default threaded BLAS commit
локализован, отдельные currentlow-thread profiles успешны; originalSTOPнепереписан.
389: TypeError тестового draft (объект вместо directorypath), отдельный исправленный
functional-tail; затем cumulativeCPUstop до old-two test. Все8states/restarts
уже были сохранены и независимо сравнены. Эти FAIL/STOP остаются в исходных
отчётах/логах; статус389PARTIAL не заменяется на PASS.
390: отдельный новый бюджет и исполненный последний GUI/APInegativeконтроль,
независимые file/state/q/S/FP проверки. Именно этот результат завершает цепочку.

## Что остаётся до выпуска0.3.3

- Явное решение владельца A/B по experimentaltwo-Q2 scope, numericB_app и
  reference-uncertainty policy386. Три historicalscientific380FAIL не сняты.
- При усилении GUI-маркировки — новый candidate fingerprint и обоснованный план
  квалификации его изменений; fe0f456 автоматически не обновлять.
- Полная относящаяся source/native/desktop/recovery release acceptance и настоящая
  isolated portable033/ZIP/SHA. Нынешний ограниченный gate их не заменяет.
- Заявленная область numerical profiles должна сохранить ограничения annual385:
  Rust Standard20 имеет отдельный diagnosticFAIL(.113353m>.1m), не входящий
  в обязательный Strict gate. Compatibility не устраняет его и не расширяет
  успешную квалификацию Strict на Standard.
- Отдельное согласование готового результата перед main/tag/release/LATEST.

Newton384 и annual385 сохраняют только свои source-bound области. Их не повторяли
и не распространяли на новую физику. Следующий полезный этап — согласовать release
scope и критерии, затем выполнять оставшуюся приёмку по готовому плану.
