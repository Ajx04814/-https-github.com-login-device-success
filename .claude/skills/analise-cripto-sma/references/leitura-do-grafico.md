# Lendo um print do TradingView

O objetivo aqui é não errar o básico. Uma análise brilhante do par errado ou do timeframe errado é lixo, e esse tipo de erro é silencioso — parece uma boa resposta.

## Extraia primeiro (antes de qualquer opinião)

1. **Par** — canto superior esquerdo (ex.: `ALICEUSDT.P`, `DUSKUSDT.P`). O sufixo `.P` indica contrato perpétuo, ou seja, operação alavancada.
2. **Timeframe** — ao lado do par (`2h`, `D`, `4h`). Cuidado: o seletor pode mostrar `D` enquanto o gráfico exibido é 2h, ou vice-versa. Use o espaçamento das datas no eixo inferior para confirmar.
3. **Preço atual** — etiqueta destacada na escala da direita.
4. **Horário do gráfico** — rodapé (ex.: `14:40:12 UTC-3`). Serve para saber quanto falta para o candle atual fechar.

Se qualquer um desses quatro estiver ilegível, diga isso em vez de adivinhar.

## Identificando as médias

Vá pela cor, não pela posição:

- **Branca** = 8
- **Amarela** = 21 → a linha da operação
- **Roxa/lilás** = 200 → tendência macro

Prints reais costumam ter linhas extras (bandas vermelhas, canais verdes, faixas de volatilidade). Elas não fazem parte deste método — ignore-as, mas mencione se estiverem claramente contradizendo a leitura, porque o usuário pode estar olhando para elas.

Quando o preço está muito acima ou abaixo, a 200 roxa pode estar fora da área visível do print. Nesse caso, diga que a tendência macro não é verificável na imagem e trabalhe só com 8 e 21 — sinalizando essa limitação, não escondendo.

## Volume

As barras no rodapé do gráfico. Compare a barra do candle de rejeição e a do candle de confirmação com a média visual das últimas 20-30 barras. Não invente números: "volume acima da média das últimas barras" é uma afirmação verificável no print; "volume de 1,2M" só se estiver escrito lá.

## Anotações desenhadas na imagem

Setas, círculos e legendas feitas pelo usuário mostram o que ele **acha** que está vendo. Elas são hipótese, não dado.

Confira a anotação contra os candles e as médias. Quando ela contradiz o gráfico — o caso mais comum é uma legenda dizendo "tendência de alta" num gráfico que está caindo — aponte a divergência de forma direta e mostre em que ponto do gráfico está a evidência. É exatamente para isso que o usuário está perguntando, mesmo quando ele só diz "vê se está certo".

## Quando a imagem não dá

Peça o que falta, sendo específico: "manda o mesmo par em 2h com a 200 visível" resolve; "a imagem está ruim" não resolve nada.
