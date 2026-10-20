//! Numerical coordinate adapter; gravity is the existing solar_core function.
use crate::{Config, Dop853, Snapshot, Statistics};
use serde::Serialize;
use solar_core::relativity::{acceleration, MAX_BODIES};

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct PhysicalSnapshot {
    pub time: f64,
    pub states: Vec<[f64; 6]>,
}

#[derive(Clone, Copy)]
struct Pair {
    first: usize,
    second: usize,
    first_fraction: f64,
    second_fraction: f64,
}

fn sum(values: impl Iterator<Item = f64>) -> f64 {
    let mut total: f64 = 0.;
    let mut lost = 0.;
    for x in values {
        let next = total + x;
        lost += if total.abs() >= x.abs() {
            (total - next) + x
        } else {
            (x - next) + total
        };
        total = next;
    }
    total + lost
}

fn decode(values: &[[f64; 3]], pair: Option<Pair>) -> Vec<[f64; 3]> {
    let mut decoded = values.to_vec();
    if let Some(p) = pair {
        for k in 0..3 {
            decoded[p.first][k] = values[p.first][k] - p.second_fraction * values[p.second][k];
            decoded[p.second][k] = values[p.first][k] + p.first_fraction * values[p.second][k];
        }
    }
    decoded
}
fn rhs(masses: &[f64], pair: Option<Pair>, state: &[f64], out: &mut [f64]) -> Result<(), String> {
    let n = masses.len();
    let positions: Vec<[f64; 3]> = state[..3 * n]
        .chunks_exact(3)
        .map(|v| [v[0], v[1], v[2]])
        .collect();
    let velocities: Vec<[f64; 3]> = state[3 * n..]
        .chunks_exact(3)
        .map(|v| [v[0], v[1], v[2]])
        .collect();
    let displacement = pair.map(|p| (p.first, p.second, positions[p.second]));
    let p = decode(&positions, pair);
    let v = decode(&velocities, pair);
    let mut force = acceleration(&p, &v, masses, None, displacement)?;
    if let Some(p) = pair {
        for k in 0..3 {
            let relative = force[p.second][k] - force[p.first][k];
            force[p.first][k] += p.second_fraction * relative;
            force[p.second][k] = relative;
        }
    }
    out[..3 * n].copy_from_slice(&state[3 * n..]);
    for (i, a) in force.iter().enumerate() {
        out[3 * n + 3 * i..3 * n + 3 * i + 3].copy_from_slice(a);
    }
    Ok(())
}

