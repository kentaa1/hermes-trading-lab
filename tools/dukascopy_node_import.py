#!/usr/bin/env python3
"""
dukascopy_node_import.py — ÚNICO camino canónico de importación de tick data al laboratorio.

Este archivo es la única fuente de verdad para la importación de datos de Dukascopy
al laboratorio Hermes-Trading-Lab. Cualquier otro script que importe ticks desde
Dukascopy debe ser eliminado en favor de este.

Formato soportado: CSV de dukascopy-node (tick-level, bid/ask reales)
Schema destino: D-2-REV1 (symbol, ts, bid, ask, bid_vol, ask_vol)

Pipeline:
  1. Market calendar (skip sábados, domingos, feriados mayores sin llamar a API)
  2. Chunking: 1 chunk = 1 día. Max 3 reintentos con backoff solo para días de mercado.
  3. Checkpoint (import_progress_<symbol>.json, reanudable)
  4. Conversión (epoch ms → TIMESTAMPTZ UTC, rename columnas)
  5. Validación (nulos, precio > 0, spread > 0 y < 100 pips, vol ≥ 0, max 5% reject)
  6. Inserción deduplicada (ON CONFLICT DO NOTHING sobre symbol, ts)
  7. Manifest final (import_manifests/)
  8. DVC snapshot (dvc add duckdb/main.duckdb)
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import duckdb

# ═══════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    sys.path.insert(0, str(REPO_ROOT))
    from hermes_config import DUCKDB_PATH
    DEFAULT_DB_PATH = str(DUCKDB_PATH)
except (ImportError, AttributeError):
    DEFAULT_DB_PATH = str(REPO_ROOT / "duckdb" / "main.duckdb")

PROGRESS_DIR = REPO_ROOT
MANIFESTS_DIR = REPO_ROOT / "import_manifests"

MAX_RETRIES = 3
RETRY_BASE_SECONDS = 2.0
BATCH_SIZE = 5000
MAX_REJECT_RATE = 0.05
MAX_SPIPS = 100

MARKET_CLOSED_DAYS = {
    (1, 1),
    (12, 25),
}

DUKASCOPY_NODE_CMD = "dukascopy-node"


# ═══════════════════════════════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════════════════════════════


def is_market_closed(date: datetime) -> bool:
    if date.weekday() >= 5:
        return True
    if (date.month, date.day) in MARKET_CLOSED_DAYS:
        return True
    return False


def get_dukascopy_version() -> str:
    try:
        result = subprocess.run(
            [DUKASCOPY_NODE_CMD, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "UNKNOWN"


def check_dukascopy_available():
    if not shutil.which(DUKASCOPY_NODE_CMD):
        print(f"ERROR: {DUKASCOPY_NODE_CMD} no encontrado en PATH.")
        print("Instalar con: npm install -g dukascopy-node")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
# PROGRESS CHECKPOINT
# ═══════════════════════════════════════════════════════════════════


def load_progress(symbol: str) -> dict:
    progress_file = PROGRESS_DIR / f"import_progress_{symbol.lower()}.json"
    if progress_file.exists():
        with open(progress_file) as f:
            return json.load(f)
    return {"symbol": symbol, "chunks": {}}


def save_progress(progress: dict, symbol: str):
    progress_file = PROGRESS_DIR / f"import_progress_{symbol.lower()}.json"
    with open(progress_file, "w") as f:
        json.dump(progress, f, indent=2, default=str)


def set_chunk_status(progress: dict, date_str: str, status: str):
    progress["chunks"][date_str] = {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    save_progress(progress, progress["symbol"])


# ═══════════════════════════════════════════════════════════════════
# DESCARGA
# ═══════════════════════════════════════════════════════════════════


def download_chunk(instrument: str, date: datetime, output_dir: Path) -> Optional[Path]:
    date_str = date.strftime("%Y-%m-%d")
    output_file = output_dir / f"{instrument}-tick-{date_str}.csv"

    cmd = [
        DUKASCOPY_NODE_CMD,
        "-i", instrument,
        "--date-from", date_str,
        "--date-to", date_str,
        "--timeframe", "tick",
        "--format", "csv",
        "--volumes",
        "--directory", str(output_dir),
        "--silent",
    ]

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                proc.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                if attempt < MAX_RETRIES:
                    wait = RETRY_BASE_SECONDS * (2 ** (attempt - 1))
                    print(f"    Timeout. Retry {attempt}/{MAX_RETRIES} en {wait:.0f}s...")
                    time.sleep(wait)
                    continue
                print(f"    Timeout después de {MAX_RETRIES} reintentos.")
                return None

            if proc.returncode == 0 and output_file.exists():
                if output_file.stat().st_size > 0:
                    return output_file
                return None

            if attempt < MAX_RETRIES:
                wait = RETRY_BASE_SECONDS * (2 ** (attempt - 1))
                print(f"    Retry {attempt}/{MAX_RETRIES} en {wait:.0f}s...")
                time.sleep(wait)
        except Exception as e:
            print(f"    Error inesperado en descarga: {e}")
            break

    return None


# ═══════════════════════════════════════════════════════════════════
# PARSE Y VALIDACIÓN
# ═══════════════════════════════════════════════════════════════════


def parse_csv(csv_path: Path, symbol: str):
    rows: list = []
    total = 0
    rejects = 0

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            try:
                ts_ms = int(row["timestamp"])
                ask = float(row["askPrice"])
                bid = float(row["bidPrice"])
                ask_vol = float(row["askVolume"])
                bid_vol = float(row["bidVolume"])
            except (KeyError, ValueError, TypeError):
                rejects += 1
                continue

            if bid <= 0 or ask <= 0 or ask <= bid:
                rejects += 1
                continue
            spread = ask - bid
            if spread <= 0 or spread > MAX_SPIPS * 0.0001:
                rejects += 1
                continue
            if bid_vol < 0 or ask_vol < 0:
                rejects += 1
                continue

            ts_utc = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
            rows.append((symbol, ts_utc, bid, ask, bid_vol, ask_vol))

    return rows, rejects, total


# ═══════════════════════════════════════════════════════════════════
# INSERCIÓN
# ═══════════════════════════════════════════════════════════════════


def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ticks (
            symbol TEXT,
            ts TIMESTAMPTZ,
            bid DOUBLE,
            ask DOUBLE,
            bid_vol DOUBLE,
            ask_vol DOUBLE
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ticks_symbol_ts
        ON ticks (symbol, ts)
    """)


