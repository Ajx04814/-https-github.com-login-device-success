"""Indicadores tecnicos em Python puro.

Todas as funcoes recebem listas e devolvem listas do mesmo comprimento, com
``None`` nas posicoes em que ainda nao ha janela suficiente. Nenhuma funcao
olha para o futuro: o valor no indice ``i`` usa somente dados ate ``i``.
"""

from __future__ import annotations

import math

from .okx import Candle

Series = list[float | None]


def sma(values: list[float], period: int) -> Series:
    out: Series = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    total = sum(values[:period])
    out[period - 1] = total / period
    for i in range(period, len(values)):
        total += values[i] - values[i - period]
        out[i] = total / period
    return out


def ema(values: list[float], period: int) -> Series:
    out: Series = [None] * len(values)
    if period <= 0 or len(values) < period:
        return out
    k = 2.0 / (period + 1.0)
    prev = sum(values[:period]) / period  # semente: SMA da primeira janela
    out[period - 1] = prev
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1.0 - k)
        out[i] = prev
    return out


def stdev(values: list[float], period: int) -> Series:
    out: Series = [None] * len(values)
    if period < 2 or len(values) < period:
        return out
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        mean = sum(window) / period
        var = sum((v - mean) ** 2 for v in window) / (period - 1)
        out[i] = math.sqrt(var)
    return out


def rsi(closes: list[float], period: int = 14) -> Series:
    """RSI de Wilder. Mede em qual regime de exaustao o preco esta."""
    out: Series = [None] * len(closes)
    if len(closes) <= period:
        return out

    gains = 0.0
    losses = 0.0
    for i in range(1, period + 1):
        delta = closes[i] - closes[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain = gains / period
    avg_loss = losses / period
    out[period] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    for i in range(period + 1, len(closes)):
        delta = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(delta, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0.0)) / period
        out[i] = 100.0 if avg_loss == 0 else 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
    return out


def true_range(candles: list[Candle]) -> list[float]:
    out = [candles[0].high - candles[0].low] if candles else []
    for i in range(1, len(candles)):
        c = candles[i]
        prev_close = candles[i - 1].close
        out.append(max(c.high - c.low, abs(c.high - prev_close), abs(c.low - prev_close)))
    return out


def atr(candles: list[Candle], period: int = 14) -> Series:
    """ATR de Wilder: a unidade natural de risco desta estrategia."""
    tr = true_range(candles)
    out: Series = [None] * len(candles)
    if len(tr) < period:
        return out
    prev = sum(tr[:period]) / period
    out[period - 1] = prev
    for i in range(period, len(tr)):
        prev = (prev * (period - 1) + tr[i]) / period
        out[i] = prev
    return out


def adx(candles: list[Candle], period: int = 14) -> Series:
    """ADX de Wilder: separa mercado em tendencia de mercado lateral."""
    n = len(candles)
    out: Series = [None] * n
    if n < 2 * period + 1:
        return out

    plus_dm, minus_dm = [], []
    for i in range(1, n):
        up = candles[i].high - candles[i - 1].high
        down = candles[i - 1].low - candles[i].low
        plus_dm.append(up if (up > down and up > 0) else 0.0)
        minus_dm.append(down if (down > up and down > 0) else 0.0)
    tr = true_range(candles)[1:]

    def wilder(seq: list[float]) -> list[float]:
        acc = sum(seq[:period])
        smoothed = [acc]
        for i in range(period, len(seq)):
            acc = acc - acc / period + seq[i]
            smoothed.append(acc)
        return smoothed

    s_tr, s_plus, s_minus = wilder(tr), wilder(plus_dm), wilder(minus_dm)

    dx: list[float] = []
    for i in range(len(s_tr)):
        if s_tr[i] == 0:
            dx.append(0.0)
            continue
        di_plus = 100.0 * s_plus[i] / s_tr[i]
        di_minus = 100.0 * s_minus[i] / s_tr[i]
        denom = di_plus + di_minus
        dx.append(0.0 if denom == 0 else 100.0 * abs(di_plus - di_minus) / denom)

    if len(dx) < period:
        return out
    adx_val = sum(dx[:period]) / period
    # dx[j] corresponde a candles[j + period]; o primeiro ADX usa ate dx[period-1].
    out[2 * period - 1] = adx_val
    for j in range(period, len(dx)):
        adx_val = (adx_val * (period - 1) + dx[j]) / period
        idx = j + period
        if idx < n:
            out[idx] = adx_val
    return out


def zscore(values: list[float], period: int) -> Series:
    """Quantos desvios-padrao o valor corrente esta da sua propria media."""
    mean = sma(values, period)
    sd = stdev(values, period)
    out: Series = [None] * len(values)
    for i in range(len(values)):
        if mean[i] is None or sd[i] is None or sd[i] == 0:
            continue
        out[i] = (values[i] - mean[i]) / sd[i]
    return out


def realized_vol(closes: list[float], period: int = 96) -> Series:
    """Volatilidade realizada por barra (desvio dos log-retornos)."""
    rets = [0.0] + [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    return stdev(rets, period)
