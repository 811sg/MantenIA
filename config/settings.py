"""Configuración central de MantenIA.

Carga las variables de entorno (archivo `.env` en local, *Secrets* en Streamlit
Community Cloud) y expone los valores que necesitan el resto de capas.
Solo contiene configuración de entorno: los prompts viven en `prompts/`.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]

APP_NAME = "MantenIA"
APP_VERSION = "3.1"


def _leer_variable(nombre: str, por_defecto: str | None = None) -> str | None:
    """Lee una variable de entorno y, si no existe, de `st.secrets`.

    Streamlit Community Cloud expone los secretos también como variables de
    entorno, pero el respaldo explícito evita sorpresas en otros despliegues.
    """
    valor = os.getenv(nombre)
    if valor:
        return valor

    try:
        import streamlit as st

        secreto = st.secrets.get(nombre)
        if secreto:
            return str(secreto)
    except Exception:  # sin secrets.toml o fuera de Streamlit
        pass

    return por_defecto


GEMINI_API_KEY = _leer_variable("GEMINI_API_KEY")
GEMINI_MODEL = _leer_variable("GEMINI_MODEL", "gemini-3.8-flash")

# Observabilidad
LOG_LEVEL = (_leer_variable("MANTENIA_LOG_LEVEL", "INFO") or "INFO").upper()
METRICS_LOG_PATH = Path(
    _leer_variable("MANTENIA_METRICS_LOG", str(BASE_DIR / "logs" / "metricas.jsonl"))
)

# Resiliencia del cliente Gemini
LLM_TIMEOUT_S = 60
LLM_MAX_RETRIES = 2


def validar_configuracion() -> None:
    """Valida las variables mínimas requeridas antes de ejecutar el grafo."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_API_KEY_AQUI":
        raise ValueError(
            "Configura una API Key válida en GEMINI_API_KEY "
            "(archivo .env en local o Secrets en Streamlit Cloud)."
        )
