#!/usr/bin/env python3
"""
dukascopy_download.py — Descarga ticks de Dukascopy y convierte a CSV importable por MT5

Descarga datos tick-by-tick de EURUSD desde los servidores de Dukascopy
y los convierte a formato CSV compatible con CustomTicksReplace de MT5.

Formato CSV MT5 para CustomTicksReplace:
    DateTime, Bid, Ask, Volume, Flags

Uso:
    python dukascopy_download.py --year-start 2020 --year-end 2025 --output-dir data/dukascopy/

Referencia:
    Dukascopy data feed: https://datafeed.dukascopy.com/datafeed/
    Formato binario: LZMA comprimido, little-endian
"""

import argparse
import lzma
import struct
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Dukascopy tick data URL pattern
# https://datafeed.dukascopy.com/datafeed/EURUSD/YYYY/MM/DD/HHh_ticks.bi5
BASE_URL = "https://datafeed.dukascopy.com/datafeed"

# Pip value for EURUSD (5 decimal places)
PIP = 0.0001
MULTIPLIER = 100000  # Dukascopy stores prices as integers * 1/MULTIPLIER

# MT5 custom tick CSV format header
MT5_HEADER = "DateTime,Bid,Ask,Volume,Flags\n"

# MT5 tick flags
TICK_FLAG_BID = 0x01
TICK_FLAG_ASK = 0x02
TICK_FLAG_LAST = 0x04
TICK_FLAG_VOLUME = 0x08


def download_file(url: str, timeout: int = 30) -> bytes | None:
    """Descarga un archivo binario desde URL."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                return response.read()
    except Exception as e:
        pass  # Archivo no disponible (fin de semana, futuro, etc.)
    return None


def decode_tick_data(raw_data: bytes) -> list[dict]:
    """
    Decodifica datos de ticks de Dukascopy (formato .bi5).
    
    Formato: LZMA comprimido, luego registros de 20 bytes:
        time(4), ask(4), bid(4), ask_volume(4), bid_volume(4)
    
    Los precios están en formato entero * pip / 10
    """
    try:
        decompressed = lzma.decompress(raw_data)
    except lzma.LZMAError:
        return []
    
    if len(decompressed) % 20 != 0:
        # A veces hay un header de 2 bytes
        if len(decompressed) > 2 and (len(decompressed) - 2) % 20 == 0:
            decompressed = decompressed[2:]
        else:
            return []
    
    ticks = []
    num_records = len(decompressed) // 20
    
    for i in range(num_records):
        offset = i * 20
        record = decompressed[offset:offset + 20]
        
        # Little-endian: 5 int32 values
        time_ms, ask_int, bid_int, ask_vol, bid_vol = struct.unpack('<5i', record)
        
        # Convertir precios: entero a double
        # Dukascopy usa unidades de 1/MULTIPLIER (1/100000 para EURUSD)
        ask = ask_int / MULTIPLIER
        bid = bid_int / MULTIPLIER
        
        # Solo incluir ticks válidos
        if bid > 0 and ask > 0 and ask >= bid:
            ticks.append({
                'time_ms': time_ms,
                'bid': bid,
                'ask': ask,
                'bid_vol': bid_vol,
                'ask_vol': ask_vol,
            })
    
    return ticks


def download_hour(symbol: str, year: int, month: int, day: int, hour: int) -> list[dict]:
    """Descarga y decodifica ticks de una hora específica."""
    # Dukascopy usa mes 0-indexed
    url = f"{BASE_URL}/{symbol}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
    
    raw = download_file(url)
    if raw is None or len(raw) == 0:
        return []
    
    ticks = decode_tick_data(raw)
    
    # Ajustar timestamps: time_ms es offset en ms desde el inicio de la hora
    base_time = datetime(year, month + 1, day, hour, 0, 0, tzinfo=timezone.utc)
    
    for tick in ticks:
        tick_time = base_time + timedelta(milliseconds=tick['time_ms'])
        tick['datetime'] = tick_time
        tick['datetime_str'] = tick_time.strftime("%Y.%m.%d %H:%M:%S.%f")[:-3]
    
    return ticks


def download_day(symbol: str, year: int, month: int, day: int) -> list[dict]:
    """Descarga todos los ticks de un día (24 horas)."""
    all_ticks = []
    for hour in range(24):
        ticks = download_hour(symbol, year, month, day)
        all_ticks.extend(ticks)
    return all_ticks


def download_range(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    max_workers: int = 4,
    progress_callback=None,
) -> list[dict]:
    """Descarga ticks para un rango de fechas."""
    all_ticks = []
    current = start_date
    total_days = (end_date - start_date).days
    days_done = 0
    
    # Generar lista de (year, month, day, hour) para descargar
    tasks = []
    while current <= end_date:
        for hour in range(24):
            tasks.append((symbol, current.year, current.month - 1, current.day, hour))
        current += timedelta(days=1)
    
    total_tasks = len(tasks)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_hour, *task): task for task in tasks}
        
        for future in as_completed(futures):
            ticks = future.result()
            all_ticks.extend(ticks)
            days_done = len(all_ticks)
            
            if progress_callback and len(all_ticks) % 240 == 0:  # ~10 days
                pct = min(100, int(len(all_ticks) / max(total_tasks, 1) * 100))
                progress_callback(pct, len(all_ticks))
    
    # Ordenar por timestamp
    all_ticks.sort(key=lambda t: t['datetime'])
    
    return all_ticks


def ticks_to_mt5_csv(ticks: list[dict], output_path: Path, symbol: str = "EURUSD"):
    """
    Convierte ticks a formato CSV importable por MT5 CustomTicksReplace.
    
    Formato MT5:
        DateTime,Bid,Ask,Volume,Flags
        2020.01.02 00:00:00.123,1.11987,1.11997,0,6
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(MT5_HEADER)
        for tick in ticks:
            # Flags: BID change = 1, ASK change = 2, ambos = 3
            flags = TICK_FLAG_BID | TICK_FLAG_ASK
            volume = tick.get('bid_vol', 0) + tick.get('ask_vol', 0)
            
            line = f"{tick['datetime_str']},{tick['bid']:.5f},{tick['ask']:.5f},{volume},{flags}\n"
            f.write(line)
    
    return len(ticks)


