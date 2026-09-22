"""Chain para priorizar una lista conocida de alertas de mantenimiento."""

import json

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import GEMINI_API_KEY, GEMINI_MODEL


def crear_priorizacion_chain():
    """Crea una Chain fija: datos -> prompt -> modelo -> salida."""
    model = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=0.1,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                Prioriza alertas de mantenimiento de motocicletas usando
                exclusivamente los datos proporcionados. Considera fecha
                límite, estado y prioridad registrada. No inventes
                alertas. Devuelve una lista numerada breve con la
                justificación de cada prioridad.
                """.strip(),
            ),
            (
                "human",
                "Alertas disponibles:\n{alertas}\n\n"
                "Contexto adicional: {contexto}",
            ),
        ]
    )

    return prompt | model | StrOutputParser()


def serializar_alertas(alertas) -> str:
    """Convierte las alertas a JSON legible para la Chain."""
    return json.dumps(alertas, ensure_ascii=False, indent=2)