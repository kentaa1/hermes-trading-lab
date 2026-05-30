# Políticas de Validación de Fuentes — Hermes-Trading-Lab

## Jerarquía de fuentes

| Nivel | Tipo | Validez | Uso permitido |
|---|---|---|---|
| **1 — Primaria** | Backtest propio (datos MT5) | Única evidencia real de edge | Validación de estrategia |
| **2 — Fuerte** | Paper académico (SSRN, arXiv, journal) con autor, año, publicación, sección | Generador de hipótesis fiable | Justificar IDEA → SPECIFIED |
| **2 — Fuerte** | Libro cuantitativo con ISBN | Generador de hipótesis fiable | Justificar IDEA → SPECIFIED |
| **3 — Débil** | Blog, foro, tweet, opinión de trader | Solo inspiración. NUNCA validación. | Generar IDEA únicamente |
| **0 — Inválido** | Resumen de LLM | **NUNCA fuente.** Solo borrador operativo. | Necesita verificación desde original |

## Citación obligatoria

Toda fuente de nivel 2 debe incluir:

1. **Autor(es)**
2. **Año de publicación**
3. **Publicación** (revista, conferencia, editorial, SSRN, arXiv)
4. **Sección/página relevante**

Sin estos 4 campos → la fuente NO es válida para justificar avance.

## Regla central

> Los papers y la literatura cuantitativa son **generadores de hipótesis**, nunca validadores de edge.
> Solo el backtest empírico con datos propios valida o rechaza una hipótesis.

## Proceso de validación de una fuente

```
1. ¿Tiene autor, año, publicación, sección? → NO → Rechazar como fuente
2. ¿El resumen coincide con el contenido real? → Verificar leyendo el paper
   → Si es un resumen de LLM → Buscar el paper original
3. ¿Es replicable la metodología? → Documentar cómo se traduce a MQL5
4. ¿Tiene crítica metodológica? → Documentar limitaciones conocidas
5. ¿Puede falsarse con backtest? → Documentar métrica y umbral que la rechazan
```

Si la fuente pasa los 5 pasos → puede justificar IDEA → SPECIFIED.

## Prohibido

- Avanzar una hipótesis basada únicamente en un resumen de LLM
- Citar un paper sin haber leído (al menos abstract, metodología, resultados)
- Usar como "evidencia" que "dicho por X en un foro"
- Usar performance pasado de un paper como garantía de futuro edge
