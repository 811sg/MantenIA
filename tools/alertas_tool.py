"""Tools para consultar y priorizar alertas de mantenimiento.

En la v3 desaparece la carpeta `chains/`: la Chain determinista de
priorización (datos -> prompt -> modelo -> salida) vive aquí, junto a la
Tool que la usa, y se ejecuta como un paso más dentro del nodo `herramientas`.
"""

import json
from pathlib import Path

from langchain.tools import tool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import GEMINI_API_KEY, GEMINI_MODEL

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "alertas.json"

PRIORIZACION_SYSTEM_PROMPT = """
Prioriza alertas de mantenimiento de motocicletas usando exclusivamente los
datos proporcionados. Considera fecha límite, estado y prioridad registrada.
No inventes alertas. Devuelve una lista numerada breve con la justificación
de cada prioridad.
""".strip()


def _cargar_alertas() -> list[dict]:
    with DATA_FILE.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def _crear_priorizacion_chain():
    """Crea una Chain fija: datos -> prompt -> modelo -> salida."""
    model = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=0.1,
    )

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

    return prompt | model | StrOutputParser()


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

    chain = _crear_priorizacion_chain()

    return chain.invoke(
        {
            "alertas": json.dumps(alertas, ensure_ascii=False, indent=2),
            "contexto": contexto or "Sin contexto adicional.",
        }
    )
