"""Cliente mínimo da API pública da OKX (sem chave de API, sem dependências)."""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Optional, Sequence

from .strategy import Candle

BASE_URL = "https://www.okx.com"
USER_AGENT = "okx-sma-scanner/1.0 (+https://github.com/ajx04814)"

# Barras aceitas pela OKX (/api/v5/market/candles).
BARS = ["1m", "3m", "5m", "15m", "30m", "1H", "2H", "4H", "6H", "12H", "1D", "1W"]

# Tokens alavancados e produtos que não servem para este setup.
_EXCLUDE_SUFFIXES = ("3L", "3S", "5L", "5S", "2L", "2S")
_STABLES = {"USDC", "USDT", "DAI", "TUSD", "FDUSD", "USDD", "PYUSD", "EURT", "EUR", "BRZ"}


class OKXError(RuntimeError):
    pass


def normalize_bar(bar: str) -> str:
    """Aceita 15m, 1h, 4H... e devolve a grafia que a OKX espera."""
    for b in BARS:
        if bar.lower() == b.lower():
            return b
    raise OKXError(f"timeframe '{bar}' inválido; use um de: {', '.join(BARS)}")


def _get(path: str, params: dict, timeout: float = 20.0, retries: int = 3) -> list:
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout,
                                        context=ssl.create_default_context()) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            if payload.get("code") not in ("0", 0):
                raise OKXError(f"OKX code={payload.get('code')} msg={payload.get('msg')}")
            return payload.get("data", [])
        except (urllib.error.URLError, OSError, ValueError, OKXError) as exc:
            last_err = exc
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))  # backoff: 1.5s, 3s
    raise OKXError(f"falha em {path}: {last_err}")


def top_symbols(limit: int = 50, quote: str = "USDT") -> List[str]:
    """Pares spot com maior volume de 24h na moeda de cotação informada."""
    data = _get("/api/v5/market/tickers", {"instType": "SPOT"})
    rows = []
    for t in data:
        inst = t.get("instId", "")
        if not inst.endswith(f"-{quote}"):
            continue
        base = inst.split("-")[0]
        if base in _STABLES or base.endswith(_EXCLUDE_SUFFIXES):
            continue
        try:
            turnover = float(t.get("volCcy24h") or 0.0)
        except ValueError:
            continue
        rows.append((turnover, inst))
    rows.sort(reverse=True)
    return [inst for _, inst in rows[:limit]]


def fetch_candles(inst_id: str, bar: str = "1H", limit: int = 300,
                  closed_only: bool = True) -> List[Candle]:
    """Candles em ordem cronológica. Por padrão descarta o candle em formação.

    É esse descarte que implementa o "só entra após o horário": a decisão nunca
    olha para um candle que ainda pode mudar de forma até fechar.
    """
    data = _get("/api/v5/market/candles",
                {"instId": inst_id, "bar": bar, "limit": str(min(limit, 300))})
    out: List[Candle] = []
    for row in data:  # OKX devolve do mais novo para o mais antigo
        confirmed = len(row) < 9 or row[8] == "1"
        if closed_only and not confirmed:
            continue
        try:
            out.append(Candle(int(row[0]), float(row[1]), float(row[2]),
                              float(row[3]), float(row[4]), float(row[5])))
        except (TypeError, ValueError):
            continue
    out.reverse()
    return out


def fallback_symbols(path: str, limit: int = 50) -> List[str]:
    """Lista estática de pares (usada quando a API de tickers não responde)."""
    syms: List[str] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                syms.append(line)
    return syms[:limit]


def bar_seconds(bar: str) -> int:
    unit = bar[-1]
    qty = int(bar[:-1])
    return qty * {"m": 60, "H": 3600, "D": 86400, "W": 604800}[unit]


def ts_label(ms: int, bar: str) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(ms / 1000)) + " UTC"


def chunked(seq: Sequence, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]
