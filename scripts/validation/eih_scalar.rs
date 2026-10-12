//! Developer-only independent scalar EIH oracle. No production modules.
//! Same direct source/target equation as the Python scalar validation oracle.
type V = [f64; 3];
fn dot(a: V, b: V) -> f64 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}

fn acceleration(
    p: &[V],
    v: &[V],
    mu: &[f64],
    c: f64,
    pair: Option<(usize, usize, V)>,
) -> Result<Vec<V>, &'static str> {
    let n = mu.len();
    if n == 0
        || p.len() != n
        || v.len() != n
        || !c.is_finite()
        || c <= 0.
        || !(c * c).is_finite()
        || mu.iter().any(|m| !m.is_finite() || *m <= 0.)
        || p.iter().chain(v.iter()).flatten().any(|x| !x.is_finite())
    {
        return Err("inputs");
    }
    if let Some((a, b, r)) = pair {
        if a >= n || b >= n || a == b || r.iter().any(|x| !x.is_finite()) {
            return Err("pair");
        }
    }
    let mut inward = vec![[0.; 3]; n * n];
    let mut radii = vec![f64::INFINITY; n * n];
    for i in 0..n {
        for j in 0..n {
            if i == j {
                continue;
            }
            let mut r = [p[j][0] - p[i][0], p[j][1] - p[i][1], p[j][2] - p[i][2]];
            if let Some((a, b, relative)) = pair {
                if (i, j) == (a, b) {
                    r = relative;
                } else if (i, j) == (b, a) {
                    r = relative.map(|x| -x);
                }
            }
            let distance = dot(r, r).sqrt();
            if !distance.is_finite() || distance <= 0. {
                return Err("distance");
            }
            inward[i * n + j] = r;
            radii[i * n + j] = distance;
        }
    }
    let mut potential = vec![0.; n];
    let mut newton = vec![[0.; 3]; n];
    for i in 0..n {
        for j in 0..n {
            if i == j {
                continue;
            }
            let r = radii[i * n + j];
            potential[i] += mu[j] / r;
            for k in 0..3 {
                newton[i][k] += inward[i * n + j][k] * (mu[j] / (r * r * r));
            }
        }
    }
    let speed2: Vec<f64> = v.iter().map(|q| dot(*q, *q)).collect();
    let mut result = newton.clone();
    for i in 0..n {
        for j in 0..n {
            if i == j {
                continue;
            }
            let r = radii[i * n + j];
            let toward = inward[i * n + j];
            let direction = toward.map(|x| x / r);
            let bracket = speed2[i] + 2. * speed2[j]
                - 4. * dot(v[i], v[j])
                - 1.5 * dot(direction, v[j]).powi(2)
                - 4. * potential[i]
                - potential[j]
                + 0.5 * dot(toward, newton[j]);
            let velocity_term = [
                4. * v[i][0] - 3. * v[j][0],
                4. * v[i][1] - 3. * v[j][1],
                4. * v[i][2] - 3. * v[j][2],
            ];
            let projection = dot(direction, velocity_term);
            for k in 0..3 {
                result[i][k] += mu[j] / (c * c)
                    * (direction[k] / (r * r) * bracket
                        - projection * (v[i][k] - v[j][k]) / (r * r)
                        + 3.5 * newton[j][k] / r);
            }
        }
    }
    if result.iter().flatten().any(|x| !x.is_finite()) {
        return Err("overflow");
    }
    Ok(result)
}

/// # Safety
/// Caller owns live arrays: p/v/out contain n*3 doubles, mu n, relative 3.
/// Arrays do not overlap; indices are -1/-1 for no pair or valid distinct n.
#[no_mangle]
pub unsafe extern "C" fn scalar_eih(
    n: usize,
    p: *const f64,
    v: *const f64,
    mu: *const f64,
    c: f64,
    first: isize,
    second: isize,
    relative: *const f64,
    out: *mut f64,
) -> i32 {
    if n == 0 || n > 1024 || p.is_null() || v.is_null() || mu.is_null() || out.is_null() {
        return 1;
    }
    let positions = std::slice::from_raw_parts(p.cast::<V>(), n);
    let velocities = std::slice::from_raw_parts(v.cast::<V>(), n);
    let masses = std::slice::from_raw_parts(mu, n);
    let pair = if first == -1 && second == -1 {
        None
    } else {
        if first < 0 || second < 0 || relative.is_null() {
            return 1;
        }
        let r = std::slice::from_raw_parts(relative, 3);
        Some((first as usize, second as usize, [r[0], r[1], r[2]]))
    };
    match acceleration(positions, velocities, masses, c, pair) {
        Ok(value) => {
            std::ptr::copy_nonoverlapping(value.as_ptr().cast::<f64>(), out, n * 3);
            0
        }
        Err(_) => 2,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn free_particle() {
        assert_eq!(
            acceleration(&[[1., 2., 3.]], &[[3., 2., 1.]], &[1.], 100., None).unwrap(),
            vec![[0.; 3]]
        );
    }
    #[test]
    fn newton_limit() {
        let a = acceleration(
            &[[0.; 3], [2., 0., 0.]],
            &[[0.; 3]; 2],
            &[3., 5.],
            1e100,
            None,
        )
        .unwrap();
        assert_eq!(a, vec![[1.25, 0., 0.], [-0.75, 0., 0.]]);
    }
    #[test]
    fn singular_and_invalid_pair() {
        assert!(acceleration(&[[0.; 3]; 2], &[[0.; 3]; 2], &[1.; 2], 100., None).is_err());
        assert!(acceleration(
            &[[0.; 3], [1.; 3]],
            &[[0.; 3]; 2],
            &[1.; 2],
            100.,
            Some((0, 2, [1.; 3]))
        )
        .is_err());
    }
}
