"""Pruebas de la clasificación de errores y del enmascarado de secretos."""

import pytest
from langgraph.errors import GraphRecursionError

from core.errors import clasificar_error, ocultar_secretos


@pytest.mark.parametrize(
    "excepcion, tipo, reintentable",
    [
        (RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded"), "cuota", True),
        (RuntimeError("400 API key not valid. Please pass a valid API key"), "credenciales", False),
        (RuntimeError("403 PERMISSION_DENIED"), "credenciales", False),
        (RuntimeError("404 models/gemini-9 is not found for API version"), "modelo", False),
        (TimeoutError("request timed out"), "conectividad", True),
        (RuntimeError("503 UNAVAILABLE"), "conectividad", True),
        (GraphRecursionError("Recursion limit of 12 reached"), "ciclo", True),
        (ValueError("algo raro"), "desconocido", True),
    ],
)
def test_clasificacion(excepcion, tipo, reintentable):
    info = clasificar_error(excepcion)
    assert info.tipo == tipo
    assert info.reintentable is reintentable
    assert info.titulo and info.sugerencia


def test_nunca_se_expone_la_api_key():
    clave = "AIza" + "A" * 35
    info = clasificar_error(RuntimeError(f"API key not valid: {clave}"))
    assert clave not in info.detalle
    assert "***" in info.detalle
    assert ocultar_secretos(f"x {clave} y") == "x *** y"
