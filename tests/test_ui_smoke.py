"""Pruebas de humo de la interfaz con `streamlit.testing.AppTest`.

Verifican que cada vista renderiza sin excepciones y que el flujo del chat
(consulta, progreso, métricas, error con reintento, falta de API key) funciona
de extremo a extremo, usando el modelo simulado en lugar de Gemini.
"""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from core import llm_factory
from tests.fakes import ModeloGuionado, decision, llamada_tool, texto

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _vista(nombre: str) -> None:
    """Script mínimo que renderiza una sola vista (AppTest no cambia st.Page)."""
    import importlib

    from core.session import inicializar_estado, inicializar_sesion
    from ui.sidebar import render_sidebar
    from ui.theme import aplicar_tema

    aplicar_tema()
    inicializar_estado()
    inicializar_sesion()
    render_sidebar()
    importlib.import_module(f"ui.views.{nombre}").render()


@pytest.fixture(autouse=True)
def _limpiar_cache():
    st.cache_resource.clear()
    yield
    st.cache_resource.clear()


def instalar(monkeypatch, *respuestas, clase=ModeloGuionado):
    modelo = clase(respuestas=list(respuestas), entradas=[])
    monkeypatch.setattr(llm_factory, "obtener_modelo", lambda temperature: modelo)
    return modelo


def app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=30)


# -- carga de vistas ---------------------------------------------------------------


def test_la_app_carga_con_estado_vacio_y_sugerencias():
    at = app().run()
    assert not at.exception
    assert len(at.chat_input) == 1
    sugerencias = [b for b in at.button if b.key and b.key.startswith("sugerencia_")]
    assert len(sugerencias) == 4


@pytest.mark.parametrize("vista", ["garaje", "observabilidad"])
def test_las_vistas_renderizan_sin_errores(vista):
    at = AppTest.from_function(_vista, args=(vista,), default_timeout=30).run()
    assert not at.exception, [e.value for e in at.exception]


def test_observabilidad_con_metricas_muestra_kpis_y_descargas():
    metricas = [
        {"id": "a1", "timestamp": "2026-10-29T10:00:00+00:00", "thread_id": "t", "pregunta": "x",
         "ruta": "herramientas", "motivo": "", "ok": True, "latencia_s": 2.4, "llamadas_modelo": 3,
         "tokens_entrada": 400, "tokens_salida": 60, "tokens_totales": 460,
         "llamadas_herramientas": 1,
         "herramientas": [{"nombre": "consultar_moto", "latencia_s": 0.01, "ok": True}],
         "nodos": [{"nodo": "enrutador", "latencia_s": 0.8}], "llm": [], "errores": []},
    ]
    at = AppTest.from_function(_vista, args=("observabilidad",), default_timeout=30)
    at.session_state["metricas"] = metricas
    at.run()

    assert not at.exception, [e.value for e in at.exception]
    assert "Latencia media" in " ".join(m.value for m in at.markdown)


# -- flujo del chat ----------------------------------------------------------------------


def test_chat_completo_con_herramientas_registra_traza_y_metricas(monkeypatch):
    instalar(
        monkeypatch,
        decision("herramientas"),
        llamada_tool("consultar_moto", {"consulta": "yamaha"}),
        texto("Tu Yamaha MT-03 está al día."),
    )
    at = app().run()
    at.chat_input[0].set_value("Mi Yamaha modelo MT-03 tiene 8500 km").run()

    assert not at.exception, [e.value for e in at.exception]
    assert [m.name for m in at.chat_message] == ["user", "assistant"]
    assert "Yamaha MT-03" in at.chat_message[1].markdown[0].value

    assert at.session_state["moto"] == {
        "marca": "Yamaha", "modelo": "MT-03", "kilometraje_actual": 8500,
    }
    assert at.session_state["ultima_ejecucion"]["tools"] == ["consultar_moto"]
    assert len(at.session_state["metricas"]) == 1
    assert at.session_state["metricas"][0]["ok"] is True


def test_boton_de_sugerencia_envia_la_consulta(monkeypatch):
    instalar(monkeypatch, decision("conceptual"), texto("Lubricar reduce el desgaste."))
    at = app().run()

    sugerencia = next(b for b in at.button if b.key == "sugerencia_3")
    sugerencia.click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert [m.name for m in at.chat_message] == ["user", "assistant"]
    assert at.session_state["ultima_ejecucion"]["ruta"] == "conceptual"


def test_reiniciar_conversacion_limpia_chat_y_abre_nuevo_hilo(monkeypatch):
    instalar(monkeypatch, decision("conceptual"), texto("Respuesta"))
    at = app().run()
    at.chat_input[0].set_value("¿Qué es el aceite?").run()
    hilo_anterior = at.session_state["thread_id"]
    metricas_previas = len(at.session_state["metricas"])

    next(b for b in at.button if b.label == "Nueva conversación").click().run()

    assert len(at.chat_message) == 0
    assert at.session_state["thread_id"] != hilo_anterior
    assert len(at.session_state["metricas"]) == metricas_previas  # las métricas se conservan


def test_error_de_cuota_muestra_tarjeta_y_permite_reintentar(monkeypatch):
    class ModeloRoto(ModeloGuionado):
        def _generate(self, *a, **k):
            raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")

    instalar(monkeypatch, texto("x"), clase=ModeloRoto)
    at = app().run()
    at.chat_input[0].set_value("¿Qué es el aceite?").run()

    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["ultimo_error"]["tipo"] == "cuota"
    assert any(b.label == "Reintentar" for b in at.button)
    assert at.session_state["metricas"][0]["ok"] is False

    # Se recupera el servicio y el reintento responde sin duplicar el mensaje del usuario.
    instalar(monkeypatch, decision("conceptual"), texto("El aceite lubrica el motor."))
    next(b for b in at.button if b.label == "Reintentar").click().run()

    assert not at.exception, [e.value for e in at.exception]
    assert [m.name for m in at.chat_message] == ["user", "assistant"]
    assert at.session_state["ultimo_error"] is None


def test_sin_api_key_muestra_ayuda_y_no_ofrece_chat(monkeypatch):
    import config.settings as settings

    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    at = app().run()

    assert not at.exception
    assert len(at.chat_input) == 0
    assert any("Falta configurar la API Key" in m.value for m in at.markdown)
