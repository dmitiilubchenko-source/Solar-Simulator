# Ten-body EIH + fixed J2 year: protocol 187

Declared before new trajectories, 15 October 2026. Research comparison only;
runtime, defaults, saved schema and optional dependencies remain unchanged.

The strict checkpoint defines ten point masses, SI, SSB, Ecliptic J2000,
JD 2461321.5 TDB. Preserve masses, states, body order, full order-reduced
harmonic EIH acceleration and the existing additive Newtonian Sun/Earth J2,
including reaction. Axes are fixed; no spin, tides, contacts or new PN×J2 force.
Outer giant masses are system barycentres; no extra satellite masses.

Use exactly the 125 cached epochs over 31557600 s. All candidates preserve
controller state and end at the same packet20 boundaries (499), with exact
output epochs and no dense-output substitute. Compare native DOP853
rtol=3e-14, xatol=1e-3 m, vatol=1e-9 m/s; the previously declared tighter
1e-7 m / 1e-13 m/s settings; optional REBOUND 5.2.2 IAS15 epsilon=1e-9 and
1e-11, PRS23, min_dt=0, initial dt=18 s, full velocity-dependent callback,
gravity=none. Epsilon and rtol are different controls.

Accept the existing independent RK45 scalar-Rust EIH + independent tensor J2
reference only after SHA, origin, physical settings, checkpoint/profile IC,
mass, order, shape, finite values, time grid and initial roundtrip checks.
The public continuous-integration NPZ carries the reference. A separate local
lineage check compares it bitwise with historical reference139/production139.
Do not substitute the Newton-only or EIH-only oracle. No expensive reference
recomputation is required for an unchanged model and verified cache.

Reference refinement 1800→900 s gave 0.098722587 m / 1.8868315e-8 m/s
over all bodies, 0.0030404212 m / 8.3952690e-9 m/s for Moon−Earth.
These are empirical sensitivities, not rigorous bounds. Reference gates:
<1 m / 1e-6 m/s all, <0.01 m / 1e-7 m/s relative Moon.
Initial reference roundtrip: <0.002 m / 1e-8 m/s all and <0.0001 m
relative Moon. Do not overwrite the cached first state to hide roundoff.

Numerical candidate gates: every body <10 m / 1e-4 m/s, Moon−Earth
<0.1 m / 1e-5 m/s against the matched reference. Also require finite output,
bitwise repeats, identical IC and boundaries. Baseline must reproduce the
old public year_continuous array bitwise. Preserve every failure; do not
change thresholds, refit states or select settings by JPL residual.

After free integration, verify pinned dense JPL vectors and all 40 raw
responses with the original parser, origin, IDs, TDB epochs, SI and overlaps.
Separate goals: <10 km each body and <1 km Moon−Earth at those 125 epochs.
This is a residual against DE441, not observational or full physical accuracy.

Cost: one repeat/warmup, then three alternating-order full trajectories per
candidate; include setup/callbacks/125 snapshots and exclude hashing,
reference/JPL loading, reporting and diagnostics. Retain all raw times,
medians and RHS/callback counters; IAS steps_done includes rejected steps.
Verify actual native .pyd, REBOUND loaded shared library, Python sources and
inputs before/after. Do not generalize timings to GUI/FPS or other hardware.

The cached reference has no torque/PN²/PN×J2 source integrals. This audit
therefore does not certify annual corrected E/P/J budgets or impose constant
raw orbital angular momentum/1PN energy. Model-specific balance checks are
documented in [the prior audit](fixed-j2-ias-validation.md). Fixed axes exert
orbital torque; additive EIH+Newtonian J2 has mixed truncation sources.

Equations and assumptions: [Park et al. 2021, §3.2](https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf),
[EIH action derivation](https://fiteoweb.unige.ch/~maggiore/GWVol1/EIHLagrangian.pdf),
[IAS15 original paper](https://arxiv.org/abs/1409.4779).
These support model definitions, not a claim of equivalence to full DE441.
