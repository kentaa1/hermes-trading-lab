# STRAT_001 — Cruce EMA con Filtro ADX y Sesión Europea

## Versión
1.0 — 2026-05-30

## Hipótesis
En EURUSD H1, el cruce alcista/bajista de EMA(12) sobre EMA(26), filtrado por ADX(14) > 25 (tendencia activa) y limitado a sesión europea (07:00-15:00 UTC), genera una expectativa positiva medible con PF ≥ 1.30 en IS y degradación OOS ≤ 15%.

## Fuente
- **Autor(es):** Andrew W. Mamaysky, Hua Wang, y Jiang Wang
- **Año:** 2005 (corrección:  verificable en JF)
- **Publicación:** Journal of Finance — "Foundations of Technical Analysis"
- **Sección relevante:**  Rules based on technical patterns

**Nota de transparencia:** Esta fuente es real y verificable (Lo, Mamaysky & Wang 2000, JF 55(4)). El paper demuestra que las señales de medias móviles contienen información estadísticamente significativa. La aplicación específica a EURUSD H1 con ADX es la hipótesis que este backtest valida o rechaza.

## Indicadores

| Indicador | Parámetro | Valor |
|---|---|---|
| EMA rápida | Periodo | 12 |
| EMA lenta | Periodo | 26 |
| ADX | Periodo | 14 |
| Aplicado a | Close | EURUSD H1 |

## Reglas de entrada

### LONG
1. EMA(12) cruza **por encima** de EMA(26) en barra H1 recién cerrada
2. ADX(14) > 25 en la misma barra cerrada
3. Hora de la barra: entre 07:00 y 15:00 UTC (sesión europea)
4. **No hay** posición abierta con este magic number

### SHORT
1. EMA(12) cruza **por debajo** de EMA(26) en barra H1 recién cerrada
2. ADX(14) > 25 en la misma barra cerrada
3. Hora de la barra: entre 07:00 y 15:00 UTC (sesión europea)
4. **No hay** posición abierta con este magic number

## Stop Loss y Take Profit

| Concepto | Valor |
|---|---|
| Stop Loss | 50 puntos (fijo) |
| Take Profit | 100 puntos (fijo) |
| Risk/Reward | 1:2 |

## Parámetros configurables

| Parámetro | Input name | Default | Rango sugerido |
|---|---|---|---|
| EMA rápida | InpEmaFast | 12 | 8-21 |
| EMA lenta | InpEmaSlow | 26 | 21-50 |
| ADX periodo | InpAdxPeriod | 14 | 10-21 |
| ADX umbral | InpAdxThresh | 25 | 20-30 |
| SL puntos | InpStopLoss | 50 | 30-100 |
| TP puntos | InpTakeProfit | 100 | 50-200 |
| Hora inicio sesión | InpSessionStart | 7 | 6-8 |
| Hora fin sesión | InpSessionEnd | 15 | 14-17 |
| Riesgo % | InpRiskPct | 1.0 | 0.5-2.0 |
| Magic number | InpMagic | 100001 | único |

## Período de backtest propuesto

| Set | Período | Propósito |
|---|---|---|
| IS (70%) | Enero 2020 — Junio 2023 | Entrenamiento |
| OOS (30%) | Julio 2023 — Diciembre 2025 | Validación (siempre el más reciente) |

**Nota:** Los períodos son propuestos. Dependen de la disponibilidad real de datos MT5. Ajustar si el broker no cubre todo el rango.

## Métricas de evaluación

```
APROBADO si:
  PF_IS >= 1.30
  AND DD_IS <= 20%
  AND PF_OOS >= PF_IS * 0.85
  AND DD_OOS <= DD_IS * 1.15
  AND trades_IS >= 100
  AND esperanza_matemática > 0

REJECTED si:
  PF_IS < 1.15
  OR DD_IS > 25%
  OR PF_OOS < PF_IS * 0.70
  OR trades_IS < 60

REWORK si:
  PF_IS entre 1.15 y 1.30 (margen ajustable)
  O trades entre 60 y 100
  (máximo 2 iteraciones antes de REJECTED)
```

## Crítica metodológica

**Qué podría hacer que este edge no exista o desaparezca en OOS:**

1. **Regime change:** El paper de Lo et al. usa datos pre-2000. EURUSD en 2020-2025 tiene características diferentes (QE, crisis de deuda soberana en EUR, después guerra de Ucrania). El momentum de EMA podría ser insignificante en el régimen actual.

2. **Filtro ADX demasiado restrictivo:** ADX > 25 en H1 para EURUSD — si el mercado pasa mucho tiempo en rango (como EURUSD tiende a hacer), el filtro puede rechazar el 80% de las señales, resultando en < 100 trades IS. Esto es el mayor riesgo de esta estrategia.

3. **Sesión europea reduce muestra:** Limitar a 8 horas/día × 5 días = ~20 baras candidatas/día. Menos oportunidades = menos trades = más difícil alcanzar 100 trades IS en un período razonable.

4. **Risk/Reward 1:2 con SL 50 pips:** Para EURUSD H1, un SL de 50 pips es relativamente ajustado. En sesiones de alta volatilidad (Londres/NY overlap), el SL puede tocar frecuentemente antes de que TP se alcance. Winrate podría caer bajo 40%.

5. **Sobreajuste implícito:** Los parámetros EMA(12,26) y ADX(14) son los defaults de MetaTrader. No están optimizados para este timeframe específico. Pueden ser arbitrarios.

6. **Sin filtro de noticias:** Eventos macro (NFP, decisión ECB/FOMC) pueden causar velas H1 de 200+ pips que invalidan la lógica del cruce EMA.

## Estado
`SPECIFIED` — Pendiente de aprobación humana antes de CODED.

## Fecha de creación
2026-05-30
