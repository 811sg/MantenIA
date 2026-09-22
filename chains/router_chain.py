"""Chain de clasificación para decidir entre Chain y Agent."""

from typing import Literal

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from prompts.mantenimiento_prompt import ROUTER_SYSTEM_PROMPT


class RutaConsulta(BaseModel):
    """Ruta seleccionada para atender la solicitud."""

    ruta: Literal["chain", "agent"] = Field(
        description="Usa 'chain' para flujos conocidos sin Tools y "
        "'agent' cuando se requieren datos externos o herramientas."
    )
    motivo: str = Field(
        description="Justificación breve de la selección."
    )


def crear_router_chain():
    """Crea la Chain que clasifica la solicitud."""
    model = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=0,
    )

    structured_model = model.with_structured_output(RutaConsulta)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ROUTER_SYSTEM_PROMPT),
            ("human", "{pregunta}"),
        ]
    )

    return prompt | structured_model