pub struct NewtonRun {
    masses: Vec<f64>,
    pair: Option<Pair>,
    center: [f64; 3],
    drift: [f64; 3],
    start: f64,
    horizon: f64,
    initial: Vec<f64>,
    solver: Option<Dop853>,
    config: Config,
    committed: PhysicalSnapshot,
    failed: bool,
    packets: usize,
    force_calls: usize,
}
impl NewtonRun {
    pub fn new(
        masses: Vec<f64>,
        states: Vec<[f64; 6]>,
        start: f64,
        horizon: f64,
        relative: Option<[usize; 2]>,
        config: Config,
    ) -> Result<Self, String> {
        let n = masses.len();
        if n == 0
            || n > MAX_BODIES
            || states.len() != n
            || !start.is_finite()
            || start < 0.
            || !horizon.is_finite()
            || horizon < start
            || masses.iter().any(|m| !m.is_finite() || *m <= 0.)
            || states.iter().flatten().any(|x| !x.is_finite())
        {
            return Err("Invalid Newtonian input".into());
        }
        let max = masses.iter().copied().fold(0_f64, f64::max);
        let mut weights: Vec<f64> = masses.iter().map(|m| m / max).collect();
        let total = sum(weights.iter().copied());
        for value in &mut weights {
            *value /= total;
        }
        let pair = if let Some([first, second]) = relative {
            if first >= n || second >= n || first == second {
                return Err("Invalid pair indices".into());
            }
            let scale = masses[first].max(masses[second]);
            let a = masses[first] / scale;
            let b = masses[second] / scale;
            let pa = a / (a + b);
            let pb = b / (a + b);
            if pa <= 0. || pb <= 0. {
                return Err("Pair mass ratio not representable".into());
            }
            Some(Pair {
                first,
                second,
                first_fraction: pa,
                second_fraction: pb,
            })
        } else {
            None
        };
        let center =
            std::array::from_fn(|k| sum(states.iter().zip(&weights).map(|(s, w)| s[k] * w)));
        let drift =
            std::array::from_fn(|k| sum(states.iter().zip(&weights).map(|(s, w)| s[k + 3] * w)));
        let mut initial = vec![0.; 6 * n];
        for (i, s) in states.iter().enumerate() {
            for k in 0..3 {
                initial[3 * i + k] = s[k] - center[k];
                initial[3 * n + 3 * i + k] = s[k + 3] - drift[k];
            }
        }
        if let Some(p) = pair {
            for k in 0..6 {
                let offset = if k < 3 { 0 } else { 3 * n };
                let index = k % 3;
                let relative = states[p.second][k] - states[p.first][k];
                initial[offset + 3 * p.first + index] += p.second_fraction * relative;
                initial[offset + 3 * p.second + index] = relative;
            }
        }
        if initial.iter().any(|x| !x.is_finite()) {
            return Err("Nonfinite transformed state".into());
        }
        // Configuration validation is shared with the solver, even at zero horizon.
        config.validate_layout(6 * n)?;
        Ok(Self {
            masses,
            pair,
            center,
            drift,
            start,
            horizon,
            initial,
            solver: None,
            config,
            committed: PhysicalSnapshot {
                time: start,
                states,
            },
            failed: false,
            packets: 0,
            force_calls: 0,
        })
    }
    pub fn current(&self) -> PhysicalSnapshot {
        self.committed.clone()
    }
    pub fn statistics(&self) -> Statistics {
        let mut stats = self
            .solver
            .as_ref()
            .map(|s| s.statistics())
            .unwrap_or_default();
        stats.rhs_calls = self.force_calls;
        stats.packets = self.packets;
        stats.failed = self.failed;
        stats
    }
    pub fn advance_to(&mut self, end: f64) -> Result<PhysicalSnapshot, String> {
        if !end.is_finite() || end < self.committed.time || end > self.horizon {
            return Err("Invalid Newton packet endpoint".into());
        }
        if self.failed {
            return Err("Failed Newton session; restart from checkpoint".into());
        }
        if end == self.committed.time {
            return Ok(self.current());
        }
        let local = end - self.start;
        if self.start + local != end {
            return Err("Newton packet time not representable".into());
        }
        let result = {
            let masses = &self.masses;
            let pair = self.pair;
            let calls = &mut self.force_calls;
            let mut function = |_: f64, state: &[f64], out: &mut [f64]| {
                *calls += 1;
                rhs(masses, pair, state, out)
            };
            let solver = &mut self.solver;
            let initial = &self.initial;
            let config = self.config;
            (|| -> Result<Snapshot, String> {
                if solver.is_none() {
                    *solver = Some(Dop853::new(
                        &mut function,
                        0.,
                        initial.clone(),
                        local,
                        config,
                    )?);
                }
                solver
                    .as_mut()
                    .ok_or("Missing solver")?
                    .advance_to(local, &mut function)
            })()
        };
        let reconstructed = result.and_then(|state| {
            let n = self.masses.len();
            let p: Vec<[f64; 3]> = state.values[..3 * n]
                .chunks_exact(3)
                .map(|a| [a[0], a[1], a[2]])
                .collect();
            let v: Vec<[f64; 3]> = state.values[3 * n..]
                .chunks_exact(3)
                .map(|a| [a[0], a[1], a[2]])
                .collect();
            let p = decode(&p, self.pair);
            let v = decode(&v, self.pair);
            let states: Vec<[f64; 6]> = (0..n)
                .map(|i| {
                    std::array::from_fn(|k| {
                        if k < 3 {
                            p[i][k] + self.center[k] + self.drift[k] * local
                        } else {
                            v[i][k - 3] + self.drift[k - 3]
                        }
                    })
                })
                .collect();
            if states.iter().flatten().any(|x| !x.is_finite()) {
                return Err("Nonfinite physical snapshot".into());
            }
            Ok(PhysicalSnapshot { time: end, states })
        });
        match reconstructed {
            Ok(snapshot) => {
                self.committed = snapshot;
                self.packets += 1;
                Ok(self.current())
            }
            Err(error) => {
                self.failed = true;
                Err(error)
            }
        }
    }
}
