# Criterios de Backtest — Hermes-Trading-Lab

## In-Sample

| Criterio | Valor mínimo |
|---|---|
| Trades | >= 100 |
| Profit Factor | >= 1.30 |
| Drawdown máximo | <= 20% |

## Out-of-Sample

| Criterio | Valor |
|---|---|
| Split temporal | 70% IS (más antiguo) / 30% OOS (más reciente) |
| Degradación OOS máxima | <= 15% vs IS |

## Configuración obligatoria

| Parámetro | Valor |
|---|---|
| Símbolo | EURUSD |
| Timeframe | H1 |
| Spread | Variable (nunca fijo) |
| Modelo de test | Every Tick |
| Slippage | Realista según broker (documentar cuál) |

## Criterio de evaluación

```
APROBADO si:
  PF_IS >= 1.30
  AND DD_IS <= 20%
  AND PF_OOS >= PF_IS * 0.85
  AND DD_OOS <= DD_IS * 1.15
  AND trades_IS >= 100
  AND esperanza_matemática > 0

REJECTED si cualquiera falla.
REWORK si falla por margen pequeño y la causa es reparable.
  Máximo 2 iteraciones de rework antes de REJECTED automático.
```

## Métricas registradas por cada backtest

- Trades totales (IS y OOS separados)
- Profit Factor (IS y OOS)
- Drawdown % (IS y OOS)
- Winrate (IS y OOS)
- Payoff ratio = avg_win / avg_loss (IS y OOS)
- Esperanza matemática
- Equity curve IS/OOS superpuesta
