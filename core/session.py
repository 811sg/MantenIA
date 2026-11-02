"""Sesión de Streamlit, estado de la interfaz y threads de LangGraph.

Integra Streamlit con los checkpoints de LangGraph: crea un `thread_id` por
sesión de usuario, ejecuta cada turno del grafo (en modo *streaming* para
poder informar el progreso) y traduce el resultado al formato que consume la
interfaz. También guarda el estado visible de la UI (moto detectada, mensajes,
traza de la última ejecución y métricas de la sesión).

La memoria conversacional NO se arma como texto: la gestiona el checkpointer
de LangGraph (MemorySaver) a través del `thread_id`.
"""

import uuid
from typing import Callable

import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

from core.moto_parser import extraer_datos_moto
from core.observability import MetricsCallback, guardar_turno
from graph.nodes import extraer_texto
from graph.workflow import crear_grafo_mantenimiento

# Tope de pasos por turno: evita ciclos infinitos agente <-> herramientas.
RECURSION_LIMIT = 12

MOTO_INICIAL = {
    "marca": "No registrada",
    "modelo": "No registrado",
    "kilometraje_actual": "No registrado",
}


class TurnoFallido(Exception):
    """Un turno del grafo falló; conserva la causa y las métricas parciales."""

    def __init__(self, causa: BaseException, metricas: dict) -> None:
        super().__init__(str(causa))
        self.causa = causa
        self.metricas = metricas


# ---------------------------------------------------------------------------
# Estado de la interfaz (moto detectada, mensajes, trazabilidad y métricas)
# ---------------------------------------------------------------------------


def _ejecucion_inicial() -> dict:
    return {"ruta": "Sin ejecución", "motivo": "", "tools": [], "pasos": []}


def inicializar_estado() -> None:
    if "moto" not in st.session_state:
        st.session_state.moto = MOTO_INICIAL.copy()

    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []

    if "ultima_ejecucion" not in st.session_state:
        st.session_state.ultima_ejecucion = _ejecucion_inicial()

    if "metricas" not in st.session_state:
        st.session_state.metricas = []

    if "ultimo_error" not in st.session_state:
        st.session_state.ultimo_error = None

    if "prompt_pendiente" not in st.session_state:
        st.session_state.prompt_pendiente = None


def actualizar_estado_moto(texto: str) -> None:
    """Actualiza marca, modelo y kilometraje con lo que mencione el usuario."""
    st.session_state.moto.update(extraer_datos_moto(texto))


def agregar_mensaje(role: str, content: str, meta: dict | None = None) -> None:
    mensaje = {"role": role, "content": content}
    if meta:
        mensaje["meta"] = meta
    st.session_state.mensajes.append(mensaje)


def registrar_ejecucion(resultado: dict) -> None:
    st.session_state.ultima_ejecucion = {
        "ruta": resultado.get("ruta", "Desconocida"),
        "motivo": resultado.get("motivo", ""),
        "tools": resultado.get("tools", []),
        "pasos": resultado.get("pasos", []),
    }


def registrar_metricas(metricas: dict) -> None:
    """Guarda las métricas del turno en la sesión y en el registro JSONL."""
    st.session_state.metricas.append(metricas)
    guardar_turno(metricas)


def reiniciar_estado() -> None:
    st.session_state.mensajes = []
    st.session_state.moto = MOTO_INICIAL.copy()
    st.session_state.ultima_ejecucion = _ejecucion_inicial()
    st.session_state.ultimo_error = None
    st.session_state.prompt_pendiente = None


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
    """Limpia la interfaz y abre un hilo nuevo (memoria en blanco).

    Las métricas de la sesión se conservan: son observabilidad, no conversación.
    """
    reiniciar_estado()
    nuevo_thread()


def invocar_grafo(
    grafo,
    thread_id: str,
    mensaje_usuario: str,
    moto: dict,
    on_paso: Callable[[str, dict], None] | None = None,
) -> dict:
    """Ejecuta un turno en el hilo indicado y devuelve el resumen para la UI.

    La memoria entre turnos la aporta el checkpointer. Los campos de trazabilidad
    (ruta, motivo, herramientas y pasos) se reinician en cada turno, porque el
    estado persiste entre turnos y de lo contrario se acumularían.

    `on_paso(nodo, cambios)` se invoca al terminar cada nodo, lo que permite a
    la interfaz mostrar el progreso en tiempo real. Si el turno falla se lanza
    `TurnoFallido` con la causa y las métricas parciales.
    """
    observador = MetricsCallback(thread_id=thread_id, pregunta=mensaje_usuario)
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": RECURSION_LIMIT,
        "callbacks": [observador],
    }

    estado_inicial = {
        "messages": [HumanMessage(content=mensaje_usuario)],
        "moto": dict(moto),
        "ruta": "",
        "motivo": "",
        "herramientas_usadas": [],
        "pasos_ejecutados": [],
    }

    try:
        for actualizacion in grafo.stream(
            estado_inicial, config=config, stream_mode="updates"
        ):
            if on_paso:
                for nodo, cambios in actualizacion.items():
                    on_paso(nodo, cambios or {})

        resultado = grafo.get_state(config).values
    except Exception as error:
        observador.registrar_error(error)
        raise TurnoFallido(
            error, observador.finalizar(ruta="error", ok=False)
        ) from error

    mensajes = resultado.get("messages", [])
    texto = extraer_texto(mensajes[-1]) if mensajes else ""
    ruta = resultado.get("ruta", "Desconocida")
    motivo = resultado.get("motivo", "")

    return {
        "respuesta": texto or "No fue posible generar una respuesta.",
        "ruta": ruta,
        "motivo": motivo,
        "tools": resultado.get("herramientas_usadas", []),
        "pasos": resultado.get("pasos_ejecutados", []),
        "metricas": observador.finalizar(ruta=ruta, motivo=motivo, ok=bool(texto)),
    }


def ejecutar_turno(
    mensaje_usuario: str,
    moto: dict,
    on_paso: Callable[[str, dict], None] | None = None,
) -> dict:
    """Ejecuta un turno sobre el hilo de la sesión actual de Streamlit."""
    try:
        return invocar_grafo(
            obtener_grafo(),
            st.session_state.thread_id,
            mensaje_usuario,
            moto,
            on_paso=on_paso,
        )
    except TurnoFallido as fallo:
        if not isinstance(fallo.causa, GraphRecursionError):
            raise

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
            "metricas": fallo.metricas,
        }

