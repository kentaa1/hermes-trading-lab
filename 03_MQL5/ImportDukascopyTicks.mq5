//+------------------------------------------------------------------+
//|                                     ImportDukascopyTicks.mq5   |
//|                          Hermes-Trading-Lab — Importación datos |
//|                          Crea símbolo personalizado EURUSD_DUKA |
//+------------------------------------------------------------------+
#property copyright "Hermes-Trading-Lab"
#property link      ""
#property version   "1.00"
#property strict
#property description "Importa ticks Dukascopy CSV a símbolo personalizado MT5"

//--- Parámetros
input string InpCustomSymbol = "EURUSD_DUKA"; // Nombre del símbolo personalizado
input string InpCsvFile      = "EURUSD_ticks_2020_01.csv"; // Archivo CSV en MQL5/Files/
input bool   InpCreateSymbol = true;  // Crear símbolo si no existe
input int    InpDigits       = 5;     // Decimales del símbolo
input int    InpSpread       = 1;     // Spread por defecto (puntos)
input double InpPoint        = 0.00001; // Tamaño del punto
input double InpTickSize     = 0.00001; // Tamaño del tick
input double InpTickValue    = 1.0;   // Valor del tick en moneda de depósito

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
{
   Print("=== ImportDukascopyTicks v1.00 ===");
   
   //--- Paso 1: Verificar/crear símbolo personalizado
   if(InpCreateSymbol)
   {
      if(!CustomSymbolCreate(InpCustomSymbol, "EURUSD"))
         {
            Print("ERROR: No se pudo crear símbolo personalizado. Error: ", GetLastError());
            Print("  Asegúrate de que MT5 permite símbolos personalizados.");
            return;
         }
      // Si ya existe, CustomSymbolCreate devuelve false con error 5300 — eso está bien
      if(GetLastError() != 0 && GetLastError() != 5300)
      {
         // Error real
      }
      else
      {
         Print("Símbolo personalizado listo: ", InpCustomSymbol);
      }
      
      //--- Configurar propiedades del símbolo
      CustomSymbolSetInteger(InpCustomSymbol, SYMBOL_DIGITS, InpDigits);
      CustomSymbolSetInteger(InpCustomSymbol, SYMBOL_SPREAD, InpSpread);
      CustomSymbolSetDouble(InpCustomSymbol, SYMBOL_POINT, InpPoint);
      CustomSymbolSetDouble(InpCustomSymbol, SYMBOL_TRADE_TICK_SIZE, InpTickSize);
      CustomSymbolSetDouble(InpCustomSymbol, SYMBOL_TRADE_TICK_VALUE, InpTickValue);
      CustomSymbolSetDouble(InpCustomSymbol, SYMBOL_VOLUME_MIN, 0.01);
      CustomSymbolSetDouble(InpCustomSymbol, SYMBOL_VOLUME_MAX, 100.0);
      CustomSymbolSetDouble(InpCustomSymbol, SYMBOL_VOLUME_STEP, 0.01);
      
      Print("Propiedades del símbolo configuradas.");
   }
   
   //--- Paso 2: Leer CSV y importar ticks
   // El CSV debe estar en MQL5/Files/ del terminal
   // Formato: DateTime,Bid,Ask,Volume,Flags
   
   int fileHandle = FileOpen(InpCsvFile, FILE_READ | FILE_CSV | FILE_ANSI, ",");
   if(fileHandle == INVALID_HANDLE)
   {
      Print("ERROR: No se pudo abrir archivo CSV: ", InpCsvFile);
      Print("  Error: ", GetLastError());
      Print("  El archivo debe estar en: <MT5_data_folder>/MQL5/Files/");
      return;
   }
   
   //--- Leer header
   string header = FileReadString(fileHandle);
   Print("Header del CSV: ", header);
   
   //--- Leer ticks y agregar al símbolo
   MqlTick customTicks[];
   ArrayResize(customTicks, 0);
   
   int totalRead = 0;
   int totalImported = 0;
   int batchSize = 100000; // Importar en lotes para eficiencia
   
   while(!FileIsEnding(fileHandle))
   {
      string dateTimeStr = FileReadString(fileHandle);
      if(dateTimeStr == "") break;
      
      string bidStr   = FileReadString(fileHandle);
      string askStr   = FileReadString(fileHandle);
      string volStr   = FileReadString(fileHandle);
      string flagsStr = FileReadString(fileHandle);
      
      //--- Parsear valores
      datetime tickTime = StringToTime(dateTimeStr);
      // Añadir milisegundos si están presentes
      int msPos = StringFind(dateTimeStr, ".");
      int milliseconds = 0;
      if(msPos > 0)
      {
         string msStr = StringSubstr(dateTimeStr, msPos + 1, 3);
         milliseconds = (int)StringToInteger(msStr);
      }
      
      long tickTimeMSC = (long)tickTime * 1000 + milliseconds;
      
      double bid = StringToDouble(bidStr);
      double ask = StringToDouble(askStr);
      long   vol = (long)StringToInteger(volStr);
      uint   flags = (uint)StringToInteger(flagsStr);
      
      if(flags == 0) flags = TICK_FLAG_BID | TICK_FLAG_ASK;
      
      //--- Agregar al array
      int size = ArraySize(customTicks);
      ArrayResize(customTicks, size + 1);
      
      customTicks[size].time = tickTime;
      customTicks[size].time_msc = tickTimeMSC;
      customTicks[size].bid = bid;
      customTicks[size].ask = ask;
      customTicks[size].last = 0;
      customTicks[size].volume = vol;
      customTicks[size].flags = flags;
      
      totalRead++;
      
      //--- Importar en lotes
      if(ArraySize(customTicks) >= batchSize)
      {
         if(CustomTicksAdd(InpCustomSymbol, customTicks) > 0)
         {
            totalImported += ArraySize(customTicks);
         }
         ArrayResize(customTicks, 0);
         
         if(totalImported % 1000000 == 0)
         {
            Print("  Importados: ", totalImported, " ticks...");
         }
      }
   }
   
   //--- Importar ticks restantes
   if(ArraySize(customTicks) > 0)
   {
      if(CustomTicksAdd(InpCustomSymbol, customTicks) > 0)
      {
         totalImported += ArraySize(customTicks);
      }
   }
   
   FileClose(fileHandle);
   
   //--- Reporte final
   Print("=== Importación completada ===");
   Print("  Ticks leídos del CSV:   ", totalRead);
   Print("  Ticks importados a MT5: ", totalImported);
   Print("  Símbolo personalizado:  ", InpCustomSymbol);
   Print("");
   Print("  Siguiente paso: Ejecutar backtest con symbol=", InpCustomSymbol);
}

//+------------------------------------------------------------------+
