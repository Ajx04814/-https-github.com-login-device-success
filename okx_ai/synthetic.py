"""Series sinteticas para rodar e testar o toolkit sem acesso a rede.

O gerador nao serve para validar estrategia: serve para exercitar o codigo com
dados que tem as propriedades estatisticas certas (retornos com cauda gorda,
volatilidade agrupada, volume correlacionado com a amplitude da barra).
"""

from __future__ import annotations

import math
import random

from .okx import Candle


def gbm_candles(
    n: int = 1500,
    start: float = 100.0,
    bar_ms: int = 300_000,
    vol_per_bar: float = 0.0025,
    drift_per_bar: float = 0.0,
    seed: int = 7,
    start_ts: int = 1_700_000_000_000,
) -> list[Candle]:
    """Gera ``n`` candles com volatilidade estocastica (GARCH-like)."""
    rng = random.Random(seed)
    price = start
    sigma = vol_per_bar
    out: list[Candle] = []

    for i in range(n):
        # Volatilidade com reversao a media + choque: produz clusters de vol.
        shock = abs(rng.gauss(0.0, 1.0))
        sigma = 0.92 * sigma + 0.08 * vol_per_bar * (0.5 + shock)
        ret = rng.gauss(drift_per_bar, sigma)

        open_ = price
        close = open_ * math.exp(ret)
        # Amplitude intrabarra proporcional a vol corrente.
        wick = abs(rng.gauss(0.0, sigma)) * open_
        high = max(open_, close) + wick
        low = min(open_, close) - wick
        low = max(low, 1e-9)

        volume = max(1.0, rng.lognormvariate(3.0, 0.6) * (1.0 + 40.0 * abs(ret)))
        out.append(
            Candle(
                ts=start_ts + i * bar_ms,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
                quote_volume=volume * close,
            )
        )
        price = close

    return out
