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
)
from tools.ohlcv_builder import build_ohlcv_h1

# -----------------------------------------------------------------------------
# Helper functions for hypothesis docstring handling
# -----------------------------------------------------------------------------

def _extract_yaml_from_docstring(file_path: Path) -> str:
    """Return the YAML block delimited by ``---`` lines in a file's top‑level docstring.

    The function reads the entire file, finds the first ``---`` line and the next
    ``---`` line and returns the raw YAML string between them.
    """
    content = file_path.read_text(encoding="utf-8")
    start = content.find("---")
    if start == -1:
        raise ValueError(f"No starting yaml delimiter found in {file_path}")
    end = content.find("---", start + 3)
    if end == -1:
        raise ValueError(f"No ending yaml delimiter found in {file_path}")
    yaml_block = content[start + 3 : end].strip()
    return yaml_block


def parse_hypothesis_docstring(signal_path: str) -> Dict[str, Any]:
    """Parse the YAML front‑matter inside the hypothesis signal file's docstring."""
    yaml_str = _extract_yaml_from_docstring(Path(signal_path))
    return yaml.safe_load(yaml_str) or {}


def update_hypothesis_docstring(signal_path: str, data: Dict[str, Any]) -> None:
    """Update the YAML block inside the hypothesis file's docstring.

    Only the keys ``dataset_used``, ``vectorbt_result`` and ``code_commit_hash``
    are overwritten/added; all other content stays unchanged.
    """
    path = Path(signal_path)
    text = path.read_text(encoding="utf-8")
    start = text.find("---")
    end = text.find("---", start + 3)
    if start == -1 or end == -1:
        raise ValueError("YAML delimiters not found in hypothesis file.")
    yaml_block = text[start + 3 : end].strip()
    existing = yaml.safe_load(yaml_block) or {}
    existing.update({
        "dataset_used": data.get("dataset_used"),
        "vectorbt_result": data.get("vectorbt_result"),
        "code_commit_hash": data.get("code_commit_hash"),
    })
    new_yaml = yaml.safe_dump(existing, sort_keys=False)
    new_text = text[: start + 3] + "\n" + new_yaml + "\n" + text[end:]
    path.write_text(new_text, encoding="utf-8")


def update_hypothesis_md(hypothesis_dir: str, data: Dict[str, Any]) -> None:
    """Update the front‑matter of ``hypothesis.md`` inside ``hypothesis_dir``."""
    md_path = Path(hypothesis_dir) / "hypothesis.md"
    if not md_path.is_file():
        raise FileNotFoundError(f"{md_path} does not exist")
    text = md_path.read_text(encoding="utf-8")
    start = text.find("---")
    end = text.find("---", start + 3)
    if start == -1 or end == -1:
        raise ValueError("Front‑matter delimiters not found in hypothesis.md")
    yaml_block = text[start + 3 : end].strip()
    existing = yaml.safe_load(yaml_block) or {}
    existing.update(data)
    new_yaml = yaml.safe_dump(existing, sort_keys=False)
    new_text = text[: start + 3] + "\n" + new_yaml + "\n" + text[end:]
    md_path.write_text(new_text, encoding="utf-8")

# -----------------------------------------------------------------------------
# Core pre‑screening logic
# -----------------------------------------------------------------------------

def _load_signal_module(signal_path: Path):
    """Dynamically import the ``generate_signals`` function from ``signal_path``.

    The module must expose ``generate_signals(ohlcv: pd.DataFrame)``.
    """
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
    """JSON encoder that converts NumPy types to native Python types."""

    def default(self, obj: Any) -> Any:  # noqa: D401
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super().default(obj)


def _write_log(hypothesis_id: str, entry: Dict[str, Any]) -> None:
    """Write a JSON log file under the hypothesis folder using ``NumpyEncoder``."""
    log_path = Path("hypotheses") / hypothesis_id / "vectorbt_log.json"
    log_path.write_text(json.dumps(entry, indent=2, cls=NumpyEncoder), encoding="utf-8")


