"""Ranking de moedas da OKX por operabilidade, nao por "potencial".

Com ordem pequena o que decide se um par e utilizavel nao e a narrativa da
moeda: e o spread, a profundidade e o tamanho minimo de ordem. Um par com
spread de 0,15%% ja custa mais que a taxa de corretagem em cada ida e volta.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import okx


@dataclass(frozen=True)
class PairStats:
    inst_id: str
    last: float
    bid: float
    ask: float
    volume_24h_usd: float
    range_24h_pct: float
    min_size_usd: float
    lot_size: float

    @property
    def spread_pct(self) -> float:
        """Spread relativo ao ponto medio, em fracao (0.001 = 0,1%)."""
        mid = (self.bid + self.ask) / 2.0
        if mid <= 0 or self.ask <= 0 or self.bid <= 0:
            return float("inf")
        return (self.ask - self.bid) / mid

    def tradable_at(self, notional_usd: float) -> bool:
        """A ordem cabe no tamanho minimo do par?"""
        return notional_usd >= self.min_size_usd

    def score(self) -> float:
        """Nota simples: volatilidade util dividida pelo atrito de execucao.

        Recompensa amplitude diaria (ha o que capturar) e pune spread largo e
        liquidez baixa. Nao e previsao de retorno, e triagem de operabilidade.
        """
        if self.spread_pct <= 0 or self.volume_24h_usd <= 0:
            return 0.0
        friction = self.spread_pct + 2.0 * okx_taker_fee()
        liquidity = min(1.0, self.volume_24h_usd / 50_000_000.0)
        return (self.range_24h_pct / friction) * liquidity


def okx_taker_fee() -> float:
    from .backtest import TAKER_FEE

    return TAKER_FEE


def _to_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def collect(inst_type: str = "SPOT", quote: str = "USDT") -> list[PairStats]:
    """Junta tickers e metadados de instrumento em uma unica visao por par."""
    meta = {i["instId"]: i for i in okx.instruments(inst_type)}
    out: list[PairStats] = []

    for t in okx.tickers(inst_type):
        inst_id = t["instId"]
        if quote and not inst_id.endswith(f"-{quote}"):
            continue
        info = meta.get(inst_id)
        if not info or info.get("state") != "live":
            continue

        last = _to_float(t.get("last"))
        high, low = _to_float(t.get("high24h")), _to_float(t.get("low24h"))
        if last <= 0 or low <= 0:
            continue

        min_sz = _to_float(info.get("minSz"))
        out.append(
            PairStats(
                inst_id=inst_id,
                last=last,
                bid=_to_float(t.get("bidPx")),
                ask=_to_float(t.get("askPx")),
                volume_24h_usd=_to_float(t.get("volCcy24h")) * (1.0 if quote == "USDT" else last),
                range_24h_pct=(high - low) / low,
                min_size_usd=min_sz * last,
                lot_size=_to_float(info.get("lotSz")),
            )
        )
    return out


def rank(
    pairs: list[PairStats],
    notional_usd: float = 200.0,
    min_volume_usd: float = 5_000_000.0,
    max_spread_pct: float = 0.0010,
    top: int = 20,
) -> list[PairStats]:
    """Filtra o que e executavel e ordena pela nota."""
    eligible = [
        p
        for p in pairs
        if p.volume_24h_usd >= min_volume_usd
        and p.spread_pct <= max_spread_pct
        and p.tradable_at(notional_usd)
    ]
    eligible.sort(key=lambda p: p.score(), reverse=True)
    return eligible[:top]
