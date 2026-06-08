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
#property version   "1.10"
#property strict
#property description "Plantilla base del laboratorio. Bloque congelado + editable."

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//+------------------------------------------------------------------+
//|  BLOQUE EDITABLE — ESTRATEGIA (DECLARACIONES FORWARD)           |
//|  Los inputs y forward declarations van ANTES del bloque         |
//|  congelado porque MQL5 requiere declaraciones previas.          |
//+------------------------------------------------------------------+

//--- Parámetros de la estrategia STRAT_001
input int    InpEmaFastPeriod  = 12;    // EMA rápida (periodos)
input int    InpEmaSlowPeriod  = 26;    // EMA lenta (periodos)
input int    InpAdxPeriod      = 14;    // ADX periodo
input int    InpAdxThreshold   = 25;    // ADX umbral mínimo (tendencia activa)
input int    InpSessionStart   = 7;     // Hora inicio sesión (UTC)
input int    InpSessionEnd     = 15;    // Hora fin sesión (UTC)

//--- Handles de indicadores (declaración global)
int handleEmaFast  = INVALID_HANDLE;
int handleEmaSlow  = INVALID_HANDLE;
int handleAdx      = INVALID_HANDLE;

//--- Forward declarations (requeridas por MQL5)
int  OnStrategyInit();
int  GetStrategySignal();
bool IsSessionActive();

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
input double InpFixedCapital = 10000.0;     // Capital fijo de referencia (USD)

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

   Print("HermesBase_Template v1.10 inicializado. Magic=", InpMagic,
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
//|  BLOQUE EDITABLE — ESTRATEGIA (IMPLEMENTACIONES)                |
//|  STRAT_001: Cruce EMA + Filtro ADX + Sesión Europea             |
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

//+------------------------------------------------------------------+
//|  OnStrategyInit: inicializar handles de indicadores             |
//+------------------------------------------------------------------+
int OnStrategyInit()
{
   handleEmaFast = iMA(_Symbol, PERIOD_H1, InpEmaFastPeriod, 0, MODE_EMA, PRICE_CLOSE);
   handleEmaSlow = iMA(_Symbol, PERIOD_H1, InpEmaSlowPeriod, 0, MODE_EMA, PRICE_CLOSE);
   handleAdx     = iADX(_Symbol, PERIOD_H1, InpAdxPeriod);

   if(handleEmaFast == INVALID_HANDLE || handleEmaSlow == INVALID_HANDLE || handleAdx == INVALID_HANDLE)
   {
      Print("ERROR: no se pudieron crear handles de indicadores");
      return INIT_FAILED;
   }

   Print("STRAT_001 inicializado. EMA(", InpEmaFastPeriod, ",", InpEmaSlowPeriod,
         ") ADX(", InpAdxPeriod, ">", InpAdxThreshold, ") Sesión: ", InpSessionStart, "-", InpSessionEnd, "UTC");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//|  IsSessionActive: verifica si la hora está en sesión europea    |
//+------------------------------------------------------------------+
bool IsSessionActive()
{
   MqlDateTime dt;
   datetime barTime = iTime(_Symbol, PERIOD_H1, 0);
   TimeToStruct(barTime, dt);

   if(dt.hour >= InpSessionStart && dt.hour < InpSessionEnd)
      return true;

   return false;
}

//+------------------------------------------------------------------+
//|  GetStrategySignal: calcula la señal de la estrategia           |
//|  Devuelve: +1 = compra, -1 = venta, 0 = sin señal              |
//+------------------------------------------------------------------+
int GetStrategySignal()
{
   //--- Verificar sesión europea
   if(!IsSessionActive()) return 0;

   //--- Obtener valores de indicadores (barra 1 = cerrada, barra 2 = anterior)
   double emaFast[], emaSlow[], adxMain[];

   if(CopyBuffer(handleEmaFast, 0, 0, 3, emaFast) < 3) return 0;
   if(CopyBuffer(handleEmaSlow, 0, 0, 3, emaSlow) < 3) return 0;
   if(CopyBuffer(handleAdx, 0, 0, 2, adxMain) < 2) return 0;

   //--- Filtro ADX: tendencia activa
   if(adxMain[1] <= InpAdxThreshold) return 0;

   //--- Cruce alcista: EMA rápida cruza por encima de EMA lenta
   if(emaFast[1] > emaSlow[1] && emaFast[2] <= emaSlow[2])
      return +1;

   //--- Cruce bajista: EMA rápida cruza por debajo de EMA lenta
   if(emaFast[1] < emaSlow[1] && emaFast[2] >= emaSlow[2])
      return -1;

   return 0; // Sin señal
}

//+------------------------------------------------------------------+
//|  FIN BLOQUE EDITABLE — ESTRATEGIA                               |
//+------------------------------------------------------------------+
// <<< FIN DEL ARCHIVO >>>
// >>> NO ESCRIBA NADA DEBAJO DE ESTA LÍNEA <<<
