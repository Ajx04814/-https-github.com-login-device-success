"""Linha de comando do toolkit.

    python -m okx_ai screener  --notional 200
    python -m okx_ai backtest  --inst BTC-USDT --bar 5m --bars 1500
    python -m okx_ai session   --hit 0.42 --payoff 2.0 --stop 0.006
    python -m okx_ai edge      --stop 0.006 --payoff 2.0
    python -m okx_ai demo      (offline, sem rede, para validar a instalacao)
"""

from __future__ import annotations

import argparse
import sys

from . import backtest, report, risk, screener, synthetic
from .backtest import Costs
from .okx import OKXError, history
from .strategy import StrategyParams


def _costs(args) -> Costs:
    return Costs(taker_fee=args.fee, slippage=args.slippage)


def _params(args) -> StrategyParams:
    return StrategyParams(
        adx_min=args.adx_min,
        stop_atr=args.stop_atr,
        payoff=args.payoff,
        max_bars=args.max_bars,
        allow_short=not args.long_only,
    )


def cmd_screener(args) -> int:
    pairs = screener.collect(inst_type=args.inst_type, quote=args.quote)
    top = screener.rank(
        pairs,
        notional_usd=args.notional,
        min_volume_usd=args.min_volume,
        max_spread_pct=args.max_spread,
        top=args.top,
    )
    print(report.header(f"MOEDAS OPERAVEIS COM ORDEM DE {args.notional:.0f}$ ({len(pairs)} pares lidos)"))
    print(f"{'par':<16}{'spread':>9}{'range 24h':>11}{'volume 24h':>16}{'min ordem':>11}{'nota':>9}")
    for p in top:
        print(
            f"{p.inst_id:<16}{report.pct(p.spread_pct, 3):>9}{report.pct(p.range_24h_pct):>11}"
            f"{p.volume_24h_usd:>15,.0f}${p.min_size_usd:>10.2f}${p.score():>9.1f}"
        )
    if not top:
        print("nenhum par passou nos filtros; afrouxe --max-spread ou --min-volume.")
    return 0


def cmd_backtest(args) -> int:
    candles = history(args.inst, bar=args.bar, bars=args.bars)
    if len(candles) < 300:
        print(f"historico insuficiente: {len(candles)} barras.", file=sys.stderr)
        return 1
    return _run_backtest(candles, args, label=f"{args.inst} {args.bar}")


def _run_backtest(candles, args, label: str) -> int:
    p, c = _params(args), _costs(args)
    res = backtest.run(candles, p, c)
    print(report.backtest_report(res, label))
    print(report.walk_forward_report(backtest.walk_forward(candles, p, c, folds=args.folds)))

    if res.n == 0:
        return 0

    # Liga o resultado medido a sessao de 59 ordens.
    stop_pct = sum(abs(t.entry - t.stop) / t.entry for t in res.trades) / res.n
    drag = risk.cost_drag_r(stop_pct, c.round_trip)
    print(
        report.sizing_report(
            risk.sizing_table(args.risk, c.round_trip, [stop_pct, 0.003, 0.005, 0.010, 0.020]),
            capital_usd=args.capital,
            costs=c,
        )
    )
    stats = risk.simulate_session(
        hit_rate=res.hit_rate,
        payoff=max(res.payoff, 0.01),
        n_trades=args.trades,
        risk_usd=args.risk,
        trials=args.trials,
    )
    print(report.session_report(stats, label="(usando acerto e payoff medidos)"))
    print(f"\nstop medio medido: {report.pct(stop_pct)}  ->  arrasto de custo: {drag:.2f} R por trade")
    print(f"acertividade de equilibrio: {report.pct(risk.breakeven_hit_rate(res.payoff or 1.0, drag))}")
    return 0


def cmd_session(args) -> int:
    drag = risk.cost_drag_r(args.stop, Costs(args.fee, args.slippage).round_trip)
    stats = risk.simulate_session(
        hit_rate=args.hit,
        payoff=args.payoff,
        n_trades=args.trades,
        risk_usd=args.risk,
        drag_r=drag,
        trials=args.trials,
    )
    print(report.session_report(stats))
    print(f"\narrasto de custo: {drag:.2f} R por trade (stop {report.pct(args.stop)})")
    print(f"acertividade de equilibrio: {report.pct(risk.breakeven_hit_rate(args.payoff, drag))}")
    for k in (5, 7, 10):
        print(f"P(sequencia de {k:>2} perdas em {args.trades}): {report.pct(risk.prob_losing_streak(args.hit, args.trades, k))}")
    mart = risk.martingale_ruin(args.hit, capital_usd=args.capital, base_usd=args.risk, n_trades=args.trades)
    print(
        f"\nse dobrasse apos perda (martingale) com {args.capital:.0f}$ de banca:"
        f"\n  probabilidade de zerar : {mart['prob_ruina'] * 100:.1f}%"
        f"\n  maior aposta media     : {mart['maior_aposta_media']:.0f}$"
        f"\n  maior aposta observada : {mart['maior_aposta_maxima']:.0f}$"
    )
    return 0


