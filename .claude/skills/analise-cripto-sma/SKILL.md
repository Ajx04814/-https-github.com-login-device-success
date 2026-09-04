---
name: analise-cripto-sma
description: Analisa gráficos de criptomoedas (prints do TradingView, listas de pares, watchlists) usando o setup de médias 8 branca / 21 amarela / 200 roxa e devolve um veredito objetivo ENTRA / ESPERA / NÃO ENTRA com plano de operação, alavancagem e stop. Use sempre que o usuário mandar print de gráfico, citar SMA/EMA 8, 21 ou 200, falar em "linha amarela", toque/rompimento/rejeição de média, tendência, volume de candle, alavancagem, margem isolada, long/short, ou pedir para analisar uma moeda, um par tipo BTCUSDT/ALICEUSDT, ou uma lista de moedas — mesmo que não use a palavra "análise". Também use quando ele pedir para conferir uma análise que ele mesmo fez.
---

# Análise de gráfico — setup SMA 8/21/200

Este é um método de **seguimento de tendência com pullback na média de 21**. A ideia central: em tendência definida, o preço se afasta e volta a "respirar" na média amarela; o dinheiro está em entrar nessa volta, a favor da tendência, **depois** que o mercado provou que a média segurou — nunca na esperança de que vá segurar.

Quase todo prejuízo nesse setup vem de dois erros: entrar contra a tendência e entrar com candle aberto. O roteiro abaixo existe para tornar esses dois erros impossíveis de cometer por descuido.

## Configuração do gráfico

| Média | Cor | Papel |
|---|---|---|
| 8 | branca | velocidade do movimento, gatilho de saída rápida |
| 21 | **amarela** | **a linha da operação** — é nela que o preço toca e é dela que sai a entrada |
| 200 | roxa | tendência macro; define de que lado é permitido operar |

Timeframe padrão: **2h**. Confirme sempre o timeframe do print antes de opinar — a mesma moeda dá sinais opostos em 15m e em 4h, e uma análise no timeframe errado é pior que nenhuma.

## Roteiro (siga na ordem — cada passo é um filtro)

### 1. Tendência
Antes de olhar qualquer toque, responda: **para onde esse gráfico está indo?**

- **Alta** (permite compra): 8 acima da 21, 21 acima da 200, médias inclinadas para cima, topos e fundos ascendentes.
- **Baixa** (permite venda, se o usuário opera vendido): ordenamento invertido, 8 abaixo da 21 abaixo da 200, fundos descendentes.
- **Lateral / indefinida**: médias embaralhadas, cruzando-se, horizontais, preço serrando em cima delas. → **NÃO ENTRA**, e nem continue o roteiro. Lateralidade é onde esse setup mais dá falso sinal, porque o preço toca a amarela dez vezes sem que isso signifique nada.

Se a tendência não for clara em três segundos de olhada, ela não é clara. Trate como lateral.

### 2. Contato com a amarela
O preço precisa **encostar, furar ou fechar em cima da SMA 21**, vindo do lado da tendência. Em alta, ele desce e testa a amarela por baixo; em baixa, sobe e testa por cima.

Não vale: preço a três candles de distância da média ("está chegando perto"), nem preço que já rompeu e disparou faz tempo — nesse caso a entrada passou, e correr atrás dela é FOMO.

### 3. Rejeição
O candle de toque tem que **mostrar a defesa**: pavio/sombra contra a média e fechamento do lado da tendência. Em alta, pavio inferior perfurando a amarela e corpo fechando acima dela.

Candle que fecha **do outro lado** da média não é rejeição — é rompimento contra você. Nesse caso o setup morreu; talvez esteja nascendo o setup oposto, então reavalie a tendência do zero.

### 4. Candle de confirmação FECHADO
Este é o passo que separa o método de um chute. Depois da rejeição, é preciso **um candle seguinte, já fechado, no sentido da tendência**.

"Após o horário" quer dizer exatamente isso: em 2h, o candle das 14h só vale às 16h. Candle em formação pode virar de cor a qualquer segundo — o que parece confirmação às 15h vira armadilha às 15h58. Se o print mostra candle aberto, o veredito é **ESPERA**, com o horário exato em que o candle fecha e o que precisa acontecer até lá.

### 5. Volume
O volume diz se quem defendeu a média tinha dinheiro ou era só falta de vendedor.

- Rejeição e confirmação com volume **igual ou acima** da média das últimas barras → sinal com gente atrás.
- Confirmação com volume **minguando** → ESPERA. Repique sem volume costuma ser correção dentro do movimento, não retomada.
- Volume explosivo **contra** a tendência no toque → sinal de alerta; pode ser rompimento real da média, não pullback.

### 6. Veredito

| Veredito | Quando |
|---|---|
| **ENTRA** | Tendência clara + toque na amarela + rejeição + candle de confirmação fechado a favor + volume sustentando |
| **ESPERA** | Falta só a confirmação fechada, ou o volume está fraco, ou o candle ainda está aberto — o setup está vivo mas não maduro |
| **NÃO ENTRA** | Contra a tendência, sem tendência, sem rejeição, ou entrada já perdida (preço longe da média) |

Na dúvida entre dois vereditos, escolha o mais conservador. Perder uma entrada custa zero; entrar errado com 20x custa dinheiro de verdade.

## Formato de saída

Para **uma moeda**, use este formato — é curto de propósito, para ser lido no celular na hora da decisão:

