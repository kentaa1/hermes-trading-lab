//+------------------------------------------------------------------+
//|                                    HermesBase_Template.mq5       |
//|                          Hermes-Trading-Lab — Plantilla Base     |
//|                                    Fase 1: EURUSD H1            |
//+------------------------------------------------------------------+
//
//  PLANTILLA CONGELADA v1 — NUNCA MODIFICAR EL BLOQUE CONGELADO
//  Ver: AGENTS.md, 01_PROMPTS/coder_mql5.md
//
//  Regla absoluta: la IA solo modifica el BLOQUE EDITABLE.
//  El bloque congelado es el motor de ejecución. Se etiqueta como
//  frozen-template-v1 en Git y no cambia jamás.
//
//+------------------------------------------------------------------+
#property copyright "Hermes-Trading-Lab"
#property link      ""
#property version   "1.00"
#property strict
#property description "Plantilla base del laboratorio. Bloque congelado + editable."

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//+------------------------------------------------------------------+
//|  BLOQUE CONGELADO — MOTOR DE EJECUCIÓN                          |
//|  ¡¡NO MODIFICAR!!                                               |
//+------------------------------------------------------------------+

//--- Input: Parámetros de gestión de órdenes
input long   InpMagic       = 100001;       // Magic Number (identificador único)
input double InpRiskPct     = 1.0;          // Riesgo por operación (% del balance)
input int    InpStopLoss    = 50;           // Stop Loss (en puntos)
input int    InpTakeProfit  = 100;          // Take Profit (en puntos)
input int    InpSlippage    = 10;           // Slippage máximo (en puntos)

//--- Objetos globales
CTrade         trade;
CPositionInfo  posInfo;
CSymbolInfo    symInfo;

//--- Variables de barra nueva
datetime lastBarTime = 0;

//+------------------------------------------------------------------+
//|  Funciones del motor (congeladas)                               |
//+------------------------------------------------------------------+

//--- IsNewBar(): devuelve true solo en nueva vela de H1
bool IsNewBar()
{
   datetime currentBarTime = iTime(_Symbol, PERIOD_H1, 0);
   if(currentBarTime != lastBarTime)
   {
      lastBarTime = currentBarTime;
      return true;
   }
   return false;
}

//--- HasOpenPosition(): devuelve true si hay posición abierta con el magic number actual
bool HasOpenPosition()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(posInfo.SelectByIndex(i))
      {
         if(posInfo.Symbol() == _Symbol && posInfo.Magic() == InpMagic)
            return true;
      }
   }
   return false;
}

//--- Capital fijo para Fase 1 (sin compounding)
input double InpFixedCapital = 10000.0; // Capital fijo de referencia (USD)

//--- CalcLotSize(): calcula el tamaño de lote según riesgo % y SL en puntos
double CalcLotSize(double slPoints)
{
   if(slPoints <= 0) return 0;

   double tickValue = symInfo.TickValue();
   double tickSize  = symInfo.TickSize();
   double riskMoney = InpFixedCapital * InpRiskPct / 100.0;
   double lotSize   = riskMoney / (slPoints * tickValue);
   double minLot    = symInfo.LotsMin();
   double maxLot    = symInfo.LotsMax();
   double lotStep   = symInfo.LotsStep();

   //--- Ajustar al lot step más cercano hacia abajo
   lotSize = MathFloor(lotSize / lotStep) * lotStep;
   lotSize = MathMax(minLot, MathMin(lotSize, maxLot));

   return lotSize;
}

//+------------------------------------------------------------------+
//|  Inicialización                                                  |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Configurar objeto de trading
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippage);
   trade.SetTypeFilling(ORDER_FILLING_IOC);

   //--- Inicializar info del símbolo
   if(!symInfo.Name(_Symbol))
   {
      Print("ERROR: no se pudo inicializar SymbolInfo para ", _Symbol);
      return INIT_FAILED;
   }
   symInfo.Refresh();

   lastBarTime = 0;

   //--- Inicializar indicadores del bloque editable
   if(OnStrategyInit() != INIT_SUCCEEDED)
   {
      Print("ERROR: fallo al inicializar indicadores de estrategia");
      return INIT_FAILED;
   }

   Print("HermesBase_Template v1.00 inicializado. Magic=", InpMagic,
         " Risk=", InpRiskPct, "% SL=", InpStopLoss, " TP=", InpTakeProfit);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//|  Tick — Solo actúa en nueva vela, solo si no hay posición       |
