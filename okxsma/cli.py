"""Varredura das 50 criptos mais líquidas da OKX com o setup SMA 8/21/200."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from . import okx
from .strategy import Config, Signal, Status, analyze

_HERE = os.path.dirname(os.path.abspath(__file__))
FALLBACK_PATH = os.path.join(_HERE, "symbols_fallback.txt")

STATUS_LABEL = {
    Status.SINAL: "SINAL",
    Status.REJEITOU_AGUARDA_CONFIRMACAO: "rejeitou/aguarda confirmação",
    Status.ROMPEU_AGUARDA_REJEICAO: "rompeu/aguarda rejeição",
    Status.TENDENCIA_SEM_ROMPIMENTO: "só tendência",
    Status.SEM_TENDENCIA: "sem tendência",
    Status.SEM_DADOS: "sem dados",
}
STATUS_ORDER = {s: i for i, s in enumerate([
    Status.SINAL,
    Status.REJEITOU_AGUARDA_CONFIRMACAO,
    Status.ROMPEU_AGUARDA_REJEICAO,
    Status.TENDENCIA_SEM_ROMPIMENTO,
    Status.SEM_TENDENCIA,
    Status.SEM_DADOS,
])}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="okx-sma",
        description="Varre os pares mais líquidos da OKX procurando o setup "
                    "SMA 8 (branca) / 21 (amarela) / 200 (roxa): rompimento da "
                    "amarela em tendência de alta, rejeição na volta e confirmação "
                    "no fechamento do candle, com volume acima da média.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-t", "--timeframe", default="1H",
                   help=f"timeframe do candle ({', '.join(okx.BARS)})")
    p.add_argument("-n", "--top", type=int, default=50,
                   help="quantos pares varrer, por volume de 24h")
    p.add_argument("-q", "--quote", default="USDT", help="moeda de cotação")
    p.add_argument("-s", "--symbols", nargs="+", metavar="PAR",
                   help="varre estes pares em vez do top N (ex.: BTC-USDT SOL-USDT)")
    p.add_argument("--min-vol-ratio", type=float, default=1.2,
                   help="volume do candle dividido pela média de 20")
    p.add_argument("--max-age", type=int, default=1,
                   help="idade máxima do sinal, em candles fechados")
    p.add_argument("--min-slope", type=float, default=0.0,
                   help="inclinação mínima da SMA 200 em %% (20 barras)")
    p.add_argument("--include-open-candle", action="store_true",
                   help="inclui o candle em formação (por padrão só candles fechados)")
    p.add_argument("--all", action="store_true",
                   help="mostra todos os pares, não só os que estão no setup")
    p.add_argument("--format", choices=["table", "json", "csv"], default="table")
    p.add_argument("--workers", type=int, default=4, help="requisições em paralelo")
    p.add_argument("--limit-candles", type=int, default=300,
                   help="candles baixados por par (máx. 300 na OKX)")
    return p


def resolve_symbols(args) -> List[str]:
    if args.symbols:
        return [s.upper() for s in args.symbols]
    try:
        syms = okx.top_symbols(args.top, args.quote)
        if syms:
            return syms
        raise okx.OKXError("lista de tickers vazia")
    except okx.OKXError as exc:
        print(f"[aviso] não consegui a lista ao vivo ({exc}); "
              f"usando a lista estática de {FALLBACK_PATH}", file=sys.stderr)
        return okx.fallback_symbols(FALLBACK_PATH, args.top)


def scan_symbol(symbol: str, args, cfg: Config) -> Signal:
    bar = okx.normalize_bar(args.timeframe)
    try:
        candles = okx.fetch_candles(symbol, bar, args.limit_candles,
                                    closed_only=not args.include_open_candle)
    except okx.OKXError as exc:
        return Signal(symbol, bar, Status.SEM_DADOS, price=0.0, notes=[str(exc)])
    return analyze(symbol, bar, candles, cfg)


def _fmt(value: Optional[float], digits: int = 6) -> str:
    if value is None:
        return "-"
    if value == 0:
        return "0"
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    if abs(value) >= 1:
        return f"{value:.4f}"
    return f"{value:.{digits}g}"


def print_table(signals: List[Signal], bar: str, show_all: bool) -> None:
    interesting = [s for s in signals
                   if show_all or s.status in (Status.SINAL,
                                               Status.REJEITOU_AGUARDA_CONFIRMACAO,
                                               Status.ROMPEU_AGUARDA_REJEICAO)]
    header = ("PAR", "STATUS", "PREÇO", "SMA8", "SMA21", "SMA200",
              "VOL×", "ENTRADA", "STOP", "ALVO 2R", "ALVO 3R", "SCORE")
    rows = []
    for s in interesting:
        vr = max([v for v in (s.vol_ratio_breakout, s.vol_ratio_confirm) if v is not None]
                 or [0.0])
        rows.append((
            s.symbol,
            STATUS_LABEL[s.status],
            _fmt(s.price), _fmt(s.sma_fast), _fmt(s.sma_mid), _fmt(s.sma_slow),
            f"{vr:.2f}x" if vr else "-",
            _fmt(s.entry), _fmt(s.stop), _fmt(s.target_2r), _fmt(s.target_3r),
            f"{s.score:.0f}" if s.status is Status.SINAL else "-",
        ))

    print(f"\nOKX · SMA 8/21/200 · timeframe {bar} · "
          f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC "
          f"· {len(signals)} pares varridos\n")
    if not rows:
        print("Nenhum par no setup agora. Use --all para ver o estágio de cada um.\n")
    else:
        widths = [max(len(str(r[i])) for r in (rows + [header])) for i in range(len(header))]
        line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(header))
        print(line)
        print("-" * len(line))
        for r in rows:
            print("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)))
        print()

    sinais = [s for s in signals if s.status is Status.SINAL]
    for s in sinais:
        quando = okx.ts_label(s.confirm_ts, bar) if s.confirm_ts else "-"
        print(f"→ {s.symbol}: confirmação no candle de {quando} "
              f"({s.bars_ago} candle(s) atrás), risco {s.risk_pct:.2f}% até o stop.")
    contagem = {}
    for s in signals:
        contagem[s.status] = contagem.get(s.status, 0) + 1
    resumo = ", ".join(f"{STATUS_LABEL[k]}: {v}" for k, v in
                       sorted(contagem.items(), key=lambda kv: STATUS_ORDER[kv[0]]))
    print(f"\nResumo — {resumo}")
    for s in signals:
        for note in s.notes:
            print(f"  · {s.symbol}: {note}")


def print_csv(signals: List[Signal]) -> None:
    fields = list(Signal("", "", Status.SEM_DADOS, 0.0).as_dict().keys())
    w = csv.DictWriter(sys.stdout, fieldnames=fields)
    w.writeheader()
    for s in signals:
        row = s.as_dict()
        row["notes"] = "; ".join(row["notes"])
        w.writerow(row)


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        bar = okx.normalize_bar(args.timeframe)
    except okx.OKXError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    cfg = Config(min_vol_ratio=args.min_vol_ratio,
                 max_age=max(0, args.max_age),
                 min_slope_pct=args.min_slope)

    symbols = resolve_symbols(args)
    if not symbols:
        print("erro: nenhum par para varrer", file=sys.stderr)
        return 1

    signals: List[Signal] = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for group in okx.chunked(symbols, max(1, args.workers)):
            signals.extend(pool.map(lambda s: scan_symbol(s, args, cfg), group))
            time.sleep(0.25)  # respeita o limite de 40 req / 2s da OKX

    signals.sort(key=lambda s: (STATUS_ORDER[s.status], -s.score, s.symbol))

    if args.format == "json":
        print(json.dumps([s.as_dict() for s in signals], indent=2, ensure_ascii=False))
    elif args.format == "csv":
        print_csv(signals)
    else:
        print_table(signals, bar, args.all)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
