//+------------------------------------------------------------------+
//|                                          ImportCSVToMT5.mq5     |
//|                          Hermes-Trading-Lab — Importador CSV v3 |
//+------------------------------------------------------------------+
#property copyright "Hermes-Trading-Lab"
#property version   "3.00"
#property strict
#property description "Importa barras M1 desde CSV tab-separated a historial de MT5"
#property script_show_inputs

input string InpCsvFile = "EURUSD_M1_201501020900_202606082251.csv";
input string InpSymbol  = "EURUSD";

void OnStart()
{
   Print("=== ImportCSVToMT5 v3.00 ===");
   
   if(!SymbolInfoInteger(InpSymbol, SYMBOL_EXIST))
   {
      Print("ERROR: ", InpSymbol, " no existe en Market Watch.");
      return;
   }
   Print("Simbolo OK: ", InpSymbol);
   
   int fh = FileOpen(InpCsvFile, FILE_READ|FILE_CSV|FILE_ANSI, '\t');
   if(fh == INVALID_HANDLE)
   {
      Print("ERROR: No se pudo abrir ", InpCsvFile, " Error: ", GetLastError());
      return;
   }
   Print("Archivo abierto: ", InpCsvFile);
   
   // Descartar header
   if(!FileIsEnding(fh))
      FileReadString(fh);
   
   int totalRead = 0;
   int totalImported = 0;
   int count = 0;
   MqlRates rates[];
   
   while(!FileIsEnding(fh))
   {
      string sDate = FileReadString(fh);
      if(sDate == "" || sDate == "<DATE>") continue;
      string sTime  = FileReadString(fh);
      string sOpen  = FileReadString(fh);
      string sHigh  = FileReadString(fh);
      string sLow   = FileReadString(fh);
      string sClose = FileReadString(fh);
      string sTVol  = FileReadString(fh);
      string sVol   = FileReadString(fh);
      string sSprd  = FileReadString(fh);
      
      datetime t = StringToTime(sDate + " " + sTime);
      if(t <= 0) continue;
      
      double o = StringToDouble(sOpen);
      double h = StringToDouble(sHigh);
      double l = StringToDouble(sLow);
      double c = StringToDouble(sClose);
      if(o <= 0 || h <= 0 || l <= 0 || c <= 0) continue;
      if(h < l) continue;
      
      ArrayResize(rates, count + 1);
      rates[count].time = t;
      rates[count].open = o;
      rates[count].high = h;
      rates[count].low = l;
      rates[count].close = c;
      rates[count].tick_volume = (long)StringToInteger(sTVol);
      rates[count].real_volume  = (long)StringToInteger(sVol);
      rates[count].spread = (int)StringToInteger(sSprd);
      count++;
      totalRead++;
      
      // Importar en lotes de 5000
      if(count >= 5000)
      {
         CustomRatesUpdate(InpSymbol, rates);
         totalImported += count;
         count = 0;
         ArrayResize(rates, 0);
         Print("  Progreso: ", totalImported, " importadas / ", totalRead, " leidas");
      }
   }
   
   // Importar resto
   if(count > 0)
   {
      CustomRatesUpdate(InpSymbol, rates);
      totalImported += count;
   }
   
   FileClose(fh);
   
   Print("=== Resultado ===");
   Print("Leidas: ", totalRead, " | Importadas: ", totalImported);
}
