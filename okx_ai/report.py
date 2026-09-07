"""Formatacao de saida em texto para o terminal."""

from __future__ import annotations

from .backtest import BacktestResult, Costs
from .risk import SessionStats, Sizing


def _line(char: str = "-", width: int = 78) -> str:
    return char * width


def header(title: str) -> str:
    return f"\n{_line('=')}\n{title}\n{_line('=')}"


def pct(value: float, digits: int = 2) -> str:
    return f"{value * 100:.{digits}f}%"


def backtest_report(res: BacktestResult, label: str = "") -> str:
    if res.n == 0:
        return f"{label}: nenhum trade gerado (filtros muito restritivos ou serie curta)."

    rows = [
        header(f"BACKTEST {label}".strip()),
        f"barras analisadas       : {res.bars}",
        f"trades                  : {res.n}",
        f"acertividade liquida    : {pct(res.hit_rate)}",
        f"payoff medio (ganho/perda em R) : {res.payoff:.2f}",
        f"expectancia por trade   : {res.expectancy_r:+.3f} R",
        f"profit factor           : {res.profit_factor:.2f}",
        f"drawdown maximo         : {res.max_drawdown_r:.2f} R",
        f"custo ida e volta       : {pct(res.costs.round_trip, 3)} do nocional",
        f"saidas                  : {res.exit_breakdown}",
    ]
    return "\n".join(rows)


def walk_forward_report(results: list[BacktestResult]) -> str:
    rows = [header("WALK-FORWARD (mesmo parametro em blocos diferentes)")]
    if not results:
        rows.append("serie curta demais para dividir em blocos.")
        return "\n".join(rows)

    rows.append(f"{'bloco':>6} {'trades':>7} {'acerto':>8} {'exp.R':>8} {'PF':>6}")
    for i, r in enumerate(results, 1):
        pf = "inf" if r.profit_factor == float("inf") else f"{r.profit_factor:.2f}"
        rows.append(f"{i:>6} {r.n:>7} {pct(r.hit_rate):>8} {r.expectancy_r:>+8.3f} {pf:>6}")

    signs = {1 if r.expectancy_r > 0 else -1 for r in results if r.n > 0}
    if len(signs) > 1:
        veredito = "expectancia TROCA DE SINAL entre blocos: o agregado nao e confiavel."
    elif signs == {1}:
        veredito = "expectancia positiva em TODOS os blocos: vantagem estavel ate aqui."
    else:
        veredito = "expectancia negativa em TODOS os blocos: o sistema perde de forma consistente."
    rows.append(f"\nveredito: {veredito}")
    return "\n".join(rows)


def sizing_report(sizings: list[Sizing], capital_usd: float, costs: Costs) -> str:
    rows = [
        header("O QUE '2 DOLARES POR OPERACAO' SIGNIFICA NA PRATICA"),
        f"custo de ida e volta assumido: {pct(costs.round_trip, 3)} do nocional",
        "",
        f"{'stop':>7} {'nocional':>12} {'alavancagem':>12} {'taxa/trade':>12} {'taxa em R':>11}",
    ]
    for s in sizings:
        lev = s.notional_usd / capital_usd if capital_usd > 0 else float("inf")
        rows.append(
            f"{pct(s.stop_pct, 2):>7} {s.notional_usd:>11.2f}$ {lev:>11.2f}x "
            f"{s.fee_usd:>11.3f}$ {s.fee_as_r:>10.2f}R"
        )
    rows.append(
        "\nLeitura: 'arriscar 2 dolares' NAO e 'comprar 2 dolares'. Quanto mais"
        "\napertado o stop, maior o nocional necessario e maior o peso da taxa em R."
    )
    return "\n".join(rows)


def session_report(stats: SessionStats, label: str = "") -> str:
    rows = [
        header(f"{stats.n_trades} OPERACOES DE {stats.risk_usd:.0f} DOLARES {label}".strip()),
        f"expectancia por trade   : {stats.expectancy_r:+.3f} R",
        f"resultado esperado      : {stats.expected_pnl:+.2f}$",
        f"mediana                 : {stats.median_pnl:+.2f}$",
        f"probabilidade de lucro  : {stats.prob_profit * 100:.1f}%",
        "",
        "distribuicao do resultado final:",
        f"  pior 5%   : {stats.p05:+.2f}$",
        f"  quartil 1 : {stats.p25:+.2f}$",
        f"  quartil 3 : {stats.p75:+.2f}$",
        f"  melhor 5% : {stats.p95:+.2f}$",
        "",
        f"drawdown medio          : {stats.mean_max_drawdown_r:.2f} R  "
        f"({stats.mean_max_drawdown_r * stats.risk_usd:.2f}$)",
        f"pior drawdown observado : {stats.worst_drawdown_r:.2f} R  "
        f"({stats.worst_drawdown_r * stats.risk_usd:.2f}$)",
        f"maior sequencia de perdas em {stats.trials} simulacoes : {stats.max_losing_streak}",
    ]
    return "\n".join(rows)
