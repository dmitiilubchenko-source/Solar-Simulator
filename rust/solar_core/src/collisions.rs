//! Sequential isolated impacts. No resting or simultaneous constraints.
use super::contacts::{first_contact_mode, Contact};
use super::impacts::resolve_contact;
use super::{evolve, norm, sub, Body};

pub struct CollisionResult {
    pub bodies: Vec<Body>,
    pub time: f64,
    pub events: Vec<Contact>,
    pub dissipated_energy: f64,
}

pub fn simulate_collisions(
    bodies: &[Body],
    radii: &[f64],
    dt: f64,
    steps: usize,
    restitution: f64,
    max_events: usize,
) -> Result<CollisionResult, String> {
    super::validate(bodies)?;
    if !dt.is_finite()
        || dt <= 0.0
        || !(dt * steps as f64).is_finite()
        || !restitution.is_finite()
        || !(0.0..=1.0).contains(&restitution)
        || max_events == 0
    {
        return Err("Invalid collision configuration".into());
    }
    if radii.len() != bodies.len() || !radii.iter().all(|r| r.is_finite() && *r >= 0.0) {
        return Err("Invalid radii".into());
    }
    let mut state = bodies.to_vec();
    let mut events = Vec::new();
    let mut loss = 0.0;
    for index in 0..steps {
        let mut consumed = 0.0;
        while consumed < dt {
            let remaining = dt - consumed;
            let Some(event) = first_contact_mode(&state, radii, remaining, true)? else {
                state = evolve(&state, remaining, 1)?;
                break;
            };
            if events.len() >= max_events {
                return Err("Impact limit reached; possible inelastic collapse".into());
            }
            if event.time > 0.0 {
                if consumed + event.time == consumed {
                    return Err("Impact time below floating point resolution".into());
                }
                state = evolve(&state, event.time, 1)?;
                consumed += event.time;
            }
            let mut touching = Vec::new();
            for i in 0..state.len() {
                for j in i + 1..state.len() {
                    let radius = radii[i] + radii[j];
                    if radius > 0.0
                        && norm(sub(state[j].position, state[i].position)) <= radius * (1.0 + 1e-7)
                    {
                        touching.push((i, j));
                    }
                }
            }
            if touching != vec![(event.first, event.second)] {
                return Err("Simultaneous contacts unsupported".into());
            }
            let impact = resolve_contact(&state, radii, event.first, event.second, restitution)?;
            if impact.impulse <= 0.0 {
                return Err("Expected approaching impact".into());
            }
            state = impact.bodies;
            loss += impact.dissipated_energy;
            if !loss.is_finite() {
                return Err("Dissipated energy overflow".into());
            }
            events.push(Contact {
                first: event.first,
                second: event.second,
                time: index as f64 * dt + consumed,
            });
        }
    }
    Ok(CollisionResult {
        bodies: state,
        time: steps as f64 * dt,
        events,
        dissipated_energy: loss,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    fn body(x: f64, v: f64) -> Body {
        Body {
            spin: [0.0; 3],
            name: "sphere".into(),
            mass: 1e-20,
            position: [x, 0.0, 0.0],
            velocity: [v, 0.0, 0.0],
        }
    }
    #[test]
    fn chain() {
        let r = simulate_collisions(
            &[body(-4.0, 2.0), body(0.0, 0.0), body(4.0, 0.0)],
            &[1.0; 3],
            3.0,
            1,
            1.0,
            10,
        )
        .unwrap();
        assert_eq!(r.events.len(), 2);
        assert!((r.events[0].time - 1.0).abs() < 1e-12);
        assert!((r.events[1].time - 2.0).abs() < 1e-12);
        assert!((r.bodies[2].position[0] - 6.0).abs() < 1e-12);
    }
    #[test]
    fn separating_and_tangent() {
        assert!(simulate_collisions(
            &[body(-1.0, -1.0), body(1.0, 1.0)],
            &[1.0; 2],
            1.0,
            2,
            1.0,
            10
        )
        .unwrap()
        .events
        .is_empty());
        let a = body(-5.0, 1.0);
        let mut b = body(5.0, -1.0);
        b.position[1] = 2.0;
        assert!(simulate_collisions(&[a, b], &[1.0; 2], 10.0, 1, 1.0, 10)
            .unwrap()
            .events
            .is_empty());
    }
    #[test]
    fn unsupported_and_limits() {
        assert!(simulate_collisions(
            &[body(-1.0, 0.0), body(1.0, 0.0)],
            &[1.0; 2],
            1.0,
            1,
            1.0,
            10
        )
        .is_err());
        assert!(simulate_collisions(
            &[body(-4.0, 2.0), body(0.0, 0.0), body(4.0, 0.0)],
            &[1.0; 3],
            3.0,
            1,
            1.0,
            1
        )
        .is_err());
    }
}
