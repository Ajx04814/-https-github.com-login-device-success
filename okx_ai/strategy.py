"""Regras de entrada e saida.

A estrategia e deliberadamente simples e falsificavel: pouca coisa para ajustar
significa pouca chance de overfit. Sao tres filtros e uma saida mecanica.

    1. Regime      - ADX acima de um piso: so opera quando ha tendencia.
    2. Direcao     - EMA rapida acima/abaixo da EMA lenta.
    3. Gatilho     - rompimento do maior maximo (menor minimo) das ultimas N barras
                     com volume acima da media (z-score de volume).
    4. Saida       - stop em k*ATR, alvo em b*k*ATR, e tempo maximo em barras.

Todo sinal e calculado com dados fechados ate a barra ``i`` e executado na
abertura da barra ``i+1``. Isso e o que impede o backtest de olhar o futuro.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import indicators as ind
from .okx import Candle


@dataclass(frozen=True)
class StrategyParams:
    ema_fast: int = 21
    ema_slow: int = 55
    adx_period: int = 14
    adx_min: float = 20.0
    breakout_lookback: int = 20
    volume_z_min: float = 0.5
    volume_z_period: int = 50
    atr_period: int = 14
    stop_atr: float = 1.5
    payoff: float = 2.0        # alvo = payoff x stop  (R multiplo do alvo)
    max_bars: int = 24         # saida por tempo, evita capital preso
    allow_short: bool = True


@dataclass(frozen=True)
class Signal:
    index: int          # barra em que o sinal foi gerado (execucao em index+1)
    side: str           # "long" ou "short"
    ref_close: float    # fechamento da barra do sinal
    atr: float          # unidade de risco no momento do sinal
    adx: float
    volume_z: float


@dataclass
class Features:
    """Indicadores pre-calculados, reaproveitados por sinal e por relatorio."""

    ema_fast: ind.Series = field(default_factory=list)
    ema_slow: ind.Series = field(default_factory=list)
    adx: ind.Series = field(default_factory=list)
    atr: ind.Series = field(default_factory=list)
    rsi: ind.Series = field(default_factory=list)
    volume_z: ind.Series = field(default_factory=list)


def compute_features(candles: list[Candle], p: StrategyParams) -> Features:
    closes = [c.close for c in candles]
    volumes = [c.quote_volume for c in candles]
    return Features(
        ema_fast=ind.ema(closes, p.ema_fast),
        ema_slow=ind.ema(closes, p.ema_slow),
        adx=ind.adx(candles, p.adx_period),
        atr=ind.atr(candles, p.atr_period),
        rsi=ind.rsi(closes, 14),
        volume_z=ind.zscore(volumes, p.volume_z_period),
    )


def generate_signals(candles: list[Candle], p: StrategyParams, feats: Features | None = None) -> list[Signal]:
    """Percorre a serie uma vez e devolve todos os sinais validos."""
    f = feats or compute_features(candles, p)
    signals: list[Signal] = []
    start = max(p.ema_slow, p.breakout_lookback, p.volume_z_period, 2 * p.adx_period) + 1

    for i in range(start, len(candles) - 1):
        atr_i, adx_i = f.atr[i], f.adx[i]
        fast, slow, vz = f.ema_fast[i], f.ema_slow[i], f.volume_z[i]
        if None in (atr_i, adx_i, fast, slow, vz) or atr_i <= 0:
            continue
        if adx_i < p.adx_min or vz < p.volume_z_min:
            continue

        window = candles[i - p.breakout_lookback : i]
        highest = max(c.high for c in window)
        lowest = min(c.low for c in window)
        close = candles[i].close

        side = None
        if fast > slow and close > highest:
            side = "long"
        elif p.allow_short and fast < slow and close < lowest:
            side = "short"
        if side is None:
            continue

        signals.append(
            Signal(index=i, side=side, ref_close=close, atr=atr_i, adx=adx_i, volume_z=vz)
        )
    return signals
