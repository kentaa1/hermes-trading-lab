# P1_STATUS.md — Cierre de Fase 1

**Fecha**: 2026-06-13
**Estado**: ✅ CERRADO

## Componentes verificados

| Componente | Estado | Evidencia |
|:-----------|:-------|:----------|
| Git init | ✅ | Commit `d6d6e5f` — primer commit del laboratorio |
| MLflow setup | ✅ | 3/3 verificaciones PASS (session recovery, persistence, tag search) |
| MLflow experiment | ✅ | `hermes-godmode` (ID: 1) |
| validate_import.py | ✅ | Creado, sin referencia a columna `vol` |
| ohlcv_builder.py | ✅ | Query DuckDB con ROW_NUMBER, smoke test PASS |
| vectorbt install | ✅ | v1.0.0, importa sin errores, smoke test PASS |
| D-2-REV1 smoke test | ✅ | 3600 ticks sintéticos → 1 barra H1 → vectorbt Portfolio OK |
| hermes_config.py | ✅ | PROVISIONAL_COST_PIPS=2.0, MIN_TRADES=30, umbrales V-2 |
| HYP_000 | ✅ | Hipótesis de infraestructura creada |
| GitHub repo | ✅ | https://github.com/kentaa1/hermes-trading-lab |

## Bugs corregidos

1. **mlflow_setup.py**: `experiment_id` NoneType — corregido con `get_experiment(exp_id)` después de `create_experiment`
2. **ohlcv_builder.py**: Query SQL con `FIRST_VALUE` no soportado en DuckDB — reemplazado por `ROW_NUMBER()` con subqueries
3. **validate_import.py**: Referencia a columna `vol` inexistente — eliminada, usa `bid_vol` + `ask_vol`

## Deuda pendiente

- **DVC**: Pendiente hasta tener datos reales de Dukascopy. Configurado remote storage pero sin `dvc init` en el repo.
- **Datos reales Dukascopy**: Smoke test usó datos sintéticos. Primer import real debe reejecutar validación completa.
- **MLflow UI**: Bajo demanda (no automático en cada sesión).

## Secuencia P2 (siguiente)

1. Agregar `PROVISIONAL_COST_PIPS` a `hermes_config.py` ✅ (ya hecho)
2. Crear función SQL de construcción de OHLCV ✅ (ya hecho)
3. Crear `hypotheses/HYP_000/` ✅ (ya hecho)
4. Implementar wrapper de pre-screening
5. Ejecutar wrapper con HYP_000
6. Crear HYP_001 (STRAT_001 EMA+ADX)
7. Ejecutar wrapper con HYP_001
8. Documento de cierre P2

## Hashes de commit relevantes

- `d6d6e5f` — INIT: Primer commit
- `6f772af` — FIX: mlflow_setup 3 verificaciones PASS
- `9e7c8fd` — FIX: ohlcv_builder query DuckDB, smoke test D-2-REV1 PASS