def cmd_edge(args) -> int:
    c = Costs(args.fee, args.slippage)
    drag = risk.cost_drag_r(args.stop, c.round_trip)
    print(report.header("VANTAGEM MINIMA EXIGIDA"))
    print(f"custo ida e volta : {report.pct(c.round_trip, 3)} do nocional")
    print(f"stop              : {report.pct(args.stop)}")
    print(f"arrasto           : {drag:.3f} R por trade\n")
    print(f"{'payoff':>8}{'acerto p/ E=0':>16}{'acerto p/ E=+0.1R':>20}{'Kelly em p*+5pp':>18}")
    for b in (1.0, 1.5, 2.0, 2.5, 3.0):
        be = risk.breakeven_hit_rate(b, drag)
        plus = (0.1 + 1.0 + drag) / (1.0 + b)
        k = risk.kelly_fraction(min(be + 0.05, 0.99), b, drag)
        print(f"{b:>8.1f}{report.pct(be):>16}{report.pct(plus):>20}{report.pct(max(k, 0.0)):>18}")
    print(
        "\nSe a acertividade realista do seu sinal estiver ABAIXO da coluna 'E=0',"
        "\no sistema perde dinheiro por construcao, independente do numero de trades."
        "\nA coluna de Kelly e o tamanho TEORICO maximo; use um quarto dela ou menos,"
        "\nporque a acertividade verdadeira e estimada, nao conhecida."
    )
    return 0


def cmd_demo(args) -> int:
    print("modo offline: serie sintetica, serve para validar o codigo, nao a estrategia.")
    candles = synthetic.gbm_candles(n=args.bars, seed=args.seed)
    return _run_backtest(candles, args, label="SINTETICO 5m")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="okx_ai", description="Estudo quantitativo de moedas da OKX")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--fee", type=float, default=backtest.TAKER_FEE, help="taxa taker por perna")
        p.add_argument("--slippage", type=float, default=0.0005, help="derrapagem por perna")
        p.add_argument("--risk", type=float, default=2.0, help="risco em dolares por operacao")
        p.add_argument("--trades", type=int, default=59, help="numero de operacoes na sessao")
        p.add_argument("--capital", type=float, default=100.0, help="banca total em dolares")
        p.add_argument("--trials", type=int, default=20_000, help="simulacoes de Monte Carlo")

    def strat(p):
        p.add_argument("--adx-min", type=float, default=20.0)
        p.add_argument("--stop-atr", type=float, default=1.5)
        p.add_argument("--payoff", type=float, default=2.0)
        p.add_argument("--max-bars", type=int, default=24)
        p.add_argument("--long-only", action="store_true")
        p.add_argument("--folds", type=int, default=4)

    s = sub.add_parser("screener", help="ranqueia pares por operabilidade")
    s.add_argument("--inst-type", default="SPOT")
    s.add_argument("--quote", default="USDT")
    s.add_argument("--notional", type=float, default=200.0)
    s.add_argument("--min-volume", type=float, default=5_000_000.0)
    s.add_argument("--max-spread", type=float, default=0.0010)
    s.add_argument("--top", type=int, default=20)
    s.set_defaults(func=cmd_screener)

    b = sub.add_parser("backtest", help="backtest com dados reais da OKX")
    b.add_argument("--inst", default="BTC-USDT")
    b.add_argument("--bar", default="5m")
    b.add_argument("--bars", type=int, default=1500)
    common(b)
    strat(b)
    b.set_defaults(func=cmd_backtest)

    ss = sub.add_parser("session", help="distribuicao de N operacoes de X dolares")
    ss.add_argument("--hit", type=float, required=True, help="acertividade estimada (0-1)")
    ss.add_argument("--payoff", type=float, default=2.0)
    ss.add_argument("--stop", type=float, default=0.006, help="stop como fracao do preco")
    common(ss)
    ss.set_defaults(func=cmd_session)

    e = sub.add_parser("edge", help="acertividade minima exigida pelos custos")
    e.add_argument("--stop", type=float, default=0.006)
    e.add_argument("--payoff", type=float, default=2.0)
    common(e)
    e.set_defaults(func=cmd_edge)

    d = sub.add_parser("demo", help="roda tudo offline com dados sinteticos")
    d.add_argument("--bars", type=int, default=3000)
    d.add_argument("--seed", type=int, default=7)
    common(d)
    strat(d)
    d.set_defaults(func=cmd_demo)

    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except OKXError as exc:
        print(f"erro ao falar com a OKX: {exc}", file=sys.stderr)
        print("dica: sem rede liberada, use `python -m okx_ai demo`.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
