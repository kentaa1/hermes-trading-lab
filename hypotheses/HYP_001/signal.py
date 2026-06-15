#!/usr/bin/env python3
"""
HYP_001 — Estrategia EMA Crossover + ADX Filter
"""

import pandas as pd
from ta.trend import ADXIndicator


def generate_signals(ohlcv: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Estrategia EMA crossover con filtro ADX.
    Long entry: EMA fast (12) cruza por encima de EMA slow (26) Y ADX(14) > 25
    Exit: EMA fast cruza por debajo de EMA slow

    ---
    hypothesis_id: HYP_001
    symbol: EURUSD
    timeframe: H1
    source: manual
    gene_ids: []
    parameters:
      fast_ema: 12
      slow_ema: 26
      adx_period: 14
      adx_threshold: 25
    dataset_used: PENDING
    vectorbt_result: PENDING
    code_commit_hash: PENDING
    notes: "EMA crossover + ADX filter strategy for trend following."
    additional_dependencies: [ta]
    ---
    """

    ema_fast = ohlcv['close'].ewm(span=12, adjust=False).mean()
    ema_slow = ohlcv['close'].ewm(span=26, adjust=False).mean()

    adx_ind = ADXIndicator(high=ohlcv['high'], low=ohlcv['low'], close=ohlcv['close'], window=14)
    adx_val = adx_ind.adx()

    entries = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1)) & (adx_val > 25)
    exits = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

    entries = entries.fillna(False)
    exits = exits.fillna(False)

    return entries, exits
