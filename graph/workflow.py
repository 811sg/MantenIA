"""Topología del grafo MantenIA: aristas, bucle cíclico y checkpointer.

Define cómo se conectan los nodos y compila el grafo con `MemorySaver`.
No importa componentes visuales de Streamlit.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from graph.nodes import (
    agente_mantenimiento_node,
    conceptual_node,
    enrutador_node,
    herramientas_node,
)
from graph.state import MantenimientoState


def decidir_ruta(state: MantenimientoState) -> str:
    """Bifurcación del enrutador: devuelve la ruta clasificada."""
    return state.get("ruta", "herramientas")


def evaluar_tools(state: MantenimientoState) -> str:
    """¿El agente pidió herramientas o ya tiene la respuesta final?"""
    ultimo = state["messages"][-1]

    if getattr(ultimo, "tool_calls", None):
        return "herramientas"

    return END


def crear_grafo_mantenimiento():
    """Construye y compila el StateGraph cíclico de MantenIA."""
    builder = StateGraph(MantenimientoState)

    builder.add_node("enrutador", enrutador_node)
    builder.add_node("nodo_conceptual", conceptual_node)
    builder.add_node("agente_mantenimiento", agente_mantenimiento_node)
    builder.add_node("herramientas", herramientas_node)

    # Arista inicial
    builder.add_edge(START, "enrutador")

    # Bifurcación del enrutador
    builder.add_conditional_edges(
        "enrutador",
        decidir_ruta,
        {
            "conceptual": "nodo_conceptual",
            "herramientas": "agente_mantenimiento",
        },
    )

    # Arista condicional: ¿llamar a herramientas o terminar?
    builder.add_conditional_edges(
        "agente_mantenimiento",
        evaluar_tools,
        {"herramientas": "herramientas", END: END},
    )

    # Bucle cíclico: de herramientas se regresa al agente
    builder.add_edge("herramientas", "agente_mantenimiento")
    builder.add_edge("nodo_conceptual", END)

    return builder.compile(checkpointer=MemorySaver())
