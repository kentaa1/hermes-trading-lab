#!/usr/bin/env python3
"""
dukascopy_download.py — Descarga ticks de Dukascopy y convierte a CSV para MT5

Descarga datos tick-by-tick de EURUSD desde Dukascopy y los convierte
a formato CSV compatible con CustomTicksAdd de MT5.

Formato CSV: DateTime,Bid,Ask,Volume,Flags

Uso:
    python dukascopy_download.py --year-start 2018 --year-end 2025 --output-dir data/dukascopy/

Referencia:
    https://datafeed.dukascopy.com/datafeed/EURUSD/YYYY/MM/DD/HHh_ticks.bi5
"""

import argparse
import lzma
import struct
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_URL = "https://datafeed.dukascopy.com/datafeed"
MULTIPLIER = 100000  # Dukascopy stores prices as integers * 1/MULTIPLIER
PIP = 0.0001

MT5_HEADER = "DateTime,Bid,Ask,Volume,Flags\n"
TICK_FLAG_BID = 0x01
TICK_FLAG_ASK = 0x02


def download_file(url: str, timeout: int = 30) -> bytes | None:
    """Descarga un archivo binario desde URL."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return response.read()
    except Exception:
        pass
    return None


def decode_tick_data(raw_data: bytes, base_time: datetime) -> list[dict]:
    """Decodifica datos .bi5 de Dukascopy."""
    try:
        decompressed = lzma.decompress(raw_data)
    except lzma.LZMAError:
        return []

    # Verificar tamaño
    if len(decompressed) == 0:
        return []

    # A veces hay header de 2 bytes
    if len(decompressed) % 20 != 0 and len(decompressed) > 2:
        if (len(decompressed) - 2) % 20 == 0:
            decompressed = decompressed[2:]

    if len(decompressed) % 20 != 0:
        return []

    ticks = []
    num_records = len(decompressed) // 20

    for i in range(num_records):
        offset = i * 20
        record = decompressed[offset:offset + 20]

        time_ms, ask_int, bid_int, ask_vol, bid_vol = struct.unpack('<5i', record)

        ask = ask_int / MULTIPLIER
        bid = bid_int / MULTIPLIER

        if bid > 0 and ask > 0 and ask >= bid:
            tick_time = base_time + timedelta(milliseconds=time_ms)
            ticks.append({
                'datetime': tick_time,
                'datetime_str': tick_time.strftime("%Y.%m.%d %H:%M:%S.%f")[:-3],
                'bid': bid,
                'ask': ask,
                'bid_vol': bid_vol,
                'ask_vol': ask_vol,
            })

    return ticks


def download_hour(symbol: str, year: int, month: int, day: int, hour: int) -> list[dict]:
    """Descarga ticks de una hora. Dukascopy usa mes 0-indexed."""
    url = f"{BASE_URL}/{symbol}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
    raw = download_file(url)
    if raw is None or len(raw) == 0:
        return []

    base_time = datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)
    return decode_tick_data(raw, base_time)


def download_day(symbol: str, year: int, month: int, day: int) -> list[dict]:
    """Descarga todos los ticks de un día."""
    all_ticks = []
    for hour in range(24):
        ticks = download_hour(symbol, year, month, day, hour)
        all_ticks.extend(ticks)
    return all_ticks


def save_month_csv(ticks: list[dict], output_dir: Path, symbol: str, year: int, month: int) -> int:
    """Guarda ticks de un mes en CSV."""
    if not ticks:
        return 0

    filename = f"{symbol}_ticks_{year}_{month:02d}.csv"
    filepath = output_dir / filename
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w') as f:
        f.write(MT5_HEADER)
        for tick in ticks:
            flags = TICK_FLAG_BID | TICK_FLAG_ASK
            volume = tick.get('bid_vol', 0) + tick.get('ask_vol', 0)
            f.write(f"{tick['datetime_str']},{tick['bid']:.5f},{tick['ask']:.5f},{volume},{flags}\n")

    return len(ticks)


def main():
    parser = argparse.ArgumentParser(description="Descarga ticks de Dukascopy para MT5")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--year-start", type=int, default=2018)
    parser.add_argument("--month-start", type=int, default=1)
    parser.add_argument("--year-end", type=int, default=2025)
    parser.add_argument("--month-end", type=int, default=6)
    parser.add_argument("--output-dir", default="data/dukascopy")
    parser.add_argument("--workers", type=int, default=1, help="Workers (default: 1 para estabilidad)")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    print("=" * 70)
    print("  Dukascopy Tick Downloader — Hermes-Trading-Lab")
    print("=" * 70)
    print(f"  Símbolo:  {args.symbol}")
    print(f"  Período:  {args.year_start}-{args.month_start:02d} a {args.year_end}-{args.month_end:02d}")
    print(f"  Output:   {output_dir}")
    print()

    start_date = datetime(args.year_start, args.month_start, 1, tzinfo=timezone.utc)

    # Calcular último día del mes final
    if args.month_end == 12:
        end_date = datetime(args.year_end + 1, 1, 1, tzinfo=timezone.utc) - timedelta(days=1)
    else:
        end_date = datetime(args.year_end, args.month_end + 1, 1, tzinfo=timezone.utc) - timedelta(days=1)

    total_days = (end_date - start_date).days + 1
    print(f"  Total días a descargar: {total_days}")
    print(f"  Inicio: {start_date.strftime('%Y-%m-%d')}")
    print(f"  Fin:    {end_date.strftime('%Y-%m-%d')}")
    print()

    # Acumulador por mes
    month_ticks = {}
    total_ticks = 0
    days_processed = 0
    start_time = time.time()

    current = start_date
    while current <= end_date:
        # Saltar fines de semana
        if current.weekday() < 5:
            year = current.year
            month = current.month
            day = current.day

            ticks = download_day(args.symbol, year, month, day)

            if ticks:
                key = (year, month)
                if key not in month_ticks:
                    month_ticks[key] = []
                month_ticks[key].extend(ticks)
                total_ticks += len(ticks)

            days_processed += 1

            # Progreso cada 30 días
            if days_processed % 30 == 0:
                elapsed = time.time() - start_time
                rate = days_processed / elapsed if elapsed > 0 else 0
                pct = days_processed / total_days * 100
                print(f"  {pct:.0f}% — {days_processed} días, {total_ticks:,} ticks, {rate:.1f} días/s")

        current += timedelta(days=1)

    # Guardar CSVs por mes
    print(f"\n  Guardando {len(month_ticks)} archivos mensuales...")
    for (year, month), ticks in sorted(month_ticks.items()):
        ticks.sort(key=lambda t: t['datetime'])
        count = save_month_csv(ticks, output_dir, args.symbol, year, month)
        print(f"    {args.symbol}_ticks_{year}_{month:02d}.csv: {count:,} ticks")

    elapsed = time.time() - start_time
    print(f"\n  ✅ Descarga completada en {elapsed:.0f}s")
    print(f"  Total ticks: {total_ticks:,}")
    print(f"  Archivos: {len(month_ticks)}")
    print(f"\n  Siguiente paso:")
    print(f"  1. Copia los CSV a <MT5>/MQL5/Files/")
    print(f"  2. Ejecuta ImportDukascopyTicks.mq5 en MT5")


if __name__ == "__main__":
    main()
