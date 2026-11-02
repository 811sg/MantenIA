"""Tools para consultar y priorizar alertas de mantenimiento.

La Chain determinista de priorización (datos -> prompt -> modelo -> salida)
vive aquí, junto a la Tool que la usa, y se ejecuta como un paso más dentro
del nodo `herramientas`.
"""

import json

from langchain.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core import llm_factory, repositorio
from tools._busqueda import coincide, normalizar

PRIORIZACION_SYSTEM_PROMPT = """
Prioriza alertas de mantenimiento de motocicletas usando exclusivamente los
datos proporcionados. Considera fecha límite, estado y prioridad registrada.
No inventes alertas. Devuelve una lista numerada breve con la justificación
de cada prioridad.
""".strip()


def _crear_priorizacion_chain():
    """Crea una Chain fija: datos -> prompt -> modelo -> salida."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PRIORIZACION_SYSTEM_PROMPT),
            (
                "human",
                "Alertas disponibles:\n{alertas}\n\n"
                "Contexto adicional: {contexto}",
            ),
        ]
    )

    return prompt | llm_factory.obtener_modelo(0.1) | StrOutputParser()


@tool
def consultar_alertas(consulta: str = "pendientes") -> dict:
    """Consulta alertas de mantenimiento por estado, moto o palabra clave."""
    alertas = repositorio.cargar_alertas()
    criterio = normalizar(consulta)

    if criterio in {"todas", "todo", "*", ""} or consulta.strip() == "*":
        resultados = alertas
    elif criterio in {"pendientes", "pendiente"}:
        resultados = [a for a in alertas if a["estado"].lower() == "pendiente"]
    else:
        resultados = [
            a
            for a in alertas
            if coincide(consulta, a["estado"], a["moto_id"], a["alerta"], a["prioridad"])
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
        a for a in repositorio.cargar_alertas() if a["estado"].lower() == "pendiente"
    ]

    return _crear_priorizacion_chain().invoke(
        {
            "alertas": json.dumps(alertas, ensure_ascii=False, indent=2),
            "contexto": contexto or "Sin contexto adicional.",
        }
    )
