#!/usr/bin/env python3
"""
HYP_002 — Estrategia EMA Crossover + ADX Filter + Session Filter
"""

import pandas as pd
from ta.trend import ADXIndicator


def generate_signals(ohlcv: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Estrategia EMA crossover con filtro ADX y filtro de sesión europea.
    Long entry: EMA fast (12) cruza por encima de EMA slow (26) Y ADX(14) > 25
                Y hora UTC entre 07:00 y 15:00
    Exit: EMA fast cruza por debajo de EMA slow

    ---
    hypothesis_id: HYP_002
    symbol: EURUSD
    timeframe: H1
    source: manual
    gene_ids: []
    parameters:
      fast_ema: 12
      slow_ema: 26
      adx_period: 14
      adx_threshold: 25
      session_start: 7
      session_end: 15
      session_timezone: UTC
    dataset_used: EURUSD:2015-01-01-2017-12-31
    vectorbt_result:
      pf: 0.20313516872027357
      dd: 0.03217642521992825
      trades: 8
    code_commit_hash: 58d7a9b8d03287e72f7afa5fa74ccaa0a2dad3f6
    notes: Implementación completa de STRAT_001. Agrega filtro de sesión 07:00-15:00 UTC
      omitido en HYP_001. Parámetros EMA y ADX sin cambios. Resultado comparado contra
      HYP_001 permite aislar el efecto del filtro de sesión del efecto de régimen 2015-2017.
    additional_dependencies:
    - ta
    ---    """
    ema_fast = ohlcv['close'].ewm(span=12, adjust=False).mean()
    ema_slow = ohlcv['close'].ewm(span=26, adjust=False).mean()

    adx_ind = ADXIndicator(high=ohlcv['high'], low=ohlcv['low'], close=ohlcv['close'], window=14)
    adx_val = adx_ind.adx()

    session_mask = (ohlcv.index.hour >= 7) & (ohlcv.index.hour < 15)

    crossover_entry = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
    entries = crossover_entry & (adx_val > 25) & session_mask
    exits = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

    entries = entries.fillna(False)
    exits = exits.fillna(False)

    return entries, exits
