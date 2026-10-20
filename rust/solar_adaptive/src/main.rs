//! Standalone stdin/stdout research harness, never a GUI or PyO3 backend.
use serde::{Deserialize, Serialize};
use solar_adaptive_research::{Config, NewtonRun, PhysicalSnapshot, Statistics};
use std::io::{self, Read};
use std::time::Instant;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    masses: Vec<f64>,
    states: Vec<[f64; 6]>,
    relative_pair: Option<[usize; 2]>,
    times: Vec<f64>,
    packet_dt: f64,
    rtol: f64,
    position_atol: f64,
    velocity_atol: f64,
    #[serde(default)]
    start_time: f64,
}
#[derive(Serialize)]
struct Response {
    complete: bool,
    error: Option<String>,
    snapshots: Vec<PhysicalSnapshot>,
    committed: PhysicalSnapshot,
    packet_endpoints: Vec<f64>,
    statistics: Statistics,
    compute_seconds: f64,
}
fn run() -> Result<Response, String> {
    let mut input = String::new();
    io::stdin()
        .take(16_000_001)
        .read_to_string(&mut input)
        .map_err(|e| e.to_string())?;
    if input.len() > 16_000_000 {
        return Err("Research request exceeds size bound".into());
    }
    let request: Request = serde_json::from_str(&input).map_err(|e| e.to_string())?;
    if request.times.is_empty()
        || request
            .times
            .iter()
            .any(|t| !t.is_finite() || *t < request.start_time)
        || request.times.windows(2).any(|t| t[1] <= t[0])
        || !request.packet_dt.is_finite()
        || request.packet_dt <= 0.
    {
        return Err("Invalid output epochs or packet interval".into());
    }
    let config = Config {
        rtol: request.rtol,
        position_atol: request.position_atol,
        velocity_atol: request.velocity_atol,
        ..Config::default()
    };
    let start = Instant::now();
    let mut session = NewtonRun::new(
        request.masses,
        request.states,
        request.start_time,
        *request.times.last().ok_or("Missing target")?,
        request.relative_pair,
        config,
    )?;
    let mut snapshots = Vec::new();
    let mut endpoints = Vec::new();
    let mut error = None;
    'epochs: for time in request.times {
        while session.current().time < time {
            let current = session.current().time;
            let end = if request.packet_dt <= time - current {
                (current + request.packet_dt).min(time)
            } else {
                time
            };
            if end <= current {
                error = Some("Packet cannot advance at floating precision".into());
                break 'epochs;
            }
            match session.advance_to(end) {
                Ok(snapshot) => endpoints.push(snapshot.time),
                Err(message) => {
                    error = Some(message);
                    break 'epochs;
                }
            }
        }
        snapshots.push(session.current());
    }
    Ok(Response {
        complete: error.is_none(),
        error,
        snapshots,
        committed: session.current(),
        packet_endpoints: endpoints,
        statistics: session.statistics(),
        compute_seconds: start.elapsed().as_secs_f64(),
    })
}
fn main() {
    match run() {
        Ok(response) => match serde_json::to_string(&response) {
            Ok(text) => {
                println!("{text}");
                if !response.complete {
                    std::process::exit(2);
                }
            }
            Err(error) => {
                eprintln!("{error}");
                std::process::exit(1);
            }
        },
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    }
}
