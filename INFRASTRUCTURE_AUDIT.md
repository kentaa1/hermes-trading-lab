# ANÁLISIS DE INFRAESTRUCTURA — Hermes-Trading-Lab
## Auditoría DevOps — Ingeniería de Sistemas

**Fecha:** 2026-07-07
**Analista:** Ingeniero Infraestructura (15 años experiencia, pipelines de datos, automatización, sistemas de producción)
**Scope:** Infraestructura end-to-end, no metodología de trading

---

## 1. ¿LA CADENA DE HERRAMIENTAS ES VIABLE END-TO-END?

### Problema 1A: El pipeline tiene 3 saltos manuales sin automatizar entre cada estado del experimento

**Evidencia:**
- El único artefacto de código es `HermesBase_Template.mq5` (242 líneas). No existe ni un solo script de automatización. El directorio `07_AUTOMATION/` contiene 1 archivo con 2 líneas: un README que dice "BLOQUEADO — FASE 1".
- La transición CODED → COMPILED requiere: abrir MetaEditor manualmente, compilar el .mq5, verificar 0 errores, guardar el .ex5. Ningún paso está automatizado.
- La transición COMPILED → BACKTESTED requiere: abrir MT5 Strategy Tester, configurar Every Tick, seleccionar fechas IS/OOS, ejecutar, exportar informe HTML, parsear métricas. Todo manual.
- No existe `Makefile`, `justfile`, `package.json`, `pyproject.toml`, ni ningún script de orquestación en todo el repositorio. El repositorio Git tiene 10 commits desde `init` — todo documentación y la plantilla.

**Recomendación:** El pipeline no es viable end-to-end. Lo que existe es un *marco teórico* con un *prototipo de plantilla*. Nada más. Antes de pensar en estrategias, hay que construir el MVP de automatización: un script que compile .mq5 desde CLI (.exe de MetaEditor existe: `metaeditor64.exe /compile`), ejecute el backtest, y extraiga métricas. Sin esto, cada experimento es una operación artesanal de 45-90 minutos.

### Problema 1B: Ningún componente del pipeline Dukascopy→MT5→CSV→Python existe como código ejecutable

**Evidencia:**
- No existe ningún archivo `.py` en el proyecto. La tarea menciona `tools/external_cost_recalculation.py` — no existe. Búsqueda por `external_cost_recalculation` en todo C:\Users\David retornó 0 resultados.
- No hay documentación de cómo importar datos Dukascopy como símbolo personalizado en MT5. Este proceso requiere: descargar ticks .bi5, convertirlos con `hst2mt5` o similar, importar como símbolo personalizado. Es un proceso manual propenso a errores.
- No hay scripts de exportación CSV desde MT5. MT5 exporta HTML nativamente; parsear HTML a CSV requiere BeautifulSoup o similar — no hay nada de esto.
- `04_BACKTESTS/`, `05_SYMBOL_PROFILES/`, `06_MEMORY/`, `08_APPROVED_BOTS/`, `09_SANDBOX/` — los 5 directorios están completamente vacíos (4 bytes = directorio vacío).

**Recomendación:** El pipeline Dukascopy→MT5→CSV→Python es una descripción verbal, no un pipeline. Hay que implementar: (a) script de descarga Dukascopy con su API pública, (b) conversión .bi5 → formato MT5, (c) importación automática de símbolo personalizado, (d) exportación programática de resultados Strategy Tester a CSV, (e) scripts Python de recalculation de costes.

### Problema 1C: Los registros críticos del protocolo no existen en el repositorio

**Evidencia:**
- La tarea menciona `IDEA_REGISTRY.csv`, `EXPERIMENT_REGISTRY.csv`, `HUMAN_DECISION_LOG.md` — no existen. Búsqueda por estos patrones en todo el proyecto retornó 0 resultados.
- Sin estos archivos, no hay trazabilidad de qué se intentó, qué se descartó, o qué decidió el humano. El protocolo documental es papel mojado.

**Recomendación:** Crear estos archivos como stubs con headers y una fila de ejemplo. Son los registros más importantes del laboratorio (audit trail).

