# Moedas da OKX: o que a IA consegue estudar, o que decide acertividade, e o que 59 ordens de 2 dólares realmente fazem

Este documento é a análise. O código em `okx_ai/` é a ferramenta que permite
refazer cada número com dados reais da sua conta e do seu par.

Aviso curto e sem rodeios: nada aqui é recomendação de investimento. Os números
abaixo são aritmética verificável, não previsão. Cripto com alavancagem perde
dinheiro para a maioria dos participantes, e o motivo principal é matemático,
não emocional.

---

## 1. As três perguntas que quase sempre são misturadas

A pergunta "qual estratégia tem boa acertividade" embute três perguntas
independentes. Separá-las é metade do trabalho:

| Pergunta | O que decide | Onde está no código |
|---|---|---|
| O sinal prevê alguma coisa? | acertividade e payoff medidos fora da amostra | `backtest.py`, `walk_forward` |
| Sobra vantagem depois do custo? | distância do stop vs. taxa + spread | `risk.cost_drag_r` |
| 59 trades bastam para provar? | variância da amostra | `risk.simulate_session` |

Um sistema pode acertar a primeira e morrer na segunda. É o caso mais comum de
scalp em ordem pequena. E pode passar nas duas e ainda assim terminar 59 trades
no prejuízo — isso não é falha, é a terceira pergunta.

---

## 2. O que a inteligência artificial consegue de fato estudar

### Consegue, e bem

**Microestrutura e custo de execução.** É a área de maior retorno e a menos
disputada por operadores de varejo. Spread efetivo por par e por horário,
profundidade do livro nos primeiros níveis, quanto uma ordem de X dólares move o
preço, quanto tempo uma ordem limite fica na fila antes de executar. Isso é
medível, estável e diretamente conversível em dinheiro. O `screener.py` faz a
versão simples: spread relativo, volume 24h e tamanho mínimo de ordem.

**Classificação de regime.** Distinguir tendência de lateralidade é um problema
de classificação com rótulo bem definido, e modelos acertam nisso melhor do que
acertam direção. Vale mais saber *se* deve operar do que *para que lado*: a
mesma regra de rompimento tem expectativa positiva em regime de tendência e
negativa em lateralidade. É o papel do filtro de ADX em `strategy.py`.

**Previsão de volatilidade.** Volatilidade tem memória forte (agrupamento):
prever a amplitude das próximas horas é muito mais fácil do que prever o sinal
do retorno. Isso não diz para que lado ir, mas dimensiona stop e tamanho — que
é onde o dinheiro é ganho ou perdido.

**Estruturas com retorno mecânico.** Taxa de financiamento de perpétuos, base
entre spot e futuro, diferenças entre corretoras. Não são previsão: são um
prêmio pago por alguém que quer alavancagem. Um modelo aqui estima quando o
prêmio compensa o custo de carregar as duas pernas, e não quando o Bitcoin sobe.

**Validação honesta.** Ironicamente, o maior valor da IA é destrutivo: detectar
vazamento de dados, medir quanto de um resultado é sobreajuste, e calcular quantos
trades seriam necessários para distinguir a vantagem do ruído. A maior parte das
estratégias que "funcionam no backtest" morre nesse teste.

### Não consegue, e vender que consegue é o golpe padrão

**Prever direção de preço de forma persistente com dados públicos de candles.**
O sinal existente nesse dado é pequeno, instável e disputado por participantes
com custo de execução dez vezes menor. Um modelo que reporta 70% de acerto
direcional em barras de 5 minutos está com vazamento de futuro, sobreajuste, ou
está medindo acerto sem descontar custo.

**Transformar acertividade em lucro.** São grandezas diferentes. 80% de acerto
com payoff 0,25 é sistema perdedor. 35% de acerto com payoff 3 é sistema
vencedor. Quem anuncia acertividade sem payoff está escondendo metade da conta.

