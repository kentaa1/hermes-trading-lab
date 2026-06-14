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
    """Return the YAML block that is delimited by ``---`` lines in a file's
    top‑level docstring.

    The function reads the file, looks for the first occurrence of a line that
    contains only three dashes, then captures everything until the next line of
    three dashes. The returned string is the raw YAML content.
    """
    content = file_path.read_text(encoding='utf-8')
    start = content.find('---')
    if start == -1:
        raise ValueError(f'No starting yaml delimiter found in {file_path}')
    end = content.find('---', start + 3)
    if end == -1:
        raise ValueError(f'No ending yaml delimiter found in {file_path}')
    yaml_block = content[start + 3 : end].strip()
    lines = yaml_block.split('\n')
    # Find base indentation from first non‑empty indented line
    base_indent = None
    for line in lines:
        stripped = line.lstrip()
        if stripped and not stripped.startswith('#'):
            indent = len(line) - len(stripped)
            if indent > 0:
                base_indent = indent
                break
    if base_indent:
        yaml_block = '\n'.join(
            line[base_indent:] if len(line) >= base_indent and line[:base_indent].strip() == '' else line
            for line in lines
        )
    return yaml_block.strip()


def parse_hypothesis_docstring(signal_path: str) -> Dict[str, Any]:
    """Parse the YAML front‑matter inside the ``signal_path`` file's docstring.

    Args:
        signal_path: Path to the hypothesis signal Python file.

    Returns:
        Dictionary representation of the YAML block.
    """
    yaml_str = _extract_yaml_from_docstring(Path(signal_path))
    return yaml.safe_load(yaml_str) or {}


def update_hypothesis_docstring(signal_path: str, data: Dict[str, Any]) -> None:
    """Update the YAML block inside the hypothesis file's docstring.

    The keys ``dataset_used``, ``vectorbt_result`` and ``code_commit_hash`` are
    replaced/added with the values from ``data``. All other content remains
    untouched.
    """
    path = Path(signal_path)
    text = path.read_text(encoding="utf-8")
    start = text.find("---")
    end = text.find("---", start + 3)
    if start == -1 or end == -1:
        raise ValueError("YAML delimiters not found in hypothesis file.")
    # Load existing yaml, update, then dump back
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
    """Update the front‑matter of ``hypothesis.md`` inside ``hypothesis_dir``.

    Only the keys that exist in the provided ``data`` are updated; others stay
    unchanged.
    """
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
    The module is expected to expose ``generate_signals(ohlcv: pd.DataFrame)``.
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


def run_pre_screen(hypothesis_id: str, symbol: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """Execute the 15‑step pre‑screening pipeline for a given hypothesis.

    Returns a dictionary with the result summary and metrics.
    """
    # 1. Ensure a clean git repo
    repo = git.Repo(search_parent_directories=True)
    if repo.is_dirty(untracked_files=True):
        raise RuntimeError("Git repository has uncommitted changes. Please commit or stash them before running the pre‑screen.")

    # 2. Current commit hash
    commit_hash = repo.head.object.hexsha

    # 3. Parse hypothesis docstring YAML
    signal_path = Path('hypotheses') / hypothesis_id / 'signal.py'
    yaml_data = parse_hypothesis_docstring(str(signal_path))

    # 4. Verify DuckDB availability
    con = duckdb.connect(database=DUCKDB_PATH, read_only=False)

    # 5. Build OHLCV data
    ohlcv = build_ohlcv_h1(con, symbol, start_date, end_date)
    if ohlcv.empty:
        raise RuntimeError("OHLCV builder returned empty dataframe")

    # 6. Start timer
    start_time = time.time()

    # 7. Generate signals via imported function
    generate_signals = _load_signal_module(signal_path)
    signal_output = generate_signals(ohlcv)

    # 8. Validate output – expecting two boolean Series with equal index
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

    # 9. Timeout check (T_VECTORBTV seconds)
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
    mean_price = ohlcv['close'].mean()
    cost = (PROVISIONAL_COST_PIPS * 0.0001) / mean_price
    portfolio = vbt.Portfolio.from_signals(
        close=ohlcv["close"],
        entries=entries,
        exits=exits,
        fees=cost,
        init_cash=10_000,
    )

    # 11. Extract performance metrics
    # Calculate profit factor
    gross_profits = portfolio.trades.winning.pnl.sum()
    gross_losses = abs(portfolio.trades.losing.pnl.sum())
    pf = gross_profits / gross_losses if gross_losses > 0 else float('inf')
    # Drawdown absolute value
    dd = abs(portfolio.max_drawdown())
    # Number of trades
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

    # 13. Apply thresholds
    passed = pf >= PF_THRESHOLD and dd <= DD_THRESHOLD
    reason = "passed" if passed else "failed thresholds"

    # 14. Update docstring and markdown
    update_data = {
        "dataset_used": f"{symbol}:{start_date}-{end_date}",
        "vectorbt_result": {"pf": float(pf), "dd": float(dd), "trades": int(trades)},
        "code_commit_hash": commit_hash,
    }
    update_hypothesis_docstring(str(signal_path), update_data)
    hypothesis_dir = Path("hypotheses") / hypothesis_id
    md_update = {"pf": float(pf), "dd": float(dd), "trades": int(trades), "status": reason}
    update_hypothesis_md(str(hypothesis_dir), md_update)

    # 15. Write log JSON
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

    # Print summary for CLI
    print(json.dumps({"hypothesis_id": hypothesis_id, "result": log_entry["result"], "pf": pf, "dd": dd, "trades": trades}, indent=2))
    return log_entry


def _write_log(hypothesis_id: str, entry: Dict[str, Any]) -> None:
    """Write a JSON log file under the hypothesis folder.
    """
    log_path = Path("hypotheses") / hypothesis_id / "vectorbt_log.json"
    log_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")


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
