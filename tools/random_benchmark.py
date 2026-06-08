#!/usr/bin/env python3
"""
random_benchmark.py - Benchmark Aleatorio para Hermes-Trading-Lab

Genera N series de señales aleatorias con la misma estructura que una
estratega real (R:R fijo, misma restricción de sesión) y calcula la
distribución de PF resultante.

Uso:
    python random_benchmark.py --trials 1000 --trades 100 --rr 2.0 --winrate 0.45

IMPORTANTE: Este script genera señales con-winrate realista (45-55%)
pero con distribución de P&L aleatoria. No simula precios reales.
Para un benchmark más sofisticado, usar ticks reales como entrada.
"""

import argparse
import json
import random
import statistics
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone


@dataclass
class TradeResult:
    """Resultado de un trade individual."""
    entry_price: float = 0.0
    exit_price: float = 0.0
    direction: int = 0      # +1 long, -1 short
    sl_pips: float = 0.0
    tp_pips: float = 0.0
    pips_result: float = 0.0
    is_win: bool = False
    is_loss: bool = False
    is_be: bool = False     # break-even


@dataclass
class BenchmarkResult:
    """Resultado de una serie de benchmark."""
    trial_id: int = 0
    num_trades: int = 0
    num_wins: int = 0
    num_losses: int = 0
    num_be: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    profit_factor: float = 0.0
    winrate: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    max_drawdown_pct: float = 0.0  # estimación simple
    avg_win_pips: float = 0.0
    avg_loss_pips: float = 0.0
    expectancy_pips: float = 0.0


def generate_random_trades(
    num_trades: int,
    base_winrate: float,
    sl_pips: float,
    tp_pips: float,
    spread_pips: float = 1.0,
    slippage_pips: float = 0.3,
    long_bias: float = 0.5,
) -> list[TradeResult]:
    """
    Genera una serie de trades aleatorios.

    Args:
        num_trades: Número de trades a simular
        base_winrate: Winrate base antes de ajuste por sesión
        sl_pips: Stop loss en pips
        tp_pips: Take profit en pips
        spread_pips: Spread promedio en pips
        slippage_pips: Slippage promedio en pips
        long_bias: Proporción de trades long (0.5 = neutral)

    Returns:
        Lista de TradeResult
    """
    trades = []

    for _ in range(num_trades):
        # Determinar dirección
        direction = 1 if random.random() < long_bias else -1

        # Determinar si es win/loss (sin path dependency por simplicidad)
        is_win = random.random() < base_winrate
        is_loss = not is_win

        # Resultado en pips
        if is_win:
            pips_result = tp_pips - spread_pips - slippage_pips
        else:
            pips_result = -(sl_pips + spread_pips + slippage_pips)

        trade = TradeResult(
            direction=direction,
            sl_pips=sl_pips,
            tp_pips=tp_pips,
            pips_result=pips_result,
            is_win=is_win,
            is_loss=is_loss,
            is_be=(pips_result == 0),
        )
        trades.append(trade)

    return trades


def calculate_metrics(trades: list[TradeResult], initial_balance: float = 10000.0) -> BenchmarkResult:
    """Calcula métricas de una serie de trades."""
    num_wins = sum(1 for t in trades if t.is_win)
    num_losses = sum(1 for t in trades if t.is_loss)
    num_be = sum(1 for t in trades if t.is_be)

    wins_pips = [t.pips_result for t in trades if t.is_win]
    losses_pips = [abs(t.pips_result) for t in trades if t.is_loss]

    gross_profit = sum(wins_pips) if wins_pips else 0.0
    gross_loss = sum(losses_pips) if losses_pips else 0.0
    net_profit = gross_profit - gross_loss

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    winrate = num_wins / len(trades) if trades else 0.0

    # Rachas
    max_consec_wins = 0
    max_consec_losses = 0
    curr_wins = 0
    curr_losses = 0
    for t in trades:
        if t.is_win:
            curr_wins += 1
            curr_losses = 0
            max_consec_wins = max(max_consec_wins, curr_wins)
        elif t.is_loss:
            curr_losses += 1
            curr_wins = 0
            max_consec_losses = max(max_consec_losses, curr_losses)

    # Drawdown simple (asumiendo lot size fijo = 0.01, ~0.10 USD/pip)
    lot_size = 0.01
    pip_value = lot_size * 0.10  # ~0.10 USD por pip para EURUSD con 0.01 lot
    equity = initial_balance
    peak = equity
    max_dd_pct = 0.0
    for t in trades:
        equity += t.pips_result * pip_value
        if equity > peak:
            peak = equity
        dd_pct = (peak - equity) / peak * 100
        max_dd_pct = max(max_dd_pct, dd_pct)

    avg_win = statistics.mean(wins_pips) if wins_pips else 0.0
    avg_loss = statistics.mean(losses_pips) if losses_pips else 0.0
    expectancy = (winrate * avg_win) - ((1 - winrate) * avg_loss)

    return BenchmarkResult(
        num_trades=len(trades),
        num_wins=num_wins,
        num_losses=num_losses,
        num_be=num_be,
        gross_profit=round(gross_profit, 2),
        gross_loss=round(gross_loss, 2),
        net_profit=round(net_profit, 2),
        profit_factor=round(profit_factor, 4),
        winrate=round(winrate, 4),
        max_consecutive_wins=max_consec_wins,
        max_consecutive_losses=max_consec_losses,
        max_drawdown_pct=round(max_dd_pct, 2),
        avg_win_pips=round(avg_win, 2),
        avg_loss_pips=round(avg_loss, 2),
        expectancy_pips=round(expectancy, 2),
    )


