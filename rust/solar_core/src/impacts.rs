//! Instantaneous central impulse for touching frictionless spheres.
use super::{add, dot, mul, norm, sub, validate, Body};

pub struct ImpactResult {
    pub bodies: Vec<Body>,
    pub dissipated_energy: f64,
    pub impulse: f64,
}

pub fn resolve_contact(
    bodies: &[Body],
    radii: &[f64],
    first: usize,
    second: usize,
    restitution: f64,
) -> Result<ImpactResult, String> {
    validate(bodies)?;
    if radii.len() != bodies.len() || !radii.iter().all(|r| r.is_finite() && *r >= 0.0) {
        return Err("Invalid radii".into());
    }
    if !restitution.is_finite() || !(0.0..=1.0).contains(&restitution) {
        return Err("Restitution must be in [0,1]".into());
    }
    if first == second || first >= bodies.len() || second >= bodies.len() {
        return Err("Invalid pair indices".into());
    }
    let (a, b) = (&bodies[first], &bodies[second]);
    let delta = sub(b.position, a.position);
    let distance = norm(delta);
    let radius = radii[first] + radii[second];
    if !radius.is_finite() || radius <= 0.0 || distance == 0.0 || !distance.is_finite() {
        return Err("Contact requires spheres and a defined normal".into());
    }
    if (distance - radius).abs() > 1e-7 * distance.max(radius) {
        return Err("Bodies do not touch or deeply overlap".into());
    }
    let normal = mul(delta, 1.0 / distance);
    let speed = dot(sub(b.velocity, a.velocity), normal);
    let mut state = bodies.to_vec();
    if speed >= 0.0 {
        return Ok(ImpactResult {
            bodies: state,
            dissipated_energy: 0.0,
            impulse: 0.0,
        });
    }
    let scale = a.mass.max(b.mass);
    let fraction_a = a.mass / scale;
    let fraction_b = b.mass / scale;
    let total = fraction_a + fraction_b;
    let reduced_mass = a.mass.min(b.mass) / (1.0 + a.mass.min(b.mass) / scale);
    let change = -(1.0 + restitution) * speed;
    let impulse = reduced_mass * change;
    let dissipated_energy = 0.5 * reduced_mass * (1.0 - restitution * restitution) * speed * speed;
    if !impulse.is_finite() || !dissipated_energy.is_finite() {
        return Err("Impact arithmetic overflow".into());
    }
    state[first].velocity = sub(a.velocity, mul(normal, change * fraction_b / total));
    state[second].velocity = add(b.velocity, mul(normal, change * fraction_a / total));
    validate(&state)?;
    Ok(ImpactResult {
        bodies: state,
        dissipated_energy,
        impulse,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn pair() -> Vec<Body> {
        vec![
            Body {
                spin: [0.0; 3],
                name: "a".into(),
                mass: 1.0,
                position: [-1.0, 0.0, 0.0],
                velocity: [2.0, 0.0, 0.0],
            },
            Body {
                spin: [0.0; 3],
                name: "b".into(),
                mass: 1.0,
                position: [1.0, 0.0, 0.0],
                velocity: [-1.0, 0.0, 0.0],
            },
        ]
    }
    #[test]
    fn elastic_exchange() {
        let p = pair();
        let r = resolve_contact(&p, &[1.0, 1.0], 0, 1, 1.0).unwrap();
        assert_eq!(r.bodies[0].velocity, [-1.0, 0.0, 0.0]);
        assert_eq!(r.bodies[1].velocity, [2.0, 0.0, 0.0]);
        assert_eq!(r.dissipated_energy, 0.0);
        assert_eq!(p[0].velocity[0], 2.0);
    }
    #[test]
    fn inelastic_energy() {
        let r = resolve_contact(&pair(), &[1.0, 1.0], 0, 1, 0.0).unwrap();
        assert_eq!(r.bodies[0].velocity[0], 0.5);
        assert_eq!(r.bodies[1].velocity[0], 0.5);
        assert!((r.dissipated_energy - 2.25).abs() < 1e-14);
    }
    #[test]
    fn separating_and_invalid_inputs() {
        let r = resolve_contact(&pair(), &[1.0, 1.0], 0, 1, 1.0).unwrap();
        assert_eq!(
            resolve_contact(&r.bodies, &[1.0, 1.0], 0, 1, 1.0)
                .unwrap()
                .impulse,
            0.0
        );
        assert!(resolve_contact(&pair(), &[1.0, 1.0], 0, 0, 1.0).is_err());
        assert!(resolve_contact(&pair(), &[1.0, 1.0], 0, 1, 1.1).is_err());
    }
}
