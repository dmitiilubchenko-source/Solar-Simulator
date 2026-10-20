use solar_adaptive_research::{grouped_error, Config, Dop853, NewtonRun};
use std::f64::consts::PI;

fn oscillator(count: usize, work: bool, automatic: bool) -> (f64, f64) {
    let mut values = vec![0.; 6 * count + usize::from(work)];
    values[0] = 0.8;
    values[1] = 0.6;
    values[3 * count] = -0.6;
    values[3 * count + 1] = 0.8;
    let mut rhs = |t: f64, y: &[f64], out: &mut [f64]| {
        out[..3 * count].copy_from_slice(&y[3 * count..6 * count]);
        for i in 0..3 * count {
            out[3 * count + i] = -y[i];
        }
        if work {
            out[6 * count] = 60. * (60. * t).cos();
        }
        Ok(())
    };
    let end = if work { 2. } else { 20. * PI };
    let config = Config {
        rtol: 1e-10,
        position_atol: 1e-12,
        velocity_atol: 1e-12,
        work_atol: 1e-12,
        first_step: if automatic { None } else { Some(0.1) },
        ..Config::default()
    };
    let mut solver = Dop853::new(&mut rhs, 0., values, end, config).unwrap();
    let mut error: f64 = 0.;
    let mut work_error: f64 = 0.;
    for i in 1..=250 {
        let t = if i == 250 { end } else { end * i as f64 / 250. };
        let snapshot = solver.advance_to(t, &mut rhs).unwrap();
        assert_eq!(snapshot.time, t);
        error = error.max(
            (snapshot.values[0] - (0.8 * t.cos() - 0.6 * t.sin()))
                .hypot(snapshot.values[1] - (0.6 * t.cos() + 0.8 * t.sin())),
        );
        if work {
            work_error = work_error.max((snapshot.values[6 * count] - (60. * t).sin()).abs());
        }
    }
    (error, work_error)
}

#[test]
fn analytic_oscillator_inactive_equations_and_initial_step() {
    for automatic in [false, true] {
        for n in [2, 27, 354] {
            assert!(oscillator(n, false, automatic).0 < 1e-8);
        }
    }
}
#[test]
fn scalar_work_has_its_own_error_budget() {
    for n in [2, 354] {
        let (position, work) = oscillator(n, true, false);
        assert!(position < 1e-10);
        assert!(work < 1e-9);
    }
}
#[test]
fn errors_from_different_blocks_are_not_combined_before_acceptance() {
    for n in [2, 354] {
        let mut a = vec![0.; 6 * n + 1];
        let mut b = a.clone();
        a[..3].fill(2.1);
        b[3..6].fill(1000.);
        assert!((grouped_error(&a, &b, 1.).unwrap() - 2.1).abs() < 1e-14);
        a.fill(0.);
        b.fill(0.);
        a[6 * n] = 2.;
        assert_eq!(grouped_error(&a, &b, 1.).unwrap(), 2.);
        assert_eq!(grouped_error(&b, &b, 1.).unwrap(), 0.);
    }
}
#[test]
fn nonfinite_and_extreme_error_estimates_are_explicit() {
    for value in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        let mut a = vec![0.; 7];
        a[6] = value;
        assert!(grouped_error(&a, &[0.; 7], 1.).is_err());
    }
    assert!(grouped_error(&[f64::MAX; 6], &[0.; 6], 1.).is_err());
    assert!(grouped_error(&[1e-300; 6], &[1e-300; 6], 1.).unwrap() > 0.);
    assert!(grouped_error(&[0.; 5], &[0.; 5], 1.).is_err());
}
#[test]
fn exact_packets_never_call_rhs_after_the_boundary_or_share_snapshots() {
    let mut limit = 0.125;
    let mut make = |t: f64, _: &[f64], out: &mut [f64]| {
        assert!(t <= limit);
        out.fill(0.);
        out[0] = 2.;
        Ok(())
    };
    let initial = vec![0.; 6];
    let mut solver = Dop853::new(&mut make, 0., initial.clone(), limit, Config::default()).unwrap();
    let first = solver.advance_to(limit, &mut make).unwrap();
    assert_eq!(first.time, 0.125);
    assert!((first.values[0] - 0.25).abs() < 1e-14);
    limit = 0.375;
    let mut rhs = |t: f64, _: &[f64], out: &mut [f64]| {
        assert!(t <= limit);
        out.fill(0.);
        out[0] = 2.;
        Ok(())
    };
    let final_state = solver.advance_to(limit, &mut rhs).unwrap();
    let mut detached = solver.current();
    detached.values[0] = 99.;
    assert!((final_state.values[0] - 0.75).abs() < 1e-14);
    assert_eq!(solver.current(), final_state);
    assert_eq!(initial, vec![0.; 6]);
    assert_eq!(first.time, 0.125);
}
#[test]
fn failed_packet_keeps_the_last_snapshot_and_latches_failure() {
    let mut zero = |_: f64, _: &[f64], out: &mut [f64]| {
        out.fill(0.);
        Ok(())
    };
    let mut solver = Dop853::new(&mut zero, 0., vec![1.; 6], 1., Config::default()).unwrap();
    let committed = solver.advance_to(0.125, &mut zero).unwrap();
    let mut fail = |t: f64, _: &[f64], out: &mut [f64]| {
        out.fill(0.);
        if t > 0.2 {
            Err("injected force failure".into())
        } else {
            Ok(())
        }
    };
    assert!(solver.advance_to(1., &mut fail).is_err());
    assert_eq!(solver.current(), committed);
    assert!(solver.statistics().failed);
    assert!(solver.advance_to(1., &mut zero).is_err());
    let mut restarted = Dop853::new(
        &mut zero,
        committed.time,
        committed.values,
        1.,
        Config::default(),
    )
    .unwrap();
    assert_eq!(
        restarted.advance_to(1., &mut zero).unwrap().values,
        vec![1.; 6]
    );
}
#[test]
fn invalid_input_and_attempt_limit_do_not_publish_a_trial() {
    let mut zero = |_: f64, _: &[f64], out: &mut [f64]| {
        out.fill(0.);
        Ok(())
    };
    assert!(Dop853::new(&mut zero, 0., vec![0.; 5], 1., Config::default()).is_err());
    assert!(Dop853::new(&mut zero, 1e100, vec![0.; 6], 1e100 + 1., Config::default()).is_err());
    assert!(Dop853::new(
        &mut zero,
        0.,
        vec![0.; 6],
        1.,
        Config {
            rtol: 1e-20,
            ..Config::default()
        }
    )
    .is_err());
    let mut solver = Dop853::new(
        &mut zero,
        0.,
        vec![1.; 6],
        1.,
        Config {
            first_step: Some(0.01),
            max_attempts: 1,
            ..Config::default()
        },
    )
    .unwrap();
    let old = solver.current();
    assert!(solver.advance_to(1., &mut zero).is_err());
    assert_eq!(solver.current(), old);
}
#[test]
fn underflow_of_a_rejected_step_is_reported() {
    let mut discontinuity = |t: f64, _: &[f64], out: &mut [f64]| {
        out.fill(if t == 1. { 0. } else { 1e100 });
        Ok(())
    };
    let config = Config {
        position_atol: 1e-300,
        velocity_atol: 1e-300,
        first_step: Some(1.),
        ..Config::default()
    };
    let mut solver = Dop853::new(&mut discontinuity, 1., vec![0.; 6], 2., config).unwrap();
    assert!(solver
        .advance_to(2., &mut discontinuity)
        .unwrap_err()
        .contains("resolution"));
}
#[test]
fn newton_free_motion_cold_checkpoint_and_repeat_are_consistent() {
    let initial = vec![[1., 2., 3., 2., -3., 4.]];
    let mut a = NewtonRun::new(vec![1.], initial.clone(), 0., 2., None, Config::default()).unwrap();
    let mut b = NewtonRun::new(vec![1.], initial.clone(), 0., 2., None, Config::default()).unwrap();
    let checkpoint = a.advance_to(0.125).unwrap();
    assert_eq!(checkpoint, b.advance_to(0.125).unwrap());
    let mut restored = NewtonRun::new(
        vec![1.],
        checkpoint.states,
        checkpoint.time,
        2.,
        None,
        Config::default(),
    )
    .unwrap();
    let end = a.advance_to(2.).unwrap();
    assert_eq!(end, b.advance_to(2.).unwrap());
    let resumed = restored.advance_to(2.).unwrap();
    for (x, y) in end.states[0].iter().zip(resumed.states[0]) {
        assert!((x - y).abs() < 1e-8);
    }
    assert_eq!(end.states[0], [5., -4., 11., 2., -3., 4.]);
    assert_eq!(initial, vec![[1., 2., 3., 2., -3., 4.]]);
}
#[test]
fn singular_force_does_not_replace_the_physical_checkpoint() {
    let initial = vec![[0.; 6], [0.; 6]];
    let mut solver = NewtonRun::new(
        vec![1., 1.],
        initial.clone(),
        0.,
        1.,
        Some([0, 1]),
        Config::default(),
    )
    .unwrap();
    assert!(solver.advance_to(1.).is_err());
    assert_eq!(solver.current().states, initial);
    assert!(solver.advance_to(1.).is_err());
    assert!(NewtonRun::new(
        vec![1., 1.],
        vec![[0.; 6]; 2],
        0.,
        1.,
        Some([0, 2]),
        Config::default()
    )
    .is_err());
}

