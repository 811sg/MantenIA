"""Fábrica única de clientes Gemini.

Centraliza la creación del modelo (clave, nombre, tiempo de espera y
reintentos) para que nodos y tools no la dupliquen y para poder sustituirla
fácilmente en las pruebas.
"""

from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT_S,
)


@lru_cache(maxsize=None)
def obtener_modelo(temperature: float) -> ChatGoogleGenerativeAI:
    """Crea (una sola vez por temperatura) el cliente de Gemini."""
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=temperature,
        timeout=LLM_TIMEOUT_S,
        max_retries=LLM_MAX_RETRIES,
    )
