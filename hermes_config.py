#!/usr/bin/env python3
"""
hermes_config.py — Configuración global del laboratorio Hermes-Trading-Lab

Centraliza todas las constantes, paths y parámetros del protocolo.
Cuando exista BROKER_COST_MANIFEST, reemplaza PROVISIONAL_COST_PIPS.
"""

from pathlib import Path

# ═══════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "data"
TOOLS_DIR = REPO_ROOT / "tools"
HYPOTHESES_DIR = REPO_ROOT / "hypotheses"
MLFLOW_DIR = REPO_ROOT / "mlflow"
DUCKDB_DIR = REPO_ROOT / "duckdb"

# ═══════════════════════════════════════════════════════════════════
# COSTO PROVISIONAL
# ═══════════════════════════════════════════════════════════════════

PROVISIONAL_COST_PIPS = 2.0
# Desglose informativo (no usado en cálculos):
#   spread: 1.2 pips
#   comisión: 0.5 pips
#   slippage: 0.3 pips
# Total: 2.0 pips round-trip
#
# Cuando exista BROKER_COST_MANIFEST, esta constante se reemplaza
# por el valor real del manifiesto sin cambiar el wrapper.

# ═══════════════════════════════════════════════════════════════════
# PARÁMETROS DE PRE-SCREENING
# ═══════════════════════════════════════════════════════════════════

MIN_TRADES = 30          # Mínimo de trades para resultado evaluable
PF_THRESHOLD = 1.05      # Profit Factor mínimo para PASS
DD_THRESHOLD = 0.40      # Drawdown máximo para PASS (40%)
T_VECTORBTV = 300        # Timeout en segundos para vectorbt

# ═══════════════════════════════════════════════════════════════════
# FRONTERAS DE DATASETS (V-1)
# ═══════════════════════════════════════════════════════════════════
# El wrapper de pre-screening DEBE validar que el rango solicitado
# cae dentro del período autorizado. Hard abort si incluye Research,
# Validation, Lockbox o Additional holdout.

DATASET_PRESCREENING_START = "2007-01-01"
DATASET_PRESCREENING_END   = "2017-12-31"
DATASET_RESEARCH_START     = "2018-01-01"
DATASET_RESEARCH_END       = "2021-12-31"
DATASET_VALIDATION_START   = "2022-01-01"
DATASET_VALIDATION_END     = "2023-06-30"
DATASET_LOCKBOX_START      = "2023-07-01"
DATASET_LOCKBOX_END        = "2024-12-31"
DATASET_HOLDOUT_START      = "2025-01-01"

# ═══════════════════════════════════════════════════════════════════
# DATASET PROVISIONAL (V-1)
# ═══════════════════════════════════════════════════════════════════

PROVISIONAL_DATASET = "Historical_Stress_2007-2017"
PROVISIONAL_SYMBOL = "EURUSD"
PROVISIONAL_TIMEFRAME = "H1"

# ═══════════════════════════════════════════════════════════════════
# STOP CONFIG (HYP_000, HYP_001 sin stops por defecto)
# ═══════════════════════════════════════════════════════════════════

STOP_CONFIG_DEFAULT = None  # Sin stops por defecto (HYP_000, HYP_001)
STOP_CONFIG_SESSION = {
    'sl_stop': 0.005,    # 50 pips stop loss (fraccion de precio para EURUSD ~1.10)
    'sl_trail': True,       # Activar trailing stop
}

# ═══════════════════════════════════════════════════════════════════
# DUCKDB
# ═══════════════════════════════════════════════════════════════════

DUCKDB_PATH = DUCKDB_DIR / "main.duckdb"

# ═══════════════════════════════════════════════════════════════════
# MLFLOW
# ═══════════════════════════════════════════════════════════════════

MLFLOW_DB = MLFLOW_DIR / "mlflow.db"
MLFLOW_TRACKING_URI = f"sqlite:///{MLFLOW_DB}"
MLFLOW_EXPERIMENT = "hermes-godmode"
MLFLOW_PORT = 5000

# ═══════════════════════════════════════════════════════════════════
# DVC
# ═══════════════════════════════════════════════════════════════════

DVC_STORAGE = REPO_ROOT / "dvc-storage"
