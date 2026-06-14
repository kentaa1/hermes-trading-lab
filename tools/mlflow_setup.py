#!/usr/bin/env python3
"""
mlflow_setup.py — Configuración de MLflow para el laboratorio

Backend SQLite, sin servidor remoto.
Corrección bug: referencia a MLFLOW_DIR eliminada (ahora usa paths relativos).
"""

import os
import sys
from pathlib import Path
import mlflow

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════

REPO_ROOT = Path(__file__).resolve().parent
MLFLOW_DIR = REPO_ROOT / "mlflow"
MLFLOW_DB = MLFLOW_DIR / "mlflow.db"
MLFLOW_TRACKING_URI = f"sqlite:///{MLFLOW_DB}"
MLFLOW_EXPERIMENT = "hermes-godmode"
MLFLOW_PORT = 5000


def setup_mlflow():
    """Configura MLflow con backend SQLite."""
    
    # Crear directorio si no existe
    MLFLOW_DIR.mkdir(parents=True, exist_ok=True)
    
    # Configurar tracking URI
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    # Crear experimento si no existe
    experiment = mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT)
    if experiment is None:
        mlflow.create_experiment(MLFLOW_EXPERIMENT)
        print(f"✅ Experimento '{MLFLOW_EXPERIMENT}' creado")
    else:
        print(f"✅ Experimento '{MLFLOW_EXPERIMENT}' ya existe (ID: {experiment.experiment_id})")
    
    # Verificar conexión
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    client = mlflow.tracking.MlflowClient()
    runs = client.search_runs(experiment_ids=[experiment.experiment_id])
    
    print(f"✅ MLflow configurado correctamente")
    print(f"   Tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"   Experimento: {MLFLOW_EXPERIMENT}")
    print(f"   Runs existentes: {len(runs)}")
    
    return True


def start_ui():
    """Inicia la UI de MLflow."""
    import subprocess
    
    print(f"\n🌐 Iniciando MLflow UI en http://127.0.0.1:{MLFLOW_PORT}")
    print("   Presiona Ctrl+C para detener\n")
    
    env = os.environ.copy()
    env["MLFLOW_TRACKING_URI"] = MLFLOW_TRACKING_URI
    
    try:
        subprocess.run(
            ["mlflow", "ui", "--backend-store-uri", MLFLOW_TRACKING_URI, 
             "--port", str(MLFLOW_PORT), "--host", "127.0.0.1"],
            env=env
        )
    except KeyboardInterrupt:
        print("\n✅ MLflow UI detenido")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Configuración de MLflow")
    parser.add_argument("--ui", action="store_true", help="Iniciar UI de MLflow")
    args = parser.parse_args()
    
    if setup_mlflow():
        if args.ui:
            start_ui()
    else:
        print("❌ Error configurando MLflow")
        sys.exit(1)
