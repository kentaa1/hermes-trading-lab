#!/usr/bin/env python3
"""
HYP_003 — Mean Reversion por Evaporación de Liquidez en Sesión NY-Asia
"""

import pandas as pd
import numpy as np
import ta


def generate_signals(ohlcv: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Mean reversal impulsado por evaporación de liquidez en sesión de transición
    NY-Asia (20:00-00:00 UTC). Entry: RSI < 25 AND close < lower Bollinger AND
    hora UTC en [20, 23]. Exit: close cruza por encima de middle Bollinger.

    ---
    hypothesis_id: HYP_003
    symbol: EURUSD
    timeframe: H1
    source: pending_verification
    gene_ids: []
    hypothesis_family: liquidity_reversal_session_transition
    parameters:
      rsi_period: 14
      rsi_oversold: 25
      rsi_overbought: 75
      bb_period: 20
      bb_std: 2
      session_filter_start_utc: 20
      session_filter_end_utc: 23
    dataset_used: PENDING
    vectorbt_result: PENDING
    notes: >-
      Mean reversal impulsado por evaporación de liquidez en sesión de transición
      NY-Asia (20:00-00:00 UTC). HYP_001 y HYP_002 diagnosticaron que EMA+ADX
      no genera edge en régimen 2015-2017. HYP_003 prueba el mecanismo
      complementario. Si no alcanza MIN_TRADES=30, el resultado es
      INSUFFICIENT_TRADES (informativo, no fallo del protocolo).
      Falsabilidad pre-registrada.
    code_commit_hash: PENDING
    additional_dependencies:
    - ta
    ---

    Args:
        ohlcv: DataFrame con columnas open, high, low, close, volume y
               DatetimeIndex UTC.

    Returns:
        (entries, exits): tupla de pd.Series[bool].
    """
    close = ohlcv["close"]

    # ── Indicadores ─────────────────────────────────────────────────────
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi()

    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    bb_upper = bb.bollinger_hband()
    bb_middle = bb.bollinger_mavg()
    bb_lower = bb.bollinger_lband()

    # ── Entry: sobreextensión en sesión de liquidez deprimida ────────────
    oversold_undercut = (rsi < 25) & (close < bb_lower)
    session_mask = ohlcv.index.hour.isin([20, 21, 22, 23])
    entries = oversold_undercut & session_mask

    # ── Exit: reversión a la media ───────────────────────────────────────
    exits = close > bb_middle

    entries = entries.fillna(False).astype(bool)
    exits = exits.fillna(False).astype(bool)

    return entries, exits
