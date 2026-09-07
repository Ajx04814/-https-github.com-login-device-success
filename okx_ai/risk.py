"""A matematica que decide se 59 ordens de 2 dolares fazem sentido.

Tres perguntas separadas, que quase sempre sao confundidas:

1. Qual acertividade minima o sistema precisa para nao perder dinheiro?
2. Quanto o custo de execucao come dessa vantagem?
3. Dado que existe vantagem, o que uma sequencia de 59 trades pode fazer?

A resposta da (3) NAO e um numero, e uma distribuicao. 59 e uma amostra pequena:
mesmo um sistema com vantagem real termina no vermelho com frequencia alta.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# 1 e 2: vantagem, custo e ponto de equilibrio
# ---------------------------------------------------------------------------


def cost_drag_r(stop_pct: float, round_trip_cost: float) -> float:
    """Custo de ida e volta expresso em multiplos do risco (R).

    Este e o numero que quase ninguem calcula. Com stop de 0,3%% e custo de
    0,20%% o operador entrega 0,67R por trade antes de o mercado se mover: o
    stop precisa ser LARGO em relacao ao custo, senao nao existe vantagem
    possivel. Alargar o stop reduz o arrasto proporcionalmente.
    """
    if stop_pct <= 0:
        raise ValueError("stop_pct deve ser > 0")
    return round_trip_cost / stop_pct


def expectancy_r(hit_rate: float, payoff: float, drag_r: float = 0.0) -> float:
    """Expectancia liquida por trade, em R.

        E = p * b - (1 - p) * 1 - custo
    """
    return hit_rate * payoff - (1.0 - hit_rate) - drag_r


def breakeven_hit_rate(payoff: float, drag_r: float = 0.0) -> float:
    """Acertividade minima para E = 0, ja considerando o custo.

        p* = (1 + custo) / (1 + b)
    """
    if payoff <= 0:
        raise ValueError("payoff deve ser > 0")
    return (1.0 + drag_r) / (1.0 + payoff)


def kelly_fraction(hit_rate: float, payoff: float, drag_r: float = 0.0) -> float:
    """Fracao de Kelly da banca a arriscar por trade, ja liquida de custo.

    Usa a forma assimetrica f = (p*W - q*L) / (W*L), com W = payoff - custo e
    L = 1 + custo. Valor <= 0 significa que nao existe tamanho positivo: nao
    operar. Na pratica se usa uma FRACAO de Kelly (um quarto, um decimo), porque
    Kelly cheio assume que ``hit_rate`` e conhecido, e ele nunca e.
    """
    win_r = payoff - drag_r
    loss_r = 1.0 + drag_r
    if win_r <= 0 or loss_r <= 0:
        return 0.0
    return (hit_rate * win_r - (1.0 - hit_rate) * loss_r) / (win_r * loss_r)


# ---------------------------------------------------------------------------
# Dimensionamento: o que "2 dolares" quer dizer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Sizing:
    """Traduz risco por trade em nocional, e checa se a ordem e executavel."""

    risk_usd: float          # quanto se perde se o stop for atingido
    stop_pct: float          # distancia do stop, em fracao do preco
    round_trip_cost: float

    @property
    def notional_usd(self) -> float:
        """Tamanho da ordem necessario para arriscar exatamente ``risk_usd``."""
        return self.risk_usd / self.stop_pct

    @property
    def fee_usd(self) -> float:
        return self.notional_usd * self.round_trip_cost

    @property
    def fee_as_r(self) -> float:
        return self.fee_usd / self.risk_usd


def sizing_table(risk_usd: float, round_trip_cost: float, stops_pct: list[float]) -> list[Sizing]:
    """Mesma perda maxima, distancias de stop diferentes."""
    return [Sizing(risk_usd, s, round_trip_cost) for s in stops_pct]


# ---------------------------------------------------------------------------
# 3: a distribuicao de 59 trades
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionStats:
    trials: int
    n_trades: int
    risk_usd: float
    expectancy_r: float
    mean_pnl: float
    median_pnl: float
    p05: float
    p25: float
    p75: float
    p95: float
    prob_profit: float
    prob_loss_gt_10r: float
    mean_max_drawdown_r: float
    worst_drawdown_r: float
    max_losing_streak: int

    @property
    def expected_pnl(self) -> float:
        return self.expectancy_r * self.n_trades * self.risk_usd


def simulate_session(
    hit_rate: float,
    payoff: float,
    n_trades: int = 59,
    risk_usd: float = 2.0,
    drag_r: float = 0.0,
    trials: int = 20_000,
    seed: int = 11,
) -> SessionStats:
    """Monte Carlo de uma sequencia de ``n_trades`` com risco fixo.

    Risco fixo (nao composto) e o que corresponde a "59 operacoes de 2 dolares":
    cada trade arrisca os mesmos 2 dolares, ganhe ou perca a anterior.
    """
    rng = random.Random(seed)
    win_r = payoff - drag_r
    loss_r = -1.0 - drag_r

    pnls: list[float] = []
    drawdowns: list[float] = []
    wins_streaks = 0
    prob_deep_loss = 0

    for _ in range(trials):
        total = 0.0
        peak = 0.0
        worst = 0.0
        streak = 0
        local_worst_streak = 0
        for _ in range(n_trades):
            if rng.random() < hit_rate:
                total += win_r
                streak = 0
            else:
                total += loss_r
                streak += 1
                local_worst_streak = max(local_worst_streak, streak)
            peak = max(peak, total)
            worst = min(worst, total - peak)
        pnls.append(total * risk_usd)
        drawdowns.append(abs(worst))
        wins_streaks = max(wins_streaks, local_worst_streak)
        if total <= -10.0:
            prob_deep_loss += 1

    pnls.sort()

    def pct(q: float) -> float:
        idx = min(len(pnls) - 1, max(0, int(q * len(pnls))))
        return pnls[idx]

    return SessionStats(
        trials=trials,
        n_trades=n_trades,
        risk_usd=risk_usd,
        expectancy_r=expectancy_r(hit_rate, payoff, drag_r),
        mean_pnl=sum(pnls) / len(pnls),
        median_pnl=pct(0.50),
        p05=pct(0.05),
        p25=pct(0.25),
        p75=pct(0.75),
        p95=pct(0.95),
        prob_profit=sum(1 for v in pnls if v > 0) / len(pnls),
        prob_loss_gt_10r=prob_deep_loss / trials,
        mean_max_drawdown_r=sum(drawdowns) / len(drawdowns),
        worst_drawdown_r=max(drawdowns),
        max_losing_streak=wins_streaks,
    )


def prob_losing_streak(hit_rate: float, n_trades: int, streak: int) -> float:
    """Probabilidade aproximada de ao menos uma sequencia de ``streak`` perdas.

    Usa a recursao exata de "sem k fracassos seguidos" em n tentativas.
    """
    q = 1.0 - hit_rate
    # f[i] = probabilidade de NAO haver sequencia de tamanho `streak` em i trades
    f = [1.0] * (streak)
    for i in range(streak, n_trades + 1):
        # subtrai os caminhos que fecham a primeira sequencia exatamente em i
        value = f[i - 1] - (q ** streak) * hit_rate * f[i - streak - 1] if i > streak else f[i - 1] - q ** streak
        f.append(max(0.0, value))
    return 1.0 - f[n_trades]


def martingale_ruin(
    hit_rate: float, capital_usd: float, base_usd: float = 2.0, n_trades: int = 59, trials: int = 20_000, seed: int = 3
) -> dict[str, float]:
    """Compara risco fixo com dobra apos perda (martingale).

    Existe para mostrar o mecanismo, nao para recomendar: a martingale troca uma
    alta probabilidade de lucro pequeno por uma probabilidade pequena de perder
    tudo, e a expectancia continua negativa se a vantagem for negativa.
    """
    rng = random.Random(seed)
    ruined = 0
    finals: list[float] = []
    max_stakes: list[float] = []

    for _ in range(trials):
        equity = capital_usd
        stake = base_usd
        peak_stake = stake
        for _ in range(n_trades):
            if stake > equity:
                ruined += 1
                equity = 0.0
                break
            if rng.random() < hit_rate:
                equity += stake
                stake = base_usd
            else:
                equity -= stake
                stake *= 2.0
                peak_stake = max(peak_stake, stake)
            if equity <= 0:
                ruined += 1
                equity = 0.0
                break
        finals.append(equity)
        max_stakes.append(peak_stake)

    return {
        "prob_ruina": ruined / trials,
        "capital_final_medio": sum(finals) / trials,
        "maior_aposta_media": sum(max_stakes) / trials,
        "maior_aposta_maxima": max(max_stakes),
    }


def required_hit_rate_for_target(
    payoff: float, drag_r: float, target_usd: float, n_trades: int, risk_usd: float
) -> float:
    """Acertividade necessaria para atingir um lucro alvo NA MEDIA.

    Devolve > 1.0 quando o alvo e aritmeticamente impossivel com esses parametros.
    """
    needed_e = target_usd / (n_trades * risk_usd)
    return (needed_e + 1.0 + drag_r) / (1.0 + payoff)


def sharpe_per_trade(expectancy: float, hit_rate: float, payoff: float, drag_r: float = 0.0) -> float:
    """Razao expectancia/desvio por trade: mede quanto ruido cerca a vantagem."""
    win_r, loss_r = payoff - drag_r, -1.0 - drag_r
    mean = hit_rate * win_r + (1 - hit_rate) * loss_r
    var = hit_rate * (win_r - mean) ** 2 + (1 - hit_rate) * (loss_r - mean) ** 2
    sd = math.sqrt(var)
    return expectancy / sd if sd > 0 else 0.0