**Compensar desvantagem estrutural.** Um modelo excelente com custo de 0,30% por
ida e volta perde para um modelo medíocre com custo de 0,02%. Na prática o
tamanho da conta e o nível de taxa determinam quais estratégias são acessíveis a
você — antes de qualquer discussão sobre modelo.

---

## 3. Anatomia de uma operação: onde ganho e perda são realmente decididos

Abrir uma operação na OKX envolve seis decisões. Cinco são mecânicas e uma é o
palpite. A maioria das pessoas gasta 100% da atenção no palpite.

**1. Par.** Filtrado por operabilidade, não por narrativa: spread apertado,
volume alto, tamanho mínimo de ordem compatível. Um par com spread de 0,15% já
custa mais que a corretagem em cada giro.

**2. Direção.** O palpite. É a única parte que não é controlável.

**3. Entrada.** Limite (taxa maker, 0,08%, mas pode não executar) ou mercado
(taxa taker, 0,10%, executa sempre e paga o spread). O backtest aqui assume
taker nas duas pernas, o cenário pior.

**4. Stop.** A distância do stop é a *unidade de risco*, o R. Tudo é medido em
múltiplos dele. Colocado onde a tese está errada — por exemplo 1,5 ATR — e não
onde a perda em dólares fica confortável. O código usa `stop_atr` justamente para
que a distância se adapte à volatilidade do momento.

**5. Alvo e saída por tempo.** Payoff é alvo dividido por stop. Sem saída por
tempo o capital fica preso em posições que não andam. `max_bars` resolve isso.

**6. Tamanho.** Derivado, nunca escolhido:

```
nocional = risco_em_dolares / distancia_do_stop_em_percentual
```

Este é o ponto que mais gera confusão na frase "operação de 2 dólares".

### "2 dólares" é o risco ou o tamanho da ordem?

São coisas radicalmente diferentes, com custo de 0,30% por ida e volta
(0,10% taker × 2 + 0,05% de derrapagem × 2):

| Stop | Nocional para arriscar 2$ | Taxa por trade | Taxa em R |
|---|---|---|---|
| 0,2% | 1.000$ | 3,00$ | **1,50 R** |
| 0,3% | 667$ | 2,00$ | **1,00 R** |
| 0,5% | 400$ | 1,20$ | 0,60 R |
| 1,0% | 200$ | 0,60$ | 0,30 R |
| 2,0% | 100$ | 0,30$ | 0,15 R |
| 3,0% | 67$ | 0,20$ | 0,10 R |

Leia a coluna da direita devagar. **Com stop de 0,3%, a corretora leva 1 R por
operação.** Você precisa acertar o equivalente a um trade inteiro só para
empatar com o custo. Este é o mecanismo real pelo qual scalp de stop curto
destrói contas pequenas — não falta de disciplina, aritmética.

Se "2 dólares" significa *comprar 2 dólares* de cripto: com stop de 2% você
arrisca 4 centavos por trade, e 59 operações movimentam no total 2,36 dólares de
resultado possível enquanto pagam 0,18 dólar em taxas. É um exercício de
aprendizado válido — e é uma forma honesta de treinar execução sem risco —, mas
não é uma operação com retorno relevante.

Reproduza a tabela com os seus parâmetros:

```bash
python -m okx_ai edge --stop 0.005 --payoff 2.0
```

---

## 4. A conta da acertividade

A expectativa por trade, em múltiplos de risco:

```
E = p × b − (1 − p) − custo_em_R
```

`p` acertividade, `b` payoff, `custo_em_R = custo_ida_e_volta ÷ distância_do_stop`.

A acertividade de equilíbrio:

```
p* = (1 + custo_em_R) / (1 + b)
```

Com payoff 2 e stop de 2% (custo = 0,15 R), `p* = 38,3%`. Com o mesmo payoff 2 e
stop de 0,3% (custo = 1,00 R), `p* = 66,7%`. **A mesma estratégia, com o mesmo
sinal, passa de viável a impossível só por causa da distância do stop.**

