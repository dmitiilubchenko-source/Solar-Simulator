//! Newtonian point masses in SI. Fixed-step Velocity Verlet.
use serde::{Deserialize, Serialize};

pub mod collisions;
pub mod contacts;
pub mod impacts;

pub const G: f64 = 6.67430e-11;
pub type Vector3 = [f64; 3];

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Body {
    pub name: String,
    pub mass: f64,
    pub position: Vector3,
    pub velocity: Vector3,
    #[serde(default)]
    pub spin: Vector3,
}

fn add(a: Vector3, b: Vector3) -> Vector3 {
    std::array::from_fn(|i| a[i] + b[i])
}
fn sub(a: Vector3, b: Vector3) -> Vector3 {
    std::array::from_fn(|i| a[i] - b[i])
}
fn mul(a: Vector3, scalar: f64) -> Vector3 {
    a.map(|x| x * scalar)
}
fn dot(a: Vector3, b: Vector3) -> f64 {
    a.iter().zip(b).map(|(x, y)| x * y).sum()
}
fn norm(a: Vector3) -> f64 {
    a[0].hypot(a[1]).hypot(a[2])
}
fn cross(a: Vector3, b: Vector3) -> Vector3 {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}

pub fn validate(bodies: &[Body]) -> Result<(), String> {
    for body in bodies {
        if body.name.trim().is_empty() || !body.mass.is_finite() || body.mass <= 0.0 {
            return Err("Invalid body name or mass".into());
        }
        if !body
            .position
            .iter()
            .chain(body.velocity.iter())
            .chain(body.spin.iter())
            .all(|v| v.is_finite())
        {
            return Err("Non-finite state".into());
        }
    }
    Ok(())
}

pub fn accelerations(bodies: &[Body]) -> Result<Vec<Vector3>, String> {
    validate(bodies)?;
    let mut result = vec![[0.0; 3]; bodies.len()];
    for i in 0..bodies.len() {
        for j in i + 1..bodies.len() {
            let delta = sub(bodies[j].position, bodies[i].position);
            let distance = norm(delta);
            if distance == 0.0 {
                return Err("Coincident positions".into());
            }
            let direction = mul(delta, 1.0 / distance);
            let factor = G / distance / distance;
            result[i] = add(result[i], mul(direction, factor * bodies[j].mass));
            result[j] = sub(result[j], mul(direction, factor * bodies[i].mass));
        }
    }
    if !result.iter().flatten().all(|v| v.is_finite()) {
        return Err("Non-finite acceleration".into());
    }
    Ok(result)
}

pub fn evolve(bodies: &[Body], dt: f64, steps: usize) -> Result<Vec<Body>, String> {
    if !dt.is_finite() || dt <= 0.0 {
        return Err("Invalid time step".into());
    }
    let mut state = bodies.to_vec();
    // The endpoint acceleration is reused at the next step.
    let mut old = accelerations(&state)?;
    for _ in 0..steps {
        for (body, a) in state.iter_mut().zip(&old) {
            body.position = add(
                add(body.position, mul(body.velocity, dt)),
                mul(*a, 0.5 * dt * dt),
            );
        }
        let new = accelerations(&state)?;
        for ((body, a0), a1) in state.iter_mut().zip(&old).zip(&new) {
            body.velocity = add(body.velocity, mul(add(*a0, *a1), 0.5 * dt));
        }
        validate(&state)?;
        old = new;
    }
    Ok(state)
}

#[derive(Debug, Serialize)]
pub struct Diagnostics {
    pub energy: f64,
    pub momentum: Vector3,
    pub angular_momentum: Vector3,
    pub center_of_mass: Vector3,
}

pub fn diagnostics(bodies: &[Body]) -> Result<Diagnostics, String> {
    validate(bodies)?;
    if bodies.is_empty() {
        return Err("Empty system has no center of mass".into());
    }
    let total_mass: f64 = bodies.iter().map(|b| b.mass).sum();
    let mut energy = 0.0;
    let mut momentum = [0.0; 3];
    let mut angular_momentum = [0.0; 3];
    let mut center_of_mass = [0.0; 3];
    for (i, body) in bodies.iter().enumerate() {
        energy += 0.5 * body.mass * dot(body.velocity, body.velocity);
        momentum = add(momentum, mul(body.velocity, body.mass));
        angular_momentum = add(
            angular_momentum,
            mul(cross(body.position, body.velocity), body.mass),
        );
        angular_momentum = add(angular_momentum, body.spin);
        center_of_mass = add(center_of_mass, mul(body.position, body.mass / total_mass));
        for other in &bodies[i + 1..] {
            let distance = norm(sub(other.position, body.position));
            if distance == 0.0 {
                return Err("Coincident positions".into());
            }
            energy -= G * body.mass * other.mass / distance;
        }
    }
    if !energy.is_finite()
        || !momentum
            .iter()
            .chain(angular_momentum.iter())
            .chain(center_of_mass.iter())
            .all(|v| v.is_finite())
    {
        return Err("Non-finite diagnostics".into());
    }
    Ok(Diagnostics {
        energy,
        momentum,
        angular_momentum,
        center_of_mass,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn body(x: f64, mass: f64) -> Body {
        Body {
            spin: [0.0; 3],
            name: "test".into(),
            mass,
            position: [x, 0.0, 0.0],
            velocity: [1.0, 0.0, 0.0],
        }
    }
    #[test]
    fn free_motion_and_unchanged_input() {
        let initial = vec![body(2.0, 1.0)];
        assert_eq!(
            evolve(&initial, 0.5, 4).unwrap()[0].position,
            [4.0, 0.0, 0.0]
        );
        assert_eq!(initial[0].position[0], 2.0);
    }
    #[test]
    fn pair_force() {
        let a = accelerations(&[body(0.0, 2.0), body(2.0, 3.0)]).unwrap();
        assert!((a[0][0] / (G * 3.0 / 4.0) - 1.0).abs() < 1e-14);
        assert!((a[1][0] / (-G * 2.0 / 4.0) - 1.0).abs() < 1e-14);
    }
    #[test]
    fn rejects_invalid_inputs() {
        assert!(evolve(&[body(0.0, 1.0)], 0.0, 1).is_err());
        assert!(evolve(&[body(0.0, -1.0)], 1.0, 1).is_err());
        assert!(accelerations(&[body(0.0, 1.0), body(0.0, 1.0)]).is_err());
        assert!(diagnostics(&[]).is_err());
    }
    #[test]
    fn zero_steps_preserves_state() {
        assert_eq!(
            evolve(&[body(3.0, 1.0)], 1.0, 0).unwrap()[0].position[0],
            3.0
        );
    }
}
