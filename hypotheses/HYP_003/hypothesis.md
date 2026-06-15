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
pf: PENDING
dd: PENDING
trades: PENDING
status: PENDING

---

# HYP_003 — EMA Crossover + ADX Filter + Session + ATR Stop Management

## Descripción
Estrategia de cruce de EMA (12, 26) con filtro ADX (14, umbral 25), filtro
de sesión europea (07:00-15:00 UTC) y gestión de salida mediante stops ATR.

- **Entrada long**: EMA fast cruza por encima de EMA slow Y ADX > 25 Y hora UTC entre 07:00 y 15:00
- **Salida**: EMA fast cruza por debajo de EMA slow
- **Stop loss**: 0.0055 (55 pips en EURUSD ~1.10)
- **Trailing stop**: Activado

## Estado
- [ ] Wrapper ejecutado: PENDING
- [ ] Pre-screening: PENDING
- [ ] Review: PENDING
