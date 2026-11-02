"""Modelo de lenguaje simulado y guionado para pruebas sin llamar a Gemini.

`ModeloGuionado` es un `BaseChatModel` real de LangChain: dispara los mismos
callbacks que Gemini (tokens, latencia), soporta `bind_tools` y
`with_structured_output`, y devuelve respuestas predefinidas en orden. Así se
prueba el grafo completo (enrutador, bucle de herramientas, memoria) de forma
determinista y gratuita.
"""

import itertools
import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda

_contador = itertools.count(1)


def decision(ruta: str, motivo: str = "prueba") -> AIMessage:
    """Respuesta del enrutador (JSON validado contra `RutaConsulta`)."""
    return AIMessage(
        content=json.dumps({"ruta": ruta, "motivo": motivo}),
        usage_metadata={"input_tokens": 50, "output_tokens": 10, "total_tokens": 60},
    )


def texto(contenido: str, entrada: int = 100, salida: int = 20) -> AIMessage:
    return AIMessage(
        content=contenido,
        usage_metadata={
            "input_tokens": entrada,
            "output_tokens": salida,
            "total_tokens": entrada + salida,
        },
    )


def llamada_tool(nombre: str, argumentos: dict | None = None) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": nombre, "args": argumentos or {}, "id": f"call_{next(_contador)}"}
        ],
        usage_metadata={"input_tokens": 120, "output_tokens": 15, "total_tokens": 135},
    )


class ModeloGuionado(BaseChatModel):
    """Devuelve `respuestas` en orden; repite la última si se agotan."""

    respuestas: list[Any]
    indice: int = 0
    entradas: list[Any] = []  # mensajes recibidos en cada invocación

    @property
    def _llm_type(self) -> str:
        return "guionado"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.entradas.append(list(messages))
        original = self.respuestas[min(self.indice, len(self.respuestas) - 1)]
        self.indice += 1

        # Copia con ids nuevos: si el guion se repite, LangGraph (add_messages)
        # no debe confundir la respuesta con una anterior.
        mensaje = original.model_copy(deep=True)
        mensaje.id = None
        for llamada in mensaje.tool_calls:
            llamada["id"] = f"call_{next(_contador)}"
        return ChatResult(generations=[ChatGeneration(message=mensaje)])

    def bind_tools(self, tools, **kwargs):
        return self

    def with_structured_output(self, schema, **kwargs):
        def _decidir(entrada, config):
            respuesta = self.invoke(entrada, config)
            return schema.model_validate_json(respuesta.content)

        return RunnableLambda(_decidir)