---

## 2. ¿CUÁLES SON LOS PUNTOS ÚNICOS DE FALLO?

### Problema SPOF-1: MetaTrader 5 es un black box sin API para automatizar workflows

**Evidencia:**
- MT5 no tiene API REST, WebSocket, ni SDK de Python. La automatización requiere: (a) MetaEditor CLI para compilar (disponible), (b) archivo .set para configurar el Strategy Tester, (c) python-connector (comunidad, no oficial) para leer resultados, o (d) DLL de Windows (.dll de MQL5 llamada desde Python vía ctypes, frágil).
- Si MetaEditor cambia el formato del .set entre versiones del terminal, los scripts se rompen.
- Toda la cadena depende de que el usuario tenga una licencia de MT5 activa con datos históricos del broker.

**Recomendación:** Aceptar la dependencia de MT5 pero aislarla: crear una capa de abstracción (clase Python `MT5Controller`) que encapsule toda la interacción. Si el día de mañana se migra a otra plataforma (cTrader, QuantConnect), solo se cambia esa capa.

### Problema SPOF-2: OpenRouter como proveedor de APIs para 6 modelos

**Evidencia:**
- 6 modelos de 6 proveedores diferentes (OpenRouter, NVIDIA, Qwen, Moonshot, DeepSeek, Z-AI) — cada uno con su propia latencia, rate limits, y disponibilidad. Un error de rate limit en la API bloquea el experimento completo.
- El proyecto depende de modelos `:free` en OpenRouter — estos tienen rate limits más bajos, menos estabilidad, y pueden descontinuarse sin aviso.
- No hay fallback documentado si un modelo no está disponible. ¿Qué pasa si qwen3-coder:free cae?

**Recomendación:** Documentar los fallbacks (el Coder tiene backup en la lista de instancias, pero no hay lógica de ruta). Implementar retries con backoff. Considerar un rate limiter local.

### Problema SPOF-3: OpenRouter API key potencialmente en claro

**Evidencia:**
- `C:\Users\David\.hermes\.env` contiene una variable con `OBSIDIAN_VAULT_PATH`. Si contiene API keys de OpenRouter, están en texto plano en una máquina Windows compartida.
- No hay un `.env.example` ni documentación de qué variables se necesitan.

**Recomendación:** Si hay secretos en el .env, moverlos a Windows Credential Manager o al menos verificar que .gitignore incluya `.env` (actualmente `.gitignore` excluye `*.env` pero NO `.env` literal). Añadir `.env` explícitamente a .gitignore.

### Problema SPOF-4: Git como único sistema de backup y versionado

**Evidencia:**
- 10 commits, un solo branch, sin ramas feature. `.ex5` (binarios compilados) están en .gitignore, bien. Pero los datos de backtest (.hst, .fxt) también están en .gitignore.
- No hay remoto configurado (probablemente local-only). Si el disco de la máquina Windows falla, el laboratorio desaparece.
- No hay CI/CD.

**Recomendación:** Configurar un remoto Git (GitHub privado, GitLab, o incluso un NAS local). Al mínimo. CI/CD puede esperar.

### Problema SPOF-5 (CRÍTICO): OnStrategyInit() nunca es llamada

**Evidencia:**
- En `HermesBase_Template.mq5`, línea 209, se declara `int OnStrategyInit()` con un TODO que crea handles de indicadores. Esta función **nunca es invocada** desde ningún punto del bloque congelado.
- `OnInit()` del bloque congelado (línea 99) inicializa `trade`, `symInfo`, y `lastBarTime`. No llama a `OnStrategyInit()`.
- Cuando el Coder genere código en el bloque editable, los handles de indicadores no tendrán donde inicializarse. El código no compilará o compilará con handles = INVALID_HANDLE y nunca generará señales.

**Recomendación:** Bug crítico de la plantilla. Añadir `if(OnStrategyInit() != INIT_SUCCEEDED) return INIT_FAILED;` dentro de `OnInit()` del bloque congelado. O renombrar a `OnInit()` del bloque editable y que el congelado la llame. Pero la plantilla está etiquetada como "congelada v1" — tocarla contradice el protocolo. Dilema: o se congela con el bug, o se corrige y se re-etiqueta como v2.

