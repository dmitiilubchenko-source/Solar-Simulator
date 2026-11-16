#410 admission failure — no full portable execution

`execution-plan.json` is a new immutable conditional execution plan referencing
unchanged409.5plan-v3 and explicit owner authorization. It was not edited after
the failed admission probe. No annual/continuous simulation was started.

- `preflight.py/json`: actual exact ZIP6005CRC/SHA/source/native/tooling checks.
- `monitor_contract.py/json`: executed bounded root-exit/known-live-descendant
  fixture for exact frozen monitor. It FAILed; production admission stops.
  The executed source SHA is preserved in post-cleanup-audit.json. Do not silently
  repair/relabel this historical attempt. Its first cleanup killed a direct
  launcher, so extra finite interpreter CPU is conservatively charged, not measured.
- `audit.py` / `independent-audit.json`: read-only actual ZIP/code/raw PID/liveness
  audit and confirmation all known test processes are gone. Not full acceptance.
- `resource-ledger.json`: all attempts and explicit allowances. Preserve spent
  budget across any separately authorized monitor correction/resume.

Raw: `C:/Users/Admin/Documents/Codex/Solar410-20261116`.
The five-second fixture is not an unbounded background service. A monitor PASS
for a network worker did not prove descendant cleanup for portable GUI/recovery.
Do not rerun the full acceptance or modify pinned monitor/ZIP/native/thresholds.
See [report](../../docs/portable-acceptance-410.md) for minimal next-fix impact.
