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
# DATASET PROVISIONAL (V-1)
# ═══════════════════════════════════════════════════════════════════

PROVISIONAL_DATASET = "Historical_Stress_2007-2017"
PROVISIONAL_SYMBOL = "EURUSD"
PROVISIONAL_TIMEFRAME = "H1"

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