Nenhum modelo, por melhor que seja, produz 66,7% de acerto direcional sustentado
em barras curtas. Por isso a conclusão prática: com custo de varejo, stops
apertados são inviáveis, e a solução não é um modelo melhor — é stop mais largo,
nocional menor, e menos operações.

---

## 5. As 59 operações de 2 dólares

Aqui está o que a simulação mostra. Todos os cenários abaixo assumem stop de 2%,
risco de 2$ por trade, custo de 0,30% por giro, 59 operações, 40.000 simulações:

| Acerto | Payoff | E por trade | Resultado esperado | P(lucro em 59) | Pior 5% | Melhor 5% | Drawdown médio |
|---|---|---|---|---|---|---|---|
| 40% | 2,0 | +0,05 R | +5,90$ | **60,6%** | −33,7$ | +44,3$ | 23,3$ |
| 45% | 2,0 | +0,20 R | +23,60$ | 85,4% | −15,7$ | +62,3$ | 18,1$ |
| 50% | 2,0 | +0,35 R | +41,30$ | 96,5% | +2,3$ | +80,3$ | 14,6$ |
| 55% | 1,5 | +0,23 R | +26,55$ | 90,1% | −5,7$ | +59,3$ | 13,8$ |
| 35% | 3,0 | +0,25 R | +29,50$ | 87,0% | −15,7$ | +80,3$ | 22,5$ |

Três leituras que importam:

**59 trades não provam nada.** Na primeira linha há vantagem real e positiva, e
mesmo assim 4 em cada 10 sessões terminam no vermelho. O contrário também vale:
uma sessão de 59 trades no lucro **não** é evidência de que o sistema funciona.
Com p=45% e payoff 2, a probabilidade de lucro sobe de 85,4% em 59 trades para
99,9% em 590. O número de operações é o que converte vantagem em resultado.

**O drawdown chega antes do lucro.** O rebaixamento médio esperado é da ordem de
15 a 23 dólares — várias vezes o risco de um único trade. Quem dimensiona a banca
pensando em "2 dólares por operação" e tem 40 dólares na conta será interrompido
por uma sequência normal, não por um evento raro.

**Sequências de perda são a regra.** Com 45% de acerto em 59 trades:

| Perdas seguidas | Probabilidade de acontecer ao menos uma vez |
|---|---|
| 4 | 94,8% |
| 5 | 76,8% |
| 6 | 52,6% |
| 7 | 32,3% |
| 8 | 18,7% |
| 10 | 5,7% |

Seis perdas seguidas em uma sessão é cara ou coroa. Não é sinal de que a
estratégia quebrou, e reagir a isso aumentando o tamanho é o mecanismo pelo qual
uma sessão ruim vira uma conta zerada.

### A matemática de metas

Quanto de acertividade uma meta exige, com payoff 2, stop 2%, 59 × 2$:

- meta de +30$ → precisa de **46,8%** de acerto (difícil, mas não absurdo)
- meta de +100$ → precisa de **66,6%** de acerto (não existe)

Metas em dólares definem acertividade exigida. Se a meta exige uma acertividade
que nenhum sistema entrega, a meta é impossível — e a única forma de "atingi-la"
é aumentar o risco até que uma sequência ruim liquide a conta.

```bash
python -m okx_ai session --hit 0.45 --payoff 2.0 --stop 0.02 --trades 59 --risk 2
```

### Por que dobrar após a perda não resolve

A martingale é a tentativa mais comum de contornar acertividade baixa. Com 48% de
acerto, base de 2$ e 59 operações:

| Banca | Probabilidade de zerar | Maior aposta observada |
|---|---|---|
| 100$ | 55,4% | 128$ |
| 500$ | 15,3% | 512$ |

Ela funciona exatamente como anunciado: quase sempre um lucro pequeno, e de vez
em quando a perda de tudo. A expectativa não muda de sinal — a martingale
redistribui o mesmo resultado esperado em uma distribuição com cauda catastrófica.
Uma sequência de 8 perdas, que tem 18,7% de chance de aparecer, exige uma aposta
de 256$ para "recuperar" 2$.