def run_pre_screen(
    hypothesis_id: str, symbol: str, start_date: str, end_date: str
) -> Dict[str, Any]:
    """Execute the 15‑step pre‑screening pipeline for a hypothesis.

    Returns a dictionary with a summary of the result and relevant metrics.
    """
    # 1. Ensure repository is clean
    repo = git.Repo(search_parent_directories=True)
    if repo.is_dirty(untracked_files=True):
        raise RuntimeError(
            "Git repository has uncommitted changes. Please commit or stash them before running the pre‑screen."
        )

    # 2. Current commit hash
    commit_hash = repo.head.object.hexsha

    # 3. Parse hypothesis docstring
    signal_path = Path("hypotheses") / hypothesis_id / "signal.py"
    yaml_data = parse_hypothesis_docstring(str(signal_path))

    # 4. Connect to DuckDB
    con = duckdb.connect(database=DUCKDB_PATH, read_only=False)

    # 5. Build OHLCV data
    ohlcv = build_ohlcv_h1(con, symbol, start_date, end_date)
    if ohlcv.empty:
        raise RuntimeError("OHLCV builder returned empty dataframe")

    # 6. Start timer
    start_time = time.time()

    # 7. Generate signals
    generate_signals = _load_signal_module(signal_path)
    entries, exits = generate_signals(ohlcv)

    # 8. Validate output
    if not isinstance(entries, pd.Series) or not isinstance(exits, pd.Series):
        raise TypeError("generate_signals must return two pandas Series")
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
        _write_log(hypothesis_id, result)
        return result

    # 10. Build vectorbt portfolio
    mean_price = ohlcv["close"].mean()
    cost = (PROVISIONAL_COST_PIPS * 0.0001) / mean_price
    portfolio = vbt.Portfolio.from_signals(
        close=ohlcv["close"], entries=entries, exits=exits, fees=cost, init_cash=10_000
    )

    # 11. Extract performance metrics
    gross_profits = portfolio.trades.winning.pnl.sum()
    gross_losses = abs(portfolio.trades.losing.pnl.sum())
    pf = gross_profits / gross_losses if gross_losses > 0 else float("inf")
    dd = abs(portfolio.max_drawdown())
    trades = portfolio.trades.count()

    # 12. Minimum trades check
    if trades < MIN_TRADES:
        reason = f"Insufficient trades: {trades} < {MIN_TRADES}"
        result = {
            "hypothesis_id": hypothesis_id,
            "timestamp": pd.Timestamp.utcnow().isoformat(),
            "git_hash": commit_hash,
            "result": "rejected",
            "reason": reason,
            "metrics": {"trades": trades, "pf": pf, "dd": dd},
        }
        _write_log(hypothesis_id, result)
        return result

    # 13. Apply performance thresholds
    passed = pf >= PF_THRESHOLD and dd <= DD_THRESHOLD
    reason = "passed" if passed else "failed thresholds"

    # 14. Update documentation files
    update_data = {
        "dataset_used": f"{symbol}:{start_date}-{end_date}",
        "vectorbt_result": {"pf": float(pf), "dd": float(dd), "trades": int(trades)},
        "code_commit_hash": commit_hash,
    }
    update_hypothesis_docstring(str(signal_path), update_data)
    hypothesis_dir = Path("hypotheses") / hypothesis_id
    md_update = {"pf": float(pf), "dd": float(dd), "trades": int(trades), "status": reason}
    update_hypothesis_md(str(hypothesis_dir), md_update)

    # 15. Write final log entry
    log_entry = {
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
    _write_log(hypothesis_id, log_entry)

    # CLI friendly output
    print(
        json.dumps(
            {
                "hypothesis_id": hypothesis_id,
                "result": log_entry["result"],
                "pf": pf,
                "dd": dd,
                "trades": trades,
            },
            indent=2,
        )
    )
    return log_entry


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Pre‑screen wrapper for hypothesis testing")
    parser.add_argument("--hypothesis_id", required=True, help="Identifier of the hypothesis (e.g., HYP_001)")
    parser.add_argument("--symbol", required=True, help="Ticker symbol, e.g., EURUSD")
    parser.add_argument("--start_date", required=True, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end_date", required=True, help="End date in YYYY-MM-DD format")
    args = parser.parse_args()
    run_pre_screen(
        hypothesis_id=args.hypothesis_id,
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
    )


if __name__ == "__main__":
    _cli()
