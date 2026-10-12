//! Working Newton/EIH point-mass forces in SI, harmonic coordinates.
//! Newtonian source accelerations order-reduce the 1PN terms.
use crate::{dot, norm, sub, Vector3, G};
pub type RelativePair = (usize, usize, Vector3);
pub const MAX_BODIES: usize = 4096;

#[derive(Clone, Copy, Default)]
struct Sum {
    value: Vector3,
    lost: Vector3,
}
impl Sum {
    fn add(&mut self, term: Vector3) {
        for (k, &component) in term.iter().enumerate() {
            let y = component - self.lost[k];
            let next = self.value[k] + y;
            self.lost[k] = (next - self.value[k]) - y;
            self.value[k] = next;
        }
    }
}
struct Pair {
    i: usize,
    j: usize,
    delta: Vector3,
    inv: f64,
}

pub fn acceleration(
    positions: &[Vector3],
    velocities: &[Vector3],
    masses: &[f64],
    light_speed: Option<f64>,
    relative: Option<RelativePair>,
) -> Result<Vec<Vector3>, String> {
    let n = masses.len();
    if n == 0 || n > MAX_BODIES || positions.len() != n || velocities.len() != n {
        return Err("Force arrays require 1..4096 bodies and matching lengths".into());
    }
    if !positions
        .iter()
        .chain(velocities)
        .flatten()
        .all(|v| v.is_finite())
        || masses.iter().any(|m| !m.is_finite() || *m <= 0.0)
    {
        return Err("Force arrays must be finite with positive masses".into());
    }
    let c2 = match light_speed {
        Some(c) if c.is_finite() && c > 0.0 && (c * c).is_finite() && c * c > 0.0 => Some(c * c),
        Some(_) => return Err("Invalid speed of light".into()),
        None => None,
    };
    if let Some((i, j, rho)) = relative {
        if i >= n || j >= n || i == j || !rho.iter().all(|v| v.is_finite()) {
            return Err("Invalid relative pair".into());
        }
    }
    let mu: Vec<_> = masses.iter().map(|m| G * m).collect();
    let mut newton = vec![Sum::default(); n];
    let mut potential = vec![0.0; n];
    let mut pairs = Vec::new();
    if c2.is_some() {
        pairs
            .try_reserve_exact(n * (n - 1) / 2)
            .map_err(|_| "Force allocation failed")?;
    }
    for i in 0..n {
        for j in i + 1..n {
            let mut delta = sub(positions[j], positions[i]);
            if let Some((first, second, rho)) = relative {
                if (i, j) == (first, second) {
                    delta = rho;
                }
                if (j, i) == (first, second) {
                    delta = rho.map(|v| -v);
                }
            }
            let distance = norm(delta);
            if distance == 0.0 {
                return Err("Coincident positions".into());
            }
            if !distance.is_finite() {
                return Err("Overflow in force geometry".into());
            }
            let inv = 1.0 / distance;
            let inv3 = inv * inv * inv;
            newton[i].add(delta.map(|d| mu[j] * inv3 * d));
            newton[j].add(delta.map(|d| -mu[i] * inv3 * d));
            potential[i] += mu[j] * inv;
            potential[j] += mu[i] * inv;
            if c2.is_some() {
                pairs.push(Pair { i, j, delta, inv });
            }
        }
    }
    let mut result: Vec<_> = newton.iter().map(|s| s.value).collect();
    if let Some(c2) = c2 {
        let speed2: Vec<_> = velocities.iter().map(|v| dot(*v, *v)).collect();
        if potential
            .iter()
            .chain(&speed2)
            .any(|v| !v.is_finite() || *v / c2 >= 1e-4)
        {
            return Err("EIH requires U/c^2 and v^2/c^2 < 1e-4".into());
        }
        let mut correction = vec![Sum::default(); n];
        for Pair { i, j, delta, inv } in pairs {
            let cross = dot(velocities[i], velocities[j]);
            for (target, source, x) in [(i, j, delta.map(|d| -d)), (j, i, delta)] {
                let projected = dot(x, velocities[source]) * inv;
                let scalar = 4.0 * potential[target] + potential[source]
                    - speed2[target]
                    - 2.0 * speed2[source]
                    + 4.0 * cross
                    + 1.5 * projected * projected
                    + 0.5 * dot(x, newton[source].value);
                let dv = sub(velocities[target], velocities[source]);
                let weighted_velocity = std::array::from_fn(|k| {
                    4.0 * velocities[target][k] - 3.0 * velocities[source][k]
                });
                let projection = dot(x, weighted_velocity);
                let radial = mu[source] * inv * inv * inv;
                correction[target].add(std::array::from_fn(|k| {
                    radial * (x[k] * scalar + dv[k] * projection)
                        + 3.5 * mu[source] * inv * newton[source].value[k]
                }));
            }
        }
        for i in 0..n {
            for k in 0..3 {
                result[i][k] += correction[i].value[k] / c2;
            }
        }
    }
    if !result.iter().flatten().all(|v| v.is_finite()) || !mu.iter().all(|v| v.is_finite()) {
        return Err("Non-finite acceleration".into());
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn free_particle_and_newton_limit() {
        assert_eq!(
            acceleration(&[[2.0; 3]], &[[0.0; 3]], &[1.0], Some(299792458.0), None).unwrap(),
            vec![[0.0; 3]]
        );
        let p = [[0.0; 3], [10.0, 0.0, 0.0]];
        let v = [[0.0; 3]; 2];
        let a = acceleration(&p, &v, &[2.0, 3.0], None, None).unwrap();
        let b = acceleration(&p, &v, &[2.0, 3.0], Some(1e30), None).unwrap();
        assert_eq!(a, b);
        assert!((a[0][0] - G * 3.0 / 100.0).abs() < 1e-27);
        assert!((2.0 * a[0][0] + 3.0 * a[1][0]).abs() < 1e-27);
    }
    #[test]
    fn pair_override_and_errors() {
        let p = [[0.0; 3]; 2];
        let v = [[0.0; 3]; 2];
        assert!(acceleration(&p, &v, &[1.0, 1.0], None, None).is_err());
        let a = acceleration(&p, &v, &[1.0, 1.0], None, Some((0, 1, [2.0, 0.0, 0.0]))).unwrap();
        assert_eq!(a[0][0], G / 4.0);
        assert!(acceleration(&p, &v, &[1.0, 1.0], None, Some((0, 2, [2.0, 0.0, 0.0]))).is_err());
        assert!(acceleration(&p, &v, &[1.0, 1.0], Some(f64::INFINITY), None).is_err());
        assert!(acceleration(
            &[[0.0; 3]],
            &[[1e8, 0.0, 0.0]],
            &[1.0],
            Some(299792458.0),
            None
        )
        .is_err());
    }
}
