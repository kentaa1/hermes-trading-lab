---
hypothesis_id: HYP_002
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
dataset_used: PENDING
vectorbt_result: PENDING
code_commit_hash: PENDING
notes: "Implementación completa de STRAT_001. Agrega filtro de sesión 07:00-15:00 UTC omitido en HYP_001. Parámetros EMA y ADX sin cambios. Resultado comparado contra HYP_001 permite aislar el efecto del filtro de sesión del efecto de régimen 2015-2017."
additional_dependencies:
- ta

---

# HYP_002 — EMA Crossover + ADX Filter + Session Filter

## Descripción
Estrategia de cruce de EMA (12, 26) con filtro ADX (14, umbral 25) y filtro
de sesión europea 07:00-15:00 UTC para identificar tendencias fuertes en EURUSD H1.

- **Entrada long**: EMA fast cruza por encima de EMA slow Y ADX > 25 Y hora en sesión
- **Salida**: EMA fast cruza por debajo de EMA slow
- **Sesión**: solo opera entre 07:00 y 15:00 UTC (sesión europea)

## Estado
- [ ] Wrapper ejecutado
- [ ] Resultado: PENDING
- [ ] Review: PENDING
