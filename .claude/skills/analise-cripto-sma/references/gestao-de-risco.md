# Gestão de risco

A alavancagem não muda a análise — muda o tamanho do erro. Um setup com 60% de acerto e stop mal colocado quebra a banca do mesmo jeito.

## Stop

O stop fica onde a tese morre, não onde dói menos. Neste setup a tese é "a SMA 21 amarela segurou o preço".

- **Compra:** stop alguns ticks abaixo do pavio mínimo do candle de rejeição.
- **Venda:** stop acima do pavio máximo do candle de rejeição.

Perder esse ponto significa que a média não segurou. Ficar dentro da operação depois disso é esperança, não plano.

## Distância do stop e alavancagem

A conta que importa:

```
distância do stop (%) = |preço de entrada − preço do stop| / preço de entrada × 100
perda na margem (%)   = distância do stop (%) × alavancagem
```

Exemplo: entrada a 0,11000, stop a 0,10780 → distância de 2%. Com 20x, o stop consome **40% da margem alocada** naquela operação. Com 50x, 100% — ou seja, o stop e a liquidação são praticamente o mesmo ponto, e qualquer pavio te tira.

Regra prática: **quanto maior a alavancagem, mais perto o stop precisa estar** — e portanto mais exato precisa ser o ponto de entrada. Alavancagem alta não é para ganhar mais no mesmo trade; é para operar o mesmo risco com menos margem parada.

## Tamanho de posição

Defina antes da entrada quanto da banca você aceita perder no trade (1% a 2% é o padrão de quem sobrevive):

```
risco em R$ = banca × % de risco
margem da operação = risco em R$ / (distância do stop % × alavancagem / 100)
```

Se a conta der uma margem maior do que você se sente confortável em ver zerada, a operação está grande demais — reduza, não relaxe o stop.

## Margem isolada

Isola a perda máxima ao valor daquela posição. Sem ela, uma liquidação puxa o saldo inteiro da conta. Só considere margem cruzada com alavancagem baixa (~3x) e com plena consciência de que o risco passa a ser da banca toda.

## Alavancagem por experiência

| Histórico | Alavancagem |
|---|---|
| Iniciante / intermediário (até 50 operações) | 20x |
| Após 50 operações | até 30x |
| Após 100 operações | 50x ou mais |

O critério é execução comprovada — operações registradas, stops respeitados — e não sequência de acertos. Quem sobe a alavancagem depois de três green seguidos está aumentando aposta, não risco calculado.

## Alvo e relação risco/retorno

Alvo mínimo razoável: 2x a distância do stop. Abaixo de 1:1 o setup precisa acertar muito mais da metade das vezes só para empatar — e nenhum método técnico entrega isso de forma consistente.

Alvos naturais neste setup: topo/fundo anterior, distância média dos últimos movimentos após toque na 21, ou saída parcial quando o preço perde a **SMA 8 branca** (que costuma virar antes da 21).
