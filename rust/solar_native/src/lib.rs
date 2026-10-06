//! Owned arrays cross the Python boundary once per batch; no Python calls in the solver.
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use solar_core::{Body, Vector3};

type StateArrays = (Vec<Vector3>, Vec<Vector3>);
type DiagnosticValues = (f64, Vector3, Vector3, Vector3);

fn bodies(
    masses: Vec<f64>,
    positions: Vec<Vector3>,
    velocities: Vec<Vector3>,
) -> PyResult<Vec<Body>> {
    if masses.len() != positions.len() || masses.len() != velocities.len() {
        return Err(PyValueError::new_err(
            "masses, positions and velocities must have equal lengths",
        ));
    }
    Ok(masses
        .into_iter()
        .zip(positions)
        .zip(velocities)
        .enumerate()
        .map(|(i, ((mass, position), velocity))| Body {
            spin: [0.0; 3],
            name: i.to_string(),
            mass,
            position,
            velocity,
        })
        .collect())
}

#[pyfunction]
fn evolve(
    py: Python<'_>,
    masses: Vec<f64>,
    positions: Vec<Vector3>,
    velocities: Vec<Vector3>,
    dt: f64,
    steps: usize,
) -> PyResult<StateArrays> {
    let input = bodies(masses, positions, velocities)?;
    let output = py
        .detach(move || solar_core::evolve(&input, dt, steps))
        .map_err(PyValueError::new_err)?;
    Ok((
        output.iter().map(|b| b.position).collect(),
        output.iter().map(|b| b.velocity).collect(),
    ))
}

#[pyfunction(signature = (masses, positions, velocities, spins=None))]
fn diagnostics(
    py: Python<'_>,
    masses: Vec<f64>,
    positions: Vec<Vector3>,
    velocities: Vec<Vector3>,
    spins: Option<Vec<Vector3>>,
) -> PyResult<DiagnosticValues> {
    let mut input = bodies(masses, positions, velocities)?;
    if let Some(values) = spins {
        if values.len() != input.len() {
            return Err(PyValueError::new_err("Spins must match bodies"));
        }
        for (body, spin) in input.iter_mut().zip(values) {
            body.spin = spin;
        }
    }
    let values = py
        .detach(move || solar_core::diagnostics(&input))
        .map_err(PyValueError::new_err)?;
    Ok((
        values.energy,
        values.momentum,
        values.angular_momentum,
        values.center_of_mass,
    ))
}

type ContactResult = (Vec<Vector3>, Vec<Vector3>, f64, Option<(usize, usize, f64)>);

#[pyfunction]
fn run_until_contact(
    py: Python<'_>,
    masses: Vec<f64>,
    positions: Vec<Vector3>,
    velocities: Vec<Vector3>,
    radii: Vec<f64>,
    dt: f64,
    steps: usize,
) -> PyResult<ContactResult> {
    let input = bodies(masses, positions, velocities)?;
    let result = py
        .detach(move || solar_core::contacts::run_until_contact(&input, &radii, dt, steps))
        .map_err(PyValueError::new_err)?;
    Ok((
        result.bodies.iter().map(|b| b.position).collect(),
        result.bodies.iter().map(|b| b.velocity).collect(),
        result.time,
        result.contact.map(|e| (e.first, e.second, e.time)),
    ))
}

type ImpactResult = (Vec<Vector3>, f64, f64);

#[pyfunction]
fn resolve_contact(
    py: Python<'_>,
    masses: Vec<f64>,
    positions: Vec<Vector3>,
    velocities: Vec<Vector3>,
    radii: Vec<f64>,
    first: usize,
    second: usize,
    restitution: f64,
) -> PyResult<ImpactResult> {
    let input = bodies(masses, positions, velocities)?;
    let result = py
        .detach(move || {
            solar_core::impacts::resolve_contact(&input, &radii, first, second, restitution)
        })
        .map_err(PyValueError::new_err)?;
    Ok((
        result.bodies.iter().map(|b| b.velocity).collect(),
        result.dissipated_energy,
        result.impulse,
    ))
}

#[allow(clippy::type_complexity)]
#[pyfunction]
fn simulate_collisions(
    py: Python<'_>,
    masses: Vec<f64>,
    positions: Vec<Vector3>,
    velocities: Vec<Vector3>,
    radii: Vec<f64>,
    dt: f64,
    steps: usize,
    restitution: f64,
    max_events: usize,
) -> PyResult<(
    Vec<Vector3>,
    Vec<Vector3>,
    f64,
    Vec<(usize, usize, f64)>,
    f64,
)> {
    let input = bodies(masses, positions, velocities)?;
    let result = py
        .detach(move || {
            solar_core::collisions::simulate_collisions(
                &input,
                &radii,
                dt,
                steps,
                restitution,
                max_events,
            )
        })
        .map_err(PyValueError::new_err)?;
    Ok((
        result.bodies.iter().map(|b| b.position).collect(),
        result.bodies.iter().map(|b| b.velocity).collect(),
        result.time,
        result
            .events
            .iter()
            .map(|e| (e.first, e.second, e.time))
            .collect(),
        result.dissipated_energy,
    ))
}

#[pymodule]
fn solar_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(evolve, module)?)?;
    module.add_function(wrap_pyfunction!(diagnostics, module)?)?;
    module.add_function(wrap_pyfunction!(run_until_contact, module)?)?;
    module.add_function(wrap_pyfunction!(resolve_contact, module)?)?;
    module.add_function(wrap_pyfunction!(simulate_collisions, module)?)?;
    Ok(())
}
