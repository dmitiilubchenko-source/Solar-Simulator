//! Diagnostic I/O only: no feedback into the numerical update.
use crate::coefficients::{A, B, C, E3, E5};
use crate::Statistics;
use serde::Serialize;
use std::fs::OpenOptions;
use std::io::{BufWriter, Write};
use std::path::Path;

pub(crate) struct Recorder {
    writer: Box<dyn Write + Send>,
}
#[derive(Serialize)]
pub(crate) struct Attempt<'a> {
    pub kind: &'static str,
    pub time: f64,
    pub next: f64,
    pub packet_end: f64,
    pub h: f64,
    pub old: &'a [f64],
    pub k: &'a [Vec<f64>],
    pub stage_sums: &'a [Vec<f64>],
    pub stages: &'a [Vec<f64>],
    pub update_sum: &'a [f64],
    pub trial: &'a [f64],
    pub error: f64,
    pub accepted: bool,
}
impl Recorder {
    pub(crate) fn create(path: &Path) -> Result<Self, String> {
        let file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .map_err(|e| format!("Trace create: {e}"))?;
        Self::from_writer(Box::new(BufWriter::new(file)))
    }
    fn from_writer(writer: Box<dyn Write + Send>) -> Result<Self, String> {
        let mut result = Self { writer };
        result.record(&serde_json::json!({"kind":"header", "schema":337,
            "a":A,"b":B,"c":C,"e3":E3,"e5":E5}))?;
        Ok(result)
    }
    pub(crate) fn record(&mut self, value: &impl Serialize) -> Result<(), String> {
        serde_json::to_writer(&mut self.writer, value).map_err(|e| format!("Trace write: {e}"))?;
        self.writer
            .write_all(b"\n")
            .map_err(|e| format!("Trace write: {e}"))
    }
    pub(crate) fn flush(&mut self) -> Result<(), String> {
        self.writer.flush().map_err(|e| format!("Trace flush: {e}"))
    }
    pub(crate) fn finish(mut self, statistics: Statistics) -> Result<(), String> {
        self.record(&serde_json::json!({"kind":"finish","statistics":statistics}))?;
        self.flush()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{Config, Dop853};
    use std::io;

    struct FailAfterHeader;
    impl Write for FailAfterHeader {
        fn write(&mut self, _: &[u8]) -> io::Result<usize> {
            Err(io::Error::other("injected diagnostic write failure"))
        }
        fn flush(&mut self) -> io::Result<()> {
            Ok(())
        }
    }
    #[test]
    fn trace_io_failure_latches_and_keeps_last_commit() {
        let mut rhs = |_: f64, _: &[f64], out: &mut [f64]| {
            out.fill(1.);
            Ok(())
        };
        let mut solver = Dop853::new(&mut rhs, 0., vec![0.; 6], 1., Config::default()).unwrap();
        let previous = solver.current();
        solver.attach_trace(Recorder {
            writer: Box::new(FailAfterHeader),
        });
        assert!(solver
            .advance_to(1., &mut rhs)
            .unwrap_err()
            .contains("Trace write"));
        assert_eq!(solver.current(), previous);
        assert!(solver.statistics().failed);
        assert!(solver.advance_to(1., &mut rhs).is_err());
    }
}
