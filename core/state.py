"""Gestión del estado de sesión y memoria del usuario en Streamlit.

Este módulo administra la información básica de la motocicleta del
usuario y el historial de mensajes almacenados en ``st.session_state``.

También incluye utilidades para identificar datos de la motocicleta a
partir de texto libre, construir una memoria reciente de la conversación
y reiniciar el estado de la sesión.
"""

import re

import streamlit as st


# Estado inicial utilizado cuando aún no se ha identificado la motocicleta.
MOTO_INICIAL = {
    "marca": "No registrada",
    "modelo": "No registrado",
    "kilometraje_actual": "No registrado",
}


# Marcas reconocidas para identificar la motocicleta mencionada por el
# usuario dentro de un mensaje en texto libre.
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


def inicializar_estado() -> None:
    """Inicializa las variables necesarias en el estado de sesión.

    Crea la información inicial de la motocicleta y el historial de
    mensajes únicamente cuando dichas variables aún no existen en
    ``st.session_state``.

    Esto permite conservar la información entre las distintas ejecuciones
    de la aplicación Streamlit dentro de una misma sesión.
    """
    if "moto" not in st.session_state:
        st.session_state.moto = MOTO_INICIAL.copy()

    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []


def actualizar_estado_moto(texto: str) -> None:
    """Actualiza los datos de la motocicleta identificados en un texto.

    Analiza el contenido recibido para detectar la marca de la
    motocicleta y su kilometraje actual. Los valores encontrados se
    almacenan directamente en ``st.session_state.moto``.

    La búsqueda de la marca no distingue entre mayúsculas y minúsculas.

    Args:
        texto: Mensaje escrito por el usuario del cual se intentará
            extraer información de su motocicleta.
    """
    texto_lower = texto.lower()

    for marca in MARCAS:
        if marca in texto_lower:
            st.session_state.moto["marca"] = marca.capitalize()
            break

    patron_modelo = r"(?:modelo)\s+([A-Za-zÁÉÍÓÚáéíóúÑñ0-9\-]+)"
    coincidencia_modelo = re.search(patron_modelo, texto, re.IGNORECASE)

    if coincidencia_modelo:
        st.session_state.moto["modelo"] = coincidencia_modelo.group(1).upper()

    patron_kilometraje = r"(\d{1,3}(?:[.,]\d{3})*)\s*(?:km|kil[oó]metros)"
    coincidencia_km = re.search(patron_kilometraje, texto_lower)

    if coincidencia_km:
        kilometraje = coincidencia_km.group(1).replace(".", "").replace(",", "")
        st.session_state.moto["kilometraje_actual"] = int(kilometraje)


def agregar_mensaje(role: str, content: str) -> None:
    """Agrega un mensaje al historial de conversación de la sesión.

    Args:
        role: Rol asociado al mensaje, por ejemplo ``"user"`` o
            ``"assistant"``.
        content: Contenido textual del mensaje que se desea almacenar.
    """
    st.session_state.mensajes.append(
        {
            "role": role,
            "content": content,
        }
    )


def obtener_memoria(limite: int = 6) -> str:
    """Construye una representación textual de los mensajes recientes.

    Recupera los últimos mensajes almacenados en la sesión y los convierte
    en una cadena de texto que puede utilizarse como contexto o memoria
    conversacional.

    Args:
        limite: Número máximo de mensajes recientes que se incluirán.
            Por defecto se utilizan los últimos 6 mensajes.

    Returns:
        Cadena con los mensajes recientes en formato ``"role: content"``,
        separados por saltos de línea. Devuelve una cadena vacía si no
        existen mensajes almacenados.
    """
    mensajes = st.session_state.mensajes[-limite:]

    return "\n".join(
        f"{mensaje['role']}: {mensaje['content']}"
        for mensaje in mensajes
    )


def reiniciar_estado() -> None:
    """Restablece la información de la sesión a sus valores iniciales.

    Elimina el historial de conversación y reemplaza la información de la
    motocicleta por una nueva copia de ``MOTO_INICIAL``.
    """
    st.session_state.mensajes = []
    st.session_state.moto = MOTO_INICIAL.copy()