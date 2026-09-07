import unittest

from okx_ai import risk


class TestEdgeMath(unittest.TestCase):
    def test_cost_drag_scales_inversely_with_stop(self):
        self.assertAlmostEqual(risk.cost_drag_r(0.003, 0.003), 1.0)
        self.assertAlmostEqual(risk.cost_drag_r(0.006, 0.003), 0.5)
        self.assertAlmostEqual(risk.cost_drag_r(0.030, 0.003), 0.1)

    def test_breakeven_matches_zero_expectancy(self):
        for payoff in (0.5, 1.0, 2.0, 3.0):
            for drag in (0.0, 0.2, 0.5):
                p = risk.breakeven_hit_rate(payoff, drag)
                self.assertAlmostEqual(risk.expectancy_r(p, payoff, drag), 0.0, places=9)

    def test_breakeven_rises_with_cost(self):
        self.assertLess(risk.breakeven_hit_rate(2.0, 0.0), risk.breakeven_hit_rate(2.0, 0.5))

    def test_classic_breakeven_without_cost(self):
        self.assertAlmostEqual(risk.breakeven_hit_rate(1.0, 0.0), 0.5)
        self.assertAlmostEqual(risk.breakeven_hit_rate(2.0, 0.0), 1 / 3)

    def test_kelly_is_zero_or_negative_without_edge(self):
        be = risk.breakeven_hit_rate(2.0, 0.3)
        self.assertAlmostEqual(risk.kelly_fraction(be, 2.0, 0.3), 0.0, places=9)
        self.assertLess(risk.kelly_fraction(be - 0.05, 2.0, 0.3), 0.0)
        self.assertGreater(risk.kelly_fraction(be + 0.05, 2.0, 0.3), 0.0)

    def test_required_hit_rate_flags_impossible_targets(self):
        # Dobrar a banca em 59 trades de 2 dolares com payoff 2 exige > 100% de acerto.
        need = risk.required_hit_rate_for_target(
            payoff=2.0, drag_r=0.5, target_usd=500.0, n_trades=59, risk_usd=2.0
        )
        self.assertGreater(need, 1.0)


class TestSizing(unittest.TestCase):
    def test_notional_is_risk_divided_by_stop(self):
        s = risk.Sizing(risk_usd=2.0, stop_pct=0.005, round_trip_cost=0.003)
        self.assertAlmostEqual(s.notional_usd, 400.0)
        self.assertAlmostEqual(s.fee_usd, 1.2)
        self.assertAlmostEqual(s.fee_as_r, 0.6)

    def test_wider_stop_means_smaller_notional_and_cheaper_fees(self):
        tight, wide = risk.sizing_table(2.0, 0.003, [0.003, 0.030])
        self.assertGreater(tight.notional_usd, wide.notional_usd)
        self.assertGreater(tight.fee_as_r, wide.fee_as_r)


class TestSession(unittest.TestCase):
    def test_expected_pnl_matches_analytic_expectancy(self):
        stats = risk.simulate_session(hit_rate=0.45, payoff=2.0, drag_r=0.1, trials=40_000, seed=1)
        analytic = risk.expectancy_r(0.45, 2.0, 0.1)
        self.assertAlmostEqual(stats.expectancy_r, analytic, places=9)
        self.assertAlmostEqual(stats.mean_pnl, analytic * 59 * 2.0, delta=0.6)

    def test_small_sample_loses_often_even_with_a_real_edge(self):
        """O ponto central: vantagem positiva NAO garante lucro em 59 trades."""
        stats = risk.simulate_session(hit_rate=0.40, payoff=2.0, drag_r=0.2, trials=20_000, seed=2)
        self.assertGreater(stats.expectancy_r, 0.0)
        self.assertLess(stats.prob_profit, 0.85)
        self.assertLess(stats.p05, 0.0)  # o pior 5% ainda termina no vermelho

    def test_negative_edge_almost_never_profits(self):
        stats = risk.simulate_session(hit_rate=0.25, payoff=2.0, drag_r=0.5, trials=10_000, seed=3)
        self.assertLess(stats.expectancy_r, 0.0)
        self.assertLess(stats.prob_profit, 0.15)

    def test_more_trades_shrink_the_relative_noise(self):
        few = risk.simulate_session(0.40, 2.0, n_trades=59, drag_r=0.2, trials=20_000, seed=4)
        many = risk.simulate_session(0.40, 2.0, n_trades=590, drag_r=0.2, trials=20_000, seed=4)
        self.assertGreater(many.prob_profit, few.prob_profit)

    def test_quantiles_are_ordered(self):
        s = risk.simulate_session(0.45, 2.0, trials=10_000, seed=5)
        self.assertLessEqual(s.p05, s.p25)
        self.assertLessEqual(s.p25, s.median_pnl)
        self.assertLessEqual(s.median_pnl, s.p75)
        self.assertLessEqual(s.p75, s.p95)


class TestStreaksAndMartingale(unittest.TestCase):
    def test_streak_probability_matches_brute_force(self):
        import itertools

        p, n, k = 0.55, 12, 4
        total = 0.0
        for combo in itertools.product([0, 1], repeat=n):
            prob = 1.0
            run = worst = 0
            for outcome in combo:
                prob *= p if outcome else (1 - p)
                run = 0 if outcome else run + 1
                worst = max(worst, run)
            if worst >= k:
                total += prob
        self.assertAlmostEqual(risk.prob_losing_streak(p, n, k), total, places=9)

    def test_losing_streaks_are_common_in_59_trades(self):
        # Com 45% de acerto, uma sequencia de 5 perdas seguidas e quase certa.
        self.assertGreater(risk.prob_losing_streak(0.45, 59, 5), 0.6)

    def test_martingale_ruins_a_small_bankroll(self):
        out = risk.martingale_ruin(hit_rate=0.50, capital_usd=100.0, base_usd=2.0, n_trades=59, trials=5_000)
        self.assertGreater(out["prob_ruina"], 0.3)
        self.assertGreater(out["maior_aposta_maxima"], 32.0)

    def test_sharpe_is_zero_at_breakeven(self):
        be = risk.breakeven_hit_rate(2.0, 0.2)
        self.assertAlmostEqual(risk.sharpe_per_trade(0.0, be, 2.0, 0.2), 0.0, places=9)


if __name__ == "__main__":
    unittest.main()
