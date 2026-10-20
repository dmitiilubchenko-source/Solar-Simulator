// SPDX-License-Identifier: BSD-3-Clause
// Adapted from the pinned SciPy 1.18.1 rk.py/common.py; see ../LICENSE-SCIPY.txt.
// Solar's existing per-three-vector estimator replaces the global RMS norm.
use crate::coefficients::{A, B, C, E3, E5};
use serde::Serialize;

#[derive(Clone, Copy, Debug)]
pub struct Config {
    pub rtol: f64,
    pub position_atol: f64,
    pub velocity_atol: f64,
    pub work_atol: f64,
    pub first_step: Option<f64>,
    pub max_attempts: usize,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            rtol: 3e-14,
            position_atol: 1e-7,
            velocity_atol: 1e-13,
            work_atol: 1e-15,
            first_step: None,
            max_attempts: 1_000_000,
        }
    }
}
impl Config {
    pub(crate) fn validate_layout(self, size: usize) -> Result<Vec<f64>, String> {
        if size < 6
            || !matches!(size % 6, 0 | 1)
            || !self.rtol.is_finite()
            || !(3e-14..=1e-2).contains(&self.rtol)
            || [self.position_atol, self.velocity_atol, self.work_atol]
                .iter()
                .any(|x| !x.is_finite() || *x <= 0.)
            || self.max_attempts == 0
            || self.first_step.is_some_and(|x| !x.is_finite() || x <= 0.)
        {
            return Err("Invalid state layout or tolerance".into());
        }
        let orbit = size - size % 6;
        let mut atol = vec![self.position_atol; orbit / 2];
        atol.extend(vec![self.velocity_atol; orbit / 2]);
        if orbit != size {
            atol.push(self.work_atol);
        }
        Ok(atol)
    }
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Snapshot {
    pub time: f64,
    pub values: Vec<f64>,
}
#[derive(Clone, Copy, Default, Debug, Serialize)]
pub struct Statistics {
    pub rhs_calls: usize,
    pub accepted: usize,
    pub rejected: usize,
    pub packets: usize,
    pub failed: bool,
}

fn finite(values: &[f64]) -> Result<(), String> {
    if values.iter().all(|x| x.is_finite()) {
        Ok(())
    } else {
        Err("Nonfinite numerical state or derivative".into())
    }
}

/// Joint 5(3) estimate in each block, never two separately aggregated maxima.
pub fn grouped_error(e5: &[f64], e3: &[f64], h: f64) -> Result<f64, String> {
    let size = e5.len();
    if size < 6 || !matches!(size % 6, 0 | 1) || e3.len() != size || !h.is_finite() {
        return Err("Invalid error layout or step".into());
    }
    finite(e5)?;
    finite(e3)?;
    let orbit = size - size % 6;
    let mut worst: f64 = 0.;
    for i in (0..orbit).step_by(3) {
        let a = e5[i].hypot(e5[i + 1]).hypot(e5[i + 2]);
        let b = e3[i].hypot(e3[i + 1]).hypot(e3[i + 2]);
        let denominator = a.hypot(0.1 * b);
        let ratio = if denominator == 0. {
            0.
        } else {
            a / denominator
        };
        let value = (h.abs() * a) * ratio / 3_f64.sqrt();
        if !value.is_finite() {
            return Err("Nonfinite local error estimate".into());
        }
        worst = worst.max(value);
    }
    if orbit != size {
        let a = e5[orbit].abs();
        let denominator = a.hypot(0.1 * e3[orbit]);
        let ratio = if denominator == 0. {
            0.
        } else {
            a / denominator
        };
        let value = (h.abs() * a) * ratio;
        if !value.is_finite() {
            return Err("Nonfinite local error estimate".into());
        }
        worst = worst.max(value);
    }
    if !worst.is_finite() {
        return Err("Nonfinite local error estimate".into());
    }
    Ok(worst)
}

/// Owns partial stages privately. Only complete packet snapshots are exposed.
pub struct Dop853 {
    time: f64,
    values: Vec<f64>,
    f: Vec<f64>,
    k: Vec<Vec<f64>>,
    stage: Vec<f64>,
    trial: Vec<f64>,
    e5: Vec<f64>,
    e3: Vec<f64>,
    atol: Vec<f64>,
    config: Config,
    h_abs: f64,
    committed: Snapshot,
    stats: Statistics,
}
impl Dop853 {
    pub fn new<F>(
        rhs: &mut F,
        start: f64,
        values: Vec<f64>,
        initial_bound: f64,
        config: Config,
    ) -> Result<Self, String>
    where
        F: FnMut(f64, &[f64], &mut [f64]) -> Result<(), String>,
    {
        if !start.is_finite() || start < 0. || !initial_bound.is_finite() || initial_bound <= start
        {
            return Err("Invalid initial time interval".into());
        }
        finite(&values)?;
        let atol = config.validate_layout(values.len())?;
        if config.first_step.is_some_and(|h| h > initial_bound - start) {
            return Err("Invalid first step".into());
        }
        let start = if start == 0. { 0. } else { start };
        let size = values.len();
        let mut f = vec![0.; size];
        rhs(start, &values, &mut f)?;
        finite(&f)?;
        let mut solver = Self {
            time: start,
            committed: Snapshot {
                time: start,
                values: values.clone(),
            },
            values,
            f,
            k: vec![vec![0.; size]; 13],
            stage: vec![0.; size],
            trial: vec![0.; size],
            e5: vec![0.; size],
            e3: vec![0.; size],
            atol,
            config,
            h_abs: 0.,
            stats: Statistics {
                rhs_calls: 1,
                ..Statistics::default()
            },
        };
        solver.h_abs = match config.first_step {
            Some(step) if step.is_finite() && step > 0. && step <= initial_bound - start => step,
            Some(_) => return Err("Invalid first step".into()),
            None => solver.initial_step(rhs, initial_bound)?,
        };
        Ok(solver)
    }
    fn initial_step<F>(&mut self, rhs: &mut F, bound: f64) -> Result<f64, String>
    where
        F: FnMut(f64, &[f64], &mut [f64]) -> Result<(), String>,
    {
        let mut d0: f64 = 0.;
        let mut d1: f64 = 0.;
        for i in 0..self.values.len() {
            let scale = self.atol[i] + self.config.rtol * self.values[i].abs();
            if !scale.is_finite() || scale <= 0. {
                return Err("Invalid initial scale".into());
            }
            d0 = d0.hypot(self.values[i] / scale);
            d1 = d1.hypot(self.f[i] / scale);
        }
        let count = (self.values.len() as f64).sqrt();
        d0 /= count;
        d1 /= count;
        if !d0.is_finite() || !d1.is_finite() {
            return Err("Nonfinite initial norm".into());
        }
        let h0 = (if d0 < 1e-5 || d1 < 1e-5 {
            1e-6
        } else {
            0.01 * d0 / d1
        })
        .min(bound - self.time);
        if !h0.is_finite() || h0 <= 0. {
            return Err("Initial step below floating resolution".into());
        }
        for i in 0..self.values.len() {
            self.stage[i] = self.values[i] + h0 * self.f[i];
        }
        finite(&self.stage)?;
        self.stats.rhs_calls += 1;
        rhs(self.time + h0, &self.stage, &mut self.trial)?;
        finite(&self.trial)?;
        let mut d2: f64 = 0.;
        for i in 0..self.values.len() {
            let scale = self.atol[i] + self.config.rtol * self.values[i].abs();
            d2 = d2.hypot((self.trial[i] - self.f[i]) / scale);
        }
        d2 = d2 / count / h0;
        if !d2.is_finite() {
            return Err("Nonfinite initial derivative norm".into());
        }
        let h1 = if d1 <= 1e-15 && d2 <= 1e-15 {
            1e-6_f64.max(h0 * 1e-3)
        } else {
            (0.01 / d1.max(d2)).powf(1. / 8.)
        };
        Ok((100. * h0).min(h1).min(bound - self.time))
    }
    pub fn current(&self) -> Snapshot {
        self.committed.clone()
    }
    pub fn statistics(&self) -> Statistics {
        self.stats
    }

