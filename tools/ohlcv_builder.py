#!/usr/bin/env python3
"""
ohlcv_builder.py — Construcción de velas OHLCV H1 desde ticks en DuckDB

Especificación P2:
- Mid price = (bid + ask) / 2.0
- Timeframe H1 alineado a UTC
- Volumen = SUM(bid_vol + ask_vol)
- Gaps no se interpolan
- Output: DataFrame con open, high, low, close, volume + DatetimeIndex UTC
"""

import duckdb
import pandas as pd
from pathlib import Path


def build_ohlcv_h1(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    Construye velas OHLCV H1 desde ticks en DuckDB.
    
    Args:
        conn: Conexión a DuckDB
        symbol: Símbolo (ej. EURUSD)
        start_date: Fecha inicio (YYYY-MM-DD)
        end_date: Fecha fin (YYYY-MM-DD)
    
    Returns:
        DataFrame con columnas [open, high, low, close, volume]
        Index: DatetimeIndex UTC
    """
    
    query = f"""
        WITH ranked AS (
            SELECT 
                date_trunc('hour', timestamp) as hour,
                (bid + ask) / 2.0 as mid_price,
                bid_vol + ask_vol as vol,
                ROW_NUMBER() OVER (PARTITION BY date_trunc('hour', timestamp) ORDER BY timestamp ASC) as rn_asc,
                ROW_NUMBER() OVER (PARTITION BY date_trunc('hour', timestamp) ORDER BY timestamp DESC) as rn_desc
            FROM ticks
            WHERE symbol = '{symbol}'
            AND timestamp >= '{start_date}'::TIMESTAMP
            AND timestamp <= '{end_date}'::TIMESTAMP
            AND bid > 0 AND ask > 0 AND ask >= bid
        ),
        first_last AS (
            SELECT hour, mid_price as open_price
            FROM ranked WHERE rn_asc = 1
        ),
        last_vals AS (
            SELECT hour, mid_price as close_price
            FROM ranked WHERE rn_desc = 1
        )
        SELECT 
            r.hour as timestamp,
            f.open_price as open,
            MAX(r.mid_price) as high,
            MIN(r.mid_price) as low,
            l.close_price as close,
            SUM(r.vol) as volume
        FROM ranked r
        JOIN first_last f ON r.hour = f.hour
        JOIN last_vals l ON r.hour = l.hour
        GROUP BY r.hour, f.open_price, l.close_price
        ORDER BY r.hour
    """
    
    df = conn.sql(query).fetchdf()
    
    if df.empty:
        return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
    
    # Establecer índice de timestamp UTC
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.set_index('timestamp')
    df.index.name = 'timestamp'
    
    # Asegurar tipos correctos
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Eliminar filas con NaN
    df = df.dropna()
    
    return df


def validate_ohlcv(df: pd.DataFrame) -> dict:
    """Valida el DataFrame OHLCV construido."""
    
    validation = {
        "total_bars": len(df),
        "empty": df.empty,
        "invalid_prices": 0,
        "high_lt_low": 0,
        "negative_volume": 0,
        "valid": True,
        "errors": []
    }
    
    if df.empty:
        validation["valid"] = False
        validation["errors"].append("DataFrame vacío")
        return validation
    
    # Validar precios inválidos
    for col in ['open', 'high', 'low', 'close']:
        invalid = (df[col] <= 0).sum()
        validation["invalid_prices"] += int(invalid)
    
    # Validar high < low
    validation["high_lt_low"] = int((df['high'] < df['low']).sum())
    
    # Validar volumen negativo
    validation["negative_volume"] = int((df['volume'] < 0).sum())
    
    # Determinar validez
    if validation["invalid_prices"] > 0:
        validation["valid"] = False
        validation["errors"].append(f"{validation['invalid_prices']} barras con precios inválidos")
    
    if validation["high_lt_low"] > 0:
        validation["valid"] = False
        validation["errors"].append(f"{validation['high_lt_low']} barras con high < low")
    
    if validation["negative_volume"] > 0:
        validation["valid"] = False
        validation["errors"].append(f"{validation['negative_volume']} barras con volumen negativo")
    
    return validation


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Construye OHLCV H1 desde DuckDB")
    parser.add_argument("--db", default="duckdb/main.duckdb")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--start", default="2007-01-01")
    parser.add_argument("--end", default="2017-12-31")
    parser.add_argument("--output", default=None, help="Output CSV path")
    
    args = parser.parse_args()
    
    conn = duckdb.connect(args.db)
    
    print(f"Construyendo OHLCV H1: {args.symbol} {args.start} → {args.end}")
    df = build_ohlcv_h1(conn, args.symbol, args.start, args.end)
    
    print(f"  Barras construidas: {len(df)}")
    
    if not df.empty:
        validation = validate_ohlcv(df)
        print(f"  Validación: {'✅ OK' if validation['valid'] else '❌ FALLIDA'}")
        if not validation['valid']:
            for err in validation['errors']:
                print(f"    - {err}")
        
        if args.output:
            df.to_csv(args.output)
            print(f"  Guardado: {args.output}")
    else:
        print("  ⚠️ No se construyeron barras (datos vacíos)")
