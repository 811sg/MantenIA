"""Interfaz Streamlit del Asistente MantenIA v3 con LangGraph."""

import streamlit as st

from config.settings import validar_configuracion
from core.session import (
    actualizar_estado_moto,
    agregar_mensaje,
    diagrama_mermaid,
    ejecutar_turno,
    inicializar_estado,
    inicializar_sesion,
    registrar_ejecucion,
    reiniciar_conversacion,
)

st.set_page_config(
    page_title="MantenIA v3",
    page_icon="🏍️",
)

try:
    validar_configuracion()
except ValueError as error:
    st.error(str(error))
    st.stop()

inicializar_estado()
inicializar_sesion()

st.title("MantenIA v3")
st.caption("Asistente inteligente de mantenimiento de motocicletas")
st.write(
    "Versión con LangGraph: grafo de estados cíclico, nodos especializados, "
    "ToolNode y memoria con checkpointer."
)

with st.sidebar:
    st.subheader("Estado de la motocicleta")

    moto = st.session_state.moto
    st.write("Marca:", moto["marca"])
    st.write("Modelo:", moto["modelo"])
    st.write("Kilometraje actual:", moto["kilometraje_actual"])

    st.divider()
    st.subheader("Hilo de conversación")
    st.caption("Thread ID activo (clave del checkpoint de memoria)")
    st.code(st.session_state.thread_id, language=None)

    st.divider()
    st.subheader("Última ejecución")

    ejecucion = st.session_state.ultima_ejecucion
    st.write("Ruta:", ejecucion["ruta"])

    if ejecucion["motivo"]:
        st.caption(ejecucion["motivo"])

    if ejecucion["pasos"]:
        st.write("Nodos recorridos:")
        st.code(
            " ➔ ".join(["START", *ejecucion["pasos"], "END"]),
            language=None,
        )

    if ejecucion["tools"]:
        st.write("Tools utilizadas:")
        for nombre in ejecucion["tools"]:
            st.write(f"- {nombre}")
    else:
        st.write("Tools utilizadas: ninguna")

    st.divider()

    with st.expander("Arquitectura del grafo"):
        try:
            diagrama = diagrama_mermaid()
            if hasattr(st, "mermaid_chart"):
                st.mermaid_chart(diagrama)
            else:
                st.code(diagrama, language="text")
        except Exception as error:
            st.caption(f"No se pudo generar el diagrama: {error}")

    if st.button("Reiniciar conversación"):
        reiniciar_conversacion()
        st.rerun()

for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

prompt = st.chat_input("Escribe tu consulta sobre mantenimiento...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    actualizar_estado_moto(prompt)
    agregar_mensaje("user", prompt)

    try:
        resultado = ejecutar_turno(
            mensaje_usuario=prompt,
            moto=st.session_state.moto,
        )
        respuesta = resultado["respuesta"]
        registrar_ejecucion(resultado)

    except Exception as error:
        respuesta = f"Ocurrió un error al procesar la solicitud: {error}"

    with st.chat_message("assistant"):
        st.markdown(respuesta)

    agregar_mensaje("assistant", respuesta)
    st.rerun()
