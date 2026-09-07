import math
import unittest

from okx_ai import indicators as ind
from okx_ai.okx import Candle
from okx_ai.synthetic import gbm_candles


def bar(o, h, l, c, v=1.0, ts=0):
    return Candle(ts=ts, open=o, high=h, low=l, close=c, volume=v, quote_volume=v * c)


class TestIndicators(unittest.TestCase):
    def test_sma_matches_manual_mean(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        out = ind.sma(values, 3)
        self.assertEqual(out[:2], [None, None])
        self.assertAlmostEqual(out[2], 2.0)
        self.assertAlmostEqual(out[4], 4.0)

    def test_ema_converges_on_constant_series(self):
        out = ind.ema([10.0] * 50, 10)
        self.assertAlmostEqual(out[-1], 10.0)

    def test_ema_reacts_faster_than_sma_right_after_a_jump(self):
        """Nas primeiras barras do salto a EMA ja subiu mais que a SMA.

        Depois que a janela inteira entra no novo patamar a SMA alcanca e
        ultrapassa a EMA, entao a comparacao so faz sentido perto do salto.
        """
        values = [1.0] * 30 + [2.0] * 10
        i = 32  # tres barras apos o salto
        self.assertGreater(ind.ema(values, 10)[i], ind.sma(values, 10)[i])

    def test_rsi_bounds_and_extremes(self):
        rising = [float(i) for i in range(1, 60)]
        self.assertAlmostEqual(ind.rsi(rising, 14)[-1], 100.0)
        falling = list(reversed(rising))
        self.assertAlmostEqual(ind.rsi(falling, 14)[-1], 0.0)

    def test_rsi_stays_in_range_on_noisy_series(self):
        closes = [c.close for c in gbm_candles(n=400, seed=1)]
        for value in ind.rsi(closes, 14):
            if value is not None:
                self.assertTrue(0.0 <= value <= 100.0)

    def test_atr_on_constant_range(self):
        candles = [bar(10, 11, 9, 10, ts=i) for i in range(40)]
        self.assertAlmostEqual(ind.atr(candles, 14)[-1], 2.0)

    def test_adx_high_on_clean_trend_low_on_chop(self):
        trend = [bar(100 + i, 101 + i, 99 + i, 100.8 + i, ts=i) for i in range(120)]
        chop = [bar(100, 101, 99, 100 + (0.2 if i % 2 else -0.2), ts=i) for i in range(120)]
        self.assertGreater(ind.adx(trend, 14)[-1], ind.adx(chop, 14)[-1])

    def test_zscore_is_zero_on_flat_then_defined(self):
        values = [1.0] * 20 + [5.0]
        out = ind.zscore(values, 20)
        self.assertIsNone(out[19])  # desvio zero: indefinido, nao infinito
        self.assertIsNotNone(out[20])

    def test_series_length_always_matches_input(self):
        candles = gbm_candles(n=200, seed=2)
        closes = [c.close for c in candles]
        for series in (
            ind.sma(closes, 20),
            ind.ema(closes, 20),
            ind.rsi(closes, 14),
            ind.atr(candles, 14),
            ind.adx(candles, 14),
            ind.realized_vol(closes, 50),
        ):
            self.assertEqual(len(series), 200)

    def test_indicators_do_not_look_ahead(self):
        """Truncar a serie no ponto i nao pode mudar o indicador em i."""
        candles = gbm_candles(n=300, seed=5)
        closes = [c.close for c in candles]
        cut = 250
        full = ind.ema(closes, 21)[cut]
        partial = ind.ema(closes[: cut + 1], 21)[cut]
        self.assertTrue(math.isclose(full, partial, rel_tol=1e-12))

        full_atr = ind.atr(candles, 14)[cut]
        partial_atr = ind.atr(candles[: cut + 1], 14)[cut]
        self.assertTrue(math.isclose(full_atr, partial_atr, rel_tol=1e-12))


if __name__ == "__main__":
    unittest.main()
