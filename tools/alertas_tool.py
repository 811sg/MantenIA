"""Tools para consultar y priorizar alertas de mantenimiento."""

import json
from pathlib import Path

from langchain.tools import tool

from chains.prioritization_chain import (
    crear_priorizacion_chain,
    serializar_alertas,
)

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "alertas.json"


def _cargar_alertas() -> list[dict]:
    with DATA_FILE.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


@tool
def consultar_alertas(consulta: str = "pendientes") -> dict:
    """Consulta alertas de mantenimiento por estado, moto o palabra clave."""
    alertas = _cargar_alertas()
    criterio = consulta.lower().strip()

    if criterio in {"todas", "todo", "*"}:
        resultados = alertas
    elif criterio in {"pendientes", "pendiente"}:
        resultados = [
            a for a in alertas
            if a["estado"].lower() == "pendiente"
        ]
    else:
        resultados = [
            a for a in alertas
            if criterio in a["estado"].lower()
            or criterio in a["moto_id"].lower()
            or criterio in a["alerta"].lower()
        ]

    return {
        "consulta": consulta,
        "resultados": resultados,
        "cantidad": len(resultados),
    }


@tool
def priorizar_alertas(contexto: str = "") -> str:
    """Prioriza las alertas de mantenimiento pendientes mediante una Chain determinista."""
    alertas = [
        a for a in _cargar_alertas()
        if a["estado"].lower() == "pendiente"
    ]

    chain = crear_priorizacion_chain()

    return chain.invoke(
        {
            "alertas": serializar_alertas(alertas),
            "contexto": contexto or "Sin contexto adicional.",
        }
    )