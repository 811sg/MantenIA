"""Tool para obtener fecha y día actual."""

from datetime import datetime

from langchain.tools import tool


@tool
def obtener_fecha() -> dict:
    """Obtiene la fecha actual y el día de la semana en español."""
    dias = {
        0: "lunes",
        1: "martes",
        2: "miércoles",
        3: "jueves",
        4: "viernes",
        5: "sábado",
        6: "domingo",
    }

    ahora = datetime.now()

    return {
        "fecha": ahora.strftime("%Y-%m-%d"),
        "dia": dias[ahora.weekday()],
        "hora": ahora.strftime("%H:%M"),
    }