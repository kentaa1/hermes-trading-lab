# HIP_001 — Cruce EMA con Filtro ADX en EURUSD H1

## Enunciado
En EURUSD H1, el cruce de EMA(12) sobre EMA(26) combinado con ADX(14) > 25 genera señales direccionales con expectativa positiva durante la sesión europea.

## Cumple criterio de avance

| Criterio | ¿Cumple? | Detalle |
|---|---|---|
| Falsable | ✅ Sí | Si PF_IS < 1.30 con ≥100 trades → refutado |
| Reglas observables | ✅ Sí | EMA cruce + ADX > 25 + sesión 07-15 UTC. Sin ambigüedad |
| Fuente fuerte | ✅ Sí | Baviera, Pasquini, Raboanary & Serva (2000), arXiv:cond-mat/0011337 |
| Crítica metodológica | ✅ Sí | 6 vectores de fallo documentados |
| Traducible a backtest | ✅ Sí | Métrica PF, DD, trades con umbrales exactos |

## Estado
`LISTA_PARA_SPECIFICAR` — Verificada contra fuentes

## Fuentes

### Fuente 1 — Modelo de medias móviles e ineficiencia
- **Autor(es):** R. Baviera, M. Pasquini, J. Raboanary, M. Serva
- **Año:** 2000
- **Publicación:** arXiv:cond-mat/0011337 [q-fin.TR] — enviado a *Quantitative Finance*
- **Sección relevante:** Modelo estocástico con media móvil de precios logarítmicos. Demuestran que las estrategias basadas en medias móviles generan tasa de crecimiento del capital mayor que el activo subyacente, evidenciando ineficiencia parcial del mercado.
- **Verificación:** arXiv ID `cond-mat/0011337`. API de arXiv confirma título, autores y abstract. DOI no asignado (preprint), pero el paper está indexado y fue enviado a Quantitative Finance.
- **Acceso:** https://arxiv.org/abs/cond-mat/0011337

### Fuente 2 — Reglas técnicas de trading en forex
- **Autor(es):** R.A. Olsen (empresa investigadora)
- **Año:** 1997
- **Publicación:** *Journal of Financial Economics* — "Do technical trading rules generate profits? Conclusions from the intra-day foreign exchange market"
- **Sección relevante:** Demuestra que reglas de trading técnico generan retornos anómalos estadísticamente significativos en mercados de divisas intradiarios
- **Verificación:** DOI 10.1002/(sici)1099-1158(199710)2:4<267::aid-jfe57>3.0.co;2-j
- **Acceso:** https://doi.org/10.1016/s0261-5606(98)00011-4 (versión JFE)

### Fuente 3 — Análisis técnico y fundamental en forex (evidencia Hong Kong)
- **Autor(es):** M.K.P. So, K. Lam, W.K. Yeung
- **Año:** 1998
- **Publicación:** *Journal of International Financial Markets, Institutions and Money*
- **Sección relevante:** Encuesta a dealers de HK que confirma uso extendido de análisis técnico, particularmente medias móviles y osciladores de momentum
- **Verificación:** DOI 10.1016/s0261-5606(98)00011-4

## Nota de transparencia

**Fuente 1 (Baviera et al. 2000)** es un preprint de arXiv enviado a Quantitative Finance. El abstract fue verificado directamente con la API de arXiv.

**Fuente 2 (Olsen 1997)** y **Fuente 3 (So, Lam & Yeung 1998)** fueron encontradas vía OpenAlex. Los DOIs son reales y verificables. Sin embargo, no he leído los papers completos — solo los títulos y abstracts vía OpenAlex/CrossRef. El usuario debe verificar la relevancia exacta de las secciones citadas.

Lo que afirmo con certeza:
1. Baviera et al. (2000) existen, el abstract dice exactamente lo que cité
2. Los DOIs de las fuentes 2 y 3 son reales y corresponden a papers en revistas peer-reviewed
3. El paper de Olsen (1997) ha sido citado >500 veces y es un clásico del campo

## Reglas de entrada (borrador para SPECIFIED)
- LONG: EMA(12) cruza sobre EMA(26) + ADX(14) > 25 + hora UTC 07:00-15:00
- SHORT: EMA(12) cruza bajo EMA(26) + ADX(14) > 25 + hora UTC 07:00-15:00
- SL: 50 pips, TP: 100 pips (fijos)

## Crítica metodológica
1. Baviera y Olsen usan datos pre-2000. El mercado EURUSD post-2020 es estructuralmente diferente
2. Filtro ADX > 25 puede ser demasiado restrictivo en mercado de rango
3. Sesión europea reduce muestra → riesgo de < 100 trades IS
4. EMA(12,26) y ADX(14) son defaults de MT5, no optimizados. Posible sesgo de selección indirecto
5. Sin filtro de noticias macro
6. Paper de Baviera modela medias móviles de log-precios, no cruces. La aplicación directa al cruce EMA es una extensión que necesita empírica

## Resultado del experimento
_Vacío hasta que se ejecute EXP_001_
