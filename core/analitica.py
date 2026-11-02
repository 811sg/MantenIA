"""Cálculos de vencimientos y resumen del garaje (funciones puras).

Los usa la vista «Garaje», que muestra en pantalla los mismos datos que
consulta el agente. No modifica ninguna fuente de datos.
"""

from datetime import date

from core import repositorio

UMBRAL_POR_VENCER_DIAS = 30


def dias_restantes(fecha_iso: str, hoy: date | None = None) -> int:
    """Días hasta una fecha ISO (negativo si ya pasó)."""
    return (date.fromisoformat(fecha_iso) - (hoy or date.today())).days


def clasificar_vencimiento(dias: int, umbral: int = UMBRAL_POR_VENCER_DIAS) -> str:
    """`vencido`, `por_vencer` (dentro del umbral) o `vigente`."""
    if dias < 0:
        return "vencido"
    if dias <= umbral:
        return "por_vencer"
    return "vigente"


def etiqueta_vencimiento(dias: int) -> str:
    """Texto corto para mostrar en tablas y tarjetas."""
    estado = clasificar_vencimiento(dias)
    if estado == "vencido":
        return f"Vencido hace {abs(dias)} d"
    if estado == "por_vencer":
        return "Vence hoy" if dias == 0 else f"Vence en {dias} d"
    return f"Vigente ({dias} d)"


def nombre_moto(moto: dict) -> str:
    return f"{moto['marca']} {moto['modelo']}"


def resumen_garaje(hoy: date | None = None) -> dict:
    """Indicadores globales para las tarjetas superiores de la vista Garaje."""
    hoy = hoy or date.today()
    alertas = [a for a in repositorio.cargar_alertas() if a["estado"].lower() == "pendiente"]
    documentos = repositorio.cargar_documentos()

    alertas_vencidas = sum(
        1 for a in alertas if dias_restantes(a["fecha_limite"], hoy) < 0
    )
    docs_estado = [
        clasificar_vencimiento(dias_restantes(d["fecha_vencimiento"], hoy))
        for d in documentos
    ]

    return {
        "motos": len(repositorio.cargar_motos()),
        "alertas_pendientes": len(alertas),
        "alertas_vencidas": alertas_vencidas,
        "documentos_vencidos": docs_estado.count("vencido"),
        "documentos_por_vencer": docs_estado.count("por_vencer"),
    }