def ticks_to_mt5_by_month(
    ticks: list[dict],
    output_dir: Path,
    symbol: str = "EURUSD",
) -> dict:
    """
    Divide ticks por mes y guarda en archivos CSV separados.
    MT5 importa más rápido con archivos mensuales.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    by_month = {}
    for tick in ticks:
        key = tick['datetime'].strftime("%Y%m")
        if key not in by_month:
            by_month[key] = []
        by_month[key].append(tick)
    
    files = {}
    for month_key, month_ticks in sorted(by_month.items()):
        year = month_key[:4]
        month = month_key[4:]
        filename = f"{symbol}_ticks_{year}_{month}.csv"
        filepath = output_dir / filename
        count = ticks_to_mt5_csv(month_ticks, filepath, symbol)
        files[month_key] = filepath
        print(f"  {filename}: {count:,} ticks")
    
    return files


def main():
    parser = argparse.ArgumentParser(description="Descarga ticks de Dukascopy y convierte a CSV para MT5")
    parser.add_argument("--symbol", default="EURUSD", help="Símbolo (default: EURUSD)")
    parser.add_argument("--year-start", type=int, default=2020, help="Año inicio (default: 2020)")
    parser.add_argument("--month-start", type=int, default=1, help="Mes inicio 1-12 (default: 1)")
    parser.add_argument("--year-end", type=int, default=2025, help="Año fin (default: 2025)")
    parser.add_argument("--month-end", type=int, default=12, help="Mes fin 1-12 (default: 12)")
    parser.add_argument("--output-dir", default="data/dukascopy", help="Directorio de salida")
    parser.add_argument("--workers", type=int, default=4, help="Workers paralelos (default: 4)")
    parser.add_argument("--single-file", action="store_true", help="Un solo archivo en vez de por mes")
    
    args = parser.parse_args()
    
    start_date = datetime(args.year_start, args.month_start, 1, tzinfo=timezone.utc)
    end_date = datetime(args.year_end, args.month_end, 31, 23, 59, 59, tzinfo=timezone.utc)
    output_dir = Path(args.output_dir)
    
    print("=" * 70)
    print("  Dukascopy Tick Downloader — Hermes-Trading-Lab")
    print("=" * 70)
    print(f"\n  Símbolo:      {args.symbol}")
    print(f"  Período:      {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
    print(f"  Output:       {output_dir}")
    print(f"  Workers:      {args.workers}")
    print(f"\n  Descargando...")
    
    def progress(pct, count):
        print(f"  Progreso: {pct}% — {count:,} ticks descargados", end='\r')
    
    ticks = download_range(
        symbol=args.symbol,
        start_date=start_date,
        end_date=end_date,
        max_workers=args.workers,
        progress_callback=progress,
    )
    
    print(f"\n\n  Total descargado: {len(ticks):,} ticks")
    
    if not ticks:
        print("\n  ❌ No se descargaron ticks. Verifica conexión o rango de fechas.")
        sys.exit(1)
    
    # Estadísticas
    first = ticks[0]['datetime']
    last = ticks[-1]['datetime']
    print(f"  Primer tick:    {first}")
    print(f"  Último tick:    {last}")
    print(f"  Spread medio:   {sum(t['ask']-t['bid'] for t in ticks)/len(ticks)/PIP:.2f} pips")
    
    # Guardar
    print(f"\n  Convirtiendo a CSV MT5...")
    
    if args.single_file:
        filepath = output_dir / f"{args.symbol}_ticks_{args.year_start}-{args.year_end}.csv"
        count = ticks_to_mt5_csv(ticks, filepath, args.symbol)
        print(f"\n  ✅ Guardado: {filepath} ({count:,} ticks)")
    else:
        files = ticks_to_mt5_by_month(ticks, output_dir, args.symbol)
        print(f"\n  ✅ {len(files)} archivos mensuales guardados en {output_dir}")
    
    # Resumen
    print(f"\n  Siguiente paso:")
    print(f"  1. Copia los CSV a la carpeta MQL5/Files/ de MT5")
    print(f"  2. Ejecuta el script MQL5 ImportDukascopyTicks.mq5 en MT5")
    print(f"  3. El script creará el símbolo personalizado EURUSD_DUKA")


if __name__ == "__main__":
    main()
