"""Chain determinista para consultas conceptuales sobre mantenimiento."""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from prompts.mantenimiento_prompt import GENERAL_SYSTEM_PROMPT


def crear_respuesta_chain():
    """Crea Prompt -> Model -> Parser para respuestas sin Tools."""
    model = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=0.2,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", GENERAL_SYSTEM_PROMPT),
            ("human", "{pregunta}"),
        ]
    )

    return prompt | model | StrOutputParser()