def run_benchmark(
    num_trials: int,
    num_trades: int,
    sl_pips: float,
    tp_pips: float,
    base_winrate: float = 0.50,
    spread_pips: float = 1.0,
    slippage_pips: float = 0.3,
    seed: int | None = None,
) -> list[BenchmarkResult]:
    """Ejecuta el benchmark completo."""
    if seed is not None:
        random.seed(seed)

    results = []
    for i in range(num_trials):
        trades = generate_random_trades(
            num_trades=num_trades,
            base_winrate=base_winrate,
            sl_pips=sl_pips,
            tp_pips=tp_pips,
            spread_pips=spread_pips,
            slippage_pips=slippage_pips,
        )
        metrics = calculate_metrics(trades)
        metrics.trial_id = i + 1
        results.append(metrics)

    return results


def analyze_pf_distribution(results: list[BenchmarkResult]) -> dict:
    """Analiza la distribución de Profit Factor."""
    pfs = [r.profit_factor for r in results]

    if not pfs:
        return {}

    sorted_pfs = sorted(pfs)
    n = len(sorted_pfs)

    return {
        "count": n,
        "min": round(min(pfs), 4),
        "max": round(max(pfs), 4),
        "mean": round(statistics.mean(pfs), 4),
        "median": round(statistics.median(pfs), 4),
        "stdev": round(statistics.stdev(pfs), 4) if n > 1 else 0.0,
        "p5": round(sorted_pfs[int(n * 0.05)], 4),
        "p10": round(sorted_pfs[int(n * 0.10)], 4),
        "p25": round(sorted_pfs[int(n * 0.25)], 4),
        "p50": round(sorted_pfs[int(n * 0.50)], 4),
        "p75": round(sorted_pfs[int(n * 0.75)], 4),
        "p90": round(sorted_pfs[int(n * 0.90)], 4),
        "p95": round(sorted_pfs[int(n * 0.95)], 4),
        "pct_above_1_0": round(sum(1 for pf in pfs if pf > 1.0) / n * 100, 1),
        "pct_above_1_1": round(sum(1 for pf in pfs if pf > 1.1) / n * 100, 1),
    }


