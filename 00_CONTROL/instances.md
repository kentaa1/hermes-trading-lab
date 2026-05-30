# Registro de Instancias — Hermes-Trading-Lab

## Propósito

Este archivo registra las instancias de modelos asignadas a cada rol.

## Instancias activas

| Rol | Modelo | Estado | Notas |
|---|---|---|---|
| Coordinador Operativo | `openrouter/owl-alpha` | ✅ Activo | Orquestador principal |
| Gestor de Riesgo | `nvidia/nemotron-3-super-120b-a12b:free` | ✅ Disponible | Se invoca cuando se necesita análisis de riesgo |
| Coder MQL5 | `qwen/qwen3-coder:free` | ✅ Disponible | Se delega para tareas de código MQL5 |
| Estratega | `moonshotai/kimi-k2.6:free` | ✅ Disponible | Se delega para diseño de estrategias e hipótesis |
| Auxiliar 1 | `deepseek/deepseek-v4-flash:free` | ✅ Disponible | Soporte general |
| Auxiliar 2 | `z-ai/glm-4.5-air:free` | ✅ Disponible | Soporte general |

## Política de delegación

- El Coordinador **nunca** implementa código MQL5 directamente
- El Coordinador **nunca** hace análisis de riesgo directamente
- Para código → delegar al Coder MQL5 con contexto completo
- Para riesgo → delegar al Gestor de Riesgo con estrategia documentada
- Para diseño de estrategia → delegar al Estratega con research disponible

## Historial de instancias

| Fecha | Rol | Modelo | Acción |
|---|---|---|---|
| 2026-05-30 | Todos | Según tabla | Configuración inicial |
