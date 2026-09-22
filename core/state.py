"""Gestión de estado, memoria y trazabilidad en Streamlit."""

import re

import streamlit as st


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


def inicializar_estado() -> None:
    if "moto" not in st.session_state:
        st.session_state.moto = MOTO_INICIAL.copy()

    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []

    if "ultima_ejecucion" not in st.session_state:
        st.session_state.ultima_ejecucion = {
            "ruta": "Sin ejecución",
            "motivo": "",
            "tools": [],
        }


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

    patron_kilometraje = r"(\d{1,3}(?:[.,]\d{3})*)\s*(?:km|kil[oó]metros)"
    coincidencia_km = re.search(patron_kilometraje, texto_lower)

    if coincidencia_km:
        kilometraje = coincidencia_km.group(1).replace(".", "").replace(",", "")
        st.session_state.moto["kilometraje_actual"] = int(kilometraje)


def agregar_mensaje(role: str, content: str) -> None:
    st.session_state.mensajes.append(
        {"role": role, "content": content}
    )


def obtener_memoria(limite: int = 6) -> str:
    mensajes = st.session_state.mensajes[-limite:]

    return "\n".join(
        f"{mensaje['role']}: {mensaje['content']}"
        for mensaje in mensajes
    )


def registrar_ejecucion(resultado: dict) -> None:
    st.session_state.ultima_ejecucion = {
        "ruta": resultado.get("ruta", "Desconocida"),
        "motivo": resultado.get("motivo", ""),
        "tools": resultado.get("tools", []),
    }


def reiniciar_estado() -> None:
    st.session_state.mensajes = []
    st.session_state.moto = MOTO_INICIAL.copy()
    st.session_state.ultima_ejecucion = {
        "ruta": "Sin ejecución",
        "motivo": "",
        "tools": [],
    }