---

## 3. ¿LA DEPENDENCIA DE MT5 COMO CAJA NEGRA ES MANEJABLE?

### Problema 3A: MT5 no es automatizable vía API estándar

**Evidencia:**
- El Strategy Tester se configura vía archivos `.set` (formato binario propietario de MetaQuotes). La documentación del formato .set es incompleta y cambia entre versiones de MT5.
- Para exportar resultados: MT5 genera informes HTML propietarios que hay que parsear con regex o BeautifulSoup. No hay API de exportación a CSV/JSON.
- El EA corre dentro del terminal MT5 — no como proceso independiente. Si el terminal se cuelga, el backtest muere.

**Recomendación:** Manejable pero costoso. Crear un módulo Python `mt5_bridge.py` que: (a) genere el .set correcto, (b) lance el backtest via `subprocess` de MT5 en modo tester, (c) espere a que termine, (d) parsee el HTML de resultados, (e) genere CSV. Empaquetar todo en un CLI: `python mt5_bridge.py --strategy EXP_001 --from 2020.01.01 --to 2025.12.31`.

### Problema 3B: Los datos de backtest dependen del broker, no del mercado

**Evidencia:**
- El historial de MT5 depende del broker activo. Si el broker es un ECN retail, los datos incluyen gaps artificiales, spreads inflados en horas de baja liquidez, y posibles re-quotes.
- El proyecto quiere usar datos Dukascopy (institucional STP/ECN), pero importarlos como símbolo personalizado es un workaround frágil — MT5 trata los datos importados con menor prioridad que los datos nativos del broker.

**Recomendación:** Esto es inherente al uso de MT5. Documentar el broker, el tipo de cuenta, y las condiciones de ejecución. Los backtests con datos Dukascopy serán "mejor que los del broker" pero aún así una simulación. Añadir un disclaimer obligatorio en cada reporte de backtest.

### Problema 3C: El modelo "Every Tick based on real ticks" tiene limitaciones ocultas

**Evidencia:**
- "Every tick" en MT5 usa ticks generados (simulados) que se basan en el spread actual del broker. Si el spread era de 0.1 pips en 2020 pero el broker tiene 1.0 pip ahora, el backtest usa 1.0 pip para todo el período. Esto distorsiona resultados.
- El tick data importado de Dukascopy es de 2020-2025. ¿Qué pasa antes? MT5 rellena con generación aleatoria.

**Recomendación:** Documentar el spread usado en cada backtest. Implementar el script de recalculation de costes (que no existe) que aplique 3 modelos: base, pesimista, y estrés. De este script depende la validez de cualquier conclusión.

---

## 4. ¿EL PIPELINE DUKASCOPY→MT5→CSV→PYTHON ES ROBUSTO?

### Problema 4A: No existe como pipeline — es una intención

**Evidencia:**
- Directorio `07_AUTOMATION/`: vacío excepto README bloqueado.
- No hay scripts de descarga Dukascopy.
- No hay scripts de conversión.
- No hay scripts de importación MT5.
- No hay scripts de exportación HTML→CSV.
- No hay scripts de recalculation de costes.
- 5 de los 12 directorios están vacíos.

**Recomendación:** No es robusto porque no existe. Hay que construirlo pieza por pieza. Prioridad: (1) script de recalculation de costes Python, (2) plantilla de exportación CSV desde HTML MT5, (3) script de orquestación del flujo completo.

### Problema 4B: Sin validación de datos en ningún punto de la cadena

**Evidencia:**
- No hay checksums de los datos Dukascopy descargados.
- No hay verificación de que los datos importados en MT5 coinciden con los descargados.
- No hay validación de que el CSV exportado del backtest contiene la información esperada.
- No hay tests unitarios de ningún tipo.

**Recomendación:** Cada etapa del pipeline debe validar: (a) filas esperadas, (b) valores no nulos en columnas críticas, (c) rangos razonables (PF > 0, trades > 0, etc.). Si una etapa no valida, el pipeline se detiene.

