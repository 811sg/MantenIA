"""Vista «Asistente»: chat con el agente, progreso en vivo y manejo de errores."""

import streamlit as st

from config.settings import validar_configuracion
from core.errors import clasificar_error
from core.session import (
    TurnoFallido,
    actualizar_estado_moto,
    agregar_mensaje,
    ejecutar_turno,
    registrar_ejecucion,
    registrar_metricas,
)
from ui import components as ui

AVATAR_USUARIO = ":material/person:"
AVATAR_ASISTENTE = ":material/two_wheeler:"

SUGERENCIAS = [
    (":material/build:", "Mantenimiento por kilometraje",
     "Mi Yamaha modelo MT-03 tiene 8500 km, ¿qué mantenimiento necesita?"),
    (":material/notification_important:", "Alertas más urgentes",
     "¿Qué alertas pendientes tengo y cuál debo atender primero?"),
    (":material/description:", "SOAT y tecnomecánica",
     "¿Cuándo vencen el SOAT y la tecnomecánica de mis motos?"),
    (":material/menu_book:", "Teoría básica",
     "¿Para qué sirve lubricar la cadena de la moto?"),
]

_ETIQUETAS_NODO = {
    "enrutador": ":material/alt_route: Clasificando la consulta",
    "nodo_conceptual": ":material/menu_book: Redactando la respuesta",
    "agente_mantenimiento": ":material/psychology: Analizando con el agente",
    "herramientas": ":material/build: Consultando los datos",
}


def _tarjeta_configuracion() -> None:
    ui.tarjeta_error(
        "Falta configurar la API Key de Gemini",
        "El asistente necesita GEMINI_API_KEY para responder. Las demás secciones funcionan sin ella.",
    )
    with st.expander("Cómo configurarla", expanded=True):
        st.markdown(
            "**En local:** edita el archivo `.env` junto a `app.py`:\n"
            "```\nGEMINI_API_KEY=tu_clave\nGEMINI_MODEL=gemini-3.8-flash\n```\n"
            "**En Streamlit Community Cloud:** *App settings → Secrets* y pega:\n"
            "```toml\nGEMINI_API_KEY = \"tu_clave\"\nGEMINI_MODEL = \"gemini-3.8-flash\"\n```"
        )


def _mostrar_mensaje(mensaje: dict) -> None:
    avatar = AVATAR_USUARIO if mensaje["role"] == "user" else AVATAR_ASISTENTE
    with st.chat_message(mensaje["role"], avatar=avatar):
        st.markdown(mensaje["content"])
        if mensaje.get("meta"):
            st.markdown(ui.meta_respuesta(mensaje["meta"]), unsafe_allow_html=True)


def _describir_paso(nodo: str, cambios: dict) -> str:
    etiqueta = _ETIQUETAS_NODO.get(nodo, nodo)

    if nodo == "enrutador" and cambios.get("ruta"):
        tipo = "con datos" if cambios["ruta"] == "herramientas" else "conceptual"
        return f"{etiqueta}: consulta **{tipo}**"

    if nodo == "agente_mantenimiento":
        mensajes = cambios.get("messages") or []
        llamadas = getattr(mensajes[-1], "tool_calls", None) if mensajes else None
        if llamadas:
            nombres = ", ".join(f"`{c['name']}`" for c in llamadas)
            return f"{etiqueta}: usará {nombres}"
        return f"{etiqueta}: redactando la respuesta"

    return etiqueta


def _procesar(prompt: str, reintento: bool = False) -> None:
    """Ejecuta un turno mostrando el progreso; termina con `st.rerun()` si todo sale bien."""
    st.session_state.ultimo_error = None

    if not reintento:
        actualizar_estado_moto(prompt)
        agregar_mensaje("user", prompt)
        with st.chat_message("user", avatar=AVATAR_USUARIO):
            st.markdown(prompt)

    with st.chat_message("assistant", avatar=AVATAR_ASISTENTE):
        with st.status("Procesando tu consulta…", expanded=True) as estado:
            try:
                resultado = ejecutar_turno(
                    prompt,
                    st.session_state.moto,
                    on_paso=lambda nodo, cambios: estado.write(_describir_paso(nodo, cambios)),
                )
            except TurnoFallido as fallo:
                info = clasificar_error(fallo.causa)
                registrar_metricas(fallo.metricas)
                st.session_state.ultimo_error = {**info.to_dict(), "prompt": prompt}
                estado.update(label="No se pudo completar la consulta", state="error", expanded=False)
                st.rerun()

            metricas = resultado["metricas"]
            estado.update(
                label=f"Listo en {metricas['latencia_s']:.1f} s", state="complete", expanded=False
            )

    agregar_mensaje(
        "assistant",
        resultado["respuesta"],
        meta={
            "ruta": resultado["ruta"],
            "tools": resultado["tools"],
            "latencia_s": metricas["latencia_s"],
            "tokens": metricas["tokens_totales"],
        },
    )
    registrar_ejecucion(resultado)
    registrar_metricas(metricas)
    st.rerun()


def _mostrar_error_pendiente() -> None:
    error = st.session_state.ultimo_error
    if not error:
        return

    ui.tarjeta_error(error["titulo"], error["sugerencia"], error["detalle"])

    if error["reintentable"] and st.button("Reintentar", icon=":material/refresh:", type="primary"):
        st.session_state.reintentar = error["prompt"]
        st.rerun()


def render() -> None:
    ui.hero(
        "Asistente de mantenimiento",
        "Escribe tu pregunta abajo. Consulto el historial, las alertas, los documentos y los intervalos técnicos de tus motos.",
    )

    try:
        validar_configuracion()
    except ValueError:
        _tarjeta_configuracion()
        return

    entrada = st.chat_input("Escribe tu pregunta sobre el mantenimiento de tu moto…")
    prompt = entrada or st.session_state.pop("prompt_pendiente", None)
    reintento = None if prompt else st.session_state.pop("reintentar", None)

    for mensaje in st.session_state.mensajes:
        _mostrar_mensaje(mensaje)

    if not prompt and not reintento:
        _mostrar_error_pendiente()

        if not st.session_state.mensajes and not st.session_state.ultimo_error:
            ui.estado_vacio(
                "¿En qué te puedo ayudar?",
                "Escribe en el cuadro de abajo o elige una de estas consultas de ejemplo.",
            )
            columnas = st.columns(2)
            for indice, (icono, titulo, consulta) in enumerate(SUGERENCIAS):
                if columnas[indice % 2].button(titulo, icon=icono, key=f"sugerencia_{indice}", width="stretch"):
                    st.session_state.prompt_pendiente = consulta
                    st.rerun()

    if prompt:
        _procesar(prompt)
    elif reintento:
        _procesar(reintento, reintento=True)
