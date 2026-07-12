"""Golden and property tests for harness/efc_intervals.py (SPEC_EFC §10.4).

§10.4: "The shared functions and enumeration must be unit-tested before
calibration contact." This suite is that unit test for the interval half.

Golden values were generated once at dev time with scipy 1.x / statsmodels
(scratchpad gen_goldens.py: scipy.stats.norm.ppf / t.ppf, scipy.special.betainc,
statsmodels proportion_confint(method="wilson"),
confint_proportions_2indep(method="newcomb"),
scipy.stats.ttest_ind(equal_var=False).confidence_interval) and hardcoded here
so the runtime harness carries no numeric dependency. The 56/70 vs 48/80
Newcombe case is additionally the published method-10 example (Newcombe 1998),
(0.0524, 0.3339).
"""

from __future__ import annotations

import math
import unittest

from harness.efc_intervals import (DegenerateVarianceError, IntervalDomainError,
                                   StratumBound, StratumCostStats, betainc_reg,
                                   half_width, linear_prevalence_sum,
                                   newcombe_diff_interval, norm_ppf, sample_mean,
                                   sample_sd, simultaneous_stratum_lower_bounds,
                                   t_cdf, t_ppf, welch_interval, wilson_interval)

NORM_PPF_GOLDENS = [
    (0.5, 0.0),
    (0.025, -1.9599639845400545),
    (0.95, 1.644853626951472),
    (0.975, 1.959963984540054),
    (0.9875, 2.241402727604947),
    (0.9916666666666667, 2.3939797998185104),
    (0.995, 2.5758293035489004),
    (0.9999, 3.7190164854557084),
    (1e-09, -5.9978070150076865),
    (0.999999999, 5.997807019601637),
]

T_PPF_GOLDENS = [
    (0.975, 1, 12.706204736174694),
    (0.975, 2, 4.302652729749462),
    (0.975, 3.7, 2.8675207071911895),
    (0.975, 5, 2.5705818356363146),
    (0.975, 10, 2.228138851986274),
    (0.975, 17.42, 2.1059472832813895),
    (0.975, 23, 2.0686576104190486),
    (0.975, 30, 2.0422724563012378),
    (0.975, 46, 2.012895598919429),
    (0.975, 200.5, 1.971866290304378),
    (0.9875, 2, 6.205346816570706),
    (0.9875, 5, 3.1633814497486084),
    (0.9875, 23, 2.397875064657111),
    (0.9875, 46, 2.317152172150019),
    (0.9916666666666667, 4.83, 3.5898688189786347),
    (0.9916666666666667, 23, 2.582017198304117),
    (0.995, 5, 4.032142983555227),
    (0.9999, 12, 5.263273007826034),
]

BETAINC_GOLDENS = [
    (0.5, 0.5, 0.3, 0.36901011956554536),
    (2.0, 3.0, 0.4, 0.5247999999999999),
    (11.5, 0.5, 0.9, 0.12355574276988121),
    (5.0, 0.5, 0.999, 0.9222819921009667),
    (0.25, 7.0, 0.01, 0.5532242059927192),
    (12.0, 12.0, 0.5, 0.5),
]

WILSON_GOLDENS = [
    (5, 10, 0.95, 0.236593090512564, 0.7634069094874361),
    (0, 10, 0.95, 0.0, 0.2775327998628892),
    (10, 10, 0.95, 0.7224672001371107, 0.9999999999999999),
    (56, 70, 0.95, 0.6918335550374695, 0.8769526075163705),
    (48, 80, 0.95, 0.4904546500516039, 0.7003817240412906),
    (4, 5, 0.95, 0.37553462976252533, 0.9637758913675698),
    (1, 24, 0.975, 0.0060851488879530985, 0.23591849397310283),
    (20, 24, 0.9875, 0.5818512862864691, 0.9472749180872906),
    (0, 5, 0.95, 0.0, 0.43448246478317476),
    (5, 5, 0.95, 0.5655175352168251, 1.0),
    (12, 24, 0.9833333333333333, 0.2804746338704249, 0.7195253661295751),
]

