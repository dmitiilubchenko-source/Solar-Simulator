#![cfg(feature = "diagnostic-trace")]
use solar_adaptive_research::{Config, NewtonRun};
use std::path::PathBuf;

fn directory() -> PathBuf {
    let path = std::env::temp_dir().join(format!(
        "solar-trace-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir(&path).unwrap();
    path
}
fn session() -> NewtonRun {
    NewtonRun::new(
        vec![1., 1.],
        vec![[0., 0., 0., 1., 0., 0.], [1000., 0., 0., 1., 0., 0.]],
        0.,
        10.,
        Some([0, 1]),
        Config::default(),
    )
    .unwrap()
}
fn rows(path: &std::path::Path) -> Vec<serde_json::Value> {
    std::fs::read_to_string(path)
        .unwrap()
        .lines()
        .map(|line| serde_json::from_str(line).unwrap())
        .collect()
}
#[test]
fn traces_are_session_owned_and_numerically_transparent() {
    let dir = directory();
    let a = dir.join("a.jsonl");
    let b = dir.join("b.jsonl");
    let mut one = session();
    let mut two = session();
    let mut control = session();
    one.enable_trace(&a).unwrap();
    two.enable_trace(&b).unwrap();
    for end in [0.125, 1., 10.] {
        let expected = control.advance_to(end).unwrap();
        assert_eq!(one.advance_to(end).unwrap(), expected);
        assert_eq!(two.advance_to(end).unwrap(), expected);
    }
    one.finish_trace().unwrap();
    two.finish_trace().unwrap();
    let left = rows(&a);
    let right = rows(&b);
    assert_eq!(left, right);
    assert_eq!(left[0]["kind"], "header");
    assert_eq!(left.last().unwrap()["kind"], "finish");
    assert_eq!(left.last().unwrap()["statistics"]["packets"], 3);
    assert!(left.iter().any(|r| r["kind"] == "attempt"));
    std::fs::remove_file(a).unwrap();
    std::fs::remove_file(b).unwrap();
    std::fs::remove_dir(dir).unwrap();
}
#[test]
fn existing_trace_is_preserved_and_incomplete_stream_cannot_be_sealed() {
    let dir = directory();
    let path = dir.join("kept.jsonl");
    std::fs::write(&path, b"previous evidence").unwrap();
    let mut run = session();
    assert!(run.enable_trace(&path).is_err());
    assert_eq!(std::fs::read(&path).unwrap(), b"previous evidence");
    assert!(run.finish_trace().is_err());
    assert_eq!(run.current().time, 0.);
    std::fs::remove_file(path).unwrap();
    std::fs::remove_dir(dir).unwrap();
}
