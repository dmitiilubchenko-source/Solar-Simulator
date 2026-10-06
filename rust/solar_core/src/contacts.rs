//! Contact of spheres along the quadratic position curve of a Verlet step.
//! Roots on [0,1] are isolated using derivative extrema, then bisected.
use super::{accelerations, add, dot, evolve, mul, norm, sub, validate, Body};

#[derive(Clone, Debug)]
pub struct Contact {
    pub first: usize,
    pub second: usize,
    pub time: f64,
}

#[derive(Debug)]
pub struct RunResult {
    pub bodies: Vec<Body>,
    pub time: f64,
    pub contact: Option<Contact>,
}

fn value(coefficients: &[f64], x: f64) -> f64 {
    coefficients.iter().rev().fold(0.0, |sum, c| sum * x + c)
}

// Unlike complex-root solvers, derivative isolation explicitly checks tangencies.
fn roots_in_unit_interval(coefficients: &[f64]) -> Vec<f64> {
    let scale = coefficients.iter().map(|c| c.abs()).fold(0.0, f64::max);
    if scale == 0.0 {
        return vec![0.0];
    }
    let mut p: Vec<f64> = coefficients.iter().map(|c| c / scale).collect();
    while p.len() > 1 && p.last().unwrap().abs() <= 1e-14 {
        p.pop();
    }
    if p.len() == 1 {
        return vec![];
    }
    if p.len() == 2 {
        let x = -p[0] / p[1];
        return if (-1e-12..=1.0 + 1e-12).contains(&x) {
            vec![x.clamp(0.0, 1.0)]
        } else {
            vec![]
        };
    }
    let derivative: Vec<f64> = p
        .iter()
        .enumerate()
        .skip(1)
        .map(|(i, c)| *c * i as f64)
        .collect();
    let mut points = vec![0.0];
    points.extend(roots_in_unit_interval(&derivative));
    points.push(1.0);
    points.sort_by(f64::total_cmp);
    points.dedup_by(|a, b| (*a - *b).abs() < 1e-14);
    let mut roots: Vec<f64> = points
        .iter()
        .copied()
        .filter(|x| value(&p, *x).abs() <= 1e-14)
        .collect();
    for interval in points.windows(2) {
        let (mut left, mut right) = (interval[0], interval[1]);
        let mut fleft = value(&p, left);
        let fright = value(&p, right);
        if fleft == 0.0 || fright == 0.0 || fleft.is_sign_positive() == fright.is_sign_positive() {
            continue;
        }
        for _ in 0..60 {
            let mid = (left + right) * 0.5;
            let fmid = value(&p, mid);
            if fmid == 0.0 {
                left = mid;
                right = mid;
                break;
            }
            if fleft.is_sign_positive() == fmid.is_sign_positive() {
                left = mid;
                fleft = fmid;
            } else {
                right = mid;
            }
        }
        roots.push((left + right) * 0.5);
    }
    roots.sort_by(f64::total_cmp);
    roots.dedup_by(|a, b| (*a - *b).abs() < 1e-12);
    roots
}

fn validate_input(bodies: &[Body], radii: &[f64], dt: f64) -> Result<(), String> {
    validate(bodies)?;
    if !dt.is_finite() || dt <= 0.0 {
        return Err("Invalid time step".into());
    }
    if radii.len() != bodies.len() || !radii.iter().all(|r| r.is_finite() && *r >= 0.0) {
        return Err("Radii must match bodies and be finite and nonnegative".into());
    }
    Ok(())
}

pub fn first_contact(bodies: &[Body], radii: &[f64], dt: f64) -> Result<Option<Contact>, String> {
    first_contact_mode(bodies, radii, dt, false)
}

