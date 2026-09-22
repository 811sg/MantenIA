"""Configuración central del Agente MantenIA v2 con LangChain.

Este módulo carga las variables definidas en el archivo `.env` y 
proporciona la configuración necesaria para interactuar con la API de Gemini.
"""

import os
from dotenv import load_dotenv


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def validar_configuracion() -> None:
    """Valida las variables mínimas requeridas."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "TU_API_KEY_AQUI":
        raise ValueError(
            "Configura una API Key válida en el archivo .env "
            "usando GEMINI_API_KEY."
        )