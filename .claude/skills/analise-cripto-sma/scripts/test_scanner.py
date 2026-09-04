"""Testes do scanner com candles sinteticos.

Nao tocam a rede: cada caso monta uma serie de candles com a geometria exata
do filtro que se quer exercitar, e as respostas das exchanges sao simuladas.
Rode com `python scripts/test_scanner.py` depois de mexer nos limiares --
afrouxar TOLERANCIA_TOQUE ou PAVIO_MINIMO sem rodar isso e como mover o stop:
parece inofensivo e nao e.
"""

import importlib.util
import json
import pathlib
import sys

_aqui = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sc", _aqui / "scanner.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

T0, STEP = 1_700_000_000_000, 7_200_000


def candle(i, o, h, l, c, v, fechado=True):
    return {"t": T0 + i * STEP, "o": o, "h": h, "l": l, "c": c, "v": v,
            "fechado": fechado}


def base(n, drift, vol=1000.0):
    out, p = [], 100.0
    for i in range(n):
        o, c = p, p * (1 + drift)
        out.append(candle(i, o, max(o, c) * 1.002, min(o, c) * 0.998, c, vol))
        p = c
    return out


def sma21(cs):
    return sum(c["c"] for c in cs[-21:]) / 21


def setup(alta=True, madura=True, vol_rej=1400, vol_conf=1600):
    """Monta um pullback com toque, pavio e confirmacao. Se madura=False, a
    rejeicao cai no ultimo candle FECHADO e quem confirmaria ainda esta rodando."""
    d = 0.004 if alta else -0.004
    cs = base(258 if madura else 259, d)
    p = cs[-1]["c"]
    rej_c = p * 0.995 if alta else p * 1.005     # fecha do lado da tendencia
    conf_c = p * 1.010 if alta else p * 0.990
    n = len(cs)
    cs.append(candle(n, p, 0, 0, rej_c, vol_rej))
    if madura:
        cs.append(candle(n + 1, rej_c, 0, 0, conf_c, vol_conf))
    m = sma21([c for c in cs if c["fechado"]])   # a SMA so depende dos fechamentos
    rej = cs[258] if madura else cs[259]
    if alta:
        rej.update(l=m * 0.996, h=max(rej["o"], rej["c"]) * 1.001)
    else:
        rej.update(h=m * 1.004, l=min(rej["o"], rej["c"]) * 0.999)
    if madura:
        cf = cs[259]
        cf.update(h=max(cf["o"], cf["c"]) * 1.002, l=min(cf["o"], cf["c"]) * 0.998)
        cs.append(candle(260, conf_c, conf_c * 1.003, conf_c * 0.997,
                         conf_c * 1.001, 500, fechado=False))
    else:
        cs.append(candle(260, rej_c, max(rej_c, conf_c) * 1.002,
                         min(rej_c, conf_c) * 0.998, conf_c, 900, fechado=False))
    return cs


falhas = []


def checa(nome, cond, ctx=None):
    print(f"{'ok  ' if cond else 'FALHA'} {nome}")
    if not cond:
        falhas.append((nome, ctx))


# 1 -- setup maduro de compra
r = sc.analisa("ALTAUSDT", setup(alta=True), "2h")
checa(f"1 alta madura -> {r['veredito']}",
      r["veredito"] == "ENTRA" and r["direcao"] == "compra"
      and r["stop"] < r["entrada"] < r["alvo"], r)

# 2 -- espelho: setup maduro de venda
r2 = sc.analisa("BAIXAUSDT", setup(alta=False), "2h")
checa(f"2 baixa madura -> {r2['veredito']} ({r2.get('direcao')})",
      r2["veredito"] == "ENTRA" and r2["direcao"] == "venda"
      and r2["stop"] > r2["entrada"] > r2["alvo"], r2)

# 3 -- confirmacao ainda em formacao => ESPERA (o erro mais caro do metodo)
r3 = sc.analisa("ESPERAUSDT", setup(alta=True, madura=False), "2h")
checa(f"3 candle aberto -> {r3['veredito']}",
      r3["veredito"] == "ESPERA" and "fecha" in r3["motivo"]
      and "fecha_em" in r3, r3)

# 4 -- setup perfeito mas volume fraco => ESPERA
r4 = sc.analisa("VOLFRACOUSDT", setup(alta=True, vol_rej=300, vol_conf=300), "2h")
checa(f"4 volume fraco -> {r4['veredito']}",
      r4["veredito"] == "ESPERA" and "volume" in r4["motivo"], r4)

# 5 -- lateral: barrado no filtro 1, sem nem avaliar toque
cs5 = [candle(i, 100 + (1 if i % 2 else -1) * .3, 100.5, 99.5,
              100 - (1 if i % 2 else -1) * .3, 1000) for i in range(261)]
