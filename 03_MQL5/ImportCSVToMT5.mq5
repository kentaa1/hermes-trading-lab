//+------------------------------------------------------------------+
//|                                          ImportCSVToMT5.mq5     |
//|                          Hermes-Trading-Lab — Importador CSV    |
//|                          Importa barras M1 desde CSV a MT5      |
//+------------------------------------------------------------------+
#property copyright "Hermes-Trading-Lab"
#property link      ""
#property version   "1.00"
#property strict
//+------------------------------------------------------------------+
//| Parámetros de entrada                                            |
//+------------------------------------------------------------------+
input string InpCsvFile      = "EURUSD_M1_201501020900_202606082251.csv"; // Archivo CSV en MQL5/Files/
input string InpSymbol       = "EURUSD";   // Símbolo destino
input int    InpTimeShift    = 0;          // Shift de tiempo en segundos (ajuste zona horaria)

//+------------------------------------------------------------------+
//| Script principal                                                 |
//+------------------------------------------------------------------+
void OnStart()
{
   string filepath = InpCsvFile;
   
   Print("=== ImportCSVToMT5 v1.00 ===");
   Print("Archivo: ", filepath);
   Print("Símbolo: ", InpSymbol);
   
   int fileHandle = FileOpen(filepath, FILE_READ|FILE_CSV|FILE_ANSI, '\t');
   if(fileHandle == INVALID_HANDLE)
   {
      Print("ERROR: No se pudo abrir el archivo CSV. Error: ", GetLastError());
      Print("Asegúrate de copiar el CSV a: <MT5>/MQL5/Files/");
      return;
   }
   
   // Leer header
   string header = FileReadString(fileHandle);
   Print("Header: ", header);
   
   // Contadores
   int totalRead = 0;
   int totalImported = 0;
   int batchSize = 50000;
   
   // Array para批量 import
   MqlRates rates[];
   ArrayResize(rates, 0);
   
   datetime lastBarTime = 0;
   
   while(!FileIsEnding(fileHandle))
   {
      // Leer línea
      string dateStr = FileReadString(fileHandle);
      if(dateStr == "" || dateStr == "<DATE>") continue;
      
      string timeStr = FileReadString(fileHandle);
      string openStr = FileReadString(fileHandle);
      string highStr = FileReadString(fileHandle);
      string lowStr  = FileReadString(fileHandle);
      string closeStr = FileReadString(fileHandle);
      string tickVolStr = FileReadString(fileHandle);
      string volStr = FileReadString(fileHandle);
      string spreadStr = FileReadString(fileHandle);
      
      // Parsear fecha y hora
      datetime barTime = StringToTime(dateStr + " " + timeStr);
      if(barTime <= 0) continue;
      
      // Evitar duplicados
      if(barTime <= lastBarTime) continue;
      
      double open  = StringToDouble(openStr);
      double high  = StringToDouble(highStr);
      double low   = StringToDouble(lowStr);
      double close = StringToDouble(closeStr);
      long   tickVol = StringToInteger(tickVolStr);
      long   vol = StringToInteger(volStr);
      int    spread = (int)StringToInteger(spreadStr);
      
      // Validar datos
      if(open <= 0 || high <= 0 || low <= 0 || close <= 0) continue;
      if(high < low) continue;
      
      // Agregar al array
      int size = ArraySize(rates);
      ArrayResize(rates, size + 1);
      
      rates[size].time = barTime;
      rates[size].open = open;
      rates[size].high = high;
      rates[size].low = low;
      rates[size].close = close;
      rates[size].tick_volume = tickVol;
      rates[size].real_volume = vol;
      rates[size].spread = spread;
      
      totalRead++;
      lastBarTime = barTime;
      
      // Importar en lotes
      if(ArraySize(rates) >= batchSize)
      {
         int imported = CustomRatesUpdate(InpSymbol, rates);
         if(imported > 0)
            totalImported += imported;
         
         ArrayResize(rates, 0);
         
         if(totalImported % 100000 == 0)
            Print("Importados: ", totalImported, " barras...");
      }
   }
   
   // Importar resto
   if(ArraySize(rates) > 0)
   {
      int imported = CustomRatesUpdate(InpSymbol, rates);
      if(imported > 0)
         totalImported += imported;
   }
   
   FileClose(fileHandle);
   
   Print("=== Importación completada ===");
   Print("Barras leídas:    ", totalRead);
   Print("Barras importadas: ", totalImported);
}
//+------------------------------------------------------------------+