def print_report(results: list[BenchmarkResult], params: dict):
    """Imprime el reporte del benchmark."""
    pf_stats = analyze_pf_distribution(results)

    print("=" * 70)
    print("  RANDOM BENCHMARK — Hermes-Trading-Lab")
    print("=" * 70)
    print(f"\n  Parámetros:")
    print(f"    Trials:              {params['trials']}")
    print(f"    Trades por trial:     {params['num_trades']}")
    print(f"    Winrate base:        {params['winrate']:.0%}")
    print(f"    SL:                  {params['sl_pips']} pips")
    print(f"    TP:                  {params['tp_pips']} pips")
    print(f"    R:R:                 1:{params['tp_pips']/params['sl_pips']:.1f}")
    print(f"    Spread:              {params['spread_pips']} pips")
    print(f"    Slippage:            {params['slippage_pips']} pips")

    print(f"\n  Distribución de Profit Factor:")
    print(f"    Min:                 {pf_stats['min']}")
    print(f"    Max:                 {pf_stats['max']}")
    print(f"    Mean:                {pf_stats['mean']}")
    print(f"    Median:              {pf_stats['median']}")
    print(f"    Stdev:               {pf_stats['stdev']}")
    print(f"    Percentil 5:         {pf_stats['p5']}")
    print(f"    Percentil 10:        {pf_stats['p10']}")
    print(f"    Percentil 25:        {pf_stats['p25']}")
    print(f"    Percentil 50:        {pf_stats['p50']}")
    print(f"    Percentil 75:        {pf_stats['p75']}")
    print(f"    Percentil 90:        {pf_stats['p90']}")
    print(f"    Percentil 95:        {pf_stats['p95']}")
    print(f"    % PF > 1.0:          {pf_stats['pct_above_1_0']}%")
    print(f"    % PF > 1.1:          {pf_stats['pct_above_1_1']}%")

    print(f"\n  Regla de decisión:")
    print(f"    PF de la estrategia DEBE superar p95 = {pf_stats['p95']}")
    print(f"    para tener evidencia de edge sobre aleatorio.")

    print("\n" + "=" * 70)


def save_results(results: list[BenchmarkResult], params: dict, output_dir: Path):
    """Guarda resultados en JSON y CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON con parámetros y estadísticas
    pf_stats = analyze_pf_distribution(results)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "parameters": params,
        "pf_distribution": pf_stats,
        "summary": {
            "mean_pf": pf_stats["mean"],
            "median_pf": pf_stats["median"],
            "p95_pf": pf_stats["p95"],
            "pct_profitable": pf_stats["pct_above_1_0"],
        },
        "all_results": [asdict(r) for r in results],
    }
    json_path = output_dir / f"benchmark_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Resultados guardados: {json_path}")

    # CSV con datos por trial
    csv_path = output_dir / f"benchmark_{ts}.csv"
    with open(csv_path, "w") as f:
        if results:
            headers = list(asdict(results[0]).keys())
            f.write(",".join(headers) + "\n")
            for r in results:
                vals = [str(getattr(r, h)) for h in headers]
                f.write(",".join(vals) + "\n")
    print(f"  CSV guardado:         {csv_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Random Benchmark para Hermes-Trading-Lab",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Benchmark básico: 1000 trials, 100 trades, R:R 1:2, winrate 50%
  python random_benchmark.py

  # Con winrate 55% (estrategia que acierta más)
  python random_benchmark.py --winrate 0.55

  # Con más trades y R:R 1:1.5
  python random_benchmark.py --trades 200 --tp 75

  # Guardar resultados
  python random_benchmark.py --save --output-dir results/
        """,
    )
    parser.add_argument("--trials", type=int, default=1000, help="Número de trials (default: 1000)")
    parser.add_argument("--trades", type=int, default=100, help="Trades por trial (default: 100)")
    parser.add_argument("--sl", type=float, default=50.0, help="Stop Loss en pips (default: 50)")
    parser.add_argument("--tp", type=float, default=100.0, help="Take Profit en pips (default: 100)")
    parser.add_argument("--winrate", type=float, default=0.50, help="Winrate base 0-1 (default: 0.50)")
    parser.add_argument("--spread", type=float, default=1.0, help="Spread en pips (default: 1.0)")
    parser.add_argument("--slippage", type=float, default=0.3, help="Slippage en pips (default: 0.3)")
    parser.add_argument("--seed", type=int, default=42, help="Seed para reproducibilidad (default: 42)")
    parser.add_argument("--save", action="store_true", help="Guardar resultados en JSON/CSV")
    parser.add_argument("--output-dir", type=str, default="results/benchmarks", help="Directorio de salida")

    args = parser.parse_args()

    params = {
        "trials": args.trials,
        "num_trades": args.trades,
        "sl_pips": args.sl,
        "tp_pips": args.tp,
        "rr_ratio": round(args.tp / args.sl, 1),
        "winrate": args.winrate,
        "spread_pips": args.spread,
        "slippage_pips": args.slippage,
        "seed": args.seed,
    }

    results = run_benchmark(
        num_trials=args.trials,
        num_trades=args.trades,
        sl_pips=args.sl,
        tp_pips=args.tp,
        base_winrate=args.winrate,
        spread_pips=args.spread,
        slippage_pips=args.slippage,
        seed=args.seed,
    )

    print_report(results, params)

    if args.save:
        save_results(results, params, Path(args.output_dir))


if __name__ == "__main__":
    main()
