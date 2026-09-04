#!/usr/bin/env python3
"""Escaneia pares de cripto aplicando o setup SMA 8/21/200.

Puxa candles fechados de uma exchange publica, calcula as tres medias e
roda os mesmos filtros do SKILL.md: tendencia, toque na SMA 21, rejeicao,
candle de confirmacao FECHADO e volume. Imprime uma tabela ordenada com os
ENTRA no topo.

O candle em formacao e sempre descartado. Um sinal que depende dele nao e
sinal, e intencao -- por isso vira ESPERA, com o horario do fechamento.

Uso:
    python scanner.py                          # watchlist padrao, 2h
    python scanner.py --tf 4h BTCUSDT LINKUSDT
    python scanner.py --json                   # saida para outro programa

Sem dependencias: so a biblioteca padrao.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

WATCHLIST = [
    "BTCUSDT", "LINKUSDT", "AXSUSDT", "OPUSDT", "GRTUSDT", "LDOUSDT",
    "DYDXUSDT", "MANAUSDT", "SKLUSDT", "BANDUSDT", "CELOUSDT", "ZRXUSDT",
    "QTUMUSDT", "KSMUSDT", "MTLUSDT", "ALICEUSDT", "DUSKUSDT", "LQTYUSDT",
]

# Quanto o candle pode ficar longe da SMA 21 e ainda contar como "toque".
# Encostar de verdade e diferente de "esta chegando perto" -- 0,25% e a
# folga que absorve o ruido do tick sem deixar passar um preco distante.
TOLERANCIA_TOQUE = 0.0025

# Fracao minima do range do candle que o pavio precisa ocupar para que a
# rejeicao seja visivel no grafico. Abaixo disso e um candle comum que por
# acaso passou pela media.
PAVIO_MINIMO = 0.30


def busca_klines(symbol, interval, limit=300, timeout=20):
    """Candles OHLCV. Tenta Binance e cai para Bybit se ela nao responder."""
    fontes = [
        (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval={interval}&limit={limit}",
            lambda d: [
                {
                    "t": int(k[0]), "o": float(k[1]), "h": float(k[2]),
                    "l": float(k[3]), "c": float(k[4]), "v": float(k[5]),
                }
                for k in d
            ],
        ),
        (
            f"https://api.bybit.com/v5/market/kline"
            f"?category=linear&symbol={symbol}"
            f"&interval={_bybit_tf(interval)}&limit={min(limit, 1000)}",
            lambda d: [
                {
                    "t": int(k[0]), "o": float(k[1]), "h": float(k[2]),
                    "l": float(k[3]), "c": float(k[4]), "v": float(k[5]),
                }
                for k in reversed(d["result"]["list"])
            ],
        ),
    ]
    erros = []
    for url, parse in fontes:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "sma-scanner/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return parse(json.loads(r.read().decode()))
        except (urllib.error.URLError, KeyError, ValueError, TimeoutError) as e:
            erros.append(f"{url.split('/')[2]}: {e}")
    raise RuntimeError(f"{symbol}: nenhuma fonte respondeu ({'; '.join(erros)})")


def _bybit_tf(interval):
    return {"15m": "15", "30m": "30", "1h": "60", "2h": "120",
            "4h": "240", "1d": "D"}.get(interval, "120")


def sma(valores, periodo, deslocamento=0):
    """Media simples terminando `deslocamento` candles antes do fim."""
    fim = len(valores) - deslocamento
    if fim < periodo:
        return None
    return sum(valores[fim - periodo:fim]) / periodo


def analisa(symbol, candles, interval):
    """Roda os seis filtros. Devolve dict com veredito e diagnostico."""
    # O ultimo candle ainda esta se formando -- ele nao entra em nenhuma
    # conta. Tudo abaixo trabalha so com historia consumada.
    formando = candles[-1]
    fechados = candles[:-1]

    if len(fechados) < 210:
        return {"symbol": symbol, "veredito": "SEM DADOS",
                "motivo": f"so {len(fechados)} candles fechados, preciso de 210+"}

    closes = [c["c"] for c in fechados]
    vols = [c["v"] for c in fechados]

    s8, s21, s200 = sma(closes, 8), sma(closes, 21), sma(closes, 200)
    s21_antes = sma(closes, 21, deslocamento=5)

    confirmacao = fechados[-1]   # ultimo candle fechado
    rejeicao = fechados[-2]      # o candle do toque, se houver setup maduro
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
            "filtros": {"tendencia": False, "toque": None, "rejeicao": None,
                        "confirmacao": None, "volume": None},
        }

    alta = tendencia == "alta"

    def avalia(toque_c, conf_c):
        """Filtros 2-5 sobre um par (candle de toque, candle seguinte)."""
        rng = toque_c["h"] - toque_c["l"]
        if rng <= 0:
            return None
        margem = s21 * TOLERANCIA_TOQUE
        if alta:
            tocou = toque_c["l"] <= s21 + margem
            pavio = (min(toque_c["o"], toque_c["c"]) - toque_c["l"]) / rng
            rejeitou = pavio >= PAVIO_MINIMO and toque_c["c"] > s21
            confirmou = conf_c["c"] > conf_c["o"] and conf_c["c"] > toque_c["c"] and conf_c["c"] > s21
        else:
            tocou = toque_c["h"] >= s21 - margem
            pavio = (toque_c["h"] - max(toque_c["o"], toque_c["c"])) / rng
            rejeitou = pavio >= PAVIO_MINIMO and toque_c["c"] < s21
            confirmou = conf_c["c"] < conf_c["o"] and conf_c["c"] < toque_c["c"] and conf_c["c"] < s21
        volume_ok = toque_c["v"] >= vol_medio * 0.8 and conf_c["v"] >= vol_medio * 0.8
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
            return {**base, "veredito": "ENTRA",
                    "motivo": "toque, rejeicao e confirmacao fechada a favor",
                    "entrada": confirmacao["c"], "stop": stop,
                    "stop_pct": risco,
                    "alvo": confirmacao["c"] + (confirmacao["c"] - stop) * 2 if alta
                            else confirmacao["c"] - (stop - confirmacao["c"]) * 2,
                    "filtros": maduro}
        return {**base, "veredito": "ESPERA",
                "motivo": "setup completo mas volume abaixo da media",
                "filtros": maduro}

    # Setup nascendo: o toque foi no ultimo candle fechado e quem confirmaria
    # e o candle que ainda esta rodando. Por definicao, ESPERA.
    nascendo = avalia(confirmacao, formando)
    if nascendo and nascendo["toque"] and nascendo["rejeicao"]:
        fecha_em = datetime.fromtimestamp(
            formando["t"] / 1000 + _ms_intervalo(interval) / 1000, tz=timezone.utc
        )
        return {**base, "veredito": "ESPERA",
                "motivo": f"rejeicao no ultimo fechado; confirmacao fecha {fecha_em:%H:%M} UTC",
                "fecha_em": fecha_em.isoformat(), "filtros": nascendo}

    if maduro and maduro["toque"] and not maduro["rejeicao"]:
        motivo = "tocou a amarela mas nao rejeitou"
    elif abs(base["dist_sma21_pct"]) > 3:
        motivo = f"preco {base['dist_sma21_pct']:+.1f}% da amarela -- entrada ja passou"
    else:
        motivo = "sem toque na amarela"
    return {**base, "veredito": "NAO ENTRA", "motivo": motivo,
            "filtros": maduro or {}}


def _ms_intervalo(interval):
    n, u = int(interval[:-1]), interval[-1]
    return n * {"m": 60, "h": 3600, "d": 86400}[u] * 1000


ORDEM = {"ENTRA": 0, "ESPERA": 1, "NAO ENTRA": 2, "SEM DADOS": 3}


def tabela(resultados):
    linhas = [
        f"{'PAR':<12} {'VEREDITO':<10} {'DIR':<7} {'TEND':<8} {'dSMA21':>8}  MOTIVO",
        "-" * 88,
    ]
    for r in resultados:
        linhas.append(
            f"{r['symbol']:<12} {r['veredito']:<10} "
            f"{r.get('direcao', '-'):<7} {r.get('tendencia', '-'):<8} "
            f"{r.get('dist_sma21_pct', 0):>7.2f}%  {r['motivo']}"
        )
    for r in resultados:
        if r["veredito"] == "ENTRA":
            linhas += [
                "",
                f"== {r['symbol']} -- {r['direcao'].upper()}",
                f"   entrada {r['entrada']:.6g} | stop {r['stop']:.6g} "
                f"({r['stop_pct']:.2f}%) | alvo {r['alvo']:.6g}",
                f"   volume da confirmacao: {r['vol_conf_x_media']:.2f}x a media",
                f"   com 20x o stop consome {r['stop_pct'] * 20:.0f}% da margem "
                f"-- margem isolada, sempre",
            ]
    return "\n".join(linhas)


def main():
    p = argparse.ArgumentParser(description="Scanner SMA 8/21/200")
    p.add_argument("symbols", nargs="*", default=None)
    p.add_argument("--tf", default="2h", help="timeframe (padrao 2h)")
    p.add_argument("--json", action="store_true", help="saida JSON")
    a = p.parse_args()

    symbols = a.symbols or WATCHLIST
    resultados = []
    for s in symbols:
        try:
            resultados.append(analisa(s, busca_klines(s, a.tf), a.tf))
        except Exception as e:  # rede, par inexistente, dados insuficientes
            resultados.append({"symbol": s, "veredito": "SEM DADOS", "motivo": str(e)})
        time.sleep(0.15)  # educacao com a API publica

    resultados.sort(key=lambda r: (ORDEM[r["veredito"]], r["symbol"]))
    print(json.dumps(resultados, indent=2) if a.json else tabela(resultados))
    return 0 if any(r["veredito"] == "ENTRA" for r in resultados) else 0


if __name__ == "__main__":
    sys.exit(main())
