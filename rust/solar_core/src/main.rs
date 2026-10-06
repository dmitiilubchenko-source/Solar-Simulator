//! Batch JSON interface for comparison with the Python reference.
use serde::{Deserialize, Serialize};
use solar_core::{diagnostics, evolve, Body, Diagnostics};
use std::io::{self, Read};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    bodies: Vec<Body>,
    dt: f64,
    steps: usize,
}
#[derive(Serialize)]
struct Response {
    bodies: Vec<Body>,
    diagnostics: Diagnostics,
}
fn run() -> Result<(), String> {
    let mut input = String::new();
    io::stdin()
        .read_to_string(&mut input)
        .map_err(|e| e.to_string())?;
    let request: Request = serde_json::from_str(&input).map_err(|e| e.to_string())?;
    let bodies = evolve(&request.bodies, request.dt, request.steps)?;
    let result = Response {
        diagnostics: diagnostics(&bodies)?,
        bodies,
    };
    println!(
        "{}",
        serde_json::to_string(&result).map_err(|e| e.to_string())?
    );
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