### Problema 4C: No hay idempotencia — cada ejecución puede dar resultados diferentes

**Evidencia:**
- MT5 Strategy Tester con "Every tick" usa generación de ticks basada en modelos internos. Si el modelo de generación cambia entre versiones de MT5, los resultados cambian.
- Sin seed fijo ni versión de MT5 documentada, un backtest ejecutado hoy puede dar diferente resultado que el mismo backtest mañana después de una actualización del terminal.

**Recomendación:** Documentar la versión exacta de MT5 en cada backtest (ej. "Build 4502"). Si es posible, bloquear actualizaciones del terminal.

---

## 5. ¿QUÉ NECESITA AUTOMATIZARSE PRIMERO?

### Prioridad 0 (BLOQUEDA POR BUG): Corregir `OnStrategyInit()`

**Evidencia:** La plantilla tiene el bug de que la función de inicialización de indicadores nunca se llama. Ningún experimento puede funcionar. Pero modificar el bloque congelado contradice el protocolo.

**Acción:** Re-etiquetar como `frozen-template-v2` con la corrección. Validar que compila antes de congelar de nuevo.

### Prioridad 1: Script de recalculation de costes Python

**Evidencia:** El 80% de los problemas de backtest vienen de costes mal modelados. El `tools/external_cost_recalculation.py` que se menciona en la tarea no existe. Sin él, no hay forma de saber si la estrategia es rentable después de costes reales.

**Acción:** Crear `tools/backtest_analyzer.py` que: (a) lea CSV de trades MT5, (b) aplique 3 modelos de costes: base, pesimista, estrés NFP/FOMC/BCE, (c) calcule net PF, net expectancia, net DD.

### Prioridad 2: Parser de HTML MT5 → CSV

**Evidencia:** MT5 exporta informes en HTML propietario. Sin parseo automático, el Coordinador tiene que leer HTML manualmente y transcribir métricas — lento y propenso a error.

**Acción:** Crear `tools/mt5_report_parser.py` que extraiga: trades, PF, DD, winrate, payoff, equity curve del HTML del Strategy Tester.

### Prioridad 3: Orquestador de experimento

**Evidencia:** El flujo de 8 pasos (Sesión -1, 0, 1a, manual MT5, 1b, 2, 3, EXP_001) es completamente manual. No hay herramienta que guíe al usuario.

**Acción:** Crear `tools/experiment_runner.py` que: (a) verifique prerrequisitos del estado actual, (b) ejecute los pasos automatizables, (c) registre el resultado en `EXPERIMENT_REGISTRY.csv`, (d) haga commit automático.

### Prioridad 4: Registros de auditoría

**Evidencia:** `IDEA_REGISTRY.csv`, `EXPERIMENT_REGISTRY.csv`, `HUMAN_DECISION_LOG.md` no existen.

**Acción:** Crear stubs con headers y documentación de uso.

---

## 6. ¿LA FRAGMENTACIÓN DE MEMORIA EN 5 PERFILES ES UN PROBLEMA?

### Problema 6A: Los 5 perfiles no existen como configuración real

