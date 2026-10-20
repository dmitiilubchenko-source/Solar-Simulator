//! Isolated research code; not used by solar_core, PyO3 or the application.
mod coefficients;
mod newton;
mod solver;

pub use newton::{NewtonRun, PhysicalSnapshot};
pub use solver::{grouped_error, Config, Dop853, Snapshot, Statistics};