    pub fn advance_to<F>(&mut self, end: f64, rhs: &mut F) -> Result<Snapshot, String>
    where
        F: FnMut(f64, &[f64], &mut [f64]) -> Result<(), String>,
    {
        if !end.is_finite() || end < self.committed.time {
            return Err("Invalid forward endpoint".into());
        }
        if self.stats.failed {
            return Err("Failed session; restart from the committed snapshot".into());
        }
        if end == self.committed.time {
            return Ok(self.current());
        }
        if let Err(error) = self.integrate(end, rhs) {
            self.stats.failed = true;
            return Err(error);
        }
        self.committed = Snapshot {
            time: self.time,
            values: self.values.clone(),
        };
        self.stats.packets += 1;
        Ok(self.current())
    }
    fn integrate<F>(&mut self, end: f64, rhs: &mut F) -> Result<(), String>
    where
        F: FnMut(f64, &[f64], &mut [f64]) -> Result<(), String>,
    {
        let mut attempts = 0;
        while self.time < end {
            let min_step = 10. * (f64::from_bits(self.time.to_bits() + 1) - self.time);
            let mut h_abs = self.h_abs.max(min_step);
            let mut rejected = false;
            loop {
                if attempts >= self.config.max_attempts {
                    return Err("Packet attempt limit exceeded".into());
                }
                attempts += 1;
                if !h_abs.is_finite() || h_abs < min_step {
                    return Err("Step below floating resolution".into());
                }
                let next = (self.time + h_abs).min(end);
                let h = next - self.time;
                if h <= 0. {
                    return Err("Endpoint below floating resolution".into());
                }
                self.k[0].copy_from_slice(&self.f);
                for s in 1..12 {
                    for i in 0..self.values.len() {
                        let mut sum = 0.;
                        for j in 0..s {
                            sum += A[s][j] * self.k[j][i];
                        }
                        self.stage[i] = self.values[i] + h * sum;
                    }
                    finite(&self.stage)?;
                    self.stats.rhs_calls += 1;
                    rhs(self.time + C[s] * h, &self.stage, &mut self.k[s])?;
                    finite(&self.k[s])?;
                }
                for i in 0..self.values.len() {
                    let mut sum = 0.;
                    for j in 0..12 {
                        sum += B[j] * self.k[j][i];
                    }
                    self.trial[i] = self.values[i] + h * sum;
                }
                finite(&self.trial)?;
                self.stats.rhs_calls += 1;
                rhs(next, &self.trial, &mut self.k[12])?;
                finite(&self.k[12])?;
                for i in 0..self.values.len() {
                    let scale = self.atol[i]
                        + self.config.rtol * self.values[i].abs().max(self.trial[i].abs());
                    if !scale.is_finite() || scale <= 0. {
                        return Err("Invalid trial scale".into());
                    }
                    let mut e5 = 0.;
                    let mut e3 = 0.;
                    for j in 0..13 {
                        e5 += E5[j] * self.k[j][i];
                        e3 += E3[j] * self.k[j][i];
                    }
                    self.e5[i] = e5 / scale;
                    self.e3[i] = e3 / scale;
                }
                let error = grouped_error(&self.e5, &self.e3, h)?;
                if error < 1. {
                    let mut factor = if error == 0. {
                        10.
                    } else {
                        (0.9 * error.powf(-1. / 8.)).min(10.)
                    };
                    if rejected {
                        factor = factor.min(1.);
                    }
                    self.h_abs = h * factor;
                    self.time = next;
                    self.values.copy_from_slice(&self.trial);
                    self.f.copy_from_slice(&self.k[12]);
                    self.stats.accepted += 1;
                    break;
                }
                self.stats.rejected += 1;
                rejected = true;
                h_abs = h * (0.9 * error.powf(-1. / 8.)).max(0.2);
            }
        }
        Ok(())
    }
}
