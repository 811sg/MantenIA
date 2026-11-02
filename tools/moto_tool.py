"""Tools para consultar motocicletas, su historial y recomendaciones."""

from langchain.tools import tool

from core import repositorio
from tools._busqueda import coincide, normalizar


@tool
def consultar_moto(consulta: str) -> dict:
    """Consulta motocicletas registradas por id, marca o modelo."""
    resultados = [
        moto
        for moto in repositorio.cargar_motos()
        if coincide(consulta, moto["id"], moto["marca"], moto["modelo"])
    ]

    return {
        "consulta": consulta,
        "resultados": resultados,
        "cantidad": len(resultados),
    }


@tool
def consultar_historial(moto_id: str) -> dict:
    """Consulta los mantenimientos realizados a una motocicleta por su id."""
    criterio = normalizar(moto_id)

    resultados = [
        mantenimiento
        for mantenimiento in repositorio.cargar_historial()
        if criterio == normalizar(mantenimiento["moto_id"])
    ]

    return {
        "consulta": moto_id,
        "resultados": resultados,
        "cantidad": len(resultados),
    }


@tool
def consultar_recomendaciones(tipo: str = "") -> dict:
    """Consulta los intervalos técnicos recomendados por tipo de mantenimiento."""
    resultados = [
        recomendacion
        for recomendacion in repositorio.cargar_recomendaciones()
        if coincide(tipo, recomendacion["tipo"])
    ]

    return {
        "consulta": tipo,
        "resultados": resultados,
        "cantidad": len(resultados),
    }
