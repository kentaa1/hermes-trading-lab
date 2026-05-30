# Convención de Nombres — Hermes-Trading-Lab

## Experimentos

```
EXP_NNN_descripcion_corta

Ejemplos:
  EXP_001_sma_crossover
  EXP_002_rsi_mean_reversion
  EXP_003_breakout_atr
```

Reglas:
- 3 dígitos, correlativos, sin saltos
- Descripción en minúsculas con guion bajo
- Si un experimento se rechaza y se re-workea: mismo número, sufijo `_v2`, `_v3`
  - Ejemplo: `EXP_001_sma_crossover_v2`

## Archivos MQL5

```
EXP_NNN_descripcion_corta.mq5

Ejemplo:
  EXP_001_sma_crossover.mq5
```

## Fichas de estrategia

Ubicación: `02_STRATEGIES/`

```
EXP_NNN_descripcion_corta.md

Ejemplo:
  EXP_001_sma_crossover.md
```

## Backtest reports

Ubicación: `04_BACKTESTS/EXP_NNN/`

```
EXP_NNN_descripcion_corta/
  ├── report_IS.html
  ├── report_OOS.html
  ├── metrics_IS.csv
  ├── metrics_OOS.csv
  ├── equity_curve.png
  └── notes.md
```

## Hipótesis de research

Ubicación: `10_RESEARCH/`

```
HIP_NNN_descripcion_corta.md

Ejemplo:
  HIP_001_mean_reversion_eurusd_h1.md
```

## Perfiles de símbolo

Ubicación: `05_SYMBOL_PROFILES/`

```
simbolo_timeframe.md

Ejemplo:
  eurusd_h1.md
```