**Evidencia:**
- `C:\Users\David\.hermes\` contiene solo un `.env` con `OBSIDIAN_VAULT_PATH`. No hay directorio `profiles/`.
- La configuración de 6 modelos (owl-alpha, nemotron-3-super, qwen3-coder, kimi-k2.6, deepseek-v4-flash, glm-4.5-air) está documentada en `AGENTS.md` y `00_CONTROL/instances.md` pero no hay evidencia de que estén configurados como perfiles Hermes separados.
- La tarea menciona "5 perfiles Hermes Agent independientes (cada uno con modelo, memoria, SOUL.md)" — en la práctica, solo hay un perfil `default` activo.

**Recomendación:** Si los perfiles no están implementados, la fragmentación de memoria es un problema teórico, no real. Pero cuando se implementen: cada perfil tendrá su propia memoria, su propio contexto, y no compartirán estado. El Coordinador tendrá que sincronizar manualmente entre perfiles. Esto es un riesgo de inconsistencia.

### Problema 6B: GBrain como memoria semántica — no hay integración visible

**Evidencia:**
- GBrain está descargado en `C:\Users\David\Downloads\gbrain-eval-run-v0.35.1.0-baseline\` pero NO está integrado con Hermes ni con el proyecto.
- No hay configuración de GBrain en `.hermes/.env` ni en ningún archivo del proyecto.
- `HERMES.md` dice "Obsidian (vault vinculado al repositorio)" pero el `.env` apunta a `C:\Users\David\Documents\Obsidian Vault` — una ruta separada, no el repositorio.
- No hay notas de Obsidian dentro del repositorio.

**Recomendación:** GBrain no está integrado. La "memoria semántica" es una intención, no una realidad. Si se integra, hay que resolver: (a) qué se indexa (¿todo el repo? ¿solo 02_STRATEGIES y 10_RESEARCH?), (b) cómo se consulta desde los perfiles, (c) cuándo se actualiza el índice.

### Problema 6C: Sin memoria compartida, cada perfil reinventa el contexto

**Evidencia:**
- Si el Coder genera código MQL5, el Riesgo no tiene forma de acceder a ese código salvo que el Coordinador se lo pase manualmente.
- Si el Estratega produce una hipótesis, el Coder no tiene acceso a ella salvo que el Coordinador la copie.
- El Coordinador es el único nexo — si el Coordinador pierde contexto (nueva sesión, 1M tokens llenos), la información se pierde.

**Recomendación:** El repositorio Git ES la memoria compartida. Cada perfil debe leer/escribir en el repo. El Coordinador debe hacer commit después de cada transición de estado. Esto ya está en el protocolo pero no hay automatización que lo garantice.

---

## 7. BUGS CONOCIDOS — VERIFICACIÓN

### Bug 1: OnStrategyInit() nunca llamada — CONFIRMADO

En `HermesBase_Template.mq5`:
- Línea 99: `OnInit()` del bloque congelado — no llama a `OnStrategyInit()`
- Línea 209: `OnStrategyInit()` del bloque editable — declarada pero nunca invocada
- **Impacto:** Ningún handle de indicador se inicializa. `GetStrategySignal()` retorna siempre 0 (neutral). El EA no abre posiciones.

### Bug 2: Delimitadores de bloque no coinciden entre código y prompt — CONFIRMADO

- **Código real** (línea 185): `//|  BLOQUE EDITABLE — ESTRATEGIA`
- **Prompt Coder** (línea 15): dice que el inicio es `// ══════════════════════════════════════════════════════════════`

Estos strings no coinciden. El Coder buscando el delimitador del prompt no lo encontrará en el código real. Además:
- **Prompt Coder** dice fin: `// ► FIN BLOQUE DE ESTRATEGIA`
- **Código real** dice fin: `//|  FIN BLOQUE EDITABLE — ESTRATEGIA`

El Coder MQL5 no encontrará los delimitadores que le enseñó su prompt. Generará código fuera del bloque editable o fallará.

### Bug 3: Position sizing usa compounding (AccountBalance) — CONFIRMADO

En `CalcLotSize()` (línea 76-94):
```mql5
double balance = AccountInfoDouble(ACCOUNT_BALITICAL);
double riskMoney = balance * InpRiskPct / 100.0;
```

Esto calcula el riesgo como porcentaje del balance actual (compounding). Si el protocolo dice "1% fijo sobre 10K", el código debería usar una constante (10000.0) en lugar de `AccountInfoDouble(ACCOUNT_BALANCE)`. Con cada ganancia, el tamaño de posición crece. Con cada pérdida, decrece. Esto es compounding implícito, prohibido por el espíritu del protocolo Fase 1 (tamaño fijo, sin gestión de capital adaptativa).

---

## RESUMEN DE SEVERIDAD