```
## PAR — timeframe
**Veredito:** ENTRA / ESPERA / NÃO ENTRA (direção: compra ou venda)

| Filtro | Situação | OK |
|---|---|---|
| Tendência | ... | ✅/❌ |
| Toque na amarela (21) | ... | ✅/❌ |
| Rejeição | ... | ✅/❌ |
| Candle de confirmação fechado | ... | ✅/❌ |
| Volume | ... | ✅/❌ |

**Plano** (só quando ENTRA)
- Entrada: ...
- Stop: abaixo/acima do pavio da rejeição
- Alvo: ...
- Alavancagem: ...x — margem isolada
- Risco: ...% da banca

**Por quê:** uma ou duas frases.
**O que invalida:** o que precisa acontecer para você desistir/sair.
```

Para uma **lista ou watchlist de moedas**: monte primeiro uma tabela com uma linha por par (par | tendência | veredito | motivo em 3-6 palavras), ordenada com os ENTRA no topo, e só depois abra o detalhamento completo dos que deram ENTRA ou ESPERA. Ninguém precisa de cinco parágrafos sobre uma moeda que está lateral.

## Gestão de risco

Nunca devolva um ENTRA sem stop. Uma entrada sem stop definido não é operação, é aposta — e com alavancagem alta o mercado cobra isso em uma única vela.

- **Stop:** logo abaixo do pavio do candle de rejeição (compra) ou acima dele (venda). É o ponto onde a tese "a média segurou" foi comprovadamente falsa.
- **Margem isolada, sempre.** Ela limita a perda ao valor daquela operação e impede que um único trade liquide a banca inteira. Margem cruzada só se o usuário optar conscientemente por operar com alavancagem baixa (~3x), e vale avisar que o risco muda de natureza.
- **Alavancagem por experiência:** até 50 operações → 20x. Depois de 50 → até 30x. Depois de 100 → 50x ou mais. O critério é histórico de execução, não confiança no sinal — um setup "perfeito" não justifica pular etapa.
- Se o usuário pedir tamanho de posição ou quiser calcular quanto perde no stop, leia `references/gestao-de-risco.md`.

## Controle emocional

O plano só protege se for seguido. Quando perceber essas situações na conversa, aponte com franqueza e sem sermão:

- Pedir para "achar uma entrada" numa moeda específica que está lateral ou contra a tendência → o mercado não deve nada; a resposta honesta é NÃO ENTRA.
- Querer entrar antes do candle fechar porque "está subindo forte" → é FOMO, e é o erro que o método existe para evitar.
- Voltar depois de um stop querendo dobrar a alavancagem → revenge trade.
- Perguntar se pode "só mover o stop um pouquinho" → o stop movido para trás transforma perda planejada em liquidação.

## Varredura automática (lista de moedas)

Quando o pedido for "que moeda dá pra operar hoje", varrer uma watchlist ou
conferir dezenas de pares, use o scanner em vez de analisar de cabeça:

```bash
python scripts/scanner.py                      # 50 maiores da OKX, 2h
python scripts/scanner.py --top 20 --tf 4h
python scripts/scanner.py BTCUSDT LINKUSDT     # pares específicos
python scripts/scanner.py --exchange binance   # ou bybit
python scripts/scanner.py --alavancagem 30     # muda o cálculo de margem
```

Sem pares na linha de comando, ele pergunta à própria exchange quais são os N
de maior volume em 24h. Isso importa: ranking de volume muda toda semana, e
uma lista fixa escrita há um mês manda você analisar moeda que secou. A OKX é
o padrão, e o par pode ser escrito como `BTCUSDT` ou `BTC-USDT-SWAP`.

A saída vem ordenada com os ENTRA no topo, seguida da contagem por veredito e
do plano de cada entrada — stop no pavio da rejeição, alvo 2:1 e quanto o stop
consome da margem na alavancagem escolhida. Quando esse consumo passa de 100%,
ele avisa: o stop está mais longe que a liquidação, então ou a entrada é mais
justa ou a alavancagem cai.

Sobre o candle em formação: a OKX marca cada candle com o campo `confirm`, e o
scanner respeita essa marcação em vez de supor qual é o último fechado. Nas
outras exchanges ele deduz pelo horário de fechamento. Em qualquer caso, um
setup cuja confirmação depende do candle que ainda está rodando sai como
ESPERA, com o horário em que ele fecha.

O scanner faz a triagem, não a decisão: ele varre depressa o que seria lento
no olho, e o veredito final ainda passa pela sua leitura do gráfico — contexto
de notícia, suporte e resistência antigos e estrutura de topos e fundos não
cabem em cinco filtros. Trate a saída como a lista de gráficos que merecem ser
abertos.

Se a rede estiver bloqueada ou a exchange fora do ar, o par sai como
`SEM DADOS`. Diga isso ao usuário; não preencha a lacuna com estimativa.

Mexeu nos limiares (`TOLERANCIA_TOQUE`, `PAVIO_MINIMO`)? Rode
`python scripts/test_scanner.py` — são 15 verificações sintéticas, sem rede,
que travam as regressões que importam: principalmente a de aceitar candle
ainda aberto como confirmação.

## Referências

- `references/leitura-do-grafico.md` — como extrair par, timeframe, médias e volume de um print do TradingView, e o que fazer quando a imagem está cortada ou ilegível.
- `references/gestao-de-risco.md` — cálculo de stop, tamanho de posição, relação risco/retorno e efeito da alavancagem.
- `references/exemplos.md` — exemplos comentados de setup válido e inválido, incluindo o caso clássico de print rotulado errado.

## Escopo

Isto é leitura técnica de gráfico segundo um método definido, para fins educacionais e de estudo — não é recomendação de investimento. Cripto alavancado perde capital rápido, e o veredito NÃO ENTRA é uma resposta tão útil quanto o ENTRA. Se a imagem ou os dados não permitirem concluir, diga o que está faltando em vez de preencher a lacuna com suposição: um palpite apresentado como análise é o pior resultado possível aqui.