NEWCOMBE_GOLDENS = [
    # (x1, n1, x2, n2, confidence, lower, upper); first row = Newcombe 1998
    # method-10 published example (0.0524, 0.3339).
    (56, 70, 48, 80, 0.95, 0.05243147240236498, 0.333872654036906),
    (5, 10, 4, 10, 0.95, -0.28979425671088216, 0.4508896685581263),
    (10, 10, 0, 10, 0.95, 0.6075093504305242, 1.0),
    (20, 24, 14, 24, 0.975, -0.04384701943261937, 0.4950057817650194),
    (19, 24, 23, 24, 0.95, -0.36600632863270594, 0.031500847620787975),
    (0, 5, 0, 5, 0.95, -0.43448246478317476, 0.43448246478317476),
]

# scipy.stats.ttest_ind(A, B, equal_var=False).confidence_interval(...)
WELCH_A = [220.0, 231.0, 215.0, 245.0, 228.0]
WELCH_B = [201.0, 199.0, 214.0, 189.0, 208.0]
WELCH_AB_DF = 7.711717386372761
WELCH_AB_GOLDENS = [
    (0.95, 10.119840794126926, 41.080159205873116),
    (0.975, 7.095700752665312, 44.10429924733476),
    (0.9833333333333333, 5.296079852054419, 45.903920147945655),
]
WELCH_C = [512.0, 480.0, 530.0, 501.0, 466.0]
WELCH_D = [300.0, 310.0, 295.0, 340.0, 288.0]
WELCH_CD_DF = 7.634122374424981
WELCH_CD_BONF3 = (0.9833333333333333, 146.8175568963986, 235.58244310360146)


class TestNormPpf(unittest.TestCase):
    def test_goldens(self):
        for p, want in NORM_PPF_GOLDENS:
            self.assertAlmostEqual(norm_ppf(p), want, delta=1e-12,
                                   msg=f"norm_ppf({p})")

    def test_erfc_roundtrip(self):
        # independent check: Phi(norm_ppf(p)) == p via stdlib erfc
        for i in range(1, 200):
            p = i / 200.0
            z = norm_ppf(p)
            phi = 0.5 * math.erfc(-z / math.sqrt(2.0))
            self.assertAlmostEqual(phi, p, delta=1e-13, msg=f"p={p}")

    def test_symmetry(self):
        for p in (0.6, 0.9, 0.975, 0.9999):
            self.assertAlmostEqual(norm_ppf(p), -norm_ppf(1.0 - p), delta=1e-13)

    def test_domain(self):
        for p in (0.0, 1.0, -0.1, 1.1):
            with self.assertRaises(IntervalDomainError):
                norm_ppf(p)


class TestStudentT(unittest.TestCase):
    def test_betainc_goldens(self):
        for a, b, x, want in BETAINC_GOLDENS:
            self.assertAlmostEqual(betainc_reg(a, b, x), want, delta=1e-12,
                                   msg=f"betainc({a},{b},{x})")

    def test_betainc_edges_and_reflection(self):
        self.assertEqual(betainc_reg(2.0, 3.0, 0.0), 0.0)
        self.assertEqual(betainc_reg(2.0, 3.0, 1.0), 1.0)
        for a, b, x in [(2.0, 3.0, 0.4), (11.5, 0.5, 0.9), (0.25, 7.0, 0.01)]:
            self.assertAlmostEqual(betainc_reg(a, b, x),
                                   1.0 - betainc_reg(b, a, 1.0 - x), delta=1e-12)

    def test_t_ppf_goldens(self):
        for p, df, want in T_PPF_GOLDENS:
            self.assertAlmostEqual(t_ppf(p, df), want, delta=1e-9,
                                   msg=f"t_ppf({p},{df})")

    def test_t_symmetry_and_median(self):
        self.assertEqual(t_ppf(0.5, 7.3), 0.0)
        self.assertAlmostEqual(t_ppf(0.025, 11.0), -t_ppf(0.975, 11.0), delta=1e-12)

    def test_t_cdf_roundtrip(self):
        for p, df, _ in T_PPF_GOLDENS:
            self.assertAlmostEqual(t_cdf(t_ppf(p, df), df), p, delta=1e-11)

    def test_t_approaches_normal(self):
        self.assertAlmostEqual(t_ppf(0.975, 1e7), norm_ppf(0.975), delta=1e-6)

    def test_domain(self):
        with self.assertRaises(IntervalDomainError):
            t_ppf(0.975, 0.0)
        with self.assertRaises(IntervalDomainError):
            t_ppf(1.0, 5.0)


