import argparse
import datetime
import random
import duckdb
from typing import Optional


def generate_ticks(
    symbol: str,
    start: datetime.datetime,
    end: datetime.datetime,
    ticks_per_second: int,
    base_price: float = 1.1000,
    spread: float = 0.0001,
) -> list[tuple]:
    """Generate synthetic tick data.

    Returns a list of tuples matching the DuckDB schema:
    (symbol, timestamp, bid, ask, bid_vol, ask_vol).
    """
    total_seconds = int((end - start).total_seconds())
    total_ticks = total_seconds * ticks_per_second
    price = base_price
    rows = []
    for i in range(total_ticks):
        # Random walk: small Gaussian step
        price += random.gauss(0, 0.00005)  # ~5 pip stddev per tick
        # Ensure price stays positive
        price = max(price, 0.0001)
        bid = price
        ask = price + spread
        bid_vol = random.uniform(1, 100)
        ask_vol = random.uniform(1, 100)
        ts = start + datetime.timedelta(seconds=i / ticks_per_second)
        rows.append((symbol, ts, bid, ask, bid_vol, ask_vol))
    return rows


def main(
    symbol: str,
    start_str: str,
    end_str: str,
    ticks_per_second: int,
    db_path: str,
) -> None:
    start = datetime.datetime.fromisoformat(start_str)
    end = datetime.datetime.fromisoformat(end_str)
    # Ensure timezone-aware UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=datetime.timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=datetime.timezone.utc)

    con = duckdb.connect(database=db_path, read_only=False)
    # Create table if not exists
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS ticks (
            symbol VARCHAR,
            timestamp TIMESTAMPTZ,
            bid DOUBLE,
            ask DOUBLE,
            bid_vol DOUBLE,
            ask_vol DOUBLE
        );
        """
    )
    # Generate data
    rows = generate_ticks(symbol, start, end, ticks_per_second)
    # Insert data in batches
    con.executemany(
        "INSERT INTO ticks VALUES (?, ?, ?, ?, ?, ?);",
        rows,
    )
    # Verify insertion
    count = con.execute("SELECT COUNT(*) FROM ticks;").fetchone()[0]
    print(f"Inserted {len(rows)} rows. Total rows in table: {count}")
    con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic tick data in DuckDB.")
    parser.add_argument("--symbol", default="EURUSD", help="Currency pair symbol")
    parser.add_argument(
        "--start",
        default="2020-01-01T00:00:00",
        help="Start timestamp in ISO format (UTC)",
    )
    parser.add_argument(
        "--end",
        default="2020-01-02T06:00:00",
        help="End timestamp in ISO format (UTC) — 30h range for sufficient trades",
    )
    parser.add_argument(
        "--ticks-per-second",
        type=int,
        default=1,
        help="Number of ticks generated per second",
    )
    parser.add_argument(
        "--db-path",
        default="duckdb/main.duckdb",
        help="Path to DuckDB file",
    )
    args = parser.parse_args()
    main(
        symbol=args.symbol,
        start_str=args.start,
        end_str=args.end,
        ticks_per_second=args.ticks_per_second,
        db_path=args.db_path,
    )
