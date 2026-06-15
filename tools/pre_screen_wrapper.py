import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict

import duckdb
import git
import numpy as np
import pandas as pd
import yaml
import vectorbt as vbt

from hermes_config import (
    PROVISIONAL_COST_PIPS,
    MIN_TRADES,
    PF_THRESHOLD,
    DD_THRESHOLD,
    T_VECTORBTV,
    DUCKDB_PATH,
    DATASET_PRESCREENING_START,
    DATASET_PRESCREENING_END,
    DATASET_RESEARCH_START,
    DATASET_RESEARCH_END,
    DATASET_VALIDATION_START,
    DATASET_VALIDATION_END,
    DATASET_LOCKBOX_START,
    DATASET_LOCKBOX_END,
    DATASET_HOLDOUT_START,
)
from tools.ohlcv_builder import build_ohlcv_h1
from tools.yaml_doc_manager import extract_yaml_docstring, update_yaml_docstring, to_native


def parse_hypothesis_docstring(signal_path: str) -> Dict[str, Any]:
    return extract_yaml_docstring(Path(signal_path))


def update_hypothesis_docstring(signal_path: str, data: Dict[str, Any]) -> None:
    update_yaml_docstring(signal_path, data)


def update_hypothesis_md(hypothesis_dir: str, data: Dict[str, Any]) -> None:
    md_path = Path(hypothesis_dir) / "hypothesis.md"
    if not md_path.is_file():
        raise FileNotFoundError(f"{md_path} does not exist")
    text = md_path.read_text(encoding="utf-8")
    start = text.find("---")
    end = text.find("---", start + 3)
    if start == -1 or end == -1:
        raise ValueError("Front-matter delimiters not found in hypothesis.md")
    yaml_block = text[start + 3 : end].strip()
    existing = yaml.safe_load(yaml_block) or {}
    existing.update(data)
    existing = to_native(existing)
    new_yaml = yaml.safe_dump(existing, sort_keys=False)
    new_text = text[: start + 3] + "\n" + new_yaml + "\n" + text[end:]
    md_path.write_text(new_text, encoding="utf-8")


