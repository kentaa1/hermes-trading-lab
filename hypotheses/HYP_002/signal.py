#!/usr/bin/env python3
"""
HYP_002 — Estrategia EMA Crossover + ADX Filter + Sesión Europea
"""

import pandas as pd
from ta.trend import ADXIndicator


def generate_signals(ohlcv: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Estrategia EMA crossover con filtro ADX y filtro de sesión europea.
    Long entry: EMA fast (12) cruza por encima de EMA slow (26) Y ADX(14) > 25
                Y hora UTC en [7, 14] inclusive.
    Exit: EMA fast cruza por debajo de EMA slow (sin filtro horario).

    ---
    hypothesis_id: HYP_002
    symbol: EURUSD
    timeframe: H1
    source: manual
    gene_ids: []
    hypothesis_family: ema_adx_trend_following
    parameters:
      fast_ema: 12
      slow_ema: 26
      adx_period: 14
      adx_threshold: 25
      session_filter_start_utc: 7
      session_filter_end_utc: 14
    dataset_used: PENDING
    vectorbt_result: PENDING
    notes: Implementación completa de STRAT_001. Agrega el filtro de sesión
      europea 07:00-15:00 UTC que HYP_001 omitió por defecto de implementación.
      Parámetros EMA y ADX sin cambios respecto a HYP_001. Experimento de
      control: el resultado, comparado contra HYP_001 sobre el mismo período,
      permite aislar el efecto del filtro de sesión del efecto de régimen
      2015-2017. No se espera que apruebe el pre-screening — el valor es
      diagnóstico.
    code_commit_hash: PENDING
    additional_dependencies:
    - ta
    ---    """

    ema_fast = ohlcv['close'].ewm(span=12, adjust=False).mean()
    ema_slow = ohlcv['close'].ewm(span=26, adjust=False).mean()

    adx_ind = ADXIndicator(high=ohlcv['high'], low=ohlcv['low'], close=ohlcv['close'], window=14)
    adx_val = adx_ind.adx()

    entries = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1)) & (adx_val > 25)
    exits = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))

    session_mask = ohlcv.index.hour.between(7, 14)
    entries = entries & session_mask

    entries = entries.fillna(False)
    exits = exits.fillna(False)

    return entries, exits