#[test]
fn a_nonfinite_rhs_cannot_publish_a_partial_packet() {
    let mut zero = |_: f64, _: &[f64], out: &mut [f64]| {
        out.fill(0.);
        Ok(())
    };
    let mut solver = Dop853::new(&mut zero, 0., vec![1.; 6], 1., Config::default()).unwrap();
    let prior = solver.advance_to(0.125, &mut zero).unwrap();
    let mut broken = |_: f64, _: &[f64], out: &mut [f64]| {
        out.fill(f64::NAN);
        Ok(())
    };
    assert!(solver.advance_to(1., &mut broken).is_err());
    assert_eq!(solver.current(), prior);
    assert!(solver.statistics().failed);
}

#[test]
fn cold_checkpoint_of_oscillatory_motion_remains_accurate() {
    let mut rhs = |_: f64, y: &[f64], out: &mut [f64]| {
        out[..3].copy_from_slice(&y[3..]);
        for i in 0..3 {
            out[3 + i] = -y[i];
        }
        Ok(())
    };
    let config = Config {
        rtol: 1e-11,
        position_atol: 1e-13,
        velocity_atol: 1e-13,
        ..Config::default()
    };
    let initial = vec![1., 0., 0., 0., 1., 0.];
    let mut solver = Dop853::new(&mut rhs, 0., initial.clone(), 2. * PI, config).unwrap();
    let saved = solver.advance_to(0.33, &mut rhs).unwrap();
    let mut resumed = Dop853::new(&mut rhs, saved.time, saved.values, 2. * PI, config).unwrap();
    let continued = solver.advance_to(2. * PI, &mut rhs).unwrap();
    let restarted = resumed.advance_to(2. * PI, &mut rhs).unwrap();
    for ((a, b), expected) in continued.values.iter().zip(&restarted.values).zip(initial) {
        assert!((a - b).abs() < 1e-8);
        assert!((a - expected).abs() < 1e-8);
    }
}
