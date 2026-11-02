"""Barra lateral: estado de la moto, hilo de memoria, traza y acciones."""

from datetime import datetime
from html import escape

import streamlit as st

from config.settings import APP_NAME, APP_VERSION, GEMINI_MODEL
from core.session import reiniciar_conversacion
from ui import components as ui


def formatear_km(valor) -> str:
    if isinstance(valor, int):
        return f"{valor:,}".replace(",", ".") + " km"
    return str(valor)


def conversacion_a_markdown(mensajes: list[dict]) -> str:
    """Exporta el historial de la conversación como texto Markdown."""
    lineas = [f"# Conversación con {APP_NAME}", f"_Exportada el {datetime.now():%Y-%m-%d %H:%M}_", ""]
    for mensaje in mensajes:
        autor = "Tú" if mensaje["role"] == "user" else APP_NAME
        lineas += [f"**{autor}:**", "", mensaje["content"], ""]
    return "\n".join(lineas)


def _tarjeta_moto() -> None:
    moto = st.session_state.moto
    filas = [
        ("Marca", moto["marca"]),
        ("Modelo", moto["modelo"]),
        ("Kilometraje", formatear_km(moto["kilometraje_actual"])),
    ]
    html = "".join(
        f'<div class="mi-moto-row"><span>{etiqueta}</span><b>{escape(str(valor))}</b></div>'
        for etiqueta, valor in filas
    )
    st.markdown(f'<div class="mi-card" style="padding:.6rem .9rem">{html}</div>', unsafe_allow_html=True)


def _traza_ultima_ejecucion() -> None:
    ejecucion = st.session_state.ultima_ejecucion
    ruta = ejecucion["ruta"]

    if not ejecucion["pasos"]:
        st.caption("Todavía no hay consultas. Escribe en el chat para ver aquí cómo respondió el agente.")
        return

    etiqueta = {"conceptual": "Consulta conceptual", "herramientas": "Consulta con datos"}.get(ruta, ruta)
    st.markdown(ui.badge(etiqueta, ui.tono_ruta(ruta)), unsafe_allow_html=True)
    if ejecucion["motivo"]:
        st.caption(ejecucion["motivo"])

    st.markdown(ui.flujo_nodos(ejecucion["pasos"]), unsafe_allow_html=True)

    if ejecucion["tools"]:
        st.markdown("".join(ui.badge(n) for n in ejecucion["tools"]), unsafe_allow_html=True)
    else:
        st.caption("Sin herramientas")


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            f'<div class="mi-brand"><div class="mi-brand-logo">M</div>'
            f"<div><b>{APP_NAME}</b><span>Asistente de mantenimiento · v{APP_VERSION}</span></div></div>",
            unsafe_allow_html=True,
        )

        ui.seccion("Tu motocicleta")
        _tarjeta_moto()
        st.caption("Se completa sola con lo que escribes en el chat.")

        ui.seccion("Última consulta")
        _traza_ultima_ejecucion()

        ui.seccion("Conversación")
        hay_mensajes = bool(st.session_state.mensajes)

        if st.button("Nueva conversación", icon=":material/add_comment:", width="stretch",
                     help="Borra el chat y empieza con la memoria en blanco"):
            reiniciar_conversacion()
            st.rerun()

        st.download_button(
            "Descargar conversación",
            data=conversacion_a_markdown(st.session_state.mensajes),
            file_name="conversacion_mantenia.md",
            mime="text/markdown",
            icon=":material/download:",
            disabled=not hay_mensajes,
            width="stretch",
            help="Guarda el chat como archivo de texto",
        )

        with st.expander("Detalles técnicos"):
            st.caption("Modelo")
            st.code(GEMINI_MODEL, language=None)
            st.caption("Hilo de memoria (thread ID)")
            st.code(st.session_state.thread_id, language=None)
