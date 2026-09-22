"""Tool para consultar documentos y vencimientos del vehículo."""

import json
from pathlib import Path

from langchain.tools import tool

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "documentos_vehiculo.json"


@tool
def consultar_documentos_vehiculo(consulta: str) -> dict:
    """Consulta documentos o vencimientos del vehículo por palabra clave."""
    with DATA_FILE.open("r", encoding="utf-8") as archivo:
        documentos = json.load(archivo)

    criterio = consulta.lower().strip()

    resultados = [
        documento
        for documento in documentos
        if criterio in documento["moto_id"].lower()
        or criterio in documento["documento"].lower()
        or criterio in documento["descripcion"].lower()
    ]

    return {
        "consulta": consulta,
        "resultados": resultados,
        "cantidad": len(resultados),
    }