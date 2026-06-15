#!/usr/bin/env python3
"""
HYP_003 — EMA Crossover + ADX Filter + Session + ATR Stop Management
"""

import pandas as pd
from ta.trend import ADXIndicator
from ta.volatility import AverageTrueRange


def generate_signals(ohlcv: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Estrategia EMA crossover con filtro ADX, filtro de sesion y stops ATR.
    Long entry: EMA fast(12) cruza sobre EMA slow(26) Y ADX(14)>25 Y sesion
    Exit: EMA fast cruza debajo de EMA slow

    ---
    hypothesis_id: HYP_003
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
      atr_period: 14
    dataset_used: PENDING
    vectorbt_result: PENDING
    code_commit_hash: PENDING
    notes: "HYP_003 controla gestion de salida con stops ATR. Derivado del diagnostico de HYP_001: win_rate 22.2% con payoff simetrico produce PF=0.286. Palanca 1: stop fijo en 2 ATR para capear outliers (-229 pips en HYP_001). Palanca 2: trailing stop para dejar correr winners. Si mejora PF significativamente, el problema de HYP_001 era la gestion de salida, no el regimen ni la senal de entrada."
    stop_config:
      sl_stop: 0.0055
      sl_trail: true
    additional_dependencies:
    - ta
    ---
    """

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
