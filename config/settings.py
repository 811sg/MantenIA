"""Configuración central del Agente MantenIA v3 con LangGraph.

Este módulo carga las variables definidas en el archivo `.env` y
proporciona la configuración necesaria para interactuar con la API de Gemini.
Solo contiene configuración de entorno: los prompts viven en `prompts/`.
"""

import os
from dotenv import load_dotenv


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def validar_configuracion() -> None:
    """Valida las variables mínimas requeridas antes de compilar el grafo."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_API_KEY_AQUI":
        raise ValueError(
            "Configura una API Key válida en el archivo .env "
            "usando GEMINI_API_KEY."
        )
