# Scanner OKX — SMA 8 / 21 / 200 (branca / amarela / roxa)

Varredura das criptomoedas mais líquidas da **OKX** procurando exatamente o setup
descrito: rompimento da **linha amarela (SMA 21)** dentro de tendência de alta,
**rejeição** na volta a essa linha e **confirmação no fechamento do candle**
("após o horário"), com **volume acima da média**.

Sem dependências: Python 3.8+ e a biblioteca padrão. Usa apenas endpoints
**públicos** da OKX (nenhuma chave de API, nenhuma ordem é enviada).

```bash
python3 scan_okx.py                       # top 50 pares USDT, gráfico de 1H
python3 scan_okx.py -t 15m -n 50          # 15 minutos
python3 scan_okx.py -t 4H --all           # mostra o estágio de todos os pares
python3 scan_okx.py -s BTC-USDT SOL-USDT  # pares específicos
python3 scan_okx.py -t 1H --format json   # saída para outro programa
```

## A regra, exatamente como o scanner a aplica

| Etapa | Condição verificada no código |
|---|---|
| 1. Tendência macro | fecho **acima da SMA 200 (roxa)** e SMA 200 subindo nas últimas 20 barras |
| 2. Rompimento | candle de alta que **fecha acima da SMA 21 (amarela)** vindo de um candle que fechou abaixo dela |
| 3. Rejeição | o preço **volta e testa a amarela** (mínima na linha, tolerância 0,35%), deixa **pavio inferior ≥ 30% do range** e **fecha acima da linha**, na metade superior do candle |
| 4. Confirmação | o candle seguinte **fecha acima da máxima do candle de rejeição**, acima da amarela e com **SMA 8 > SMA 21** |
| 5. Volume | volume do rompimento **ou** da confirmação **≥ 1,2×** a média de 20 candles |
| 6. "Após o horário" | só entram candles **fechados** (`confirm=1` na API); o candle em formação é descartado |

Cada par recebe um **estágio**, o que transforma a varredura numa watchlist:

- `SINAL` — as cinco condições fecharam; sai entrada, stop e alvos.
- `rejeitou/aguarda confirmação` — falta o próximo candle fechar acima da máxima da rejeição.
- `rompeu/aguarda rejeição` — rompeu a amarela, ainda não voltou para testá-la.
- `só tendência` / `sem tendência` / `sem dados`.

**Gestão de risco calculada:** stop no menor valor entre a mínima do candle de
rejeição e a SMA 21 (−0,1%); alvos em **2R** e **3R**; `score` de 0 a 100
ponderando volume, inclinação da SMA 200, folga em relação à roxa e tamanho do risco.

## Ajustes

| Flag | Padrão | Para quê |
|---|---|---|
| `-t, --timeframe` | `1H` | `1m 3m 5m 15m 30m 1H 2H 4H 6H 12H 1D 1W` |
| `-n, --top` | `50` | quantos pares varrer, ordenados por volume de 24h |
| `-q, --quote` | `USDT` | moeda de cotação (`USDC`, `BTC`…) |
| `--min-vol-ratio` | `1.2` | exigência de volume sobre a média de 20 |
| `--max-age` | `1` | quão recente a confirmação precisa ser, em candles |
| `--min-slope` | `0.0` | inclinação mínima da SMA 200, em % sobre 20 barras |
| `--include-open-candle` | desligado | inclui o candle em formação (não recomendado) |
| `--all` | desligado | lista todos os pares, não só os que estão no setup |
| `--format` | `table` | `table`, `json` ou `csv` |

## As 50 criptomoedas

A lista de trabalho é montada **ao vivo** a cada execução — os 50 pares `-USDT`
com maior volume em 24h em `/api/v5/market/tickers`, já sem stablecoins e sem
tokens alavancados (`3L/3S/5L/5S`). É isso que garante liquidez para o setup.

Se a API de tickers não responder, o scanner cai para a lista estática em
[`okxsma/symbols_fallback.txt`](okxsma/symbols_fallback.txt) (BTC, ETH, SOL, XRP,
DOGE, ADA, TON, AVAX, LINK, DOT, TRX, LTC, BCH, NEAR, APT, SUI, ARB, OP, FIL,
ATOM, ICP, INJ, UNI, ETC, XLM, HBAR, IMX, STX, RENDER, GRT, AAVE, LDO, SAND,
MANA, AXS, CRV, MKR, SNX, ALGO, EGLD, FLOW, CHZ, GALA, PEPE, WIF, BONK, SHIB,
JUP, TIA, SEI, POL, ENA, ORDI) e avisa no `stderr`. Essa lista estática envelhece
— tickers são renomeados e deslistados —, então prefira sempre a lista ao vivo.

## Testes

```bash
python3 -m unittest discover -s tests -v
```

Os testes montam séries sintéticas de candles e checam o setup completo, o setup
sem confirmação, sem rejeição, com volume fraco, em tendência de baixa, sinal
velho e o cálculo de stop/alvos. Não tocam a rede.

## Estrutura

```
scan_okx.py                  atalho de linha de comando
okxsma/strategy.py           SMAs e a máquina de estados do setup (sem rede)
okxsma/okx.py                cliente HTTP dos endpoints públicos da OKX
okxsma/cli.py                argumentos, varredura paralela e formatação
okxsma/symbols_fallback.txt  lista estática de pares (plano B)
tests/test_strategy.py       testes offline
```

## Aviso

Ferramenta de **apoio à decisão**: ela lê preço e volume públicos e diz onde o
setup apareceu. Não envia ordens, não prevê preço e não é recomendação de
investimento. Backtest e valide o tamanho de posição antes de operar dinheiro real.