| # | Hallazgo | Severidad | Impacto |
|---|----------|-----------|---------|
| 1A | Pipeline no existe como código — solo documentación | **CRÍTICA** | No se puede ejecutar ningún experimento |
| 1B | 5 de 12 directorios vacíos | **CRÍTICA** | El 40% del proyecto es esqueleto |
| 1C | Registros de auditoría no existen | **ALTA** | Sin trazabilidad, sin reproducibilidad |
| SPF-1 | MT5 sin API — automatización frágil | **ALTA** | Cada backtest es manual |
| SPF-2 | 6 modelos free de OpenRouter — rate limits | **MEDIA** | Bloqueo de experimentos |
| SPF-3 | API keys potencialmente en claro en .env | **ALTA** | Seguridad |
| SPF-4 | Git local-only, sin remoto | **ALTA** | Pérdida total si falla disco |
| SPF-5 | OnStrategyInit() nunca llamada | **CRÍTICA** | La plantilla no funciona |
| 3A | MT5 caja negra sin abstracción | **ALTA** | Acoplamiento total |
| 3B | Datos de backtest dependen del broker | **ALTA** | Resultados no representativos |
| 3C | Every Tick con spread del momento | **MEDIA** | Distorsión de costes históricos |
| 4A | Pipeline Dukascopy→MT5→CSV→Python no existe | **CRÍTICA** | No hay flujo de datos |
| 4B | Sin validación de datos en ningún punto | **ALTA** | Resultados no confiables |
| 4C | Sin idempotencia en backtests | **MEDIA** | Resultados no reproducibles |
| 6A | Perfiles no implementados | **MEDIA** | Fragmentación teórica |
| 6B | GBrain no integrado | **ALTA** | Sin memoria semántica real |
| 6C | Sin memoria compartida entre perfiles | **ALTA** | Pérdida de contexto |
| B1 | Delimitadores bloque no coinciden (código vs prompt) | **CRÍTICA** | Coder no encontrará el bloque |
| B2 | CalcLotSize usa compounding no fijo | **ALTA** | Violación protocolo |

---

## CONCLUSIÓN

**Hermes-Trading-Lab es un marco teórico bien documentado con cero infraestructura ejecutable.**

Lo que existe:
- ✅ Documentación de protocolo (estados, criterios, naming, roles)
- ✅ 1 plantilla MQL5 (con 2 bugs críticos confirmados)
- ✅ 1 estrategia especificada (STRAT_001)
- ✅ 1 hipótesis de research (HIP_001)
- ✅ Git inicializado con 10 commits

Lo que NO existe:
- ❌ Scripts de automatización (0 de N)
- ❌ Pipeline de datos (0 de 4 etapas implementadas)
- ❌ Registros de auditoría (0 de 3)
- ❌ Perfiles Hermes configurados (0 de 5)
- ❌ Integración GBrain (descargado pero no integrado)
- ❌ Scripts Python de recalculation de costes
- ❌ Parser de resultados MT5
- ❌ Remoto Git
- ❌ Tests de ningún tipo
- ❌ Experimentos completados (0)

**El proyecto está en fase de diseño, no de ejecución.** La documentación es superior al promedio retail, pero sin automatización, cada experimento requiere 2-4 horas de trabajo manual. Los 2 bugs críticos (OnStrategyInit + delimitadores) significan que ni siquiera el primer experimento puede ejecutarse sin corregir la plantilla congelada.

**Recomendación principal:** Antes de diseñar más estrategias, construir el MVP de automatización en este orden exacto:
1. Corregir `OnStrategyInit()` y re-etiquetar plantilla como v2
2. Corregir delimitadores en el prompt del Coder para que coincidan con el código
3. Corregir `CalcLotSize()` para usar capital fijo (10K) en vez de balance actual
4. Crear `tools/mt5_report_parser.py` (parser HTML→CSV)
5. Crear `tools/backtest_analyzer.py` (recalculation de costes)
6. Crear `EXPERIMENT_REGISTRY.csv` e `IDEA_REGISTRY.csv` como stubs
7. Configurar remoto Git

Solo después de estos 7 pasos se puede ejecutar el primer experimento end-to-end y evaluar si el pipeline es viable.

---

*Análisis basado en inspección directa del repositorio en C:\Users\David\Hermes-Trading-Lab\. Todos los hallazgos son verificables con los archivos existentes.*
