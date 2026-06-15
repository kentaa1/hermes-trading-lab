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
dataset_used: Research_2020-01_2021-03_WRONG_PERIOD
vectorbt_result:
  pf: 0.28625024715036657
  dd: 0.12243367719779064
  trades: 54
  win_rate: PENDING
  avg_win: PENDING
  avg_loss: PENDING
code_commit_hash: 1b7005fc9df177546d9e652a41c7646c5b4f6bb3
notes: "EMA crossover + ADX filter strategy for trend following. NOTA: primer pre-screening\
  \ ejecutado sobre Research 2020-01 a 2021-03 por error (deb\xEDa ser Historical\
  \ Stress 2007-2017). Resultado no v\xE1lido para protocolo formal. Per\xEDodo Research\
  \ contaminado para HYP_001: 2020-01 a 2021-03 (prescreening exposure). Research\
  \ disponible para evaluaci\xF3n formal restringido a 2018-01 a 2019-12."
contaminated_range: 2020-01_2021-03_prescreening_exposure
error_taxonomy:
  primary: implementation_deficiency
  detail: "Filtro de sesi\xF3n 07:00-15:00 UTC omitido en la implementaci\xF3n. Componente\
    \ pre-especificado en STRAT_001 original."
  secondary: regime_mismatch_unconfirmed
  secondary_detail: "2015-2017 adverso para trend-following en EURUSD H1. Contribuci\xF3\
    n exacta no separable sin HYP_002 como control."
  resolution: "HYP_002 implementa STRAT_001 completo. Diferencia en PF atribuible\
    \ al filtro de sesi\xF3n."
additional_dependencies:
- ta
pf: 0.28625024715036657
dd: 0.12243367719779064
trades: 54
status: failed thresholds

---

# HYP_001 — EMA Crossover + ADX Filter

## Descripción
Estrategia de cruce de EMA (12, 26) con filtro ADX (14, umbral 25) para
identificar tendencias fuertes en EURUSD H1.

- **Entrada long**: EMA fast cruza por encima de EMA slow Y ADX > 25
- **Salida**: EMA fast cruza por debajo de EMA slow

## Estado
- [x] Wrapper ejecutado (2020-01 a 2021-03 — período incorrecto)
- [x] Resultado: DISCARD (19 trades < 30, PF=0.81)
- [ ] Pre-screening válido sobre Historical Stress 2007-2017
- [ ] Review: PENDING