class TestWilson(unittest.TestCase):
    def test_goldens(self):
        for x, n, conf, lo, hi in WILSON_GOLDENS:
            got_lo, got_hi = wilson_interval(x, n, conf)
            self.assertAlmostEqual(got_lo, lo, delta=1e-12, msg=f"({x},{n},{conf}) lo")
            self.assertAlmostEqual(got_hi, hi, delta=1e-12, msg=f"({x},{n},{conf}) hi")

    def test_boundary_width_never_zero(self):
        # §10.4: a zero-variance K=5 binary pilot cannot claim n_required = 0;
        # Wilson width stays strictly positive at observed 0/n and n/n.
        for n in (2, 5, 24):
            for successes in (0, n):
                lo, hi = wilson_interval(successes, n, 0.95)
                self.assertGreater(hi - lo, 0.05, msg=f"{successes}/{n}")

    def test_continuous_successes_projection(self):
        # planner projection p_hat * N may be non-integral; must interpolate
        lo25, hi25 = wilson_interval(2.5, 10, 0.95)
        lo2, _ = wilson_interval(2, 10, 0.95)
        lo3, _ = wilson_interval(3, 10, 0.95)
        self.assertTrue(lo2 < lo25 < lo3)
        self.assertTrue(0.0 < lo25 < hi25 < 1.0)

    def test_domain(self):
        with self.assertRaises(IntervalDomainError):
            wilson_interval(5, 0, 0.95)
        with self.assertRaises(IntervalDomainError):
            wilson_interval(11, 10, 0.95)
        with self.assertRaises(IntervalDomainError):
            wilson_interval(5, 10, 1.0)


class TestNewcombe(unittest.TestCase):
    def test_goldens(self):
        for x1, n1, x2, n2, conf, lo, hi in NEWCOMBE_GOLDENS:
            got_lo, got_hi = newcombe_diff_interval(x1, n1, x2, n2, conf)
            self.assertAlmostEqual(got_lo, lo, delta=1e-10,
                                   msg=f"({x1}/{n1},{x2}/{n2},{conf}) lo")
            self.assertAlmostEqual(got_hi, hi, delta=1e-10,
                                   msg=f"({x1}/{n1},{x2}/{n2},{conf}) hi")

    def test_zero_variance_pair_still_wide(self):
        # both arms 5/5 at K=5: observed diff 0 with zero variance, yet the
        # interval keeps real width — the §10.4 planner guard.
        lo, hi = newcombe_diff_interval(5, 5, 5, 5, 0.95)
        self.assertLess(lo, -0.3)
        self.assertGreater(hi, 0.3)

    def test_stricter_confidence_is_wider(self):
        lo95, hi95 = newcombe_diff_interval(20, 24, 14, 24, 0.95)
        lo975, hi975 = newcombe_diff_interval(20, 24, 14, 24, 0.975)
        self.assertLess(lo975, lo95)
        self.assertGreater(hi975, hi95)


class TestWelch(unittest.TestCase):
    def test_goldens(self):
        m1, s1 = sample_mean(WELCH_A), sample_sd(WELCH_A)
        m2, s2 = sample_mean(WELCH_B), sample_sd(WELCH_B)
        for conf, lo, hi in WELCH_AB_GOLDENS:
            w = welch_interval(m1, s1, 5, m2, s2, 5, conf)
            self.assertAlmostEqual(w.lower, lo, delta=1e-8, msg=f"conf={conf} lo")
            self.assertAlmostEqual(w.upper, hi, delta=1e-8, msg=f"conf={conf} hi")
            self.assertAlmostEqual(w.df, WELCH_AB_DF, delta=1e-9)
            self.assertAlmostEqual(w.diff, 25.6, delta=1e-12)

    def test_degenerate_variance_refused(self):
        with self.assertRaises(DegenerateVarianceError):
            welch_interval(10.0, 0.0, 5, 10.0, 0.0, 5, 0.95)

    def test_one_sided_zero_sd_df(self):
        # sd1 == 0 collapses W-S df to n2 - 1
        w = welch_interval(10.0, 0.0, 5, 8.0, 2.0, 5, 0.95)
        self.assertAlmostEqual(w.df, 4.0, delta=1e-12)

    def test_domain(self):
        with self.assertRaises(IntervalDomainError):
            welch_interval(1.0, 1.0, 1, 2.0, 1.0, 5, 0.95)
        with self.assertRaises(IntervalDomainError):
            welch_interval(1.0, -0.5, 5, 2.0, 1.0, 5, 0.95)


