"""Punto de entrada de MantenIA (Streamlit).

Solo configura la página, aplica el tema, inicializa el estado y enruta entre
las vistas de `ui/views/`. La lógica del agente vive en `graph/` y `core/`.
"""

import streamlit as st

from config.settings import APP_NAME
from core.observability import configurar_logging
from core.session import inicializar_estado, inicializar_sesion
from ui.sidebar import render_sidebar
from ui.theme import aplicar_tema
from ui.views import chat, garaje, observabilidad

st.set_page_config(
    page_title=f"{APP_NAME} · Asistente de mantenimiento",
    page_icon=":material/two_wheeler:",
    layout="wide",
    initial_sidebar_state="auto",
)

configurar_logging()
aplicar_tema()
inicializar_estado()
inicializar_sesion()

pagina = st.navigation(
    [
        st.Page(chat.render, title="Asistente", icon=":material/chat:", url_path="asistente", default=True),
        st.Page(garaje.render, title="Garaje", icon=":material/two_wheeler:", url_path="garaje"),
        st.Page(observabilidad.render, title="Observabilidad", icon=":material/monitoring:", url_path="observabilidad"),
    ],
    position="top",
)

render_sidebar()
pagina.run()
