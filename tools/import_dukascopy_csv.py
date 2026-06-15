#!/usr/bin/env python3
"""
import_dukascopy_csv.py — Importa CSV de Dukascopy (M1) a DuckDB.

Formato CSV tab-separated:
  <DATE>, <TIME>, <OPEN>, <HIGH>, <LOW>, <CLOSE>, <TICKVOL>, <VOL>, <SPREAD>
Ejemplo:
  2015.01.02	09:00:00	1.20538	1.20541	1.20509	1.20511	56	0	11

SPREAD en puntos (1 pip = 10 puntos para EURUSD).
Timestamps se almacenan como TIMESTAMP (naive) en UTC por convención.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Generator

import duckdb


def csv_row_generator(filepath: str, chunk_size: int) -> Generator[list[tuple], None, None]:
    """Lee el CSV en chunks. Cada tupla: (symbol, timestamp_str, bid, ask, bid_vol, ask_vol)."""
    import csv
    chunk: list[tuple] = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            timestamp_str = f"{row['<DATE>']} {row['<TIME>']}"
            timestamp_str = timestamp_str.replace('.', '-')
            close = float(row['<CLOSE>'])
            spread = float(row['<SPREAD>'])
            tickvol = float(row['<TICKVOL>'])
            bid = close
            ask = close + (spread / 100000.0)
            bid_vol = tickvol / 2.0
            ask_vol = tickvol / 2.0
            chunk.append(('EURUSD', timestamp_str, bid, ask, bid_vol, ask_vol))
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
    if chunk:
        yield chunk


def create_or_replace_table(conn: duckdb.DuckDBPyConnection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ticks (
            symbol VARCHAR,
            timestamp TIMESTAMPTZ,
            bid DOUBLE,
            ask DOUBLE,
            bid_vol DOUBLE,
            ask_vol DOUBLE
        )
    """)


def insert_chunk(conn: duckdb.DuckDBPyConnection, chunk: list[tuple]):
    conn.executemany(
        """
        INSERT INTO ticks (symbol, timestamp, bid, ask, bid_vol, ask_vol)
        VALUES (?, ?::TIMESTAMPTZ, ?, ?, ?, ?)
        """,
        chunk
    )


def main():
    parser = argparse.ArgumentParser(description="Importa CSV de Dukascopy a DuckDB")
    parser.add_argument("--csv-path", default="data/dukascopy/EURUSD_M1_2015_2026.csv",
                        help="Ruta al CSV tab-separated de Dukascopy")
    parser.add_argument("--db-path", default="duckdb/main.duckdb",
                        help="Ruta a la base DuckDB")
    parser.add_argument("--chunk-size", type=int, default=10000,
                        help="Registros por lote de inserción")
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    db_path = Path(args.db_path)

    if not csv_path.exists():
        print(f"ERROR: No se encuentra el archivo CSV: {csv_path}")
        sys.exit(1)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))

    create_or_replace_table(conn)
    # Limpiar tabla para importación limpia
    conn.execute("DELETE FROM ticks")

    print(f"Importando: {csv_path}")
    print(f"  Chunk size: {args.chunk_size:,}")
    print()

    total = 0
    start_time = time.time()
    last_progress = 0

    for chunk in csv_row_generator(str(csv_path), args.chunk_size):
        insert_chunk(conn, chunk)
        total += len(chunk)

        new_progress = total // 100000
        if new_progress > last_progress:
            elapsed = time.time() - start_time
            rate = total / elapsed if elapsed > 0 else 0
            print(f"  {total:>8,} filas — {elapsed:.0f}s — {rate:,.0f} filas/s")
            last_progress = new_progress

    elapsed = time.time() - start_time
    rate = total / elapsed if elapsed > 0 else 0
    print(f"\n  ✅ Importación completada en {elapsed:.1f}s")
    print(f"  Total registros insertados: {total:,}")
    print(f"  Tasa promedio: {rate:,.0f} filas/s")

    # Date range
    row = conn.execute("""
        SELECT MIN(timestamp), MAX(timestamp)
        FROM ticks
    """).fetchone()
    print(f"  Rango de fechas: {row[0]} → {row[1]}")

    # Schema verification
    print()
    print(conn.execute("DESCRIBE ticks").fetchdf().to_string(index=False))

    conn.close()


if __name__ == "__main__":
    main()
