"""Lógica da estratégia SMA 8 / 21 / 200 (branco / amarelo / roxo).

Regra descrita pelo operador:

    1. Tendência de alta (preço acima da SMA 200 roxa, SMA 200 subindo).
    2. O candle ROMPE a linha amarela (SMA 21) para cima, fechando acima dela.
    3. O preço volta, TESTA a amarela e REJEITA (pavio inferior, fecha acima).
    4. O candle seguinte CONFIRMA (fecha acima da máxima do candle de rejeição)
       — só depois do candle fechar, ou seja, "após o horário".
    5. O volume do rompimento e/ou da confirmação acima da média.

Este módulo não faz rede: recebe candles e devolve o diagnóstico.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class Candle:
    ts: int          # epoch em milissegundos (abertura do candle)
    open: float
    high: float
    low: float
    close: float
    volume: float    # volume na moeda base

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open


class Status(str, Enum):
    """Em que estágio do setup o par está — serve como watchlist."""

    SEM_DADOS = "sem_dados"                       # candles insuficientes p/ SMA 200
    SEM_TENDENCIA = "sem_tendencia"               # abaixo da roxa ou roxa caindo
    TENDENCIA_SEM_ROMPIMENTO = "tendencia_sem_rompimento"
    ROMPEU_AGUARDA_REJEICAO = "rompeu_aguarda_rejeicao"
    REJEITOU_AGUARDA_CONFIRMACAO = "rejeitou_aguarda_confirmacao"
    SINAL = "sinal"                               # entrada válida


@dataclass(frozen=True)
class Config:
    fast: int = 8                 # SMA branca
    mid: int = 21                 # SMA amarela (gatilho)
    slow: int = 200               # SMA roxa (tendência macro)
    vol_ma: int = 20              # média do volume
    min_vol_ratio: float = 1.2    # volume mínimo / média
    slope_lookback: int = 20      # barras p/ medir inclinação da SMA 200
    min_slope_pct: float = 0.0    # inclinação mínima da roxa, em % do preço
    min_break_pct: float = 0.05   # rompimento mínimo acima da amarela, em %
    touch_tol_pct: float = 0.35   # tolerância p/ considerar que testou a amarela
    min_wick_ratio: float = 0.30  # pavio inferior / range do candle de rejeição
    max_close_pos: float = 0.50   # fecho na metade superior do range (0=topo)
    breakout_lookback: int = 8    # até quantas barras antes da rejeição buscar o rompimento
    max_rejection_gap: int = 3    # barras entre rejeição e confirmação
    max_age: int = 1              # confirmação no último candle fechado (0) ou até N atrás
    require_stack: bool = True    # exige SMA 8 > SMA 21 na confirmação


@dataclass
class Signal:
    symbol: str
    timeframe: str
    status: Status
    price: float
    sma_fast: Optional[float] = None
    sma_mid: Optional[float] = None
    sma_slow: Optional[float] = None
    slope_pct: Optional[float] = None
    breakout_index: Optional[int] = None
    rejection_index: Optional[int] = None
    confirm_index: Optional[int] = None
    confirm_ts: Optional[int] = None
    bars_ago: Optional[int] = None
    vol_ratio_breakout: Optional[float] = None
    vol_ratio_confirm: Optional[float] = None
    entry: Optional[float] = None
    stop: Optional[float] = None
    target_2r: Optional[float] = None
    target_3r: Optional[float] = None
    risk_pct: Optional[float] = None
    score: float = 0.0
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["status"] = self.status.value
        return d


def sma(values: Sequence[float], period: int) -> List[Optional[float]]:
    """Média móvel simples; None enquanto não há barras suficientes."""
    if period <= 0:
        raise ValueError("period deve ser > 0")
    out: List[Optional[float]] = [None] * len(values)
    total = 0.0
    for i, v in enumerate(values):
        total += v
        if i >= period:
            total -= values[i - period]
        if i >= period - 1:
            out[i] = total / period
    return out


def _close_position(c: Candle) -> float:
    """0.0 = fechou na máxima, 1.0 = fechou na mínima."""
    if c.range <= 0:
        return 0.0
    return (c.high - c.close) / c.range


def _trend_ok(i: int, candles, mid, slow, cfg) -> bool:
    if slow[i] is None or mid[i] is None:
        return False
    return candles[i].close > slow[i]


def _slope_pct(i: int, slow: Sequence[Optional[float]], cfg: Config) -> Optional[float]:
    j = i - cfg.slope_lookback
    if j < 0 or slow[i] is None or slow[j] is None or slow[j] == 0:
        return None
    return (slow[i] - slow[j]) / slow[j] * 100.0


def _is_breakout(i: int, candles, mid, cfg) -> bool:
    """Candle de alta que fecha acima da amarela vindo de baixo dela."""
    if i <= 0 or mid[i] is None or mid[i - 1] is None:
        return False
    c, prev = candles[i], candles[i - 1]
    if not c.is_bullish:
        return False
    if c.close < mid[i] * (1 + cfg.min_break_pct / 100.0):
        return False
    return prev.close <= mid[i - 1]


def _is_rejection(j: int, candles, mid, cfg) -> bool:
    """Voltou na amarela, deixou pavio e fechou acima dela."""
    if mid[j] is None:
        return False
    c = candles[j]
    tol = mid[j] * (1 + cfg.touch_tol_pct / 100.0)
    if c.low > tol:              # nem chegou a testar a linha
        return False
    if c.close <= mid[j]:        # fechou abaixo: não rejeitou, perdeu a linha
        return False
    if c.range <= 0:
        return False
    if c.lower_wick / c.range < cfg.min_wick_ratio:
        return False
    return _close_position(c) <= cfg.max_close_pos


def _is_confirmation(k: int, j: int, candles, fast, mid, cfg) -> bool:
    """Fecha acima da máxima do candle de rejeição, com as médias empilhadas."""
    if mid[k] is None or fast[k] is None:
        return False
    c = candles[k]
    if not c.is_bullish or c.close <= candles[j].high:
        return False
    if c.close <= mid[k]:
        return False
    if cfg.require_stack and fast[k] <= mid[k]:
        return False
    return True


def _vol_ratio(i: int, vol_avg: Sequence[Optional[float]], candles) -> Optional[float]:
    avg = vol_avg[i]
    if avg in (None, 0):
        return None
    return candles[i].volume / avg


def _score(sig: Signal, cfg: Config) -> float:
    """0-100: qualidade do setup (volume, inclinação, folga da roxa, pavio)."""
    score = 40.0
    vr = max(v for v in (sig.vol_ratio_breakout, sig.vol_ratio_confirm, 0.0) if v is not None)
    score += min(25.0, (vr - 1.0) * 25.0) if vr > 1.0 else 0.0
    if sig.slope_pct is not None:
        score += min(15.0, max(0.0, sig.slope_pct) * 3.0)
    if sig.sma_slow and sig.price:
        folga = (sig.price - sig.sma_slow) / sig.sma_slow * 100.0
        score += min(10.0, max(0.0, folga) / 2.0)
    if sig.risk_pct:
        score += 10.0 if sig.risk_pct <= 2.0 else (5.0 if sig.risk_pct <= 4.0 else 0.0)
    return round(min(100.0, score), 1)


def analyze(
    symbol: str,
    timeframe: str,
    candles: Sequence[Candle],
    cfg: Config = Config(),
) -> Signal:
    """Avalia a série (apenas candles FECHADOS) e devolve o estágio do setup."""
    closes = [c.close for c in candles]
    vols = [c.volume for c in candles]
    n = len(candles)

    if n < cfg.slow + cfg.slope_lookback + 2:
        return Signal(symbol, timeframe, Status.SEM_DADOS,
                      price=closes[-1] if closes else 0.0,
                      notes=[f"{n} candles; preciso de {cfg.slow + cfg.slope_lookback + 2}"])

    fast = sma(closes, cfg.fast)
    mid = sma(closes, cfg.mid)
    slow = sma(closes, cfg.slow)
    vol_avg = sma(vols, cfg.vol_ma)

    last = n - 1
    sig = Signal(
        symbol=symbol,
        timeframe=timeframe,
        status=Status.SEM_TENDENCIA,
        price=closes[last],
        sma_fast=fast[last],
        sma_mid=mid[last],
        sma_slow=slow[last],
        slope_pct=_slope_pct(last, slow, cfg),
    )

    if not _trend_ok(last, candles, mid, slow, cfg):
        sig.notes.append("preço abaixo da SMA 200 (roxa)")
        return sig
    if sig.slope_pct is None or sig.slope_pct < cfg.min_slope_pct:
        sig.status = Status.SEM_TENDENCIA
        sig.notes.append("SMA 200 sem inclinação de alta")
        return sig

    sig.status = Status.TENDENCIA_SEM_ROMPIMENTO

    # Confirmação: último candle fechado (ou até cfg.max_age barras atrás).
    for k in range(last, max(last - cfg.max_age, 0) - 1, -1):
        for j in range(k - 1, max(k - 1 - cfg.max_rejection_gap, 0) - 1, -1):
            if not _is_rejection(j, candles, mid, cfg):
                continue
            for i in range(j, max(j - cfg.breakout_lookback, 1) - 1, -1):
                if not _is_breakout(i, candles, mid, cfg):
                    continue
                if not _trend_ok(i, candles, mid, slow, cfg):
                    continue
                # Estágios parciais úteis mesmo sem a confirmação fechada.
                if sig.status is Status.TENDENCIA_SEM_ROMPIMENTO:
                    sig.status = Status.REJEITOU_AGUARDA_CONFIRMACAO
                    sig.breakout_index, sig.rejection_index = i, j
                if not _is_confirmation(k, j, candles, fast, mid, cfg):
                    continue

                vr_b = _vol_ratio(i, vol_avg, candles)
                vr_c = _vol_ratio(k, vol_avg, candles)
                best_vr = max([v for v in (vr_b, vr_c) if v is not None] or [0.0])
                if best_vr < cfg.min_vol_ratio:
                    sig.status = Status.REJEITOU_AGUARDA_CONFIRMACAO
                    sig.breakout_index, sig.rejection_index = i, j
                    sig.vol_ratio_breakout, sig.vol_ratio_confirm = vr_b, vr_c
                    sig.notes.append(
                        f"confirmou, mas volume fraco ({best_vr:.2f}x < {cfg.min_vol_ratio:.2f}x)")
                    return sig

                entry = candles[k].close
                stop = min(candles[j].low, mid[k] or candles[j].low) * 0.999
                risk = entry - stop
                sig.status = Status.SINAL
                sig.breakout_index, sig.rejection_index, sig.confirm_index = i, j, k
                sig.confirm_ts = candles[k].ts
                sig.bars_ago = last - k
                sig.vol_ratio_breakout, sig.vol_ratio_confirm = vr_b, vr_c
                sig.entry = entry
                sig.stop = stop
                sig.target_2r = entry + 2 * risk
                sig.target_3r = entry + 3 * risk
                sig.risk_pct = risk / entry * 100.0 if entry else None
                sig.score = _score(sig, cfg)
                return sig

    # Rejeitou no último candle fechado? Então a confirmação é o próximo candle.
    if sig.status is Status.TENDENCIA_SEM_ROMPIMENTO:
        janela = cfg.max_age + cfg.max_rejection_gap
        for j in range(last, max(last - janela, 1) - 1, -1):
            if not _is_rejection(j, candles, mid, cfg):
                continue
            for i in range(j, max(j - cfg.breakout_lookback, 1) - 1, -1):
                if _is_breakout(i, candles, mid, cfg) and _trend_ok(i, candles, mid, slow, cfg):
                    sig.status = Status.REJEITOU_AGUARDA_CONFIRMACAO
                    sig.breakout_index, sig.rejection_index = i, j
                    sig.vol_ratio_breakout = _vol_ratio(i, vol_avg, candles)
                    sig.notes.append(
                        f"rejeitou a amarela há {last - j} candle(s); entra se o "
                        f"próximo fechar acima de {candles[j].high:.8g}")
                    break
            if sig.status is Status.REJEITOU_AGUARDA_CONFIRMACAO:
                break

    # Sem rejeição ainda: o par rompeu a amarela recentemente?
    if sig.status is Status.TENDENCIA_SEM_ROMPIMENTO:
        for i in range(last, max(last - cfg.breakout_lookback, 1) - 1, -1):
            if _is_breakout(i, candles, mid, cfg) and _trend_ok(i, candles, mid, slow, cfg):
                sig.status = Status.ROMPEU_AGUARDA_REJEICAO
                sig.breakout_index = i
                sig.vol_ratio_breakout = _vol_ratio(i, vol_avg, candles)
                sig.notes.append(f"rompeu a amarela há {last - i} candle(s)")
                break
    return sig
