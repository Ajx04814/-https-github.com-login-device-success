"""Testes da lógica do setup — não tocam a rede."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from okxsma.strategy import Candle, Config, Status, analyze, sma  # noqa: E402

CFG = Config()
MS = 3_600_000


def _bar(i, o, h, l, c, v):
    return Candle(i * MS, o, h, l, c, v)


def build_series(
    *,
    dip_bars=5,
    dip_step=1.2,
    breakout_pct=1.6,
    rejection=True,
    confirmation=True,
    breakout_volume=3.0,
    confirm_volume=3.0,
    downtrend=False,
):
    """Monta uma série sintética com o setup completo (ou faltando uma peça).

    Cada candle é posicionado em relação à SMA 21 corrente, então o setup
    aparece exatamente onde queremos, sem depender de dados reais.
    """
    candles = []
    closes = []
    base_vol = 1000.0

    def push(o, h, l, c, v):
        candles.append(_bar(len(candles), o, h, l, c, v))
        closes.append(c)

    # 1) 240 barras de tendência de alta: preço acima da SMA 200 e ela subindo.
    price = 100.0
    for _ in range(240):
        step = -0.15 if downtrend else 0.6
        nxt = price + step
        push(price, max(price, nxt) + 0.2, min(price, nxt) - 0.2, nxt, base_vol)
        price = nxt

    def sma21():
        return sma(closes, CFG.mid)[-1]

    # 2) Recuo: o preço volta e fecha abaixo da amarela (pré-requisito do rompimento).
    for _ in range(dip_bars):
        nxt = price - dip_step
        push(price, price + 0.2, nxt - 0.3, nxt, base_vol * 0.8)
        price = nxt
    while closes[-1] > sma21():  # garante o fechamento abaixo da amarela
        nxt = price - dip_step
        push(price, price + 0.2, nxt - 0.3, nxt, base_vol * 0.8)
        price = nxt

    # 3) Rompimento: candle de alta fechando acima da amarela, com volume.
    linha = sma21()
    close_b = linha * (1 + breakout_pct / 100.0)
    push(price, close_b + 0.3, price - 0.3, close_b, base_vol * breakout_volume)
    price = close_b

    # 4) Rejeição: volta na amarela, deixa pavio e fecha acima dela.
    if rejection:
        linha = sma21()
        low = linha * 0.998
        close_r = linha * 1.006
        high_r = close_r + (close_r - low) * 0.10
        push(price, high_r, low, close_r, base_vol * 1.1)
        price = close_r
        rejection_high = high_r
    else:  # sem rejeição: candle neutro longe da linha
        nxt = price + 0.2
        push(price, nxt + 0.1, price - 0.05, nxt, base_vol)
        price = nxt
        rejection_high = candles[-1].high

    # 5) Confirmação: fecha acima da máxima do candle de rejeição, com volume.
    if confirmation:
        close_c = rejection_high * 1.01
        push(price, close_c + 0.2, price - 0.2, close_c, base_vol * confirm_volume)
    return candles


class SmaTest(unittest.TestCase):
    def test_sma_valores(self):
        self.assertEqual(sma([1, 2, 3, 4, 5], 3), [None, None, 2.0, 3.0, 4.0])

    def test_sma_periodo_invalido(self):
        with self.assertRaises(ValueError):
            sma([1, 2, 3], 0)


class SetupTest(unittest.TestCase):
    def analyze(self, candles, cfg=CFG):
        return analyze("TEST-USDT", "1H", candles, cfg)

    def test_setup_completo_gera_sinal(self):
        sig = self.analyze(build_series())
        self.assertIs(sig.status, Status.SINAL)
        self.assertGreater(sig.entry, sig.stop)
        self.assertAlmostEqual(sig.target_2r - sig.entry,
                               2 * (sig.entry - sig.stop), places=6)
        self.assertAlmostEqual(sig.target_3r - sig.entry,
                               3 * (sig.entry - sig.stop), places=6)
        self.assertGreater(sig.score, 40)
        self.assertEqual(sig.bars_ago, 0)          # confirmou no último candle fechado
        self.assertGreater(sig.sma_fast, sig.sma_mid)
        self.assertGreater(sig.price, sig.sma_slow)

    def test_sem_dados_suficientes(self):
        sig = self.analyze(build_series()[:100])
        self.assertIs(sig.status, Status.SEM_DADOS)

    def test_tendencia_de_baixa_nao_gera_sinal(self):
        sig = self.analyze(build_series(downtrend=True))
        self.assertIn(sig.status, (Status.SEM_TENDENCIA, Status.SEM_DADOS))
        self.assertIsNone(sig.entry)

    def test_sem_confirmacao_fica_aguardando(self):
        sig = self.analyze(build_series(confirmation=False))
        self.assertIs(sig.status, Status.REJEITOU_AGUARDA_CONFIRMACAO)
        self.assertIsNone(sig.entry)

    def test_sem_rejeicao_fica_aguardando(self):
        sig = self.analyze(build_series(rejection=False, confirmation=False))
        self.assertIs(sig.status, Status.ROMPEU_AGUARDA_REJEICAO)

    def test_volume_fraco_derruba_o_sinal(self):
        sig = self.analyze(build_series(breakout_volume=0.9, confirm_volume=0.9))
        self.assertIs(sig.status, Status.REJEITOU_AGUARDA_CONFIRMACAO)
        self.assertTrue(any("volume" in n for n in sig.notes))

    def test_sinal_velho_e_descartado(self):
        candles = build_series()
        seguinte = candles[-1]
        # dois candles neutros depois da confirmação: sinal envelhece
        for i in (1, 2):
            candles.append(Candle(seguinte.ts + i * MS, seguinte.close,
                                  seguinte.close + 0.1, seguinte.close - 0.1,
                                  seguinte.close, 1000.0))
        sig = self.analyze(candles)
        self.assertIsNot(sig.status, Status.SINAL)

    def test_max_age_maior_reencontra_o_sinal(self):
        candles = build_series()
        ultimo = candles[-1]
        candles.append(Candle(ultimo.ts + MS, ultimo.close, ultimo.close + 0.1,
                              ultimo.close - 0.1, ultimo.close, 1000.0))
        sig = self.analyze(candles, Config(max_age=3))
        self.assertIs(sig.status, Status.SINAL)
        self.assertEqual(sig.bars_ago, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
