"""Utilidades para la consulta de motocicletas y su historial de mantenimiento.

Este módulo proporciona funciones para cargar y consultar la información
de motocicletas, mantenimientos y recomendaciones técnicas almacenada en
los archivos JSON de datos de la aplicación.
"""

import json
from pathlib import Path
from typing import TypedDict


class Moto(TypedDict):
    """Representa una motocicleta registrada en el sistema."""

    id: str
    marca: str
    modelo: str
    año: int
    cilindraje: int
    kilometraje_actual: int


class Mantenimiento(TypedDict):
    """Representa un mantenimiento realizado a una motocicleta."""

    moto_id: str
    tipo: str
    fecha: str
    kilometraje: int


class Recomendacion(TypedDict):
    """Representa la recomendación técnica de un tipo de mantenimiento."""

    tipo: str
    intervalo_km: int
    intervalo_meses: int
    descripcion: str


# Rutas a los archivos que contienen la información de motos, historial y
# recomendaciones técnicas.
MOTOS_FILE = Path(__file__).resolve().parents[1] / "data" / "motos.json"
HISTORIAL_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "historial_mantenimientos.json"
)
RECOMENDACIONES_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "recomendaciones_tecnicas.json"
)


def consultar_moto(consulta: str) -> list[Moto]:
    """Busca motocicletas registradas según un criterio de consulta.

    La búsqueda no distingue entre mayúsculas y minúsculas y permite
    coincidencias parciales por id, marca o modelo.

    Args:
        consulta: Id, marca, modelo o fragmento de texto utilizado como
            criterio de búsqueda.

    Returns:
        Lista de motocicletas que coinciden con el criterio de búsqueda.
        Devuelve una lista vacía si no se encuentran coincidencias.

    Raises:
        FileNotFoundError: Si el archivo de motos no existe.
        json.JSONDecodeError: Si el archivo contiene un JSON inválido.
    """
    with MOTOS_FILE.open("r", encoding="utf-8") as archivo:
        motos: list[Moto] = json.load(archivo)

    criterio = consulta.lower().strip()

    return [
        moto
        for moto in motos
        if criterio in moto["id"].lower()
        or criterio in moto["marca"].lower()
        or criterio in moto["modelo"].lower()
    ]


def consultar_historial(moto_id: str) -> list[Mantenimiento]:
    """Busca los mantenimientos realizados a una motocicleta específica.

    Args:
        moto_id: Identificador de la motocicleta cuyo historial se desea
            consultar.

    Returns:
        Lista de mantenimientos registrados para la motocicleta indicada,
        ordenada según el orden almacenado en el archivo. Devuelve una
        lista vacía si no se encuentran coincidencias.

    Raises:
        FileNotFoundError: Si el archivo de historial no existe.
        json.JSONDecodeError: Si el archivo contiene un JSON inválido.
    """
    with HISTORIAL_FILE.open("r", encoding="utf-8") as archivo:
        historial: list[Mantenimiento] = json.load(archivo)

    criterio = moto_id.lower().strip()

    return [
        mantenimiento
        for mantenimiento in historial
        if criterio == mantenimiento["moto_id"].lower()
    ]


def consultar_recomendaciones(tipo: str = "") -> list[Recomendacion]:
    """Busca recomendaciones técnicas de mantenimiento según un tipo.

    Si no se especifica un tipo, se devuelven todas las recomendaciones
    técnicas disponibles.

    Args:
        tipo: Nombre o fragmento del tipo de mantenimiento a consultar,
            por ejemplo "cambio_aceite" o "aceite". Si se deja vacío, se
            devuelven todas las recomendaciones registradas.

    Returns:
        Lista de recomendaciones técnicas que coinciden con el criterio
        de búsqueda. Devuelve una lista vacía si no se encuentran
        coincidencias.

    Raises:
        FileNotFoundError: Si el archivo de recomendaciones no existe.
        json.JSONDecodeError: Si el archivo contiene un JSON inválido.
    """
    with RECOMENDACIONES_FILE.open("r", encoding="utf-8") as archivo:
        recomendaciones: list[Recomendacion] = json.load(archivo)

    if not tipo:
        return recomendaciones

    criterio = tipo.lower().strip()

    return [
        recomendacion
        for recomendacion in recomendaciones
        if criterio in recomendacion["tipo"].lower()
    ]