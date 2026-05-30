# Estados de Experimento — Hermes-Trading-Lab

## Diagrama de estados

```
                    ┌──────────┐
                    │   IDEA   │
                    └────┬─────┘
                         │ ¿Fuente + falsable + reglas?
                         ▼
                    ┌──────────────┐
                    │  SPECIFIED   │
                    └────┬─────────┘
                         │ ¿Ficha completa + commit?
                         ▼
                    ┌──────────┐
                    │  CODED   │
                    └────┬─────┘
                         │ ¿.bloque editable modificado correctamente?
                         ▼
                    ┌────────────┐
                    │  COMPILED  │
                    └────┬───────┘
                         │ ¿0 errores en MetaEditor?
                         ▼
                    ┌──────────────┐
                    │  BACKTESTED  │
                    └────┬─────────┘
                         │ ¿Métricas completas?
                         ▼
                 ┌───────┴───────┐
                 │               │
          ┌──────┴─────┐  ┌─────┴──────┐
          │  REJECTED  │  │   REWORK   │
          └────────────┘  └─────┬──────┘
                                │ max 2 iteraciones
                                ▼
                          ┌────────────┐
                          │  REJECTED  │
                          └────────────┘
```

## Descripción de estados

| Estado | Significado | Entregable |
|---|---|---|
| **IDEA** | Hipótesis sin especificar. Puede venir de research o intuición documentada | Nota en 10_RESEARCH/ |
| **SPECIFIED** | Hipótesis con fuente, parámetros, crítica metodológica y regla observable | Ficha en 02_STRATEGIES/ con checkbox. Commit. |
| **CODED** | Lógica implementada en bloque editable de plantilla MQL5 | Archivo .mq5 en 03_MQL5/ |
| **COMPILED** | Compilación exitosa en MetaEditor | Log de compilación guardado |
| **BACKTESTED** | Strategy Tester ejecutado, métricas IS/OOS obtenidas | Carpeta en 04_BACKTESTS/EXP_NNN/ |
| **REJECTED** | No cumple criterios. Archivado en 09_SANDBOX/ | Nota con razón específica del rechazo |
| **REWORK** | Fallo marginal, causa reparable. Máximo 2 reworks antes de REJECTED | Nota con qué se cambia y por qué |

## Decisiones terminales

| Decisión | Cuándo |
|---|---|
| REJECTED | No cumple 1+ criterios por margen no reparable |
| REWORK | Fallo marginal, causa identificada, cambio acotado |
| APPROVED_FOR_MORE_TESTING | Cumple IS/OOS pero necesita más validación |
| APPROVED_FOR_DEMO | Solo con DEMO_READY desbloqueado por humano |

## Regla de rework

Máximo **2 iteraciones** de rework por experimento. Si el segundo rework no aprueba → REJECTED automático. No hay tercera oportunidad.
