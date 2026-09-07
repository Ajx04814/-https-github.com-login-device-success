"""Cliente REST publico da OKX.

Usa apenas a biblioteca padrao. Nenhum endpoint privado e nenhuma chave de API:
tudo aqui e leitura de dados publicos de mercado.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

BASE_URL = os.environ.get("OKX_BASE_URL", "https://www.okx.com")
USER_AGENT = "okx-ai-study/0.1 (+https://github.com)"

# Granularidades aceitas pelo endpoint /market/candles.
BARS = ("1m", "3m", "5m", "15m", "30m", "1H", "2H", "4H", "6H", "12H", "1D")

# Duracao de cada barra em milissegundos, usada para paginar historico.
BAR_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1H": 3_600_000,
    "2H": 7_200_000,
    "4H": 14_400_000,
    "6H": 21_600_000,
    "12H": 43_200_000,
    "1D": 86_400_000,
}


class OKXError(RuntimeError):
    """Falha de rede ou erro logico devolvido pela API da OKX."""


@dataclass(frozen=True)
class Candle:
    """Uma barra OHLCV ja convertida para float.

    ``ts`` e o timestamp de abertura em milissegundos (UTC).
    ``quote_volume`` e o volume em moeda de cotacao (USDT), util para liquidez.
    """

    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float

    @property
    def typical(self) -> float:
        return (self.high + self.low + self.close) / 3.0


def _request(path: str, params: dict | None = None, retries: int = 4) -> list[dict]:
    """GET em um endpoint publico, com backoff exponencial em falha de rede."""
    url = f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    delay = 1.0
    last_error: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == retries - 1:
                break
            time.sleep(delay)
            delay *= 2
            continue

        if payload.get("code") != "0":
            raise OKXError(f"{path}: code={payload.get('code')} msg={payload.get('msg')}")
        return payload.get("data", [])

    raise OKXError(f"{path}: falha de rede apos {retries} tentativas ({last_error})")


def instruments(inst_type: str = "SPOT") -> list[dict]:
    """Lista instrumentos negociaveis (SPOT, SWAP, FUTURES...).

    Campos relevantes para dimensionar ordens pequenas: ``minSz`` (tamanho
    minimo em moeda base), ``lotSz`` (incremento) e ``tickSz`` (passo de preco).
    """
    return _request("/api/v5/public/instruments", {"instType": inst_type})


def tickers(inst_type: str = "SPOT") -> list[dict]:
    """Snapshot de todos os tickers: melhor bid/ask, ultimo preco e volume 24h."""
    return _request("/api/v5/market/tickers", {"instType": inst_type})


def candles(inst_id: str, bar: str = "5m", limit: int = 300, before_ts: int | None = None) -> list[Candle]:
    """Busca ate ``limit`` candles de ``inst_id``, do mais antigo para o mais novo.

    A OKX devolve do mais novo para o mais antigo e o parametro ``after`` pede
    barras *anteriores* ao timestamp informado, por isso a inversao no final.
    """
    if bar not in BARS:
        raise ValueError(f"bar invalido: {bar!r}; use um de {BARS}")

    params: dict[str, str] = {"instId": inst_id, "bar": bar, "limit": str(min(limit, 300))}
    if before_ts is not None:
        params["after"] = str(before_ts)

    rows = _request("/api/v5/market/candles", params)
    out = []
    for row in rows:
        # [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        if len(row) >= 9 and row[8] == "0":
            continue  # barra ainda em formacao: descarta para nao vazar futuro
        out.append(
            Candle(
                ts=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                quote_volume=float(row[7]) if len(row) > 7 and row[7] else float(row[4]) * float(row[5]),
            )
        )
    out.reverse()
    return out


def history(inst_id: str, bar: str = "5m", bars: int = 1500, pause: float = 0.12) -> list[Candle]:
    """Pagina o historico ate acumular ``bars`` candles ordenados no tempo."""
    step = BAR_MS[bar]
    collected: dict[int, Candle] = {}
    cursor: int | None = None

    while len(collected) < bars:
        chunk = candles(inst_id, bar=bar, limit=300, before_ts=cursor)
        if not chunk:
            break
        for candle in chunk:
            collected[candle.ts] = candle
        oldest = min(c.ts for c in chunk)
        next_cursor = oldest
        if cursor is not None and next_cursor >= cursor:
            break  # sem progresso: fim do historico disponivel
        cursor = next_cursor
        if len(chunk) < 300:
            break
        time.sleep(pause)  # respeita o rate limit publico

    ordered = sorted(collected.values(), key=lambda c: c.ts)
    # Sanidade: descarta buracos maiores que 3 barras no inicio da serie.
    if len(ordered) > 2:
        for i in range(len(ordered) - 1, 0, -1):
            if ordered[i].ts - ordered[i - 1].ts > 3 * step:
                ordered = ordered[i:]
                break
    return ordered[-bars:]
