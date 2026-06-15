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
pf: 0.0
dd: 0.0
trades: 0
status: PENDING

---

# HYP_001 — EMA Crossover + ADX Filter

## Descripción
Estrategia de cruce de EMA (12, 26) con filtro ADX (14, umbral 25) para
identificar tendencias fuertes en EURUSD H1.

- **Entrada long**: EMA fast cruza por encima de EMA slow Y ADX > 25
- **Salida**: EMA fast cruza por debajo de EMA slow

## Estado
- [ ] Wrapper ejecutado
- [ ] Resultado: PENDING
- [ ] Review: PENDING
