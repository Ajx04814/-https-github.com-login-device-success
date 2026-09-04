#!/usr/bin/env python3
"""Escaneia pares de cripto aplicando o setup SMA 8/21/200.

Puxa candles de uma exchange publica (OKX por padrao), calcula as tres medias
e roda os mesmos filtros do SKILL.md: tendencia, toque na SMA 21, rejeicao,
candle de confirmacao FECHADO e volume. Imprime uma tabela ordenada com os
ENTRA no topo.

O candle em formacao nunca entra em conta. A OKX marca isso explicitamente no
campo `confirm` de cada candle, e o scanner respeita essa marcacao -- um sinal
que depende do candle que ainda esta rodando nao e sinal, e intencao, e por
isso vira ESPERA com o horario do fechamento.

Uso:
    python scanner.py                        # 50 maiores da OKX, 2h
    python scanner.py --top 20 --tf 4h
    python scanner.py BTCUSDT LINKUSDT       # pares especificos
    python scanner.py --exchange binance     # ou bybit
    python scanner.py --json                 # saida para outro programa

Sem dependencias: so a biblioteca padrao.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

# Quanto o candle pode ficar longe da SMA 21 e ainda contar como "toque".
# Encostar de verdade e diferente de "esta chegando perto" -- 0,25% e a folga
# que absorve o ruido do tick sem deixar passar um preco distante.
TOLERANCIA_TOQUE = 0.0025

# Fracao minima do range do candle que o pavio precisa ocupar para que a
# rejeicao seja visivel no grafico. Abaixo disso e um candle comum que por
# acaso passou pela media.
PAVIO_MINIMO = 0.30

UA = {"User-Agent": "sma-scanner/2.0"}


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# --------------------------------------------------------------------------
# Exchanges. Cada fetcher devolve candles do mais antigo para o mais novo,
# cada um marcado com `fechado`. Quem consome nunca precisa adivinhar qual
# candle ainda esta em formacao.
# --------------------------------------------------------------------------

def _okx_id(symbol):
    """BTCUSDT -> BTC-USDT-SWAP. Ja no formato da OKX, passa direto."""
    if "-" in symbol:
        return symbol
    for quote in ("USDT", "USDC", "USD"):
        if symbol.endswith(quote):
            return f"{symbol[:-len(quote)]}-{quote}-SWAP"
    return symbol


_OKX_BAR = {"15m": "15m", "30m": "30m", "1h": "1H", "2h": "2H",
            "4h": "4H", "6h": "6H", "12h": "12H", "1d": "1D"}


def okx_klines(symbol, interval, limit=300):
    d = _get(f"https://www.okx.com/api/v5/market/candles"
             f"?instId={_okx_id(symbol)}&bar={_OKX_BAR.get(interval, '2H')}"
             f"&limit={min(limit, 300)}")
    if d.get("code") not in ("0", 0) or not d.get("data"):
        raise RuntimeError(f"OKX: {d.get('msg') or 'sem dados'}")
    # OKX devolve do mais novo para o mais antigo
    return [
        {"t": int(k[0]), "o": float(k[1]), "h": float(k[2]), "l": float(k[3]),
         "c": float(k[4]), "v": float(k[5]), "fechado": k[8] == "1"}
        for k in reversed(d["data"])
    ]


def okx_top(n, quote="USDT"):
    """Os n perpetuos de maior volume em 24h -- a lista sai da propria OKX,
    nao de memoria, porque ranking de volume muda toda semana."""
    d = _get("https://www.okx.com/api/v5/market/tickers?instType=SWAP")
    if d.get("code") not in ("0", 0):
        raise RuntimeError(f"OKX tickers: {d.get('msg')}")
    pares = [t for t in d["data"] if t["instId"].endswith(f"-{quote}-SWAP")]
    pares.sort(key=lambda t: float(t.get("volCcy24h") or 0), reverse=True)
    return [t["instId"] for t in pares[:n]]


_BINANCE_TF = {"15m": "15m", "30m": "30m", "1h": "1h", "2h": "2h",
               "4h": "4h", "1d": "1d"}


def binance_klines(symbol, interval, limit=300):
    d = _get(f"https://api.binance.com/api/v3/klines?symbol={symbol}"
             f"&interval={_BINANCE_TF.get(interval, '2h')}&limit={limit}")
    agora = time.time() * 1000
    return [
        {"t": int(k[0]), "o": float(k[1]), "h": float(k[2]), "l": float(k[3]),
         "c": float(k[4]), "v": float(k[5]), "fechado": int(k[6]) < agora}
        for k in d
    ]


def binance_top(n, quote="USDT"):
    d = _get("https://api.binance.com/api/v3/ticker/24hr")
    pares = [t for t in d if t["symbol"].endswith(quote)]
    pares.sort(key=lambda t: float(t.get("quoteVolume") or 0), reverse=True)
    return [t["symbol"] for t in pares[:n]]


_BYBIT_TF = {"15m": "15", "30m": "30", "1h": "60", "2h": "120",
             "4h": "240", "1d": "D"}


def bybit_klines(symbol, interval, limit=300):
    d = _get(f"https://api.bybit.com/v5/market/kline?category=linear"
             f"&symbol={symbol}&interval={_BYBIT_TF.get(interval, '120')}"
             f"&limit={min(limit, 1000)}")
    ms = _ms_intervalo(interval)
    agora = time.time() * 1000
    return [
        {"t": int(k[0]), "o": float(k[1]), "h": float(k[2]), "l": float(k[3]),
         "c": float(k[4]), "v": float(k[5]), "fechado": int(k[0]) + ms < agora}
        for k in reversed(d["result"]["list"])
    ]


def bybit_top(n, quote="USDT"):
    d = _get("https://api.bybit.com/v5/market/tickers?category=linear")
    pares = [t for t in d["result"]["list"] if t["symbol"].endswith(quote)]
    pares.sort(key=lambda t: float(t.get("turnover24h") or 0), reverse=True)
    return [t["symbol"] for t in pares[:n]]


EXCHANGES = {
    "okx": (okx_klines, okx_top),
    "binance": (binance_klines, binance_top),
    "bybit": (bybit_klines, bybit_top),
}


def sma(valores, periodo, deslocamento=0):
    """Media simples terminando `deslocamento` candles antes do fim."""
    fim = len(valores) - deslocamento
    if fim < periodo:
        return None
    return sum(valores[fim - periodo:fim]) / periodo


def _ms_intervalo(interval):
    n, u = int(interval[:-1]), interval[-1]
    return n * {"m": 60, "h": 3600, "d": 86400}[u] * 1000


def analisa(symbol, candles, interval):
    """Roda os seis filtros. Devolve dict com veredito e diagnostico."""
    fechados = [c for c in candles if c.get("fechado", True)]
    abertos = [c for c in candles if not c.get("fechado", True)]
    formando = abertos[0] if abertos else None

    if len(fechados) < 210:
        return {"symbol": symbol, "veredito": "SEM DADOS",
                "motivo": f"so {len(fechados)} candles fechados, preciso de 210+"}

    closes = [c["c"] for c in fechados]
    vols = [c["v"] for c in fechados]

    s8, s21, s200 = sma(closes, 8), sma(closes, 21), sma(closes, 200)
    s21_antes = sma(closes, 21, deslocamento=5)

    confirmacao = fechados[-1]   # ultimo candle fechado
    rejeicao = fechados[-2]      # o candle do toque, se o setup ja estiver maduro
    vol_medio = sum(vols[-20:]) / 20

    # --- Filtro 1: tendencia ---------------------------------------------
    inclinacao = (s21 - s21_antes) / s21_antes if s21_antes else 0
    if s8 > s21 > s200 and inclinacao > 0.001:
        tendencia, direcao = "alta", "compra"
    elif s8 < s21 < s200 and inclinacao < -0.001:
        tendencia, direcao = "baixa", "venda"
    else:
        return {
            "symbol": symbol, "veredito": "NAO ENTRA", "tendencia": "lateral",
            "motivo": "medias embaralhadas ou sem inclinacao",
            "preco": confirmacao["c"], "sma8": s8, "sma21": s21, "sma200": s200,
            "dist_sma21_pct": (confirmacao["c"] - s21) / s21 * 100,
            "filtros": {"tendencia": False},
        }

    alta = tendencia == "alta"

    def avalia(toque_c, conf_c):
        """Filtros 2-5 sobre um par (candle de toque, candle seguinte)."""
        rng = toque_c["h"] - toque_c["l"]
        if rng <= 0 or conf_c is None:
            return None
        margem = s21 * TOLERANCIA_TOQUE
        if alta:
            tocou = toque_c["l"] <= s21 + margem
            pavio = (min(toque_c["o"], toque_c["c"]) - toque_c["l"]) / rng
            rejeitou = pavio >= PAVIO_MINIMO and toque_c["c"] > s21
            confirmou = (conf_c["c"] > conf_c["o"] and conf_c["c"] > toque_c["c"]
                         and conf_c["c"] > s21)
        else:
            tocou = toque_c["h"] >= s21 - margem
            pavio = (toque_c["h"] - max(toque_c["o"], toque_c["c"])) / rng
            rejeitou = pavio >= PAVIO_MINIMO and toque_c["c"] < s21
            confirmou = (conf_c["c"] < conf_c["o"] and conf_c["c"] < toque_c["c"]
                         and conf_c["c"] < s21)
        volume_ok = (toque_c["v"] >= vol_medio * 0.8
                     and conf_c["v"] >= vol_medio * 0.8)
        return {"toque": tocou, "rejeicao": rejeitou, "confirmacao": confirmou,
                "volume": volume_ok, "pavio": pavio}

    maduro = avalia(rejeicao, confirmacao)

    base = {
        "symbol": symbol, "tendencia": tendencia, "direcao": direcao,
        "preco": confirmacao["c"], "sma8": s8, "sma21": s21, "sma200": s200,
        "dist_sma21_pct": (confirmacao["c"] - s21) / s21 * 100,
        "vol_conf_x_media": confirmacao["v"] / vol_medio if vol_medio else 0,
    }

    if maduro and all([maduro["toque"], maduro["rejeicao"], maduro["confirmacao"]]):
        if maduro["volume"]:
            stop = rejeicao["l"] if alta else rejeicao["h"]
            risco = abs(confirmacao["c"] - stop) / confirmacao["c"] * 100
            alvo = (confirmacao["c"] + (confirmacao["c"] - stop) * 2 if alta
                    else confirmacao["c"] - (stop - confirmacao["c"]) * 2)
            return {**base, "veredito": "ENTRA",
                    "motivo": "toque, rejeicao e confirmacao fechada a favor",
                    "entrada": confirmacao["c"], "stop": stop,
                    "stop_pct": risco, "alvo": alvo, "filtros": maduro}
        return {**base, "veredito": "ESPERA",
                "motivo": "setup completo mas volume abaixo da media",
                "filtros": maduro}

    # Setup nascendo: o toque foi no ultimo candle fechado e quem confirmaria e
    # o candle que ainda esta rodando. Por definicao, ESPERA.
    nascendo = avalia(confirmacao, formando)
    if nascendo and nascendo["toque"] and nascendo["rejeicao"]:
        if formando:
            fecha = datetime.fromtimestamp(
                (formando["t"] + _ms_intervalo(interval)) / 1000, tz=timezone.utc)
            motivo = f"rejeicao no ultimo fechado; confirmacao fecha {fecha:%H:%M} UTC"
            extra = {"fecha_em": fecha.isoformat()}
        else:
            motivo = "rejeicao no ultimo fechado; falta o candle de confirmacao"
            extra = {}
        return {**base, "veredito": "ESPERA", "motivo": motivo,
                "filtros": nascendo, **extra}

    if maduro and maduro["toque"] and not maduro["rejeicao"]:
        motivo = "tocou a amarela mas nao rejeitou"
    elif abs(base["dist_sma21_pct"]) > 3:
        motivo = f"preco {base['dist_sma21_pct']:+.1f}% da amarela -- entrada ja passou"
    else:
        motivo = "sem toque na amarela"
    return {**base, "veredito": "NAO ENTRA", "motivo": motivo,
            "filtros": maduro or {}}


ORDEM = {"ENTRA": 0, "ESPERA": 1, "NAO ENTRA": 2, "SEM DADOS": 3}


def tabela(resultados, alavancagem=20):
    larg = max([12] + [len(r["symbol"]) + 1 for r in resultados])
    linhas = [
        f"{'PAR':<{larg}} {'VEREDITO':<10} {'DIR':<7} {'TEND':<8} {'dSMA21':>8}  MOTIVO",
        "-" * (larg + 78),
    ]
    for r in resultados:
        linhas.append(
            f"{r['symbol']:<{larg}} {r['veredito']:<10} "
            f"{r.get('direcao', '-'):<7} {r.get('tendencia', '-'):<8} "
            f"{r.get('dist_sma21_pct', 0):>7.2f}%  {r['motivo']}"
        )
    contagem = {}
    for r in resultados:
        contagem[r["veredito"]] = contagem.get(r["veredito"], 0) + 1
    linhas.append("")
    linhas.append("  ".join(f"{k}: {v}" for k, v in
                            sorted(contagem.items(), key=lambda kv: ORDEM[kv[0]])))

    for r in resultados:
        if r["veredito"] != "ENTRA":
            continue
        consumo = r["stop_pct"] * alavancagem
        aviso = ("  <-- stop maior que a margem: reduza a alavancagem"
                 if consumo >= 100 else "")
        linhas += [
            "",
            f"== {r['symbol']} -- {r['direcao'].upper()}",
            f"   entrada {r['entrada']:.6g} | stop {r['stop']:.6g} "
            f"({r['stop_pct']:.2f}%) | alvo {r['alvo']:.6g}",
            f"   volume da confirmacao: {r['vol_conf_x_media']:.2f}x a media",
            f"   com {alavancagem}x o stop consome {consumo:.0f}% da margem"
            f" -- margem isolada, sempre{aviso}",
        ]
    return "\n".join(linhas)


def main():
    p = argparse.ArgumentParser(description="Scanner SMA 8/21/200")
    p.add_argument("symbols", nargs="*", help="pares; vazio = top por volume")
    p.add_argument("--exchange", default="okx", choices=sorted(EXCHANGES))
    p.add_argument("--tf", default="2h", help="timeframe (padrao 2h)")
    p.add_argument("--top", type=int, default=50, help="quantos pares varrer")
    p.add_argument("--alavancagem", type=int, default=20)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    klines, top = EXCHANGES[a.exchange]
    symbols = a.symbols
    if not symbols:
        try:
            symbols = top(a.top)
        except Exception as e:
            print(f"nao consegui listar os pares da {a.exchange}: {e}",
                  file=sys.stderr)
            return 1
        print(f"# {len(symbols)} pares de maior volume na {a.exchange.upper()}"
              f" -- {a.tf}\n", file=sys.stderr)

    resultados = []
    for i, s in enumerate(symbols, 1):
        try:
            resultados.append(analisa(s, klines(s, a.tf), a.tf))
        except Exception as e:  # rede, par inexistente, dados insuficientes
            resultados.append({"symbol": s, "veredito": "SEM DADOS", "motivo": str(e)})
        print(f"\r  {i}/{len(symbols)}", end="", file=sys.stderr)
        time.sleep(0.12)  # educacao com a API publica
    print("\r" + " " * 20 + "\r", end="", file=sys.stderr)

    resultados.sort(key=lambda r: (ORDEM[r["veredito"]], r["symbol"]))
    print(json.dumps(resultados, indent=2) if a.json
          else tabela(resultados, a.alavancagem))
    return 0


if __name__ == "__main__":
    sys.exit(main())
