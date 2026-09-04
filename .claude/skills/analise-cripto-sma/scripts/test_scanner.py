"""Testes do scanner com candles sinteticos.

Nao tocam a rede: cada caso monta uma serie de candles com a geometria exata
do filtro que se quer exercitar. Rode com `python scripts/test_scanner.py`
depois de mexer nos limiares -- afrouxar TOLERANCIA_TOQUE ou PAVIO_MINIMO sem
rodar isso e como mover o stop: parece inofensivo e nao e.
"""

import importlib.util
import pathlib
import sys

_aqui = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sc", _aqui / "scanner.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

T0, STEP = 1_700_000_000_000, 7_200_000
def candle(i, o, h, l, c, v): return {"t": T0+i*STEP, "o": o, "h": h, "l": l, "c": c, "v": v}

def base(n, drift, vol=1000.0):
    out, p = [], 100.0
    for i in range(n):
        o, c = p, p*(1+drift)
        out.append(candle(i, o, max(o,c)*1.002, min(o,c)*0.998, c, vol)); p = c
    return out

def sma21(cs): return sum(c["c"] for c in cs[-21:]) / 21

def setup_valido(alta=True, madura=True, vol_rej=1400, vol_conf=1600):
    """Monta um pullback com toque, pavio e confirmacao. Se madura=False, a
    rejeicao cai no ultimo candle FECHADO e quem confirmaria ainda esta rodando."""
    d = 0.004 if alta else -0.004
    cs = base(258 if madura else 259, d)
    p = cs[-1]["c"]
    rej_c = p*0.995 if alta else p*1.005      # fecha do lado da tendencia
    conf_c = p*1.010 if alta else p*0.990
    n = len(cs)
    cs.append(candle(n, p, 0, 0, rej_c, vol_rej))
    if madura:
        cs.append(candle(n+1, rej_c, 0, 0, conf_c, vol_conf))
    # a SMA so depende dos fechamentos, entao ja pode ser calculada
    m = sma21(cs)
    rej = cs[258] if madura else cs[259]
    if alta:
        rej.update(l=m*0.996, h=max(rej["o"], rej["c"])*1.001)
    else:
        rej.update(h=m*1.004, l=min(rej["o"], rej["c"])*0.999)
    if madura:
        cf = cs[259]
        cf.update(h=max(cf["o"], cf["c"])*1.002, l=min(cf["o"], cf["c"])*0.998)
        cs.append(candle(260, conf_c, conf_c*1.003, conf_c*0.997, conf_c*1.001, 500))
    else:
        f_c = conf_c
        cs.append(candle(260, rej_c, max(rej_c, f_c)*1.002, min(rej_c, f_c)*0.998, f_c, 900))
    return cs

# 1 -- setup maduro de compra
r = sc.analisa("ALTAUSDT", setup_valido(alta=True), "2h")
print("1 alta madura     ->", r["veredito"], "|", r.get("direcao"), "|", r["motivo"])
assert r["veredito"] == "ENTRA" and r["direcao"] == "compra", r
assert r["stop"] < r["entrada"] < r["alvo"], r
assert r["stop_pct"] > 0, r

# 2 -- espelho: setup maduro de venda
r2 = sc.analisa("BAIXAUSDT", setup_valido(alta=False), "2h")
print("2 baixa madura    ->", r2["veredito"], "|", r2.get("direcao"), "|", r2["motivo"])
assert r2["veredito"] == "ENTRA" and r2["direcao"] == "venda", r2
assert r2["stop"] > r2["entrada"] > r2["alvo"], r2

# 3 -- confirmacao ainda em formacao => ESPERA (o erro mais caro)
r3 = sc.analisa("ESPERAUSDT", setup_valido(alta=True, madura=False), "2h")
print("3 candle aberto   ->", r3["veredito"], "|", r3["motivo"])
assert r3["veredito"] == "ESPERA" and "fecha" in r3["motivo"] and "fecha_em" in r3, r3

# 4 -- setup perfeito mas volume fraco => ESPERA
r4 = sc.analisa("VOLFRACOUSDT", setup_valido(alta=True, vol_rej=300, vol_conf=300), "2h")
print("4 volume fraco    ->", r4["veredito"], "|", r4["motivo"])
assert r4["veredito"] == "ESPERA" and "volume" in r4["motivo"], r4

# 5 -- lateral: barrado no filtro 1, sem nem avaliar toque
cs5 = [candle(i, 100+(1 if i%2 else -1)*0.3, 100.5, 99.5, 100-(1 if i%2 else -1)*0.3, 1000) for i in range(261)]
r5 = sc.analisa("LATERALUSDT", cs5, "2h")
print("5 lateral         ->", r5["veredito"], "|", r5["motivo"])
assert r5["veredito"] == "NAO ENTRA" and r5["tendencia"] == "lateral", r5

# 6 -- alta, mas preco esticado longe da amarela => entrada ja passou
cs6 = base(259, 0.004); p6 = cs6[-1]["c"]
cs6.append(candle(259, p6, p6*1.13, p6*0.999, p6*1.12, 1500))
cs6.append(candle(260, p6*1.12, p6*1.13, p6*1.11, p6*1.115, 500))
r6 = sc.analisa("ESTICADOUSDT", cs6, "2h")
print("6 esticado        ->", r6["veredito"], "|", r6["motivo"])
assert r6["veredito"] == "NAO ENTRA" and "passou" in r6["motivo"], r6

# 7 -- historico curto: nunca opinar sem as 200
r7 = sc.analisa("CURTOUSDT", base(50, 0.004), "2h")
print("7 poucos candles  ->", r7["veredito"], "|", r7["motivo"])
assert r7["veredito"] == "SEM DADOS", r7

# 8 -- o candle em formacao nao pode mudar veredito nenhum
cs8 = setup_valido(alta=True)
cs8[-1] = candle(260, cs8[-1]["o"], cs8[-1]["o"]*1.5, cs8[-1]["o"]*0.5, cs8[-1]["o"]*0.5, 99999)
r8 = sc.analisa("IGNORAUSDT", cs8, "2h")
print("8 candle aberto ignorado ->", r8["veredito"])
assert r8["veredito"] == r["veredito"] and r8["entrada"] == r["entrada"], r8

print("\n--- tabela ---\n")
print(sc.tabela(sorted([r,r2,r3,r4,r5,r6,r7], key=lambda x:(sc.ORDEM[x["veredito"]], x["symbol"]))))
print("\n8/8 TESTES PASSARAM")
