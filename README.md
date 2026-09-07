# okx-ai-study

Toolkit para estudar moedas da OKX de forma quantitativa: triagem de pares por
operabilidade, backtest com custo de execução embutido, e a matemática que decide
se uma sessão de N operações de X dólares tem chance de dar certo.

**A análise completa está em [`ESTRATEGIA.md`](ESTRATEGIA.md)** — o que a IA
consegue e não consegue estudar, como uma operação é realmente decidida, como os
grandes players operam, e o que 59 operações de 2 dólares produzem na prática.

Python 3.11+, sem dependências externas. Apenas endpoints **públicos** da OKX:
nenhuma chave de API, nenhuma ordem é enviada, nada é executado na sua conta.

Não é recomendação de investimento. É uma calculadora que mostra, com aritmética
verificável, o que uma configuração de trade precisa entregar para não perder
dinheiro.

## Uso

```bash
# valida a instalação offline, sem rede (dados sintéticos)
python -m okx_ai demo

# acertividade mínima exigida pelo seu custo e pela distância do seu stop
python -m okx_ai edge --stop 0.005 --payoff 2.0

# distribuição de 59 operações de 2 dólares
python -m okx_ai session --hit 0.45 --payoff 2.0 --stop 0.02 --trades 59 --risk 2

# pares operáveis com uma ordem de 200 dólares (precisa de rede)
python -m okx_ai screener --notional 200

# backtest com dados reais da OKX (precisa de rede)
python -m okx_ai backtest --inst BTC-USDT --bar 15m --bars 3000
```

Ajuda por subcomando: `python -m okx_ai <comando> --help`.

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| `okx.py` | cliente REST público: instrumentos, tickers, candles paginados |
| `synthetic.py` | séries offline com volatilidade agrupada, para testes sem rede |
| `indicators.py` | EMA, SMA, RSI, ATR, ADX, z-score, volatilidade realizada |
| `screener.py` | ranking por spread, liquidez e tamanho mínimo de ordem |
| `strategy.py` | regras de entrada/saída: regime + direção + rompimento com volume |
| `backtest.py` | motor sequencial com custo de ida e volta e walk-forward |
| `risk.py` | expectativa, ponto de equilíbrio, Kelly, Monte Carlo da sessão |
| `report.py` | formatação das saídas |

## Premissas do backtest

Escolhidas para errar para o lado pessimista — um backtest otimista é pior que
nenhum:

- Sinal calculado no fechamento da barra `i`, **entrada na abertura da barra `i+1`**.
- Barra que toca stop e alvo conta como **stop**.
- Custo de ida e volta = 2 × taxa taker (0,10%) + 2 × derrapagem (0,05%) = **0,30%**.
- Uma posição por vez, sem sobreposição.
- Barras ainda em formação (`confirm = 0`) são descartadas.

Os testes em `tests/test_indicators.py` verificam que nenhum indicador olha para
o futuro, e `tests/test_backtest.py` verifica que a entrada nunca acontece na
barra do sinal.

## Testes

```bash
python -m unittest discover -s tests -t .
```

46 testes, sem rede. Incluem verificação por força bruta da fórmula de
sequências de perda e a checagem de que passeio aleatório não gera vantagem
depois dos custos.

## Limitações conhecidas

- Sem dados de livro de ofertas: o spread vem do melhor bid/ask do ticker, não da
  profundidade real. Ordens grandes derrapam mais do que o modelo assume.
- Backtest em candles não captura o que acontece dentro da barra, então o
  preenchimento de stop é uma aproximação (pessimista, mas aproximação).
- Sem taxa de financiamento: para perpétuos, o custo de carregar posição fica
  fora da conta.
- A estratégia em `strategy.py` é um exemplo funcional e testável, não uma
  recomendação. O valor do repositório é o arcabouço de medição.