---

## 6. Como os grandes players operam de verdade

A diferença entre um fundo e um operador de varejo não é o modelo. É a estrutura.

**Eles ganham no spread, não na direção.** A maior parte do volume institucional
em cripto é formação de mercado: colocar bid e ask simultaneamente, capturar o
spread, e administrar o estoque que sobra. A "previsão" envolvida é de segundos e
serve para ajustar a cotação, não para apostar. Renda vem do fluxo, não do
palpite.

**O custo deles é outro.** Nível VIP alto na OKX paga *rebate* de maker — a
corretora paga por fornecer liquidez. Enquanto o varejo entrega 0,30% por giro,
o formador de mercado recebe alguns pontos-base. Um sistema com vantagem
levemente negativa para você é lucrativo para ele, sem mudar uma linha do modelo.

**Eles operam prêmio estrutural, não previsão.** Base entre spot e futuro, taxa
de financiamento de perpétuos, arbitragem entre corretoras, empréstimo de moeda.
São retornos de dois a quinze por cento ao ano com risco direcional próximo de
zero — sem graça, escaláveis, e é onde está a maior parte do capital sério.

**Execução é uma disciplina separada.** Uma posição de 40 milhões não é comprada
com uma ordem a mercado. Ela é fatiada por TWAP, VWAP ou percentual-do-volume,
com ordens iceberg, ao longo de horas, para não mover o preço contra si mesma.
Existem equipes cujo trabalho inteiro é reduzir o custo de implementação em dois
pontos-base. Para o varejo, ordem de 200$ é irrelevante para o livro — o que é
uma vantagem genuína e raramente aproveitada.

**Risco é orçamento, não sentimento.** O tamanho vem de volatilidade alvo e
limite de perda, não de convicção. Regra de corte é automática. Nenhuma decisão
de tamanho é tomada durante um drawdown.

**Eles medem em milhares de trades.** Nenhuma mesa avalia um sistema por 59
operações. O ciclo é: hipótese, teste fora da amostra, teste em produção com
tamanho mínimo por meses, e só então capital. O que o varejo chama de "estratégia
validada" é o que uma mesa chama de ruído inicial.

**O que dá para copiar com conta pequena:** stop largo com nocional pequeno
(reduz o peso da taxa); ordens limite sempre que possível (maker em vez de
taker); poucos pares muito líquidos; tamanho fixo em risco; e medir em centenas
de trades, não dezenas. **O que não dá para copiar:** o nível de taxa, a
infraestrutura de latência, e o balanço que permite carregar as duas pernas de
uma operação de base.

---

## 7. Protocolo antes de arriscar dinheiro

1. **Medir o custo real.** Rode `screener` e veja o spread verdadeiro dos seus
   pares. Some 2 × taxa + 2 × spread/2. Esse é o número que a estratégia precisa
   superar.
2. **Escolher o stop pelo custo.** Se o arrasto passar de 0,25 R, o stop está
   curto demais para a sua estrutura de taxas. Alargue ou não opere.
3. **Backtest com custo dentro.** `python -m okx_ai backtest --inst BTC-USDT --bar 15m --bars 3000`.
4. **Walk-forward.** Se a expectativa troca de sinal entre blocos, pare. O
   agregado positivo era sorte.
5. **Simular a sessão.** Use a acertividade *medida*, não a desejada, e olhe o
   percentil 5 e o drawdown médio — não a média.
6. **Papel/tamanho mínimo por 200+ trades** antes de qualquer aumento de tamanho.
7. **Definir o critério de abandono antes de começar.** Por exemplo: se o
   drawdown passar de 15 R, o sistema está fora da distribuição esperada e é
   desligado. Escrever isso antes é o que impede a decisão ser tomada no meio de
   uma sequência de perdas.

O passo 4 elimina a maioria das ideias. É esse o objetivo dele.
