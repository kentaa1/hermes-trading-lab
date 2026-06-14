#!/usr/bin/env python3
"""
HYP_000 — Hipótesis de infraestructura (TEST)

Señales aleatorias para validar el wrapper de pre-screening.
No es una estrategia real. Solo valida que el pipeline funciona end-to-end.
"""

import numpy as np
import pandas as pd


def generate_signals(ohlcv: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Genera señales aleatorias para validación de infraestructura.
    
    ---
hypothesis_id: HYP_000
symbol: EURUSD
timeframe: H1
source: synthetic
gene_ids: []
parameters:
  seed: 42
  entry_prob: 0.02
  exit_prob: 0.02
dataset_used: EURUSD:2020-01-01-2020-01-01
vectorbt_result:
  pf: .inf
  dd: 0.0
  trades: 0
code_commit_hash: d88ade72dd9f7232ffd2ec82644bc40a78d84632
notes: "Hip\xF3tesis de infraestructura. Se\xF1ales aleatorias para validar wrapper."
additional_dependencies: []

---
    """
    
    np.random.seed(42)
    n = len(ohlcv)
    
    # Entradas aleatorias (2% de probabilidad por barra)
    entries = pd.Series(np.random.random(n) < 0.02, index=ohlcv.index)
    
    # Salidas aleatorias (2% de probabilidad por barra)
    exits = pd.Series(np.random.random(n) < 0.02, index=ohlcv.index)
    
    return entries, exits
