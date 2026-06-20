#!/usr/bin/env python3
"""
mt5_csv_import.py — Importa CSV de MT5/Descargas a DuckDB.

Formato origen: CSV tab-separado sin header (DATE, TIME, BID, ASK, LAST, VOLUME, FLAGS)
Schema destino: D-2-REV1 (symbol, ts, bid, ask, bid_vol, ask_vol)

Pipeline:
  1. Lectura por chunks (200K líneas por defecto)
  2. Parseo de cada línea (fecha MT5 → TIMESTAMPTZ, LAST fallback, volumen/2)
  3. Validación (precio > 0, ask >= bid, spread < 100 pips, max 5% reject)
  4. Inserción deduplicada (ON CONFLICT DO NOTHING sobre symbol, ts)
  5. Manifest final (import_manifests/)
  6. DVC snapshot (dvc add duckdb/main.duckdb)
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    sys.path.insert(0, str(REPO_ROOT))
    from hermes_config import DUCKDB_PATH
    DEFAULT_DB_PATH = str(DUCKDB_PATH)
except (ImportError, AttributeError):
    DEFAULT_DB_PATH = str(REPO_ROOT / "duckdb" / "main.duckdb")

MANIFESTS_DIR = REPO_ROOT / "import_manifests"

BATCH_SIZE = 5000
MAX_REJECT_RATE = 0.05
MAX_SPREAD_PIPS = 100
SYMBOL = "EURUSD"
PROGRESS_INTERVAL = 1_000_000


def parse_timestamp(date_str: str, time_str: str) -> datetime:
    """Convierte YYYY.MM.DD + HH:MM:SS.mmm → datetime UTC."""
    dt_str = f"{date_str} {time_str}"
    return datetime.strptime(dt_str, "%Y.%m.%d %H:%M:%S.%f").replace(tzinfo=timezone.utc)


def parse_csv_chunk(file_obj, chunk_size: int, skip_first_n: int = 0):
    """Lee un chunk de líneas desde file_obj (que ya está en la posición correcta).
    skip_first_n se resta de las líneas leídas para contadores cuando se usa en el primer chunk.
    Devuelve (rows, total_read, rejects, reject_reasons).
    """
    rows: list = []
    total_read = 0
    rejects = 0
    reject_reasons = {"empty_bid_ask": 0, "invalid_price": 0, "spread": 0}

    reader = csv.reader(file_obj, delimiter="\t")
    for line_no, parts in enumerate(reader):
        if len(parts) < 7:
            total_read += 1
            rejects += 1
            reject_reasons.setdefault("too_few_columns", 0)
            reject_reasons["too_few_columns"] += 1
            if total_read >= chunk_size:
                break
            continue

        date_str = parts[0].strip()
        time_str = parts[1].strip()
        bid_str = parts[2].strip()
        ask_str = parts[3].strip()
        last_str = parts[4].strip()
        vol_str = parts[5].strip()

        total_read += 1

        # Parsear BID y ASK (pueden estar vacíos individualmente)
        try:
            bid = float(bid_str) if bid_str else None
            ask = float(ask_str) if ask_str else None
        except ValueError:
            rejects += 1
            reject_reasons["invalid_price"] += 1
            if total_read >= chunk_size:
                break
            continue

        # Fallback: si uno está vacío, usar el otro como ambos
        if bid is None and ask is None:
            # Ambos vacíos — intentar LAST
            if last_str:
                try:
                    bid = ask = float(last_str)
                except ValueError:
                    rejects += 1
                    reject_reasons["empty_bid_ask"] += 1
                    if total_read >= chunk_size:
                        break
                    continue
            else:
                rejects += 1
                reject_reasons["empty_bid_ask"] += 1
                if total_read >= chunk_size:
                    break
                continue
        elif bid is None:
            bid = ask  # Solo ASK presente → usar ASK como precio
        elif ask is None:
            ask = bid  # Solo BID presente → usar BID como precio

        # Validación: bid > 0 y ask > 0
        if bid <= 0 or ask <= 0:
            rejects += 1
            reject_reasons["invalid_price"] += 1
            if total_read >= chunk_size:
                break
            continue

        # Validación: ask >= bid
        if ask < bid:
            rejects += 1
            reject_reasons["spread"] += 1
            if total_read >= chunk_size:
                break
            continue

        # Validación: spread < 100 pips (0.01 para EURUSD)
        spread = ask - bid
        if spread > MAX_SPREAD_PIPS * 0.0001:
            rejects += 1
            reject_reasons["spread"] += 1
            if total_read >= chunk_size:
                break
            continue

        # Volumen: dividir por 2 si tiene valor
        if vol_str:
            try:
                vol = float(vol_str) / 2.0
            except ValueError:
                vol = 0.0
        else:
            vol = 0.0

        ts = parse_timestamp(date_str, time_str)
        rows.append((SYMBOL, ts, bid, ask, vol, vol))

        if total_read >= chunk_size:
            break

    return rows, total_read, rejects, reject_reasons


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
    if not rows:
        return 0
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


def write_manifest(
    csv_path: str,
    total_read: int,
    total_inserted: int,
    total_rejects: int,
    reject_reasons: dict,
    elapsed_seconds: float,
    date_min: Optional[str],
    date_max: Optional[str],
):
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    source_name = Path(csv_path).stem
    manifest = {
        "source": str(csv_path),
        "symbol": SYMBOL,
        "schema": "D-2-REV1",
        "tool": "mt5_csv_import",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "date_range": {"min": date_min, "max": date_max},
        "total_read": total_read,
        "total_inserted": total_inserted,
        "total_rejects": total_rejects,
        "reject_reasons": reject_reasons,
        "elapsed_seconds": round(elapsed_seconds, 1),
    }
    manifest_file = MANIFESTS_DIR / f"import_{SYMBOL}_mt5_{source_name[:30]}.json"
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


def main():
    parser = argparse.ArgumentParser(
        description="Importa CSV de MT5/Descargas a DuckDB"
    )
    parser.add_argument(
        "--csv-path",
        default=r"C:\Users\David\Downloads\EURUSD_201112190000_202606192201.csv",
        help="Ruta al archivo CSV",
    )
    parser.add_argument(
        "--db",
        default=None,
        help=f"Path DuckDB (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=200000,
        help="Líneas por chunk (default: 200000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo contar filas sin insertar",
    )
    parser.add_argument(
        "--skip-lines",
        type=int,
        default=0,
        help="Líneas iniciales a saltar (default: 0)",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    db_path = Path(args.db) if args.db else Path(DEFAULT_DB_PATH)
    chunk_size = args.chunk_size
    skip_lines = args.skip_lines

    # ── Prerrequisitos ──────────────────────────────────────────────
    if not csv_path.exists():
        print(f"ERROR: Archivo no encontrado: {csv_path}")
        sys.exit(1)

    file_size_gb = csv_path.stat().st_size / (1024 ** 3)
    print(f"mt5_csv_import — {csv_path.name}")
    print(f"  Tamaño: {file_size_gb:.2f} GB")
    print(f"  DB: {db_path}")
    print(f"  Chunk size: {chunk_size:,}")
    print(f"  Skip lines: {skip_lines}")

    # ── Dry run: contar filas ───────────────────────────────────────
    if args.dry_run:
        print(f"\n[DRY RUN] Contando filas en {csv_path}...")
        t0 = time.time()
        total = 0
        with open(csv_path, encoding="utf-8") as f:
            if skip_lines:
                for _ in range(skip_lines):
                    next(f)
            for _ in f:
                total += 1
        elapsed = time.time() - t0
        print(f"  Total filas: {total:,}")
        print(f"  Tiempo: {elapsed:.1f}s")
        return

    # ── Inicializar DuckDB ──────────────────────────────────────────
    print(f"\nConectando a DuckDB...")
    try:
        conn = duckdb.connect(str(db_path))
        ensure_table(conn)
        conn.close()
    except Exception as e:
        print(f"ERROR: DuckDB no responde — {e}")
        print("ABORTANDO: Fallo total de base de datos.")
        sys.exit(1)

    # ── Pipeline ────────────────────────────────────────────────────
    t_start = time.time()
    total_read = 0
    total_inserted = 0
    total_rejects = 0
    reject_reasons_global: dict = {}
    date_min: Optional[str] = None
    date_max: Optional[str] = None

    print(f"\nIniciando importación...")
    print(f"{'━' * 60}")

    with open(csv_path, encoding="utf-8") as f:
        # Saltar header si existe (primera fila contiene <DATE>, <BID>, etc.)
        first_line = f.readline()
        if not first_line.startswith("<DATE>"):
            # No es header, volver al inicio
            f.seek(0)
        # Saltar líneas adicionales si el usuario lo pidió
        if skip_lines:
            for _ in range(skip_lines):
                next(f)

        chunk_num = 0
        while True:
            chunk_rows, chunk_read, chunk_rejects, chunk_reasons = parse_csv_chunk(
                f, chunk_size
            )

            if chunk_read == 0:
                break

            total_read += chunk_read
            total_rejects += chunk_rejects
            for reason, count in chunk_reasons.items():
                reject_reasons_global[reason] = (
                    reject_reasons_global.get(reason, 0) + count
                )

            # Validar tasa de rechazo
            reject_rate = chunk_rejects / chunk_read if chunk_read > 0 else 0
            if reject_rate > MAX_REJECT_RATE:
                print(
                    f"  [Chunk {chunk_num}] WARNING: reject rate "
                    f"{reject_rate:.1%} > {MAX_REJECT_RATE:.0%} ({chunk_rejects}/{chunk_read})"
                )

            # Insertar
            if chunk_rows:
                conn = duckdb.connect(str(db_path))
                inserted = insert_rows(conn, chunk_rows)
                conn.close()
                total_inserted += inserted

                # Trackear rango de fechas
                first_ts = chunk_rows[0][1]
                last_ts = chunk_rows[-1][1]
                if date_min is None or first_ts < date_min:
                    date_min = first_ts
                if date_max is None or last_ts > date_max:
                    date_max = last_ts

            chunk_num += 1

            # Progress indicator
            if total_read % PROGRESS_INTERVAL < chunk_size:
                elapsed = time.time() - t_start
                rate = total_read / elapsed if elapsed > 0 else 0
                print(
                    f"  Progreso: {total_read:,} líneas leídas, "
                    f"{total_inserted:,} insertadas, "
                    f"{total_rejects:,} rechazadas "
                    f"({rate:,.0f} líneas/s)"
                )

    elapsed = time.time() - t_start

    # ── Resumen ─────────────────────────────────────────────────────
    print(f"{'━' * 60}")
    print("Importación completada:")
    print(f"  Total leído: {total_read:,}")
    print(f"  Total insertado: {total_inserted:,}")
    print(f"  Total rechazado: {total_rejects:,}")
    print(f"  Rechazos por razón: {reject_reasons_global}")
    print(f"  Rango fechas: {date_min} → {date_max}")
    print(f"  Tiempo total: {elapsed:.1f}s")

    # ── Manifest ────────────────────────────────────────────────────
    write_manifest(
        str(csv_path),
        total_read,
        total_inserted,
        total_rejects,
        reject_reasons_global,
        elapsed,
        date_min.isoformat() if date_min else None,
        date_max.isoformat() if date_max else None,
    )

    # ── DVC Snapshot ────────────────────────────────────────────────
    print(f"\nCreando DVC snapshot...")
    dvc_snapshot(db_path)

    print(f"\n{'=' * 60}")
    print("Importación finalizada.")


if __name__ == "__main__":
    main()