r5 = sc.analisa("LATERALUSDT", cs5, "2h")
checa(f"5 lateral -> {r5['veredito']}",
      r5["veredito"] == "NAO ENTRA" and r5["tendencia"] == "lateral", r5)

# 6 -- alta, mas preco esticado longe da amarela => entrada ja passou
cs6 = base(259, 0.004)
p6 = cs6[-1]["c"]
cs6.append(candle(259, p6, p6 * 1.13, p6 * .999, p6 * 1.12, 1500))
cs6.append(candle(260, p6 * 1.12, p6 * 1.13, p6 * 1.11, p6 * 1.115, 500, False))
r6 = sc.analisa("ESTICADOUSDT", cs6, "2h")
checa(f"6 esticado -> {r6['veredito']}",
      r6["veredito"] == "NAO ENTRA" and "passou" in r6["motivo"], r6)

# 7 -- historico curto: nunca opinar sem as 200
r7 = sc.analisa("CURTOUSDT", base(50, 0.004), "2h")
checa(f"7 poucos candles -> {r7['veredito']}", r7["veredito"] == "SEM DADOS", r7)

# 8 -- o candle em formacao nao pode mudar veredito nenhum
cs8 = setup(alta=True)
cs8[-1] = candle(260, cs8[-1]["o"], cs8[-1]["o"] * 1.5, cs8[-1]["o"] * .5,
                 cs8[-1]["o"] * .5, 99999, fechado=False)
r8 = sc.analisa("IGNORAUSDT", cs8, "2h")
checa("8 candle aberto nao altera o veredito",
      r8["veredito"] == r["veredito"] and r8["entrada"] == r["entrada"], r8)

# 9 -- sem candle em formacao (exchange so devolveu fechados)
cs9 = [dict(c, fechado=True) for c in setup(alta=True, madura=False)]
r9 = sc.analisa("SEMABERTOUSDT", cs9, "2h")
checa(f"9 sem candle aberto -> {r9['veredito']}", r9["veredito"] in ("ENTRA", "ESPERA"), r9)

# 10 -- traducao de simbolo para o formato da OKX
checa("10 BTCUSDT -> BTC-USDT-SWAP", sc._okx_id("BTCUSDT") == "BTC-USDT-SWAP")
checa("10 BTC-USDT-SWAP passa direto", sc._okx_id("BTC-USDT-SWAP") == "BTC-USDT-SWAP")

# 11 -- parsing da OKX: ordem invertida e flag `confirm`
payload = {"code": "0", "data": [
    ["1700000007200000", "2", "3", "1", "2.5", "10", "0", "0", "0"],   # formando
    ["1700000000000000", "1", "2", "0.5", "1.5", "20", "0", "0", "1"],  # fechado
]}
sc.urllib.request.urlopen = lambda *a, **k: type(
    "R", (), {"read": lambda s: json.dumps(payload).encode(),
              "__enter__": lambda s: s, "__exit__": lambda *x: False})()
ks = sc.okx_klines("BTCUSDT", "2h")
checa("11 OKX devolve do mais antigo para o mais novo", ks[0]["t"] < ks[1]["t"], ks)
checa("11 OKX marca fechado/formando pelo campo confirm",
      ks[0]["fechado"] is True and ks[1]["fechado"] is False, ks)
checa("11 OKX le OHLCV corretamente",
      (ks[0]["o"], ks[0]["h"], ks[0]["l"], ks[0]["c"], ks[0]["v"]) == (1, 2, .5, 1.5, 20), ks)

# 12 -- ranking por volume: a lista sai da exchange, ja ordenada e filtrada
tickers = {"code": "0", "data": [
    {"instId": "BTC-USDT-SWAP", "volCcy24h": "100"},
    {"instId": "ETH-USDT-SWAP", "volCcy24h": "300"},
    {"instId": "SOL-USDC-SWAP", "volCcy24h": "999"},
    {"instId": "XRP-USDT-SWAP", "volCcy24h": "200"},
]}
sc.urllib.request.urlopen = lambda *a, **k: type(
    "R", (), {"read": lambda s: json.dumps(tickers).encode(),
              "__enter__": lambda s: s, "__exit__": lambda *x: False})()
top = sc.okx_top(2)
checa("12 top OKX ordena por volume e filtra o quote",
      top == ["ETH-USDT-SWAP", "XRP-USDT-SWAP"], top)

print("\n--- tabela ---\n")
print(sc.tabela(sorted([r, r2, r3, r4, r5, r6, r7],
                       key=lambda x: (sc.ORDEM[x["veredito"]], x["symbol"]))))

print(f"\n{'TODOS OS TESTES PASSARAM' if not falhas else 'FALHAS: ' + str(falhas)}")
sys.exit(1 if falhas else 0)
