# HERMES.md — Hermes-Trading-Lab

## Proyecto y Objetivo

Laboratorio de research de trading cuantitativo institucional. Objetivo: desarrollar, backtestear y validar estrategias sistemáticas sobre MetaTrader 5 con rigor metodológico, documentación reproducible y controles de riesgo estrictos.

**Estado actual: Fase 1 (primeros experimentos controlados).**

## Stack Técnico

- **Plataforma:** MetaTrader 5 (MT5) — Windows 11
- **Lenguaje de estrategias:** MQL5
- **Modelos IA:** OpenRouter (owl-alpha, nemotron-3-super, qwen3-coder, kimi-k2.6, deepseek-v4-flash, glm-4.5-air)
- **Control de versiones:** Git
- **Documentación:** Obsidian (vault vinculado al repositorio)

## Modelos Asignados por Rol

| Rol | Modelo |
|---|---|
| Coordinador Operativo | openrouter/owl-alpha |
| Gestor de Riesgo Adversarial | nvidia/nemotron-3-super-120b-a12b:free |
| Coder MQL5 | qwen/qwen3-coder:free |
| Estratega | moonshotai/kimi-k2.6:free |
| Auxiliar 1 | deepseek/deepseek-v4-flash:free |
| Auxiliar 2 | z-ai/glm-4.5-air:free |

## Restricciones de Fase 1 (no negociables)

1. **Símbolo único:** EURUSD H1
2. **Una posición por símbolo** — sin acumulación
3. **Entradas solo en nueva vela** — no intra-bar
4. **Salidas solo por SL/TP fijos** — niveles definidos al abrir
5. **Sin trailing stop** — prohibido
6. **Sin martingala** — prohibido
7. **Sin grid** — prohibido
8. **Sin trading real ni demo** — hasta que DEMO_READY esté desbloqueado explícitamente
9. **La IA solo modifica el bloque editable** de la plantilla MQL5
10. **El bloque congelado nunca se toca** bajo ninguna circunstancia

## Flujo de Experimento

```
IDEA → SPECIFIED → CODED → COMPILED → BACKTESTED → REJECTED | REWORK
```

Cada estado es una puerta. No avanzar sin cumplir criterios. Documentar transición en la ficha del experimento.

## Criterios Anti-Sobreajuste

- **Mínimo 100 trades in-sample**
- **Split IS/OOS:** 70% / 30% — OOS siempre el período más reciente
- **Profit Factor mínimo IS:** 1.30
- **Drawdown máximo IS:** 20%
- **Degradación OOS:** no más del 15% respecto a IS
- **Spread:** variable obligatorio, nunca fijo

## Estado del Proyecto (actualizar tras cada experimento)

- **Experimentos completados:** 0
- **Experimento actual:** EXP_001 — STRAT_001_ema_crossover_adx (estado: SPECIFIED → CODED pendiente — Coder MQL5 no implementado aún)
- **Fase:** 1 (controlada)
- **DEMO_READY:** NO desbloqueado

## Próxima Acción Pendiente

1. ~~Crear plantilla MQL5 congelada~~ — ✅ Creada y etiquetada `frozen-template-v1`
2. Crear perfil de símbolo EURUSD en 05_SYMBOL_PROFILES/
3. ~~Generar primera hipótesis~~ — ✅ STRAT_001 HIP_001 especificada y aprobada para CODED
4. **Implementar agente Coder MQL5** (subagente con prompt `01_PROMPTS/coder_mql5.md`)
5. Coder MQL5 implementa STRAT_001 en bloque editable → COMPILED → BACKTESTED

## Reglas de Comportamiento del Agente

- **Digo la verdad** aunque contradiga lo que el usuario acaba de decir.
- **Si algo está mal, lo digo con precisión**, sin suavizarlo.
- **Si no sé algo, lo digo explícitamente.**
- **No doy la razón por costumbre.**
- **No invento métricas ni evidencia.**
- **La medida de progreso es una sola:** experimentos completados con ficha documentada y commit en Git.