def insert_rows(conn, rows: list) -> int:
    conn.execute("BEGIN TRANSACTION")
    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        conn.executemany(
            """
            INSERT INTO ticks (symbol, ts, bid, ask, bid_vol, ask_vol)
            VALUES (?, ?::TIMESTAMPTZ, ?, ?, ?, ?)
            ON CONFLICT (symbol, ts) DO NOTHING
            """,
            batch,
        )
        inserted += len(batch)
    conn.execute("COMMIT")
    return inserted


# ═══════════════════════════════════════════════════════════════════
# MANIFEST Y DVC
# ═══════════════════════════════════════════════════════════════════


def write_manifest(
    symbol: str,
    start_date: str,
    end_date: str,
    chunks_ok: int,
    chunks_skipped: int,
    chunks_failed: int,
    total_ticks: int,
    elapsed_seconds: float,
):
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "symbol": symbol,
        "date_range": f"{start_date} to {end_date}",
        "dukascopy_node_version": get_dukascopy_version(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chunks": {
            "ok": chunks_ok,
            "skipped_market_closed": chunks_skipped,
            "failed_after_retries": chunks_failed,
            "total": chunks_ok + chunks_skipped + chunks_failed,
        },
        "total_ticks_inserted": total_ticks,
        "elapsed_seconds": round(elapsed_seconds, 1),
        "tool": "dukascopy-node (tick-level, bid/ask reales)",
        "schema": "D-2-REV1",
        "notes": (
            "Reimportación tras incidente INC_001. Fuente: dukascopy-node "
            "(tick-level real, bid/ask sin derivar). No comparable "
            "numéricamente con la base perdida — ver INC_001."
        ),
    }
    manifest_file = MANIFESTS_DIR / f"import_{symbol}_{start_date}_{end_date}.json"
    with open(manifest_file, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Manifest: {manifest_file}")
    return manifest_file


def dvc_snapshot(db_path: Path):
    try:
        result = subprocess.run(
            ["dvc", "add", str(db_path)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=120,
        )
        if result.returncode == 0:
            print("  DVC snapshot OK")
            return True
        print(f"  WARNING: dvc add falló: {result.stderr}")
        print("  Ejecutar manualmente: dvc add duckdb/main.duckdb")
        return False
    except FileNotFoundError:
        print("  WARNING: dvc no encontrado en PATH.")
        return False
    except subprocess.TimeoutExpired:
        print("  WARNING: dvc add timeout.")
        return False


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="Importa ticks de Dukascopy a DuckDB (canónico)"
    )
    parser.add_argument(
        "--symbol", default="EURUSD", help="Símbolo (default: EURUSD)"
    )
    parser.add_argument(
        "--from",
        dest="date_from",
        default="2015-01-01",
        help="Fecha inicio YYYY-MM-DD (default: 2015-01-01)",
    )
    parser.add_argument(
        "--to",
        dest="date_to",
        default="2017-12-31",
        help="Fecha fin YYYY-MM-DD (default: 2017-12-31)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help=f"Path DuckDB (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reimportar chunks ya marcados OK",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar chunks sin ejecutar nada",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directorio temporal para descargas (default: TEMP/dukascopy_<symbol>)",
    )
    args = parser.parse_args()

    # ── Prerrequisitos ──────────────────────────────────────────────
    check_dukascopy_available()

    symbol = args.symbol.upper()
    instrument = symbol.lower()
    db_path = Path(args.db) if args.db else Path(DEFAULT_DB_PATH)
    start_date = datetime.strptime(args.date_from, "%Y-%m-%d")
    end_date = datetime.strptime(args.date_to, "%Y-%m-%d")

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = (
            Path(os.environ.get("TEMP", "/tmp")) / f"dukascopy_{symbol}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    progress = load_progress(symbol)

    print(f"dukascopy_node_import — {symbol} {args.date_from} → {args.date_to}")
    print(f"  DB: {db_path}")
    print(f"  Instrument: {instrument}")
    print(f"  Output temp: {output_dir}")

    # ── Dry run ──────────────────────────────────────────────────────
    if args.dry_run:
        print(f"\n[DRY RUN] Chunks a procesar (1 día por chunk):")
        current = start_date
        market_days = 0
        while current <= end_date:
            chunk_key = current.strftime("%Y-%m-%d")
            existing = progress.get("chunks", {}).get(chunk_key, {}).get("status")
            if existing == "OK" and not args.force:
                print(f"  [{chunk_key}] SKIP (ya importado)")
            elif is_market_closed(current):
                print(f"  [{chunk_key}] SKIP (mercado cerrado)")
            else:
                print(f"  [{chunk_key}] PROCESS")
                market_days += 1
            current += timedelta(days=1)
        print(f"\n  Días de mercado a procesar: {market_days}")
        return

    # ── Pipeline ────────────────────────────────────────────────────
    t_start = time.time()
    chunks_ok = 0
    chunks_skipped = 0
    chunks_failed = 0
    total_ticks = 0

    current = start_date
    while current <= end_date:
        chunk_key = current.strftime("%Y-%m-%d")
        day_abbr = current.strftime("%a")

        # Checkpoint: saltar si ya OK (a menos que --force)
        existing = progress.get("chunks", {}).get(chunk_key, {}).get("status")
        if existing == "OK" and not args.force:
            chunks_ok += 1
            print(f"  [{chunk_key} {day_abbr}] SKIP (ya importado)")
            current += timedelta(days=1)
            continue

        # Market calendar: skip sin llamar a API
        if is_market_closed(current):
            chunks_skipped += 1
            set_chunk_status(progress, chunk_key, "SKIPPED_MARKET_CLOSED")
            print(f"  [{chunk_key} {day_abbr}] SKIPPED (mercado cerrado)")
            current += timedelta(days=1)
            continue

        # Descargar
        print(f"  [{chunk_key} {day_abbr}] descargando...", end=" ", flush=True)
        try:
            csv_path = download_chunk(instrument, current, output_dir)
        except Exception as e:
            print(f"ERROR EN DESCARGA: {e}")
            chunks_failed += 1
            set_chunk_status(progress, chunk_key, "FAILED_AFTER_RETRIES")
            current += timedelta(days=1)
            continue

        if csv_path is None:
            chunks_failed += 1
            set_chunk_status(progress, chunk_key, "FAILED_AFTER_RETRIES")
            print("FAILED (descarga vacía tras reintentos)")
            current += timedelta(days=1)
            continue

        # Parsear y validar
        rows, rejects, total_parsed = parse_csv(csv_path, symbol)
        reject_rate = rejects / total_parsed if total_parsed > 0 else 0

        if reject_rate > MAX_REJECT_RATE:
            chunks_failed += 1
            set_chunk_status(progress, chunk_key, "FAILED_AFTER_RETRIES")
            print(f"FAILED (reject rate {reject_rate:.1%} > {MAX_REJECT_RATE:.0%})")
            csv_path.unlink(missing_ok=True)
            current += timedelta(days=1)
            continue

        if not rows:
            chunks_skipped += 1
            set_chunk_status(progress, chunk_key, "SKIPPED_MARKET_CLOSED")
            print("SKIPPED (sin filas válidas)")
            csv_path.unlink(missing_ok=True)
            current += timedelta(days=1)
            continue

        # Insertar en DuckDB
        try:
            conn = duckdb.connect(str(db_path))
            ensure_table(conn)
            inserted = insert_rows(conn, rows)
            conn.close()
        except Exception as e:
            print(f"\nERROR: DuckDB no responde — {e}")
            print("ABORTANDO: Fallo total de base de datos.")
            sys.exit(1)

        chunks_ok += 1
        total_ticks += inserted
        set_chunk_status(progress, chunk_key, "OK")
        print(f"OK ({inserted} ticks)")

        csv_path.unlink(missing_ok=True)
        current += timedelta(days=1)

    elapsed = time.time() - t_start

    # ── Manifest ────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("Importación completada:")
    print(f"  Chunks OK: {chunks_ok}")
    print(f"  Chunks SKIPPED (mercado cerrado): {chunks_skipped}")
    print(f"  Chunks FAILED: {chunks_failed}")
    print(f"  Total ticks insertados: {total_ticks}")
    print(f"  Tiempo: {elapsed:.1f}s")

    write_manifest(
        symbol,
        args.date_from,
        args.date_to,
        chunks_ok,
        chunks_skipped,
        chunks_failed,
        total_ticks,
        elapsed,
    )

    # ── DVC Snapshot ────────────────────────────────────────────────
    print(f"\nCreando DVC snapshot...")
    dvc_snapshot(db_path)

    shutil.rmtree(output_dir, ignore_errors=True)

    print(f"\n{'=' * 60}")
    print("✅ Importación completa.")


if __name__ == "__main__":
    main()
