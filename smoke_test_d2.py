#!/usr/bin/env python3
"""Smoke test D-2-REV1 con datos sintéticos"""
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path

print("🧪 Smoke test D-2-REV1 con datos sintéticos")
print("=" * 60)

db_path = Path("data/duckdb_smoke.duckdb")
db_path.unlink(missing_ok=True)
conn = duckdb.connect(str(db_path))

# Crear tabla de ticks (sin columna 'vol')
conn.sql("""
    CREATE TABLE ticks (
        symbol VARCHAR,
        timestamp TIMESTAMPTZ,
        bid DOUBLE,
        ask DOUBLE,
        bid_vol DOUBLE,
        ask_vol DOUBLE
    )
""")

# Insertar ticks sintéticos
np.random.seed(42)
base_time = pd.Timestamp("2020-01-01 00:00:00", tz="UTC")
n_ticks = 3600
timestamps = [base_time + pd.Timedelta(seconds=i) for i in range(n_ticks)]
base_price = 1.1000
prices = base_price + np.cumsum(np.random.randn(n_ticks) * 0.0001)
bids = prices - 0.00005
asks = prices + 0.00005
bid_vols = np.random.randint(1, 100, n_ticks).astype(float)
ask_vols = np.random.randint(1, 100, n_ticks).astype(float)

df = pd.DataFrame({
    "symbol": "EURUSD",
    "timestamp": timestamps,
    "bid": bids,
    "ask": asks,
    "bid_vol": bid_vols,
    "ask_vol": ask_vols
})
conn.sql("INSERT INTO ticks SELECT * FROM df")
print(f"  ✅ {n_ticks} ticks insertados")

# Verificar schema
schema = conn.sql("DESCRIBE ticks").fetchall()
col_names = [row[0] for row in schema]
print(f"  ✅ Schema: {col_names}")
assert "vol" not in col_names, "Columna 'vol' no debería existir"
assert "bid_vol" in col_names, "Columna 'bid_vol' debe existir"
assert "ask_vol" in col_names, "Columna 'ask_vol' debe existir"

# Construir OHLCV H1
ohlcv_query = """
    WITH ranked AS (
        SELECT 
            date_trunc('hour', timestamp) as hour,
            (bid + ask) / 2.0 as mid_price,
            bid_vol + ask_vol as vol,
            ROW_NUMBER() OVER (PARTITION BY date_trunc('hour', timestamp) ORDER BY timestamp ASC) as rn_asc,
            ROW_NUMBER() OVER (PARTITION BY date_trunc('hour', timestamp) ORDER BY timestamp DESC) as rn_desc
        FROM ticks
        WHERE symbol = 'EURUSD'
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
        r.hour,
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
ohlcv = conn.sql(ohlcv_query).fetchdf()
ohlcv = ohlcv.rename(columns={"hour": "timestamp"})
ohlcv["timestamp"] = pd.to_datetime(ohlcv["timestamp"], utc=True)
ohlcv = ohlcv.set_index("timestamp")

print(f"  ✅ OHLCV construido: {len(ohlcv)} barras")

# Validar
assert isinstance(ohlcv.index, pd.DatetimeIndex)
assert ohlcv.index.tz is not None
assert len(ohlcv) > 0
assert (ohlcv["high"] >= ohlcv["low"]).all()
assert (ohlcv["close"] > 0).all()
assert (ohlcv["volume"] >= 0).all()

print(f"  ✅ Validaciones OHLCV PASS")
print(f"     Rango: {ohlcv.index[0]} → {ohlcv.index[-1]}")
print(f"     Precio: {ohlcv['low'].min():.5f} - {ohlcv['high'].max():.5f}")
print(f"     Volumen total: {ohlcv['volume'].sum():.0f}")

# Test vectorbt con datos sintéticos
import vectorbt as vbt
entries = pd.Series(np.random.random(len(ohlcv)) < 0.05, index=ohlcv.index)
exits = pd.Series((np.arange(len(ohlcv)) % 20 == 0), index=ohlcv.index)
pf = vbt.Portfolio.from_signals(ohlcv["close"], entries, exits, fees=0.001, init_cash=10000)
print(f"  ✅ vectorbt Portfolio creado")
print(f"     Total Return: {pf.total_return():.2%}")
print(f"     # Trades: {pf.trades.count()}")

conn.close()
db_path.unlink(missing_ok=True)

print("\n✅ D-2-REV1 smoke test PASS (datos sintéticos)")
