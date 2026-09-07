"""Motor de backtest com custos de execucao explicitos.

Premissas que tornam o resultado honesto:

* Entrada na ABERTURA da barra seguinte ao sinal, nunca no fechamento do sinal.
* Stop e alvo checados barra a barra usando maxima e minima.
* Quando a mesma barra toca stop e alvo, assume-se o STOP (pior caso). Sem essa
  regra qualquer backtest de intrabarra fica otimista demais.
* Custo de ida e volta = 2 x taxa taker + 2 x slippage, aplicado sobre o nocional.
* Uma posicao por vez: e o que da para executar de verdade com conta pequena.
"""

from __future__ import annotations

from dataclasses import dataclass

from .okx import Candle
from .strategy import Features, Signal, StrategyParams, compute_features, generate_signals

# Taxas padrao da OKX para conta sem nivel VIP (spot).
TAKER_FEE = 0.0010
MAKER_FEE = 0.0008


@dataclass(frozen=True)
class Costs:
    taker_fee: float = TAKER_FEE
    slippage: float = 0.0005  # meio ponto-base de derrapagem por perna

    @property
    def round_trip(self) -> float:
        """Custo total de abrir e fechar, em fracao do nocional."""
        return 2.0 * (self.taker_fee + self.slippage)


@dataclass(frozen=True)
class Trade:
    side: str
    entry_index: int
    exit_index: int
    entry: float
    exit: float
    stop: float
    target: float
    reason: str              # "target", "stop" ou "time"
    gross_return: float      # retorno do preco, com sinal da direcao
    net_return: float        # ja descontado o custo de ida e volta
    r_multiple: float        # resultado em multiplos do risco inicial (liquido)

    @property
    def win(self) -> bool:
        return self.net_return > 0


@dataclass
class BacktestResult:
    trades: list[Trade]
    costs: Costs
    params: StrategyParams
    bars: int

    @property
    def n(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> list[Trade]:
        return [t for t in self.trades if t.win]

    @property
    def losses(self) -> list[Trade]:
        return [t for t in self.trades if not t.win]

    @property
    def hit_rate(self) -> float:
        """Acertividade liquida: fracao de trades positivos DEPOIS dos custos."""
        return len(self.wins) / self.n if self.n else 0.0

    @property
    def avg_win_r(self) -> float:
        return sum(t.r_multiple for t in self.wins) / len(self.wins) if self.wins else 0.0

    @property
    def avg_loss_r(self) -> float:
        """Media das perdas em R, valor positivo."""
        return abs(sum(t.r_multiple for t in self.losses) / len(self.losses)) if self.losses else 0.0

    @property
    def payoff(self) -> float:
        return self.avg_win_r / self.avg_loss_r if self.avg_loss_r else 0.0

    @property
    def expectancy_r(self) -> float:
        """Expectancia por trade em R. E o unico numero que decide tudo."""
        return sum(t.r_multiple for t in self.trades) / self.n if self.n else 0.0

    @property
    def profit_factor(self) -> float:
        gains = sum(t.r_multiple for t in self.wins)
        pains = abs(sum(t.r_multiple for t in self.losses))
        return gains / pains if pains else float("inf")

    def equity_curve_r(self) -> list[float]:
        equity, total = [0.0], 0.0
        for t in self.trades:
            total += t.r_multiple
            equity.append(total)
        return equity

    @property
    def max_drawdown_r(self) -> float:
        peak, worst = 0.0, 0.0
        for value in self.equity_curve_r():
            peak = max(peak, value)
            worst = min(worst, value - peak)
        return abs(worst)

    @property
    def exit_breakdown(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for t in self.trades:
            out[t.reason] = out.get(t.reason, 0) + 1
        return out


def _simulate_one(
    candles: list[Candle], signal: Signal, p: StrategyParams, costs: Costs
) -> Trade | None:
    entry_index = signal.index + 1
    if entry_index >= len(candles):
        return None

    entry = candles[entry_index].open
    risk = p.stop_atr * signal.atr
    if risk <= 0:
        return None

    if signal.side == "long":
        stop, target = entry - risk, entry + p.payoff * risk
    else:
        stop, target = entry + risk, entry - p.payoff * risk

    exit_price, exit_index, reason = candles[-1].close, len(candles) - 1, "time"
    last = min(entry_index + p.max_bars, len(candles) - 1)

    for j in range(entry_index, last + 1):
        bar = candles[j]
        if signal.side == "long":
            hit_stop, hit_target = bar.low <= stop, bar.high >= target
        else:
            hit_stop, hit_target = bar.high >= stop, bar.low <= target

        if hit_stop:  # pessimista de proposito: stop vence o empate na barra
            exit_price, exit_index, reason = stop, j, "stop"
            break
        if hit_target:
            exit_price, exit_index, reason = target, j, "target"
            break
        if j == last:
            exit_price, exit_index, reason = bar.close, j, "time"

    direction = 1.0 if signal.side == "long" else -1.0
    gross = direction * (exit_price - entry) / entry
    net = gross - costs.round_trip
    risk_fraction = risk / entry  # risco inicial como fracao do nocional

    return Trade(
        side=signal.side,
        entry_index=entry_index,
        exit_index=exit_index,
        entry=entry,
        exit=exit_price,
        stop=stop,
        target=target,
        reason=reason,
        gross_return=gross,
        net_return=net,
        r_multiple=net / risk_fraction,
    )


def run(
    candles: list[Candle],
    p: StrategyParams | None = None,
    costs: Costs | None = None,
    feats: Features | None = None,
) -> BacktestResult:
    """Executa o backtest sequencial, sem sobreposicao de posicoes."""
    p = p or StrategyParams()
    costs = costs or Costs()
    signals = generate_signals(candles, p, feats or compute_features(candles, p))

    trades: list[Trade] = []
    busy_until = -1
    for signal in signals:
        if signal.index <= busy_until:
            continue  # ja ha posicao aberta nesta barra
        trade = _simulate_one(candles, signal, p, costs)
        if trade is None:
            continue
        trades.append(trade)
        busy_until = trade.exit_index

    return BacktestResult(trades=trades, costs=costs, params=p, bars=len(candles))


def walk_forward(
    candles: list[Candle],
    p: StrategyParams | None = None,
    costs: Costs | None = None,
    folds: int = 4,
) -> list[BacktestResult]:
    """Divide a serie em blocos contiguos e roda o mesmo parametro em cada um.

    Nao e otimizacao: e teste de estabilidade. Se a expectancia muda de sinal
    entre os blocos, o resultado agregado e sorte, nao vantagem.
    """
    p = p or StrategyParams()
    size = len(candles) // folds
    out: list[BacktestResult] = []
    for k in range(folds):
        chunk = candles[k * size : (k + 1) * size if k < folds - 1 else len(candles)]
        if len(chunk) < 200:
            continue
        out.append(run(chunk, p, costs))
    return out
