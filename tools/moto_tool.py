"""Tools para consultar motocicletas, su historial y recomendaciones."""

import json
from pathlib import Path

from langchain.tools import tool

MOTOS_FILE = Path(__file__).resolve().parents[1] / "data" / "motos.json"
HISTORIAL_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "historial_mantenimientos.json"
)
RECOMENDACIONES_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "recomendaciones_tecnicas.json"
)


@tool
def consultar_moto(consulta: str) -> dict:
    """Consulta motocicletas registradas por id, marca o modelo."""
    with MOTOS_FILE.open("r", encoding="utf-8") as archivo:
        motos = json.load(archivo)

    criterio = consulta.lower().strip()

    resultados = [
        moto
        for moto in motos
        if criterio in moto["id"].lower()
        or criterio in moto["marca"].lower()
        or criterio in moto["modelo"].lower()
    ]

    return {
        "consulta": consulta,
        "resultados": resultados,
        "cantidad": len(resultados),
    }


@tool
def consultar_historial(moto_id: str) -> dict:
    """Consulta los mantenimientos realizados a una motocicleta por su id."""
    with HISTORIAL_FILE.open("r", encoding="utf-8") as archivo:
        historial = json.load(archivo)

    criterio = moto_id.lower().strip()

    resultados = [
        mantenimiento
        for mantenimiento in historial
        if criterio == mantenimiento["moto_id"].lower()
    ]

    return {
        "consulta": moto_id,
        "resultados": resultados,
        "cantidad": len(resultados),
    }


@tool
def consultar_recomendaciones(tipo: str = "") -> dict:
    """Consulta los intervalos técnicos recomendados por tipo de mantenimiento."""
    with RECOMENDACIONES_FILE.open("r", encoding="utf-8") as archivo:
        recomendaciones = json.load(archivo)

    criterio = tipo.lower().strip()

    resultados = (
        recomendaciones
        if not criterio
        else [
            recomendacion
            for recomendacion in recomendaciones
            if criterio in recomendacion["tipo"].lower()
        ]
    )

    return {
        "consulta": tipo,
        "resultados": resultados,
        "cantidad": len(resultados),
    }