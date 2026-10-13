"""Catálogo unificado de Tools de MantenIA para el ToolNode del grafo."""

from tools.alertas_tool import consultar_alertas, priorizar_alertas
from tools.documentos_tool import consultar_documentos_vehiculo
from tools.fecha_tool import obtener_fecha
from tools.moto_tool import (
    consultar_historial,
    consultar_moto,
    consultar_recomendaciones,
)

TOOLS_MANTENIMIENTO = [
    obtener_fecha,
    consultar_moto,
    consultar_historial,
    consultar_recomendaciones,
    consultar_documentos_vehiculo,
    consultar_alertas,
    priorizar_alertas,
]
