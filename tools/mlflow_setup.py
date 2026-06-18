#!/usr/bin/env python3
"""
mlflow_setup.py — Configuración de MLflow para el laboratorio

Backend SQLite, sin servidor remoto.
Corrección bug: referencia a MLFLOW_DIR eliminada (ahora usa paths relativos).
"""

import os
import sys
import time
from pathlib import Path
import mlflow

from hermes_config import (
    MLFLOW_TRACKING_URI,
    MLFLOW_EXPERIMENT,
    MLFLOW_PORT,
)


def setup_mlflow():
    """Configura MLflow con backend SQLite."""

    # Configurar tracking URI
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    # Crear experimento si no existe
    experiment = mlflow.get_experiment_by_name(MLFLOW_EXPERIMENT)
    if experiment is None:
        exp_id = mlflow.create_experiment(MLFLOW_EXPERIMENT)
        print(f"✅ Experimento '{MLFLOW_EXPERIMENT}' creado (ID: {exp_id})")
        experiment = mlflow.get_experiment(exp_id)
    else:
        print(f"✅ Experimento '{MLFLOW_EXPERIMENT}' ya existe (ID: {experiment.experiment_id})")
    
    # Crear cliente antes de las verificaciones
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    client = mlflow.tracking.MlflowClient()
    
    # ═══════════════════════════════════════════════════════════════════
    # VERIFICACIÓN 1: Recuperación en sesión
    # ═══════════════════════════════════════════════════════════════════
    print("\n[VERIFICACIÓN 1] Recuperación en sesión...")
    test_run_name = f"MLFLOW_VERIFY_{int(time.time())}"
    with mlflow.start_run(run_name=test_run_name) as run:
        mlflow.log_param("test", "session_recovery")
        mlflow.log_metric("verify", 1.0)
        run_id = run.info.run_id
    
    # Verificar que el run existe en la misma sesión
    recovered = client.get_run(run_id)
    assert recovered is not None, "Run no recuperado en sesión"
    assert recovered.data.params["test"] == "session_recovery", "Param no coincide"
    print(f"  ✅ Run creado y recuperado: {run_id[:12]}...")

    # ═══════════════════════════════════════════════════════════════════
    # VERIFICACIÓN 2: Persistencia tras restart simulado
    # ═══════════════════════════════════════════════════════════════════
    print("\n[VERIFICACIÓN 2] Persistencia tras restart simulado...")
    # Simular restart: nuevo cliente, misma DB
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    client2 = mlflow.tracking.MlflowClient()
    
    # Recuperar el run creado anteriormente
    persisted = client2.get_run(run_id)
    assert persisted is not None, "Run no persistió tras restart"
    assert persisted.data.metrics["verify"] == 1.0, "Metric no persistió"
    print(f"  ✅ Run persiste tras restart: {run_id[:12]}...")

    # ═══════════════════════════════════════════════════════════════════
    # VERIFICACIÓN 3: Búsqueda por tag
    # ═══════════════════════════════════════════════════════════════════
    print("\n[VERIFICACIÓN 3] Búsqueda por tag...")
    # Agregar tag al run
    client.set_tag(run_id, "verification", "mlflow_setup")
    client.set_tag(run_id, "type", "infrastructure_test")
    
    # Buscar por tag
    results = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="tags.verification = 'mlflow_setup'"
    )
    assert len(results) >= 1, "Búsqueda por tag no retornó resultados"
    assert results[0].info.run_id == run_id, "Run encontrado no coincide"
    print(f"  ✅ Búsqueda por tag funciona: {len(results)} run(s) encontrado(s)")

    # ═══════════════════════════════════════════════════════════════════
    # RESUMEN
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n{'=' * 60}")
    print(f"✅ MLflow verificado correctamente")
    print(f"   Tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"   Experimento: {MLFLOW_EXPERIMENT} (ID: {experiment.experiment_id})")
    print(f"   Runs existentes: {len(client.search_runs(experiment_ids=[experiment.experiment_id]))}")
    print(f"   Verificaciones: 3/3 PASS")
    print(f"{'=' * 60}")
    
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