def _load_signal_module(signal_path: Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("signal_module", str(signal_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import module from {signal_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["signal_module"] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "generate_signals"):
        raise AttributeError("generate_signals function not found in signal module")
    return module.generate_signals


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super().default(obj)


def _write_log(hypothesis_id: str, entry: Dict[str, Any]) -> None:
    log_path = Path("hypotheses") / hypothesis_id / "vectorbt_log.json"
    log_path.write_text(json.dumps(entry, indent=2, cls=NumpyEncoder), encoding="utf-8")


def _update_docs_and_log(signal_path, hypothesis_id, symbol, start_date, end_date, commit_hash, result):
    update_data = {
        "dataset_used": f"{symbol}:{start_date}-{end_date}",
        "vectorbt_result": {
            "pf": result.get("metrics", {}).get("pf"),
            "dd": result.get("metrics", {}).get("dd"),
            "trades": result.get("metrics", {}).get("trades"),
        },
        "code_commit_hash": commit_hash,
    }
    update_data = to_native(update_data)
    update_hypothesis_docstring(str(signal_path), update_data)
    hypothesis_dir = Path("hypotheses") / hypothesis_id
    md_update = {
        "pf": result.get("metrics", {}).get("pf"),
        "dd": result.get("metrics", {}).get("dd"),
        "trades": result.get("metrics", {}).get("trades"),
        "status": result.get("reason"),
    }
    update_hypothesis_md(str(hypothesis_dir), md_update)
    _write_log(hypothesis_id, result)
    print(json.dumps({
        "hypothesis_id": hypothesis_id,
        "result": result["result"],
        "pf": result.get("metrics", {}).get("pf"),
        "dd": result.get("metrics", {}).get("dd"),
        "trades": result.get("metrics", {}).get("trades"),
    }, indent=2, cls=NumpyEncoder))


def run_pre_screen(hypothesis_id: str, symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
    # 1. Git limpio
    repo = git.Repo(search_parent_directories=True)
    if repo.is_dirty(untracked_files=True):
        raise RuntimeError("Git repository has uncommitted changes. Commit or stash before running.")

    # 2. Commit hash
    commit_hash = repo.head.object.hexsha

    # 2.5 VALIDACIÓN DE FRONTERAS DE DATASET
    if not (DATASET_PRESCREENING_START <= start_date <= DATASET_PRESCREENING_END):
        raise RuntimeError(
            f"start_date {start_date} fuera del rango de pre-screening "
            f"[{DATASET_PRESCREENING_START}, {DATASET_PRESCREENING_END}]. "
            f"El wrapper no opera sobre Research, Validation, Lockbox ni Holdout."
        )
    if not (DATASET_PRESCREENING_START <= end_date <= DATASET_PRESCREENING_END):
        raise RuntimeError(
            f"end_date {end_date} fuera del rango de pre-screening "
            f"[{DATASET_PRESCREENING_START}, {DATASET_PRESCREENING_END}]. "
            f"Historical Stress disponible: {DATASET_PRESCREENING_START} a {DATASET_PRESCREENING_END}."
        )
    print(f"  ✓ Rango validado: {start_date} a {end_date} dentro de Historical Stress [{DATASET_PRESCREENING_START}, {DATASET_PRESCREENING_END}]")

    # 3. Parsear docstring YAML
    signal_path = Path("hypotheses") / hypothesis_id / "signal.py"
    yaml_data = parse_hypothesis_docstring(str(signal_path))

    # 4. DuckDB
    con = duckdb.connect(database=DUCKDB_PATH, read_only=False)

    # 5. Construir OHLCV
    ohlcv = build_ohlcv_h1(con, symbol, start_date, end_date)
    if ohlcv.empty:
        raise RuntimeError("OHLCV builder returned empty dataframe")

    # 6. Timer
    start_time = time.time()

    # 7. Generar señales
    generate_signals = _load_signal_module(signal_path)
    signal_output = generate_signals(ohlcv)

    # 8. Validar output
    if not isinstance(signal_output, (list, tuple)) or len(signal_output) != 2:
        raise ValueError("generate_signals must return a tuple/list of (entries, exits)")
    entries, exits = signal_output
    if not isinstance(entries, pd.Series) or not isinstance(exits, pd.Series):
        raise TypeError("entries and exits must be pandas Series")
    if not entries.index.equals(exits.index) or not entries.index.equals(ohlcv.index):
        raise ValueError("Series indices must match OHLCV index")
    if entries.dtype != bool:
        entries = entries.astype(bool)
    if exits.dtype != bool:
        exits = exits.astype(bool)

    # 9. Timeout check
    elapsed = time.time() - start_time
    if elapsed > T_VECTORBTV:
        reason = f"Timeout after {elapsed:.2f}s (limit {T_VECTORBTV}s)"
        result = {
            "hypothesis_id": hypothesis_id,
            "timestamp": pd.Timestamp.utcnow().isoformat(),
            "git_hash": commit_hash,
            "result": "timeout",
            "reason": reason,
            "execution_time_seconds": round(elapsed, 2),
        }
        _update_docs_and_log(signal_path, hypothesis_id, symbol, start_date, end_date, commit_hash, result)
        return result

    # 10. Portfolio vectorbt
    mean_price = ohlcv["close"].mean()
    cost = (PROVISIONAL_COST_PIPS * 0.0001) / mean_price
    portfolio = vbt.Portfolio.from_signals(
        close=ohlcv["close"], entries=entries, exits=exits, fees=cost, init_cash=10_000
    )

    # 11. Métricas
    gross_profits = portfolio.trades.winning.pnl.sum()
    gross_losses = abs(portfolio.trades.losing.pnl.sum())
    pf = gross_profits / gross_losses if gross_losses > 0 else float("inf")
    dd = abs(portfolio.max_drawdown())
    trades = portfolio.trades.count()

    # 12. Minimum trades
    if trades < MIN_TRADES:
        reason = f"Insufficient trades: {trades} < {MIN_TRADES}"
        result = {
            "hypothesis_id": hypothesis_id,
            "timestamp": pd.Timestamp.utcnow().isoformat(),
            "git_hash": commit_hash,
            "result": "rejected",
            "reason": reason,
            "metrics": {"trades": trades, "pf": float(pf), "dd": float(dd)},
        }
        _update_docs_and_log(signal_path, hypothesis_id, symbol, start_date, end_date, commit_hash, result)
        return result

    # 13. Umbrales
    passed = pf >= PF_THRESHOLD and dd <= DD_THRESHOLD
    reason = "passed" if passed else "failed thresholds"

    # 14-15. Actualizar docs y log
    result = {
        "hypothesis_id": hypothesis_id,
        "timestamp": pd.Timestamp.utcnow().isoformat(),
        "git_hash": commit_hash,
        "result": "accepted" if passed else "rejected",
        "reason": reason,
        "metrics": {"pf": float(pf), "dd": float(dd), "trades": int(trades)},
        "cost_applied": cost,
        "data_range": {"start": start_date, "end": end_date},
        "total_bars": len(ohlcv),
        "execution_time_seconds": round(elapsed, 2),
    }
    _update_docs_and_log(signal_path, hypothesis_id, symbol, start_date, end_date, commit_hash, result)
    return result


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Pre-screen wrapper for hypothesis testing")
    parser.add_argument("--hypothesis_id", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start_date", required=True)
    parser.add_argument("--end_date", required=True)
    args = parser.parse_args()
    run_pre_screen(args.hypothesis_id, args.symbol, args.start_date, args.end_date)


if __name__ == "__main__":
    _cli()
