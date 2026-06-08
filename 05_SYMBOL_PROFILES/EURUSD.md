# Perfil de Símbolo — EURUSD

## Información General

| Campo | Valor |
|---|---|
| **Símbolo** | EURUSD |
| **Descripción** | Euro vs US Dollar |
| **Timeframe Fase 1** | H1 |
| **Categoría** | Forex Mayor |

## Especificaciones del Símbolo

| Campo | Valor |
|---|---|
| **Tamaño del contrato** | 100,000 unidades (1 lote estándar) |
| **Punto (tick)** | 0.00001 (5 decimales) |
| **Valor del punto** | ~10 USD por lote estándar (varía con el precio) |
| **Spread típico** | 0.5-1.5 pips (broker dependiente) |
| **Min lot** | 0.01 (varía por broker) |
| **Max lot** | 50-100 (varía por broker) |
| **Lot step** | 0.01 (varía por broker) |

## Datos Históricos

| Campo | Valor |
|---|---|
| **Fuente** | Dukascopy |
| **Formato origen** | .bi5 / .csv |
| **Rango disponible** | 2003 – presente |
| **Modo de test** | Every tick based on real ticks |
| **Importación** | Símbolo personalizado en MT5 |

## Costes de Transacción

| Concepto | Valor |
|---|---|
| **Comisiones** | [PENDIENTE — definir broker] |
| **Swap long** | [PENDIENTE — verificar con broker] |
| **Swap short** | [PENDIENTE — verificar con broker] |

## Sesiones de Mercado (UTC)

| Sesión | Horario | Características |
|---|---|---|
| **Asia (Tokio)** | 00:00 – 08:00 | Baja volatilidad, rango estrecho |
| **Europa (Londres)** | 07:00 – 16:00 | Alta volatilidad, tendencias |
| **Nueva York** | 12:00 – 21:00 | Alta volatilidad, overlaps con Londres |
| **Overlap EU/US** | 12:00 – 16:00 | Máxima volatilidad |

## Eventos de Alto Impacto (Calendario Estrés)

| Evento | Frecuencia | Impacto |
|---|---|---|
| **NFP** | Mensual (viernes 1er viernes) | Alto — spread se amplía 3-5x |
| **FOMC** | 8 veces/año | Alto — volatilidad extrema |
| **BCE** | 8 veces/año | Alto — volatilidad EUR |
| **CPI US** | Mensual | Medio-Alto |
| **GDP** | Trimestral | Medio |

## Estado de Validación

| Check | Estado |
|---|---|
| Datos Dukascopy importados | ⬜ PENDIENTE |
| DATA_IMPORT_VALIDATION_REPORT.md | ⬜ PENDIENTE |
| MT5_ENGINE_VALIDATION_REPORT.md | ⬜ PENDIENTE |
| Spread verificado vs benchmark | ⬜ PENDIENTE |
| Broker definido | ⬜ PENDIENTE |

## Notas

- El perfil debe completarse con datos REALES del broker antes de EXP_001
- El spread variable es obligatorio — nunca usar spread fijo en backtest
- Las ventanas de estrés (NFP, FOMC, BCE) requieren spread triplicado en el modelo de costes pesimista
