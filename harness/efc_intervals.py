"""Shared interval functions — SPEC_EPISTEMIC_FRAME_CHECK_V0 §9.2/§9.3/§9.4/§10.4.

The one statistics module for the epistemic-frame-check instrument. The §10.4
N-rule requires that the calibration planner and the score-time verdict invoke
the SAME interval functions at the same confidence levels; this module is that
shared code. Policy (margins, gate composition, verdict labels) lives in
efc_contracts/efc_planner — nothing here knows what a lane or a stratum is.

Statistical constructions pinned by the sealed Part I:

- binary superiority and non-inferiority: Wilson component intervals combined
  by the Newcombe hybrid-score difference (§9.2, §10.4). Wilson width is
  strictly positive even at an observed 0/n or n/n boundary, which is the
  §10.4 guard against a zero-variance K=5 pilot claiming n_required = 0.
- scalar cost: Welch interval with Welch–Satterthwaite degrees of freedom
  (§9.3 efficiency, §10.4). Zero pooled standard error is DEGENERATE, never a
  free pass — callers receive DegenerateVarianceError and must fail closed.
- population cost: simultaneous per-stratum Welch lower bounds under a
  Bonferroni split of the family alpha (§9.4); saving surfaces are linear in
  prevalence, so vertex evaluation is exact for a convex region.

Quantiles are computed in pure stdlib so the harness adds no numeric
dependency: normal via Wichura's AS241 (PPND16), Student-t via the regularized
incomplete beta (continued fraction) inverted by bisection. Golden tests in
tests/test_efc_intervals.py pin all of them against scipy/statsmodels values
generated at dev time (scratchpad gen_goldens.py), plus independent erfc
round-trips. No closed-form z approximation exists anywhere in this module —
§10.4 forbids one deciding admission.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class IntervalDomainError(ValueError):
    """Inputs outside the statistical domain (counts, probabilities, df)."""


class DegenerateVarianceError(ValueError):
    """Welch construction with zero pooled standard error. The §10.4 planner
    must treat this as an inadmissible pilot, never as n_required = 0."""


# ---------------------------------------------------------------------------
# Normal quantile — Wichura (1988) algorithm AS241, PPND16.
# ---------------------------------------------------------------------------

def norm_ppf(p: float) -> float:
    """Inverse standard normal CDF, |relative error| ~ 1e-15."""
    if not (0.0 < p < 1.0):
        raise IntervalDomainError(f"norm_ppf domain: p={p}")
    q = p - 0.5
    if abs(q) <= 0.425:
        r = 0.180625 - q * q
        num = (((((((2.5090809287301226727e3 * r + 3.3430575583588128105e4) * r
                    + 6.7265770927008700853e4) * r + 4.5921953931549871457e4) * r
                  + 1.3731693765509461125e4) * r + 1.9715909503065514427e3) * r
                + 1.3314166789178437745e2) * r + 3.3871328727963666080e0)
        den = (((((((5.2264952788528545610e3 * r + 2.8729085735721942674e4) * r
                    + 3.9307895800092710610e4) * r + 2.1213794301586595867e4) * r
                  + 5.3941960214247511077e3) * r + 6.8718700749205790830e2) * r
                + 4.2313330701600911252e1) * r + 1.0)
        return q * num / den
    r = p if q < 0.0 else 1.0 - p
    r = math.sqrt(-math.log(r))
    if r <= 5.0:
        r -= 1.6
        num = (((((((7.74545014278341407640e-4 * r + 2.27238449892691845833e-2) * r
                    + 2.41780725177450611770e-1) * r + 1.27045825245236838258e0) * r
                  + 3.64784832476320460504e0) * r + 5.76949722146069140550e0) * r
                + 4.63033784615654529590e0) * r + 1.42343711074968357734e0)
        den = (((((((1.05075007164441684324e-9 * r + 5.47593808499534494600e-4) * r
                    + 1.51986665636164571966e-2) * r + 1.48103976427480074590e-1) * r
                  + 6.89767334985100004550e-1) * r + 1.67638483018380384940e0) * r
                + 2.05319162663775882187e0) * r + 1.0)
    else:
        r -= 5.0
        num = (((((((2.01033439929228813265e-7 * r + 2.71155556874348757815e-5) * r
                    + 1.24266094738807843860e-3) * r + 2.65321895265761230930e-2) * r
                  + 2.96560571828504891230e-1) * r + 1.78482653991729133580e0) * r
                + 5.46378491116411436990e0) * r + 6.65790464350110377720e0)
        den = (((((((2.04426310338993978564e-15 * r + 1.42151175831644588870e-9) * r
                    + 1.84631831751005468180e-6) * r + 7.86869131145613259100e-4) * r
                  + 1.48753612908506148525e-2) * r + 1.36929880922735805310e-1) * r
                + 5.99832206555887937690e-1) * r + 1.0)
    val = num / den
    return -val if q < 0.0 else val


# ---------------------------------------------------------------------------
# Regularized incomplete beta and Student-t.
# ---------------------------------------------------------------------------

_BETACF_MAXIT = 300
_BETACF_EPS = 3.0e-16
_BETACF_FPMIN = 1.0e-300


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta (modified Lentz)."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _BETACF_FPMIN:
        d = _BETACF_FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, _BETACF_MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _BETACF_FPMIN:
            d = _BETACF_FPMIN
        c = 1.0 + aa / c
        if abs(c) < _BETACF_FPMIN:
            c = _BETACF_FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _BETACF_FPMIN:
            d = _BETACF_FPMIN
        c = 1.0 + aa / c
        if abs(c) < _BETACF_FPMIN:
            c = _BETACF_FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < _BETACF_EPS:
            return h
    raise IntervalDomainError(
        f"incomplete beta continued fraction did not converge: a={a} b={b} x={x}")


def betainc_reg(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if a <= 0.0 or b <= 0.0:
        raise IntervalDomainError(f"betainc_reg domain: a={a} b={b}")
    if not (0.0 <= x <= 1.0):
        raise IntervalDomainError(f"betainc_reg domain: x={x}")
    if x == 0.0:
        return 0.0
    if x == 1.0:
        return 1.0
    ln_front = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                + a * math.log(x) + b * math.log(1.0 - x))
    front = math.exp(ln_front)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(t: float, df: float) -> float:
    """Student-t CDF for real df > 0 (Welch–Satterthwaite df is fractional)."""
    if df <= 0.0:
        raise IntervalDomainError(f"t_cdf domain: df={df}")
    if t == 0.0:
        return 0.5
    x = df / (df + t * t)
    tail = 0.5 * betainc_reg(0.5 * df, 0.5, x)
    return 1.0 - tail if t > 0.0 else tail


def t_ppf(p: float, df: float) -> float:
    """Inverse Student-t CDF via bisection on the monotone t_cdf.

    Deterministic, ~1e-12 absolute; the golden suite pins it to scipy at
    1e-9. Bisection keeps the inversion free of any closed-form normal
    approximation (§10.4 prohibition).
    """
    if not (0.0 < p < 1.0):
        raise IntervalDomainError(f"t_ppf domain: p={p}")
    if df <= 0.0:
        raise IntervalDomainError(f"t_ppf domain: df={df}")
    if p == 0.5:
        return 0.0
    if p < 0.5:
        return -t_ppf(1.0 - p, df)
    lo, hi = 0.0, 1.0
    for _ in range(2048):
        if t_cdf(hi, df) >= p:
            break
        hi *= 2.0
    else:  # pragma: no cover - unreachable for p < 1
        raise IntervalDomainError(f"t_ppf bracket failure: p={p} df={df}")
    for _ in range(300):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo <= 1.0e-12 * max(1.0, hi):
            break
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------------------
# Wilson score interval — the binary component interval (§9.2, §10.4).
# ---------------------------------------------------------------------------

def wilson_interval(successes: float, n: int, confidence: float) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    `successes` may be non-integral: the §10.4 planner projects a pilot pass
    rate onto a candidate N as p_hat * N, and the same function must serve
    plan time and score time (score time passes integers).
    """
    if n < 1:
        raise IntervalDomainError(f"wilson_interval domain: n={n}")
    if not (0.0 <= successes <= n):
        raise IntervalDomainError(f"wilson_interval domain: successes={successes} n={n}")
    if not (0.0 < confidence < 1.0):
        raise IntervalDomainError(f"wilson_interval domain: confidence={confidence}")
    z = norm_ppf(0.5 + 0.5 * confidence)
    p_hat = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p_hat + z2 / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt(p_hat * (1.0 - p_hat) / n + z2 / (4.0 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def newcombe_diff_interval(successes1: float, n1: int, successes2: float, n2: int,
                           confidence: float) -> tuple[float, float]:
    """Newcombe hybrid-score interval for p1 - p2 (method 10, Newcombe 1998).

    Built from the Wilson component intervals at the same confidence — the
    §9.2/§9.3 quality-difference construction.
    """
    p1 = successes1 / n1 if n1 >= 1 else _raise_n(n1)
    p2 = successes2 / n2 if n2 >= 1 else _raise_n(n2)
    l1, u1 = wilson_interval(successes1, n1, confidence)
    l2, u2 = wilson_interval(successes2, n2, confidence)
    d = p1 - p2
    lower = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    upper = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return (max(-1.0, lower), min(1.0, upper))


def _raise_n(n: int) -> float:
    raise IntervalDomainError(f"newcombe_diff_interval domain: n={n}")


# ---------------------------------------------------------------------------
# Welch interval — the scalar cost construction (§9.3, §9.4, §10.4).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WelchResult:
    diff: float          # mean1 - mean2
    lower: float
    upper: float
    se: float
    df: float


def welch_interval(mean1: float, sd1: float, n1: int,
                   mean2: float, sd2: float, n2: int,
                   confidence: float) -> WelchResult:
    """Two-sided Welch interval for mean1 - mean2, Welch–Satterthwaite df.

    Standard deviations are sample SDs (ddof=1). Zero pooled SE raises
    DegenerateVarianceError — a zero-variance cost pilot is inadmissible,
    not infinitely precise.
    """
    if n1 < 2 or n2 < 2:
        raise IntervalDomainError(f"welch_interval domain: n1={n1} n2={n2}")
    if sd1 < 0.0 or sd2 < 0.0:
        raise IntervalDomainError(f"welch_interval domain: sd1={sd1} sd2={sd2}")
    if not (0.0 < confidence < 1.0):
        raise IntervalDomainError(f"welch_interval domain: confidence={confidence}")
    v1 = sd1 * sd1 / n1
    v2 = sd2 * sd2 / n2
    se2 = v1 + v2
    if se2 <= 0.0:
        raise DegenerateVarianceError(
            f"welch_interval: zero pooled variance (sd1={sd1}, sd2={sd2})")
    se = math.sqrt(se2)
    df = se2 * se2 / ((v1 * v1) / (n1 - 1) + (v2 * v2) / (n2 - 1))
    t = t_ppf(0.5 + 0.5 * confidence, df)
    diff = mean1 - mean2
    return WelchResult(diff=diff, lower=diff - t * se, upper=diff + t * se,
                       se=se, df=df)


def sample_mean(values: list[float]) -> float:
    if not values:
        raise IntervalDomainError("sample_mean: empty sample")
    return sum(values) / len(values)


def sample_sd(values: list[float]) -> float:
    """Sample standard deviation, ddof=1 (needs n >= 2)."""
    n = len(values)
    if n < 2:
        raise IntervalDomainError(f"sample_sd: n={n} < 2")
    m = sample_mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


# ---------------------------------------------------------------------------
# §9.4 simultaneous stratum bounds and linear prevalence composition.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StratumCostStats:
    """Per-stratum cost summaries for one comparison (e.g. A vs C)."""
    stratum: str
    mean_a: float
    sd_a: float
    n_a: int
    mean_c: float
    sd_c: float
    n_c: int


@dataclass(frozen=True)
class StratumBound:
    stratum: str
    d_point: float   # mean_a - mean_c
    d_lower: float   # simultaneous lower confidence bound for d


def simultaneous_stratum_lower_bounds(strata: list[StratumCostStats],
                                      family_alpha: float = 0.05,
                                      ) -> list[StratumBound]:
    """Simultaneous lower bounds for d_s = mean_cost(A,s) - mean_cost(C,s).

    §9.4: each stratum gets a two-sided Welch interval at Bonferroni coverage
    1 - family_alpha/m; by the union bound the m lower endpoints form one
    simultaneous family. This is the single function both the §10.4 planner
    and the score-time verdict must call.
    """
    m = len(strata)
    if m < 1:
        raise IntervalDomainError("simultaneous_stratum_lower_bounds: no strata")
    if not (0.0 < family_alpha < 1.0):
        raise IntervalDomainError(
            f"simultaneous_stratum_lower_bounds: family_alpha={family_alpha}")
    per_confidence = 1.0 - family_alpha / m
    out: list[StratumBound] = []
    for s in strata:
        w = welch_interval(s.mean_a, s.sd_a, s.n_a, s.mean_c, s.sd_c, s.n_c,
                           per_confidence)
        out.append(StratumBound(stratum=s.stratum, d_point=w.diff, d_lower=w.lower))
    return out


def linear_prevalence_sum(prevalence: dict[str, float],
                          per_stratum: dict[str, float]) -> float:
    """sum_s p_s * value_s over exactly-matching stratum keys (§9.4/§12).

    Both saving surfaces are linear in p, so evaluating declared vertices is
    exact for the whole convex region.
    """
    if set(prevalence) != set(per_stratum):
        raise IntervalDomainError(
            f"linear_prevalence_sum: stratum mismatch {sorted(prevalence)} "
            f"vs {sorted(per_stratum)}")
    total = sum(prevalence.values())
    if abs(total - 1.0) > 1.0e-9:
        raise IntervalDomainError(f"linear_prevalence_sum: prevalence sums to {total}")
    if any(p < 0.0 for p in prevalence.values()):
        raise IntervalDomainError("linear_prevalence_sum: negative prevalence")
    return sum(p * per_stratum[s] for s, p in prevalence.items())


def half_width(interval: tuple[float, float]) -> float:
    """Half-width of a (lower, upper) interval, defined as (upper - lower)/2.

    Newcombe intervals are asymmetric; the §10.3 half-width targets are read
    against this symmetric definition (recorded in EFC_TRACEABILITY).
    """
    lo, hi = interval
    if hi < lo:
        raise IntervalDomainError(f"half_width: inverted interval ({lo}, {hi})")
    return 0.5 * (hi - lo)