pub fn first_contact_mode(
    bodies: &[Body],
    radii: &[f64],
    dt: f64,
    incoming_only: bool,
) -> Result<Option<Contact>, String> {
    validate_input(bodies, radii, dt)?;
    let mut pairs = Vec::new();
    for i in 0..bodies.len() {
        for j in i + 1..bodies.len() {
            let radius = radii[i] + radii[j];
            if !radius.is_finite() {
                return Err("Radius sum overflow".into());
            }
            if radius == 0.0 {
                continue;
            }
            let delta = sub(bodies[j].position, bodies[i].position);
            let distance = norm(delta);
            if incoming_only {
                if distance < radius * (1.0 - 1e-7) {
                    return Err("Deep sphere overlap".into());
                }
                if (distance - radius).abs() <= radius * 1e-12 {
                    let speed = dot(sub(bodies[j].velocity, bodies[i].velocity), delta);
                    if speed < 0.0 {
                        return Ok(Some(Contact {
                            first: i,
                            second: j,
                            time: 0.0,
                        }));
                    }
                    if speed == 0.0 {
                        return Err("Resting contact needs constraint forces".into());
                    }
                }
            } else if distance <= radius {
                return Ok(Some(Contact {
                    first: i,
                    second: j,
                    time: 0.0,
                }));
            }
            pairs.push((i, j, radius));
        }
    }
    if pairs.is_empty() {
        return Ok(None);
    }
    let a = accelerations(bodies)?;
    let mut earliest: Option<Contact> = None;
    for (i, j, radius) in pairs {
        let mut q = [
            sub(bodies[j].position, bodies[i].position),
            mul(sub(bodies[j].velocity, bodies[i].velocity), dt),
            mul(sub(a[j], a[i]), 0.5 * dt * dt),
        ];
        if !q.iter().flatten().all(|v| v.is_finite()) {
            return Err("Contact trajectory overflow".into());
        }
        let scale = q.iter().flatten().map(|v| v.abs()).fold(radius, f64::max);
        for coefficient in &mut q {
            *coefficient = mul(*coefficient, 1.0 / scale);
        }
        let r = radius / scale;
        let p = [
            dot(q[0], q[0]) - r * r,
            2.0 * dot(q[0], q[1]),
            dot(q[1], q[1]) + 2.0 * dot(q[0], q[2]),
            2.0 * dot(q[1], q[2]),
            dot(q[2], q[2]),
        ];
        for u in roots_in_unit_interval(&p) {
            let point = add(add(q[0], mul(q[1], u)), mul(q[2], u * u));
            if incoming_only {
                let tangent = add(q[1], mul(q[2], 2.0 * u));
                if dot(point, tangent) >= -64.0 * f64::EPSILON * norm(point) * norm(tangent) {
                    continue;
                }
            }
            if (norm(point) - r).abs() > 1e-7 {
                continue;
            }
            let time = u * dt;
            if earliest.as_ref().is_none_or(|event| time < event.time) {
                earliest = Some(Contact {
                    first: i,
                    second: j,
                    time,
                });
            }
        }
    }
    Ok(earliest)
}

pub fn run_until_contact(
    bodies: &[Body],
    radii: &[f64],
    dt: f64,
    steps: usize,
) -> Result<RunResult, String> {
    validate_input(bodies, radii, dt)?;
    let mut state = bodies.to_vec();
    let mut elapsed = 0.0;
    for _ in 0..steps {
        if let Some(mut event) = first_contact(&state, radii, dt)? {
            if event.time > 0.0 {
                state = evolve(&state, event.time, 1)?;
            }
            elapsed += event.time;
            event.time = elapsed;
            return Ok(RunResult {
                bodies: state,
                time: elapsed,
                contact: Some(event),
            });
        }
        state = evolve(&state, dt, 1)?;
        elapsed += dt;
        if !elapsed.is_finite() {
            return Err("Elapsed time overflow".into());
        }
    }
    Ok(RunResult {
        bodies: state,
        time: elapsed,
        contact: None,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn pair(y: f64) -> Vec<Body> {
        vec![
            Body {
                spin: [0.0; 3],
                name: "a".into(),
                mass: 1e-20,
                position: [-5.0, y, 0.0],
                velocity: [1.0, 0.0, 0.0],
            },
            Body {
                spin: [0.0; 3],
                name: "b".into(),
                mass: 1e-20,
                position: [5.0, 0.0, 0.0],
                velocity: [-1.0, 0.0, 0.0],
            },
        ]
    }
    #[test]
    fn crossing_between_endpoints() {
        let result = run_until_contact(&pair(0.0), &[1.0, 1.0], 10.0, 1).unwrap();
        assert!((result.time - 4.0).abs() < 1e-10);
        assert!(
            (norm(sub(result.bodies[1].position, result.bodies[0].position)) - 2.0).abs() < 1e-10
        );
    }
    #[test]
    fn tangent_and_near_miss() {
        assert!(
            (first_contact(&pair(2.0), &[1.0, 1.0], 10.0)
                .unwrap()
                .unwrap()
                .time
                - 5.0)
                .abs()
                < 1e-6
        );
        assert!(first_contact(&pair(2.01), &[1.0, 1.0], 10.0)
            .unwrap()
            .is_none());
    }
    #[test]
    fn invalid_radii() {
        assert!(first_contact(&pair(0.0), &[-1.0, 1.0], 1.0).is_err());
        assert!(first_contact(&pair(0.0), &[1.0], 1.0).is_err());
    }
    #[test]
    fn initial_overlap_before_force() {
        let mut p = pair(0.0);
        p[1].position = p[0].position;
        assert_eq!(
            run_until_contact(&p, &[1.0, 1.0], 1.0, 10).unwrap().time,
            0.0
        );
    }
    #[test]
    fn quartic_with_four_roots() {
        let roots = roots_in_unit_interval(&[0.0384, -0.4, 1.4, -2.0, 1.0]);
        assert_eq!(roots.len(), 4);
        for (a, b) in roots.iter().zip([0.2, 0.4, 0.6, 0.8]) {
            assert!((a - b).abs() < 1e-10);
        }
    }
}
