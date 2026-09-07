import unittest
from unittest import mock

from okx_ai import screener

TICKERS = [
    # par liquido e apertado
    {"instId": "BTC-USDT", "last": "60000", "bidPx": "59997", "askPx": "60003", "high24h": "61200", "low24h": "59000", "volCcy24h": "900000000"},
    # spread largo demais
    {"instId": "JUNK-USDT", "last": "0.01", "bidPx": "0.0099", "askPx": "0.0101", "high24h": "0.012", "low24h": "0.009", "volCcy24h": "20000000"},
    # volume baixo demais
    {"instId": "THIN-USDT", "last": "5", "bidPx": "4.999", "askPx": "5.001", "high24h": "5.5", "low24h": "4.8", "volCcy24h": "100000"},
    # ordem minima acima do nocional pretendido
    {"instId": "BIG-USDT", "last": "1000", "bidPx": "999.9", "askPx": "1000.1", "high24h": "1050", "low24h": "980", "volCcy24h": "80000000"},
    # par de outra cotacao: deve ser ignorado pelo filtro de quote
    {"instId": "ETH-BTC", "last": "0.05", "bidPx": "0.0499", "askPx": "0.0501", "high24h": "0.052", "low24h": "0.049", "volCcy24h": "50000000"},
]

INSTRUMENTS = [
    {"instId": "BTC-USDT", "state": "live", "minSz": "0.00001", "lotSz": "0.00000001", "tickSz": "0.1"},
    {"instId": "JUNK-USDT", "state": "live", "minSz": "1", "lotSz": "0.1", "tickSz": "0.0001"},
    {"instId": "THIN-USDT", "state": "live", "minSz": "0.1", "lotSz": "0.01", "tickSz": "0.001"},
    {"instId": "BIG-USDT", "state": "live", "minSz": "1", "lotSz": "0.1", "tickSz": "0.1"},
    {"instId": "ETH-BTC", "state": "live", "minSz": "0.001", "lotSz": "0.0001", "tickSz": "0.00001"},
    {"instId": "DEAD-USDT", "state": "suspend", "minSz": "1", "lotSz": "0.1", "tickSz": "0.01"},
]


class TestScreener(unittest.TestCase):
    def collect(self):
        with mock.patch.object(screener.okx, "tickers", return_value=TICKERS), mock.patch.object(
            screener.okx, "instruments", return_value=INSTRUMENTS
        ):
            return screener.collect(quote="USDT")

    def test_only_live_usdt_pairs_are_collected(self):
        ids = {p.inst_id for p in self.collect()}
        self.assertEqual(ids, {"BTC-USDT", "JUNK-USDT", "THIN-USDT", "BIG-USDT"})

    def test_spread_is_relative_to_mid(self):
        btc = next(p for p in self.collect() if p.inst_id == "BTC-USDT")
        self.assertAlmostEqual(btc.spread_pct, 6.0 / 60000.0, places=9)
        self.assertAlmostEqual(btc.range_24h_pct, (61200 - 59000) / 59000, places=9)

    def test_min_order_size_in_dollars(self):
        big = next(p for p in self.collect() if p.inst_id == "BIG-USDT")
        self.assertAlmostEqual(big.min_size_usd, 1000.0)
        self.assertFalse(big.tradable_at(200.0))
        self.assertTrue(big.tradable_at(1500.0))

    def test_rank_drops_wide_spread_thin_volume_and_oversized_minimum(self):
        top = screener.rank(self.collect(), notional_usd=200.0)
        self.assertEqual([p.inst_id for p in top], ["BTC-USDT"])

    def test_loosening_filters_lets_more_pairs_through(self):
        top = screener.rank(self.collect(), notional_usd=2000.0, min_volume_usd=1_000.0, max_spread_pct=0.05)
        self.assertGreater(len(top), 1)

    def test_score_prefers_tight_spread_for_equal_range(self):
        tight = screener.PairStats("A-USDT", 100, 99.99, 100.01, 5e7, 0.05, 1.0, 0.01)
        wide = screener.PairStats("B-USDT", 100, 99.8, 100.2, 5e7, 0.05, 1.0, 0.01)
        self.assertGreater(tight.score(), wide.score())

    def test_malformed_fields_do_not_crash(self):
        broken = [{"instId": "X-USDT", "last": "", "bidPx": None, "askPx": "abc", "high24h": "1", "low24h": "0", "volCcy24h": "x"}]
        with mock.patch.object(screener.okx, "tickers", return_value=broken), mock.patch.object(
            screener.okx, "instruments", return_value=[{"instId": "X-USDT", "state": "live", "minSz": "1", "lotSz": "1"}]
        ):
            self.assertEqual(screener.collect(quote="USDT"), [])


if __name__ == "__main__":
    unittest.main()
