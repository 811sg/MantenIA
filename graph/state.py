"""Esquema de estado del grafo MantenIA (el corazón de LangGraph).

Solo define la estructura de datos tipada y los reducers: aquí no hay
llamadas a LLM ni lógica de negocio.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MotoInfo(TypedDict):
    marca: str
    modelo: str
    kilometraje_actual: str


class MantenimientoState(TypedDict):
    # Reducer automático: gestiona HumanMessage, AIMessage y ToolMessage
    # y los empareja por id de llamada a herramienta.
    messages: Annotated[list[BaseMessage], add_messages]
    moto: MotoInfo
    ruta: str
    motivo: str
    herramientas_usadas: list[str]
    pasos_ejecutados: list[str]  # Traza de nodos recorridos en el turno
