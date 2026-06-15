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
  pf: 0.8095194925409115
  dd: 0.01919670298977627
  trades: 19
code_commit_hash: d2bfd67c8f8c7a25bd6705ca8611e0671fa8af8a
notes: "EMA crossover + ADX filter strategy for trend following. NOTA: primer pre-screening\
  \ ejecutado sobre Research 2020-01 a 2021-03 por error (deb\xEDa ser Historical\
  \ Stress 2007-2017). Resultado no v\xE1lido para protocolo formal. Per\xEDodo Research\
  \ contaminado para HYP_001: 2020-01 a 2021-03 (prescreening exposure). Research\
  \ disponible para evaluaci\xF3n formal restringido a 2018-01 a 2019-12."
contaminated_range: 2020-01_2021-03_prescreening_exposure
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
