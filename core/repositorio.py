"""Capa de acceso a datos: lectura de las fuentes JSON de `data/`.

Es la única que conoce las rutas y el formato de los archivos. La usan tanto
las Tools del agente como las vistas de la interfaz, de modo que ambos ven
siempre exactamente los mismos datos.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _cargar(nombre_archivo: str) -> list[dict]:
    with (DATA_DIR / nombre_archivo).open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def cargar_motos() -> list[dict]:
    return _cargar("motos.json")


def cargar_historial() -> list[dict]:
    return _cargar("historial_mantenimientos.json")


def cargar_recomendaciones() -> list[dict]:
    return _cargar("recomendaciones_tecnicas.json")


def cargar_alertas() -> list[dict]:
    return _cargar("alertas.json")


def cargar_documentos() -> list[dict]:
    return _cargar("documentos_vehiculo.json")
