"""Tool para consultar documentos y vencimientos del vehículo."""

from langchain.tools import tool

from core import repositorio
from tools._busqueda import coincide


@tool
def consultar_documentos_vehiculo(consulta: str) -> dict:
    """Consulta documentos o vencimientos del vehículo por palabra clave."""
    resultados = [
        documento
        for documento in repositorio.cargar_documentos()
        if coincide(
            consulta,
            documento["moto_id"],
            documento["documento"],
            documento["descripcion"],
        )
    ]

    return {
        "consulta": consulta,
        "resultados": resultados,
        "cantidad": len(resultados),
    }
