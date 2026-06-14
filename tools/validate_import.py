#!/usr/bin/env python3
"""
validate_import.py — Validación de datos importados desde Dukascopy

Verifica integridad de ticks OHLCV construidos desde DuckDB.
Corrección D-2-REV1: no referencia columna 'vol' (inexistente).
"""

import sys
import duckdb
from pathlib import Path

def validate_ohlcv(conn: duckdb.DuckDBPyConnection, symbol: str, start_date: str, end_date: str) -> dict:
    """Valida el DataFrame OHLCV construido desde DuckDB."""
    
    query = f"""
        SELECT 
            COUNT(*) as total_bars,
            MIN(timestamp) as first_bar,
            MAX(timestamp) as last_bar,
            AVG(volume) as avg_volume,
            MIN(low) as min_low,
            MAX(high) as max_high,
            SUM(CASE WHEN open <= 0 OR high <= 0 OR low <= 0 OR close <= 0 THEN 1 ELSE 0 END) as invalid_prices,
            SUM(CASE WHEN high < low THEN 1 ELSE 0 END) as high_lt_low,
            SUM(CASE WHEN volume < 0 THEN 1 ELSE 0 END) as negative_volume
        FROM ohlcv
        WHERE symbol = '{symbol}'
        AND timestamp >= '{start_date}'
        AND timestamp <= '{end_date}'
    """
    
    result = conn.sql(query).fetchone()
    
    validation = {
        "total_bars": result[0],
        "first_bar": str(result[1]),
        "last_bar": str(result[2]),
        "avg_volume": float(result[3]) if result[3] else 0,
        "min_low": float(result[4]) if result[4] else 0,
        "max_high": float(result[5]) if result[5] else 0,
        "invalid_prices": result[6],
        "high_lt_low": result[7],
        "negative_volume": result[8],
        "valid": True,
        "errors": []
    }
    
    # Validaciones
    if validation["total_bars"] == 0:
        validation["valid"] = False
        validation["errors"].append("No se encontraron barras para el período especificado")
    
    if validation["invalid_prices"] > 0:
        validation["valid"] = False
        validation["errors"].append(f"{validation['invalid_prices']} barras con precios inválidos (<=0)")
    
    if validation["high_lt_low"] > 0:
        validation["valid"] = False
        validation["errors"].append(f"{validation['high_lt_low']} barras con high < low")
    
    if validation["negative_volume"] > 0:
        validation["valid"] = False
        validation["errors"].append(f"{validation['negative_volume']} barras con volumen negativo")
    
    return validation


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Valida datos OHLCV importados")
    parser.add_argument("--db", default="duckdb/main.duckdb", help="Path a DuckDB")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--start", default="2007-01-01")
    parser.add_argument("--end", default="2017-12-31")
    args = parser.parse_args()
    
    conn = duckdb.connect(args.db)
    result = validate_ohlcv(conn, args.symbol, args.start, args.end)
    
    print(f"Validación OHLCV: {args.symbol} {args.start} → {args.end}")
    print(f"  Barras totales: {result['total_bars']}")
    print(f"  Primera barra: {result['first_bar']}")
    print(f"  Última barra: {result['last_bar']}")
    print(f"  Volumen promedio: {result['avg_volume']:.2f}")
    print(f"  Precio mínimo: {result['min_low']:.5f}")
    print(f"  Precio máximo: {result['max_high']:.5f}")
    
    if result['valid']:
        print("  ✅ VALIDACIÓN OK")
    else:
        print("  ❌ VALIDACIÓN FALLIDA:")
        for err in result['errors']:
            print(f"    - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