class TestSimultaneousBounds(unittest.TestCase):
    def test_bonferroni_three_strata_matches_direct_welch(self):
        # with m=3 and family alpha 0.05 each stratum runs two-sided at
        # 1 - 0.05/3; golden row (C vs D) pins exactly that confidence.
        mc, sc = sample_mean(WELCH_C), sample_sd(WELCH_C)
        md, sd = sample_mean(WELCH_D), sample_sd(WELCH_D)
        strata = [StratumCostStats(stratum=s, mean_a=mc, sd_a=sc, n_a=5,
                                   mean_c=md, sd_c=sd, n_c=5)
                  for s in ("match_mismatch", "match_commit", "irrelevant")]
        bounds = simultaneous_stratum_lower_bounds(strata, family_alpha=0.05)
        conf, lo, _hi = WELCH_CD_BONF3
        self.assertEqual(conf, 1.0 - 0.05 / 3.0)
        for b in bounds:
            self.assertAlmostEqual(b.d_lower, lo, delta=1e-8)
            self.assertAlmostEqual(b.d_point, mc - md, delta=1e-12)

    def test_simultaneous_is_stricter_than_marginal(self):
        mc, sc = sample_mean(WELCH_C), sample_sd(WELCH_C)
        md, sd = sample_mean(WELCH_D), sample_sd(WELCH_D)
        marginal = welch_interval(mc, sc, 5, md, sd, 5, 0.95)
        strata = [StratumCostStats("s1", mc, sc, 5, md, sd, 5)]
        strata3 = strata + [StratumCostStats("s2", mc, sc, 5, md, sd, 5),
                            StratumCostStats("s3", mc, sc, 5, md, sd, 5)]
        bonf3 = simultaneous_stratum_lower_bounds(strata3, 0.05)[0]
        self.assertLess(bonf3.d_lower, marginal.lower)

    def test_domain(self):
        with self.assertRaises(IntervalDomainError):
            simultaneous_stratum_lower_bounds([], 0.05)


class TestPrevalenceComposition(unittest.TestCase):
    def test_linear_sum(self):
        p = {"match_mismatch": 0.2, "match_commit": 0.3, "irrelevant": 0.5}
        d = {"match_mismatch": 100.0, "match_commit": 50.0, "irrelevant": 10.0}
        self.assertAlmostEqual(linear_prevalence_sum(p, d), 40.0, delta=1e-12)

    def test_stratum_mismatch_refused(self):
        with self.assertRaises(IntervalDomainError):
            linear_prevalence_sum({"a": 1.0}, {"b": 1.0})

    def test_bad_simplex_refused(self):
        with self.assertRaises(IntervalDomainError):
            linear_prevalence_sum({"a": 0.6, "b": 0.6}, {"a": 1.0, "b": 1.0})
        with self.assertRaises(IntervalDomainError):
            linear_prevalence_sum({"a": -0.5, "b": 1.5}, {"a": 1.0, "b": 1.0})


class TestHalfWidth(unittest.TestCase):
    def test_half_width(self):
        self.assertAlmostEqual(half_width((0.1, 0.5)), 0.2, delta=1e-15)
        with self.assertRaises(IntervalDomainError):
            half_width((0.5, 0.1))

    def test_sample_helpers(self):
        self.assertAlmostEqual(sample_mean(WELCH_A), 227.8, delta=1e-12)
        self.assertAlmostEqual(sample_sd(WELCH_A), 11.519548602267365, delta=1e-12)
        with self.assertRaises(IntervalDomainError):
            sample_sd([1.0])


if __name__ == "__main__":
    unittest.main()
