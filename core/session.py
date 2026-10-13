"""Sesión de Streamlit, estado de la interfaz y threads de LangGraph.

Integra Streamlit con los checkpoints de LangGraph: crea un `thread_id` por
sesión de usuario, ejecuta cada turno del grafo y traduce el resultado al
formato que consume la interfaz. También guarda el estado visible de la UI
(moto detectada, mensajes mostrados y traza de la última ejecución).

La memoria conversacional NO se arma como texto: la gestiona el checkpointer
de LangGraph (MemorySaver) a través del `thread_id`.
"""

import re
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

from graph.nodes import extraer_texto
from graph.workflow import crear_grafo_mantenimiento

# Tope de pasos por turno: evita ciclos infinitos agente <-> herramientas.
RECURSION_LIMIT = 12


# ---------------------------------------------------------------------------
# Estado de la interfaz (moto detectada, mensajes y trazabilidad)
# ---------------------------------------------------------------------------

MOTO_INICIAL = {
    "marca": "No registrada",
    "modelo": "No registrado",
    "kilometraje_actual": "No registrado",
}


MARCAS = [
    "yamaha",
    "honda",
    "suzuki",
    "kawasaki",
    "bajaj",
    "akt",
    "ktm",
    "tvs",
]


def _ejecucion_inicial() -> dict:
    return {
        "ruta": "Sin ejecución",
        "motivo": "",
        "tools": [],
        "pasos": [],
    }


def inicializar_estado() -> None:
    if "moto" not in st.session_state:
        st.session_state.moto = MOTO_INICIAL.copy()

    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []

    if "ultima_ejecucion" not in st.session_state:
        st.session_state.ultima_ejecucion = _ejecucion_inicial()


def actualizar_estado_moto(texto: str) -> None:
    texto_lower = texto.lower()

    for marca in MARCAS:
        if marca in texto_lower:
            st.session_state.moto["marca"] = marca.capitalize()
            break

    patron_modelo = r"(?:modelo)\s+([A-Za-zÁÉÍÓÚáéíóúÑñ0-9\-]+)"
    coincidencia_modelo = re.search(patron_modelo, texto, re.IGNORECASE)

    if coincidencia_modelo:
        st.session_state.moto["modelo"] = coincidencia_modelo.group(1).upper()

    patron_kilometraje = r"(\d{1,3}(?:[.,]\d{3})+|\d+)\s*(?:km|kil[oó]metros)"
    coincidencia_km = re.search(patron_kilometraje, texto_lower)

    if coincidencia_km:
        kilometraje = coincidencia_km.group(1).replace(".", "").replace(",", "")
        st.session_state.moto["kilometraje_actual"] = int(kilometraje)


def agregar_mensaje(role: str, content: str) -> None:
    st.session_state.mensajes.append(
        {"role": role, "content": content}
    )


def registrar_ejecucion(resultado: dict) -> None:
    st.session_state.ultima_ejecucion = {
        "ruta": resultado.get("ruta", "Desconocida"),
        "motivo": resultado.get("motivo", ""),
        "tools": resultado.get("tools", []),
        "pasos": resultado.get("pasos", []),
    }


def reiniciar_estado() -> None:
    st.session_state.mensajes = []
    st.session_state.moto = MOTO_INICIAL.copy()
    st.session_state.ultima_ejecucion = _ejecucion_inicial()


# ---------------------------------------------------------------------------
# Grafo, threads y ejecución de turnos
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def obtener_grafo():
    """Compila el grafo una sola vez; así MemorySaver persiste entre reruns."""
    return crear_grafo_mantenimiento()


def inicializar_sesion() -> None:
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())


def nuevo_thread() -> None:
    st.session_state.thread_id = str(uuid.uuid4())


def reiniciar_conversacion() -> None:
    """Limpia la interfaz y abre un hilo nuevo (memoria en blanco)."""
    reiniciar_estado()
    nuevo_thread()


def invocar_grafo(grafo, thread_id: str, mensaje_usuario: str, moto: dict) -> dict:
    """Ejecuta un turno en el hilo indicado y devuelve el resumen para la UI.

    La memoria entre turnos la aporta el checkpointer. Los campos de trazabilidad
    (ruta, motivo, herramientas y pasos) se reinician en cada turno, porque el
    estado persiste entre turnos y de lo contrario se acumularían.
    """
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": RECURSION_LIMIT,
    }

    estado_inicial = {
        "messages": [HumanMessage(content=mensaje_usuario)],
        "moto": dict(moto),
        "ruta": "",
        "motivo": "",
        "herramientas_usadas": [],
        "pasos_ejecutados": [],
    }

    resultado = grafo.invoke(estado_inicial, config=config)

    mensajes = resultado.get("messages", [])
    texto = extraer_texto(mensajes[-1]) if mensajes else ""

    return {
        "respuesta": texto or "No fue posible generar una respuesta.",
        "ruta": resultado.get("ruta", "Desconocida"),
        "motivo": resultado.get("motivo", ""),
        "tools": resultado.get("herramientas_usadas", []),
        "pasos": resultado.get("pasos_ejecutados", []),
    }


def ejecutar_turno(mensaje_usuario: str, moto: dict) -> dict:
    """Ejecuta un turno sobre el hilo de la sesión actual de Streamlit."""
    try:
        return invocar_grafo(
            obtener_grafo(),
            st.session_state.thread_id,
            mensaje_usuario,
            moto,
        )
    except GraphRecursionError:
        # El hilo quedó con una llamada a herramienta sin respuesta: se abre
        # uno nuevo para no arrastrar un historial inconsistente.
        nuevo_thread()
        return {
            "respuesta": (
                "No pude completar la consulta (el agente entró en un ciclo "
                "de herramientas). Reinicié el hilo de conversación; intenta "
                "reformular la pregunta."
            ),
            "ruta": "herramientas",
            "motivo": "Se alcanzó el límite de recursión del grafo.",
            "tools": [],
            "pasos": [],
        }


def diagrama_mermaid() -> str:
    """Diagrama Mermaid exportado de forma nativa por el grafo compilado."""
    return obtener_grafo().get_graph().draw_mermaid()
