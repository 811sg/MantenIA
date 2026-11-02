"""Configuración común: clave de prueba y aislamiento del registro de métricas."""

import os

# Debe fijarse antes de importar `config.settings`.
os.environ.setdefault("GEMINI_API_KEY", "clave-de-prueba")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

import pytest


@pytest.fixture(autouse=True)
def _aislar_registro_metricas(tmp_path, monkeypatch):
    """Evita que las pruebas escriban en `logs/metricas.jsonl` del proyecto."""
    import core.observability as observability

    monkeypatch.setattr(observability, "METRICS_LOG_PATH", tmp_path / "metricas.jsonl")
