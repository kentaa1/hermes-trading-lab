# STRAT_001 — Cruce EMA con Filtro ADX y Sesión Europea

## Versión
1.0 — 2026-05-30

## Hipótesis
En EURUSD H1, el cruce alcista/bajista de EMA(12) sobre EMA(26), filtrado por ADX(14) > 25 (tendencia activa) y limitado a sesión europea (07:00-15:00 UTC), genera una expectativa positiva medible con PF ≥ 1.30 en IS y degradación OOS ≤ 15%.

## Fuente

### Fuente 1 — Modelo de medias móviles e ineficiencia (VERIFICADA)
- **Autor(es):** R. Baviera, M. Pasquini, J. Raboanary, M. Serva
- **Año:** 2000
- **Publicación:** arXiv:cond-mat/0011337 [q-fin.TR] — enviado a *Quantitative Finance*
- **Sección relevante:** Modelo estocástico con media móvil de log-precios. Las estrategias basadas en medias móviles generan crecimiento del capital mayor que el activo subyacente, evidenciando ineficiencia parcial del mercado.
- **Verificación:** API de arXiv confirma título, autores y abstract.
- **Acceso:** https://arxiv.org/abs/cond-mat/0011337

### Fuente 2 — Reglas técnicas intradiarias en forex (VERIFICABLE)
- **Autor(es):** Cheung, Y.W. & Wong, C.Y.P.
- **Año:** 1997
- **Publicación:** *Journal of Financial Economics* — "Do technical trading rules generate profits? Conclusions from the intra-day foreign exchange market"
- **Sección relevante:** Demuestra que reglas de trading técnico generan retornos significativos en mercados de divisas intradiarios
- **Verificación:** DOI 10.1002/(sici)1099-1158(199710)2:4<267::aid-jfe57>3.0.co;2-j

### Fuente 3 — Uso de análisis técnico por dealers de forex (VERIFICABLE)
- **Autor(es):** So, M.K.P., Lam, K. & Yeung, W.K.
- **Año:** 1998
- **Publicación:** *Journal of International Financial Markets, Institutions and Money*
- **Sección relevante:** Encuesta confirma que medias móviles y osciladores de momentum son las herramientas más usadas por profesionales
- **Verificación:** DOI 10.1016/s0261-5606(98)00011-4

**Nota de transparencia:** La Fuente 1 fue verificada directamente con la API de arXiv (abstract confirmado). Las Fuentes 2 y 3 fueron verificadas por DOI vía OpenAlex. No he leído los papers completos de las fuentes 2 y 3 — solo títulos y abstracts.


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

1. **Datos antiguos (Fuente 1: Baviera et al. 2000, datos pre-2000; Fuente 2: Cheung & Wong 1997, datos de los 90).** El mercado EURUSD en 2020-2025 tiene características estructurales muy diferentes: QBs, tipos de interés negativos, guerra en Ucrania, sentiment de divisas como safe haven. Un edge que existía en los 90 puede estar arbitraged away hoy.

2. **ADX(14) > 25 en EURUSD H1 es muy restrictivo.** EURUSD pasa largos periodos en rango (< 200 pips en un mes). Si ADX no supera 25, no se genera señal. El riesgo principal es que el filtro de sesión + ADX produzca < 100 trades IS en el período propuesto.

3. **Sesión europea reduce la muestra.** De ~24 horas/día de mercado forex, solo operamos en 8 horas × 5 días = ~20 barras candidatas/día. Menos oportunidades = menos trades = difícil alcanzar 100 trades IS en 3.5 años. Si no se alcanzan 100 trades IS → REJECTED por criterio de minimum sample.

4. **EMA(12,26) y ADX(14) son defaults de MetaTrader 5.** No están optimizados para EURUSD H1. Son los valores que el 90% de los traders minoristas usan, lo que crea un posible bias: si hay edge, puede ser porque miles de traders crean el mismo patrón de entrada/salida (self-fulfilling prophecy), que desaparece si el sentimiento cambia.

5. **Sin filtro de noticias macro.** Eventos como NFP, decisiones de ECB/FOMC, discursos de gobernadores — pueden causar velas H1 de 150-300 pips. Un SL de 50 pips puede tocar frecuente en estos contextos, antes de que TP se alcance.

6. **Baviera et al. modelan medias de log-precios, no cruces.** La aplicación directa al cruce EMA(12/26) es una extensión que necesita validación empírica. El paper justifica el momentum de medias, pero no el cruce específico como señal de entrada.

7. **Posible look-ahead bias en la definición de sesión.** La sesión europea (07:00-15:00 UTC) es fija. Si la hora de la barra H1 es la hora de apertura (estándar MT5), la señal se calcula al cierre de la barra, no al inicio. Esto debería funcionar correctamente en la plantilla (el bloque congelado solo actúa en nueva barra), pero debe verificarse.


## Estado
`SPECIFIED` — Pendiente de aprobación humana antes de CODED.

## Fecha de creación
2026-05-30
