"""Clasificación de errores en mensajes comprensibles para el usuario.

Traduce las excepciones técnicas (cuota, credenciales, red, ciclos del grafo)
a un `ErrorInfo` con título, explicación y sugerencia. Nunca expone la API key.
"""

import re
from dataclasses import asdict, dataclass

from langgraph.errors import GraphRecursionError

_PATRON_CLAVE = re.compile(r"AIza[0-9A-Za-z_\-]{20,}")


@dataclass(frozen=True)
class ErrorInfo:
    tipo: str
    titulo: str
    sugerencia: str
    reintentable: bool
    detalle: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def ocultar_secretos(texto: str) -> str:
    """Enmascara cualquier API key de Google que aparezca en un mensaje."""
    return _PATRON_CLAVE.sub("***", texto)


def _contiene(texto: str, *claves: str) -> bool:
    return any(clave in texto for clave in claves)


def clasificar_error(error: BaseException) -> ErrorInfo:
    """Devuelve el `ErrorInfo` correspondiente a una excepción."""
    detalle = ocultar_secretos(str(error))[:400]
    texto = f"{type(error).__name__} {detalle}".lower()

    if isinstance(error, GraphRecursionError):
        return ErrorInfo(
            tipo="ciclo",
            titulo="El agente entró en un ciclo de herramientas",
            sugerencia="Reformula la pregunta de forma más concreta e inténtalo de nuevo.",
            reintentable=True,
            detalle=detalle,
        )

    if _contiene(texto, "resource_exhausted", "429", "quota", "rate limit", "rate_limit"):
        return ErrorInfo(
            tipo="cuota",
            titulo="Se alcanzó el límite de uso del modelo",
            sugerencia=(
                "Espera un minuto y reintenta. Si persiste, es posible que se haya "
                "agotado la cuota diaria del plan gratuito: prueba con otro modelo "
                "en GEMINI_MODEL (por ejemplo gemini-2.5-flash)."
            ),
            reintentable=True,
            detalle=detalle,
        )

    if _contiene(
        texto, "api key", "api_key", "permission_denied", "unauthenticated",
        "401", "403", "invalid_argument: api",
    ):
        return ErrorInfo(
            tipo="credenciales",
            titulo="La API Key de Gemini no es válida o no tiene permisos",
            sugerencia="Revisa GEMINI_API_KEY en el archivo .env o en los Secrets del despliegue.",
            reintentable=False,
            detalle=detalle,
        )

    if _contiene(texto, "404") and _contiene(texto, "model", "not found"):
        return ErrorInfo(
            tipo="modelo",
            titulo="El modelo configurado no está disponible",
            sugerencia="Verifica el valor de GEMINI_MODEL (por ejemplo gemini-2.5-flash).",
            reintentable=False,
            detalle=detalle,
        )

    if _contiene(
        texto, "timeout", "timed out", "unavailable", "503", "502", "504",
        "connect", "network", "connection", "dns", "deadline",
    ):
        return ErrorInfo(
            tipo="conectividad",
            titulo="No se pudo contactar al servicio de Gemini",
            sugerencia="Revisa tu conexión a internet y vuelve a intentarlo en unos segundos.",
            reintentable=True,
            detalle=detalle,
        )

    if _contiene(texto, "safety", "blocked", "prohibited"):
        return ErrorInfo(
            tipo="contenido",
            titulo="El modelo no pudo responder a esa consulta",
            sugerencia="Reformula la pregunta enfocándola en el mantenimiento de la moto.",
            reintentable=True,
            detalle=detalle,
        )

    return ErrorInfo(
        tipo="desconocido",
        titulo="Ocurrió un error inesperado al procesar la solicitud",
        sugerencia="Intenta de nuevo. Si el problema continúa, reinicia la conversación.",
        reintentable=True,
        detalle=detalle,
    )