//+------------------------------------------------------------------+
void OnTick()
{
   //--- Solo ejecutar en nueva barra H1
   if(!IsNewBar()) return;

   //--- Una posición por símbolo: no abrir si hay posición abierta
   if(HasOpenPosition()) return;

   //--- Refrescar datos del símbolo
   symInfo.Refresh();
   symInfo.RefreshRates();

   //--- Obtener señal de la estrategia (bloque editable)
   int signal = GetStrategySignal(); // -1 = sell, 0 = neutral, +1 = buy

   if(signal == 0) return; // Sin señal

   double lotSize = CalcLotSize((double)InpStopLoss);
   if(lotSize <= 0)
   {
      Print("WARN: lot size calculado <= 0, omitiendo operación");
      return;
   }

   symInfo.RefreshRates();
   double price = symInfo.Ask();

   if(signal > 0)
   {
      //--- Comprar
      double sl = price - InpStopLoss * symInfo.Point();
      double tp = price + InpTakeProfit * symInfo.Point();
      if(!trade.Buy(lotSize, _Symbol, price, sl, tp, "Hermes EXP"))
      {
         Print("ERROR Buy: ", GetLastError());
      }
      else
      {
         Print("BUY abierto: lot=", lotSize, " SL=", sl, " TP=", tp);
      }
   }
   else if(signal < 0)
   {
      //--- Vender
      double sl = price + InpStopLoss * symInfo.Point();
      double tp = price - InpTakeProfit * symInfo.Point();
      if(!trade.Sell(lotSize, _Symbol, price, sl, tp, "Hermes EXP"))
      {
         Print("ERROR Sell: ", GetLastError());
      }
      else
      {
         Print("SELL abierto: lot=", lotSize, " SL=", sl, " TP=", tp);
      }
   }
}
//+------------------------------------------------------------------+
//|  FIN BLOQUE CONGELADO                                           |
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//|  BLOQUE EDITABLE — ESTRATEGIA                                   |
//|  Límites de este bloque:                                        |
//|   ✅ Definir inputs de parámetros de indicadores                |
//|   ✅ Calcular señales de entrada/salida con indicadores         |
//|   ✅ Definir señal en GetStrategySignal()                        |
//|   ❌ Acceder a Close() / PositionClose() / trade.PositionClose()|
//|   ❌ Modificar cualquier cosa fuera de este bloque              |
//|   ❌ Usar trailing stop, martingala, grid                        |
//|   ❌ Modificar SL/TP definidos en el bloque congelado           |
//|   ❌ Abrir/cerrar posiciones directamente                       |
//+------------------------------------------------------------------+

//--- TODO: Aquí se definen los parámetros de la estrategia (inputs)
input int    InpEmaFastPeriod = 12;    // EMA rápida (periodos)
input int    InpEmaSlowPeriod = 26;    // EMA lenta (periodos)
input ENUM_APPLIED_PRICE InpEmaPrice = PRICE_CLOSE; // Precio aplicado

//--- TODO: Declarar handles de indicadores aquí
int handleEmaFast = INVALID_HANDLE;
int handleEmaSlow = INVALID_HANDLE;

//+------------------------------------------------------------------+
//|  OnInit editable: inicializar handles de indicadores             |
//+------------------------------------------------------------------+
int OnStrategyInit()
{
   // TODO: Crear handles de indicadores
   // handleEmaFast = iMA(_Symbol, PERIOD_H1, InpEmaFastPeriod, 0, MODE_EMA, InpEmaPrice);
   // handleEmaSlow = iMA(_Symbol, PERIOD_H1, InpEmaSlowPeriod, 0, MODE_EMA, InpEmaPrice);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//|  GetStrategySignal(): calcula la señal de la estrategia         |
//|  Devuelve: +1 = compra, -1 = venta, 0 = sin señal              |
//+------------------------------------------------------------------+
int GetStrategySignal()
{
   // TODO: Implementar lógica de señales aquí
   //
   // Ejemplo:
   //   double emaFast[], emaSlow[];
   //   if(CopyBuffer(handleEmaFast, 0, 0, 3, emaFast) < 3) return 0;
   //   if(CopyBuffer(handleEmaSlow, 0, 0, 3, emaSlow) < 3) return 0;
   //
   //   // Cruce alcista: emaFast cruza por encima de emaSlow
   //   if(emaFast[1] > emaSlow[1] && emaFast[2] <= emaSlow[2]) return +1;
   //   // Cruce bajista: emaFast cruza por debajo de emaSlow
   //   if(emaFast[1] < emaSlow[1] && emaFast[2] >= emaSlow[2]) return -1;

   return 0; // Neutral por defecto
}

//+------------------------------------------------------------------+
//|  FIN BLOQUE EDITABLE — ESTRATEGIA                               |
//+------------------------------------------------------------------+
 // <<< FIN DEL ARCHIVO >>>   
 // >>> NO ESCRIBA NADA DEBAJO DE ESTA LÍNEA <<<