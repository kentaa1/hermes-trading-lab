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

| Concepto | Valor | Notas |
|---|---|---|
| **Tipo de cuenta** | Raw Spread / Zero (recomendado para backtest) | Spreads más bajos, comisión por lote |
| **Spread EURUSD (típico)** | 0.0 – 0.3 pips (Raw) / 0.6 – 1.2 pips (Standard) | Variable según sesión |
| **Spread EURUSD (máximo histórico)** | 3-5 pips en eventos de alta volatilidad | NFP, FOMC, BCE |
| **Comisión (Raw Spread)** | ~$3.5 USD por lote por lado ($7 round-trip) | Solo en cuenta Raw |
| **Swap long EURUSD** | Negativo (varía ~-0.5 a -2.0 pips/día) | Verificar con broker |
| **Swap short EURUSD** | Positivo o negativo (según diferencial de tasas) | Verificar con broker |
| **Slippage esperado** | 0.1 – 0.5 pips (normal), hasta 2-3 pips (noticias) | Backtest debe incluir al menos 0.3 pips |
| **Requisito de margen** | 1:20 a 1:2000 (varía por cuenta) | Para backtest con 10K, suficiente |

## Datos por Sesión (Exness Raw Spread)

| Sesión | Hora UTC | Spread típico EURUSD | Características |
|---|---|---|---|
| **Asia (Tokio)** | 00:00 – 08:00 | 0.3 – 0.8 pips | Menor liquidez, spread más amplio |
| **Europa (Londres)** | 07:00 – 16:00 | 0.0 – 0.3 pips | Máxima liquidez, spread mínimo |
| **Nueva York** | 12:00 – 21:00 | 0.0 – 0.4 pips | Alta liquidez, overlap con Londres |
| **Overlap EU/US** | 12:00 – 16:00 | 0.0 – 0.2 pips | Mejor ejecución del día |
| **Pre/Post mercado** | 21:00 – 00:00 | 0.5 – 1.5 pips | Menor liquidez |

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
