"""Interfaz principal del agente MantenIA desarrollado con Streamlit.

Este módulo configura y ejecuta la interfaz web del asistente de
mantenimiento de motocicletas. Gestiona la visualización del estado de la
motocicleta, el historial de conversación y la interacción entre el
usuario y el agente basado en Gemini.

El flujo principal de la aplicación incluye:

- Validación de la configuración requerida.
- Inicialización del estado de sesión.
- Visualización de la información de la motocicleta del usuario.
- Renderizado del historial de conversación.
- Captura de nuevos mensajes del usuario.
- Actualización del estado y la memoria conversacional.
- Generación de respuestas mediante el agente MantenIA.
- Reinicio de la conversación cuando el usuario lo solicita.
"""

import streamlit as st

from config.settings import validar_configuracion
from core.agent import responder
from core.state import (
    agregar_mensaje,
    actualizar_estado_moto,
    inicializar_estado,
    obtener_memoria,
    reiniciar_estado,
)


st.set_page_config(
    page_title="MantenIA",
    page_icon="🏍️",
)


# Valida que las variables necesarias para utilizar Gemini estén configuradas.
try:
    validar_configuracion()
except ValueError as error:
    st.error(str(error))
    st.stop()


# Inicializa el estado persistente de la sesión de Streamlit.
inicializar_estado()


# Encabezado principal de la aplicación.
st.title("MantenIA")
st.caption("Asistente inteligente de mantenimiento de motocicletas")
st.write("MVP con Gemini, contexto, memoria, estado y herramientas.")


# Panel lateral con la información conocida de la motocicleta.
with st.sidebar:
    st.subheader("Estado de la motocicleta")

    moto = st.session_state.moto

    st.write("Marca:", moto["marca"])
    st.write("Modelo:", moto["modelo"])
    st.write("Kilometraje actual:", moto["kilometraje_actual"])

    st.divider()

    if st.button("Reiniciar conversación"):
        reiniciar_estado()
        st.rerun()


# Renderiza el historial de mensajes almacenados en la sesión.
for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])


# Captura una nueva consulta del usuario.
prompt = st.chat_input("Escribe tu consulta sobre mantenimiento...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    actualizar_estado_moto(prompt)
    agregar_mensaje("user", prompt)

    try:
        respuesta = responder(
            mensaje_usuario=prompt,
            moto=st.session_state.moto,
            memoria=obtener_memoria(),
        )
    except Exception as error:
        respuesta = f"Ocurrió un error al consultar Gemini: {error}"

    with st.chat_message("assistant"):
        st.markdown(respuesta)

    agregar_mensaje("assistant", respuesta)

    st.rerun()