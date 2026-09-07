import unittest

from okx_ai import backtest
from okx_ai.backtest import Costs
from okx_ai.okx import Candle
from okx_ai.strategy import Signal, StrategyParams, generate_signals
from okx_ai.synthetic import gbm_candles


def bar(o, h, l, c, ts=0, v=100.0):
    return Candle(ts=ts, open=o, high=h, low=l, close=c, volume=v, quote_volume=v * c)


class TestTradeSimulation(unittest.TestCase):
    """Testa _simulate_one com barras montadas a mao, sem depender do sinal."""

    def setUp(self):
        self.p = StrategyParams(stop_atr=1.0, payoff=2.0, max_bars=10)
        self.costs = Costs(taker_fee=0.0, slippage=0.0)  # zero para isolar a mecanica

    def _run(self, candles, side="long", atr=1.0, index=0):
        signal = Signal(index=index, side=side, ref_close=candles[index].close, atr=atr, adx=30.0, volume_z=1.0)
        return backtest._simulate_one(candles, signal, self.p, self.costs)

    def test_long_hits_target(self):
        candles = [bar(100, 100, 100, 100, ts=0), bar(100, 101, 99.5, 101, ts=1), bar(101, 103, 100.5, 102.5, ts=2)]
        trade = self._run(candles)
        self.assertEqual(trade.reason, "target")
        self.assertAlmostEqual(trade.entry, 100.0)
        self.assertAlmostEqual(trade.exit, 102.0)   # entrada + 2 x ATR
        self.assertAlmostEqual(trade.r_multiple, 2.0, places=6)

    def test_long_hits_stop(self):
        candles = [bar(100, 100, 100, 100, ts=0), bar(100, 100.5, 98.0, 98.5, ts=1)]
        trade = self._run(candles)
        self.assertEqual(trade.reason, "stop")
        self.assertAlmostEqual(trade.exit, 99.0)
        self.assertAlmostEqual(trade.r_multiple, -1.0, places=6)

    def test_stop_wins_the_tie_inside_one_bar(self):
        """Barra que toca stop e alvo deve contar como STOP (premissa pessimista)."""
        candles = [bar(100, 100, 100, 100, ts=0), bar(100, 103, 98, 102, ts=1)]
        trade = self._run(candles)
        self.assertEqual(trade.reason, "stop")

    def test_short_hits_target(self):
        candles = [bar(100, 100, 100, 100, ts=0), bar(100, 100.5, 97.5, 98.0, ts=1)]
        trade = self._run(candles, side="short")
        self.assertEqual(trade.reason, "target")
        self.assertAlmostEqual(trade.exit, 98.0)
        self.assertAlmostEqual(trade.r_multiple, 2.0, places=6)

    def test_time_exit_when_nothing_is_touched(self):
        candles = [bar(100, 100, 100, 100, ts=0)] + [
            bar(100, 100.2, 99.8, 100.1, ts=i) for i in range(1, 15)
        ]
        trade = self._run(candles)
        self.assertEqual(trade.reason, "time")
        self.assertLessEqual(trade.exit_index, 11)  # entrada em 1 + max_bars 10

    def test_costs_reduce_the_result(self):
        candles = [bar(100, 100, 100, 100, ts=0), bar(100, 100, 100, 100, ts=1), bar(100, 103, 99.5, 102.5, ts=2)]
        free = self._run(candles)
        self.costs = Costs(taker_fee=0.001, slippage=0.0005)
        charged = self._run(candles)
        self.assertLess(charged.r_multiple, free.r_multiple)
        self.assertAlmostEqual(free.net_return - charged.net_return, 0.003, places=9)


class TestEngine(unittest.TestCase):
    def test_no_overlapping_positions(self):
        candles = gbm_candles(n=3000, seed=4)
        res = backtest.run(candles)
        for a, b in zip(res.trades, res.trades[1:]):
            self.assertGreater(b.entry_index, a.exit_index)

    def test_entry_always_after_the_signal_bar(self):
        candles = gbm_candles(n=2000, seed=6)
        p = StrategyParams()
        signals = {s.index: s for s in generate_signals(candles, p)}
        res = backtest.run(candles, p)
        for trade in res.trades:
            self.assertIn(trade.entry_index - 1, signals)
            self.assertAlmostEqual(trade.entry, candles[trade.entry_index].open)

    def test_metrics_are_internally_consistent(self):
        res = backtest.run(gbm_candles(n=4000, seed=8))
        self.assertGreater(res.n, 0)
        self.assertEqual(len(res.wins) + len(res.losses), res.n)
        self.assertAlmostEqual(res.hit_rate, len(res.wins) / res.n)
        total = sum(t.r_multiple for t in res.trades)
        self.assertAlmostEqual(res.expectancy_r * res.n, total, places=6)
        self.assertAlmostEqual(res.equity_curve_r()[-1], total, places=6)
        self.assertGreaterEqual(res.max_drawdown_r, 0.0)

    def test_higher_costs_never_improve_expectancy(self):
        candles = gbm_candles(n=4000, seed=9)
        cheap = backtest.run(candles, costs=Costs(taker_fee=0.0, slippage=0.0))
        pricey = backtest.run(candles, costs=Costs(taker_fee=0.002, slippage=0.001))
        self.assertLess(pricey.expectancy_r, cheap.expectancy_r)

    def test_random_walk_has_no_edge_after_costs(self):
        """Sanidade: em passeio aleatorio a expectancia liquida tem de ser <= 0."""
        candles = gbm_candles(n=6000, seed=21, drift_per_bar=0.0)
        res = backtest.run(candles)
        self.assertLessEqual(res.expectancy_r, 0.0)

    def test_walk_forward_splits_the_series(self):
        results = backtest.walk_forward(gbm_candles(n=4000, seed=12), folds=4)
        self.assertEqual(len(results), 4)
        self.assertTrue(all(r.bars >= 200 for r in results))


if __name__ == "__main__":
    unittest.main()
