# Уточнение статуса версий на28 октября2026

**Исходники `main` соответствуют0.3.2, несмотря на заголовок README0.3.1.**
Это расхождение документации, не доказательство отката кода. GitHub Release
и публикация ZIP — отдельные действия, их нельзя выводить из существования тега.

| Проверка | Наблюдение |
|---|---|
| `origin/main` | `cf653c9ca4b60649e70658b002a5e70669411266` |
| Annotated `v0.3.2` | tag object `fabc702958cfb7ec6f8e3f0fcbd1c3a51a57d816`, peeled commit тот жеcf653c9 |
| Metadata этого дерева | pyproject, solar_core и solar_native:0.3.2 |
| README этого дерева | всё ещё `# Solar Simulator 0.3.1`; docs/README также содержит старое обозначение |
| `v0.3.1` | сохранён, peeled commit `e74d73ed71276771d3177fad207e2dd17ca8894f` |
| Исторический acceptance0.3.2 | `product_acceptance_passed=true`, источник/native/изолированная portable проверены до согласования публикации |
| Принятый локальный ZIP |112312650bytes, SHA256 `7c578220ec77e792aa9589f32a30352e88277d0d096bff0ad3ca5aae9c014c49`; наличие и SHA повторно проверены |
| Публичный GitHub Releases API | перечисляет только `v0.2.0`; опубликованный Release0.3.2 не обнаружен; черновики не проверялись |

Полные наблюдения и SHA: [release-status-20261028.json](release-status-20261028.json).
Основные Git-свидетельства: [commit0.3.2](https://github.com/dmitiilubchenko-source/Solar-Simulator/commit/cf653c9ca4b60649e70658b002a5e70669411266),
[README в этом commit](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/cf653c9ca4b60649e70658b002a5e70669411266/README.md),
[pyproject в этом commit](https://github.com/dmitiilubchenko-source/Solar-Simulator/blob/cf653c9ca4b60649e70658b002a5e70669411266/pyproject.toml),
[публичный Releases API](https://api.github.com/repos/dmitiilubchenko-source/Solar-Simulator/releases?per_page=100).

Поле `prepared-in-dev; main/tag require user approval` в старом
[release-032-validation.json](release-032-validation.json) описывает момент
приёмки до последующего размещения `main`/тега. Оно не переписывалось;
[описание кандидата](releases/v0.3.2.md) также сохранено как исторический документ.
Актуальный вывод: **принятие исходников0.3.2 в main/tag подтверждено; публичная
публикация GitHub Release/ZIP0.3.2 не подтверждена.** Локальный принятый ZIP
не означает, что пользователь может скачать его из GitHub Releases.

Повторная read-only проверка:

```powershell
git ls-remote origin refs/heads/main refs/tags/v0.3.1 refs/tags/v0.3.2 'refs/tags/v0.3.1^{}' 'refs/tags/v0.3.2^{}'
git show cf653c9:pyproject.toml
git show cf653c9:README.md
```

На этом этапе `main`, теги, принятый ZIP и старые отчёты не изменяются.
Новое расширение пользовательской диагностики отправляется только в `dev`;
оно само по себе не является новым релизом или portable-приёмкой.
