"""Nodos del grafo MantenIA: funciones transformadoras `state -> dict`.

Cada nodo recibe el estado y devuelve solo las modificaciones a aplicar.
Aquí no se crean aristas ni se compila el grafo (eso vive en workflow.py).
"""

from functools import lru_cache
from typing import Literal

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from graph.state import MantenimientoState
from prompts.mantenimiento_prompt import (
    AGENT_SYSTEM_TEMPLATE,
    CONCEPTUAL_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT,
)
from tools import TOOLS_MANTENIMIENTO


# ---------------------------------------------------------------------------
# Utilidades puras para leer mensajes de LangChain
# ---------------------------------------------------------------------------


def extraer_texto(mensaje: BaseMessage) -> str:
    """Devuelve el texto de un mensaje, sea `str` o lista de bloques."""
    contenido = mensaje.content

    if isinstance(contenido, str):
        return contenido

    if isinstance(contenido, list):
        partes = []
        for bloque in contenido:
            if isinstance(bloque, dict) and bloque.get("type") == "text":
                partes.append(str(bloque.get("text", "")))
            elif isinstance(bloque, str):
                partes.append(bloque)
        return "\n".join(p for p in partes if p).strip()

    return str(contenido)


def contexto_para_router(mensajes: list[BaseMessage], limite: int = 4) -> str:
    """Resume la conversación reciente y marca la consulta actual."""
    previos: list[str] = []

    for mensaje in mensajes[:-1]:
        if isinstance(mensaje, HumanMessage):
            previos.append(f"Usuario: {extraer_texto(mensaje)}")
        elif isinstance(mensaje, AIMessage) and not mensaje.tool_calls:
            texto = extraer_texto(mensaje)
            if texto:
                previos.append(f"Asistente: {texto}")

    reciente = "\n".join(previos[-limite:]) or "Sin contexto previo."
    actual = extraer_texto(mensajes[-1]) if mensajes else ""

    return (
        f"Contexto reciente:\n{reciente}\n\n"
        f"Consulta actual del usuario:\n{actual}"
    )


def solo_conversacion(mensajes: list[BaseMessage]) -> list[BaseMessage]:
    """Deja solo los turnos de diálogo (usuario y respuestas finales).

    Descarta las llamadas a herramientas y sus resultados. Se usa en el nodo
    conceptual, cuyo modelo no tiene herramientas vinculadas: así conserva la
    memoria de la charla sin enviarle historial de function calling.
    """
    dialogo: list[BaseMessage] = []

    for mensaje in mensajes:
        if isinstance(mensaje, HumanMessage):
            dialogo.append(mensaje)
        elif (
            isinstance(mensaje, AIMessage)
            and not mensaje.tool_calls
            and extraer_texto(mensaje)
        ):
            dialogo.append(mensaje)

    return dialogo


class RutaConsulta(BaseModel):
    """Ruta seleccionada por el nodo enrutador."""

    ruta: Literal["conceptual", "herramientas"] = Field(
        description="Usa 'conceptual' para teoría general sin datos y "
        "'herramientas' cuando se requieren datos de la moto, historial, "
        "intervalos, alertas, documentos o la fecha actual."
    )
    motivo: str = Field(description="Justificación breve de la selección.")


@lru_cache(maxsize=None)
def _modelo(temperature: float) -> ChatGoogleGenerativeAI:
    """Crea (una sola vez por temperatura) el cliente de Gemini."""
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=temperature,
    )


def _registrar_paso(state: MantenimientoState, nombre: str) -> list[str]:
    return [*state.get("pasos_ejecutados", []), nombre]


# Nodo 1: Clasificador estructurado (temperatura 0)
def enrutador_node(state: MantenimientoState) -> dict:
    clasificador = _modelo(0).with_structured_output(RutaConsulta)

    decision = clasificador.invoke(
        [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=contexto_para_router(state["messages"])),
        ]
    )

    # Si el modelo no devuelve una salida estructurada válida, la ruta más
    # segura es 'herramientas': nunca se responde de memoria sobre datos.
    if decision is None:
        ruta = "herramientas"
        motivo = "No se pudo clasificar; se usa la ruta segura con herramientas."
    else:
        ruta, motivo = decision.ruta, decision.motivo

    return {
        "ruta": ruta,
        "motivo": motivo,
        "pasos_ejecutados": _registrar_paso(state, "enrutador"),
    }


# Nodo 2: Respuesta teórica sin herramientas
def conceptual_node(state: MantenimientoState) -> dict:
    respuesta = _modelo(0.2).invoke(
        [
            SystemMessage(content=CONCEPTUAL_SYSTEM_PROMPT),
            *solo_conversacion(state["messages"]),
        ]
    )

    return {
        "messages": [respuesta],
        "pasos_ejecutados": _registrar_paso(state, "nodo_conceptual"),
    }


# Nodo 3: Razonamiento con herramientas vinculadas (ReAct)
def agente_mantenimiento_node(state: MantenimientoState) -> dict:
    moto = state["moto"]

    system_prompt = AGENT_SYSTEM_TEMPLATE.format(
        marca=moto["marca"],
        modelo=moto["modelo"],
        kilometraje_actual=moto["kilometraje_actual"],
    )

    modelo_con_tools = _modelo(0.1).bind_tools(TOOLS_MANTENIMIENTO)
    respuesta = modelo_con_tools.invoke(
        [SystemMessage(content=system_prompt), *state["messages"]]
    )

    return {
        "messages": [respuesta],
        "pasos_ejecutados": _registrar_paso(state, "agente_mantenimiento"),
    }


# Nodo 4: Ejecución nativa con ToolNode
_ejecutor_tools = ToolNode(TOOLS_MANTENIMIENTO)


def herramientas_node(state: MantenimientoState) -> dict:
    ultimo = state["messages"][-1]
    solicitadas = [
        llamada["name"] for llamada in (getattr(ultimo, "tool_calls", None) or [])
    ]

    usadas = list(state.get("herramientas_usadas", []))
    for nombre in solicitadas:
        if nombre not in usadas:
            usadas.append(nombre)

    resultado = _ejecutor_tools.invoke(state)

    return {
        "messages": resultado["messages"],
        "herramientas_usadas": usadas,
        "pasos_ejecutados": _registrar_paso(state, "herramientas"),
    }
