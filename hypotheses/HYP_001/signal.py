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
    dataset_used: EURUSD:2015-01-01-2017-12-31
    vectorbt_result:
      pf: 0.28625024715036657
      dd: 0.12243367719779064
      trades: 54
    code_commit_hash: 1b7005fc9df177546d9e652a41c7646c5b4f6bb3
    notes: 'EMA crossover + ADX filter strategy for trend following. NOTA: primer pre-screening
      ejecutado sobre Research 2020-01 a 2021-03 por error (debía ser Historical Stress
      2007-2017). Resultado no válido para protocolo formal. Período Research contaminado
      para HYP_001: 2020-01 a 2021-03 (prescreening exposure). Research disponible para
      evaluación formal restringido a 2018-01 a 2019-12.'
    contaminated_range: 2020-01_2021-03_prescreening_exposure
    additional_dependencies:
    - ta
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
