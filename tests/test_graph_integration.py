"""Pruebas de integración de LangGraph, memoria, estado y Tools (modelo simulado).

Ejercitan el grafo REAL (`crear_grafo_mantenimiento`) y el flujo de sesión
(`invocar_grafo`); solo se sustituye el cliente de Gemini por `ModeloGuionado`.
"""

import pytest
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from core import llm_factory
from core.session import TurnoFallido, invocar_grafo
from graph.workflow import crear_grafo_mantenimiento
from tests.fakes import ModeloGuionado, decision, llamada_tool, texto

MOTO = {"marca": "Yamaha", "modelo": "MT-03", "kilometraje_actual": 8500}


@pytest.fixture
def usar_modelo(monkeypatch):
    """Instala un `ModeloGuionado` como único cliente LLM del grafo."""

    def _instalar(*respuestas):
        modelo = ModeloGuionado(respuestas=list(respuestas), entradas=[])
        monkeypatch.setattr(llm_factory, "obtener_modelo", lambda temperature: modelo)
        return modelo

    return _instalar


def turno(grafo, mensaje, thread="hilo-1", moto=None, **kw):
    return invocar_grafo(grafo, thread, mensaje, moto or MOTO, **kw)


# -- topología --------------------------------------------------------------------


def test_el_grafo_compila_con_los_4_nodos_y_el_bucle():
    grafo = crear_grafo_mantenimiento()
    nodos = set(grafo.get_graph().nodes)
    assert {"enrutador", "nodo_conceptual", "agente_mantenimiento", "herramientas"} <= nodos

    aristas = {(a.source, a.target) for a in grafo.get_graph().edges}
    assert ("herramientas", "agente_mantenimiento") in aristas  # ciclo ReAct
    assert "graph" in grafo.get_graph().draw_mermaid()


# -- rutas -----------------------------------------------------------------------------


def test_ruta_conceptual_no_usa_herramientas(usar_modelo):
    usar_modelo(decision("conceptual"), texto("La tecnomecánica es una revisión anual."))

    r = turno(crear_grafo_mantenimiento(), "¿Qué es la tecnomecánica?")

    assert r["ruta"] == "conceptual"
    assert r["pasos"] == ["enrutador", "nodo_conceptual"]
    assert r["tools"] == []
    assert "tecnomecánica" in r["respuesta"]
    assert r["metricas"]["llamadas_herramientas"] == 0
    assert r["metricas"]["llamadas_modelo"] == 2  # enrutador + respuesta


def test_ruta_herramientas_ejecuta_el_ciclo_agente_tools_agente(usar_modelo):
    modelo = usar_modelo(
        decision("herramientas"),
        llamada_tool("consultar_moto", {"consulta": "yamaha"}),
        texto("Tu Yamaha MT-03 tiene 8.500 km."),
    )

    r = turno(crear_grafo_mantenimiento(), "¿Qué moto tengo?")

    assert r["ruta"] == "herramientas"
    assert r["pasos"] == [
        "enrutador", "agente_mantenimiento", "herramientas", "agente_mantenimiento"
    ]
    assert r["tools"] == ["consultar_moto"]
    assert r["respuesta"] == "Tu Yamaha MT-03 tiene 8.500 km."

    # El ToolNode devolvió datos reales al agente (segunda llamada del agente).
    mensajes_agente = modelo.entradas[-1]
    resultados = [m for m in mensajes_agente if isinstance(m, ToolMessage)]
    assert resultados and "moto_001" in resultados[0].content


def test_varias_herramientas_en_un_mismo_turno(usar_modelo):
    usar_modelo(
        decision("herramientas"),
        llamada_tool("obtener_fecha"),
        llamada_tool("consultar_alertas", {"consulta": "pendientes"}),
        texto("Tienes 4 alertas pendientes."),
    )

    r = turno(crear_grafo_mantenimiento(), "¿Qué alertas tengo hoy?")

    assert r["tools"] == ["obtener_fecha", "consultar_alertas"]
    assert r["metricas"]["llamadas_herramientas"] == 2
    nombres = [h["nombre"] for h in r["metricas"]["herramientas"]]
    assert nombres == ["obtener_fecha", "consultar_alertas"]


def test_herramienta_con_error_no_rompe_el_turno(usar_modelo):
    """Una tool llamada con argumentos inválidos devuelve un ToolMessage de error."""
    modelo = usar_modelo(
        decision("herramientas"),
        llamada_tool("consultar_moto", {"argumento_inexistente": 1}),
        texto("No pude consultar la moto; ¿puedes darme más datos?"),
    )

    r = turno(crear_grafo_mantenimiento(), "¿Qué moto tengo?")

    assert r["respuesta"].startswith("No pude consultar")
    mensajes = [m for m in modelo.entradas[-1] if isinstance(m, ToolMessage)]
    assert mensajes and mensajes[0].status == "error"


# -- estado y memoria ----------------------------------------------------------------------


def test_el_estado_de_la_moto_llega_al_prompt_del_agente(usar_modelo):
    modelo = usar_modelo(decision("herramientas"), texto("ok"))

    turno(crear_grafo_mantenimiento(), "¿Qué mantenimiento necesito?")

    sistema = modelo.entradas[-1][0].content
    assert "Yamaha" in sistema and "MT-03" in sistema and "8500" in sistema


def test_memoria_el_segundo_turno_recuerda_el_primero(usar_modelo):
    modelo = usar_modelo(
        decision("conceptual"), texto("La cadena transmite la fuerza."),
        decision("conceptual"), texto("Se lubrica cada 500 km."),
    )
    grafo = crear_grafo_mantenimiento()

    turno(grafo, "¿Para qué sirve la cadena?", thread="A")
    turno(grafo, "¿y cada cuánto se lubrica?", thread="A")

    previos = [
        m.content for m in modelo.entradas[-1] if isinstance(m, HumanMessage)
    ]
    assert "¿Para qué sirve la cadena?" in previos  # memoria vía checkpointer


def test_memoria_aislada_por_thread_id(usar_modelo):
    modelo = usar_modelo(
        decision("conceptual"), texto("Respuesta A"),
        decision("conceptual"), texto("Respuesta B"),
    )
    grafo = crear_grafo_mantenimiento()

    turno(grafo, "pregunta del hilo A", thread="A")
    turno(grafo, "pregunta del hilo B", thread="B")

    humanos = [m.content for m in modelo.entradas[-1] if isinstance(m, HumanMessage)]
    assert "pregunta del hilo A" not in humanos


def test_la_traza_se_reinicia_en_cada_turno(usar_modelo):
    usar_modelo(
        decision("herramientas"), llamada_tool("obtener_fecha"), texto("Hoy es hoy."),
        decision("conceptual"), texto("Teoría."),
    )
    grafo = crear_grafo_mantenimiento()

    turno(grafo, "¿Qué fecha es?", thread="T")
    r2 = turno(grafo, "¿Qué es el aceite?", thread="T")

    assert r2["pasos"] == ["enrutador", "nodo_conceptual"]
    assert r2["tools"] == []


# -- observabilidad integrada ----------------------------------------------------------------


def test_metricas_de_un_turno_con_herramientas(usar_modelo):
    usar_modelo(
        decision("herramientas"),          # 60 tokens
        llamada_tool("consultar_moto", {"consulta": "yamaha"}),  # 135
        texto("Listo", entrada=200, salida=10),                  # 210
    )

    m = turno(crear_grafo_mantenimiento(), "¿Qué moto tengo?")["metricas"]

    assert m["llamadas_modelo"] == 3
    assert m["tokens_totales"] == 60 + 135 + 210
    assert m["tokens_entrada"] == 50 + 120 + 200
    assert m["llamadas_herramientas"] == 1
    assert [n["nodo"] for n in m["nodos"]] == [
        "enrutador", "agente_mantenimiento", "herramientas", "agente_mantenimiento"
    ]
    assert {c["origen"] for c in m["llm"]} == {"enrutador", "agente_mantenimiento"}
    assert m["ok"] is True and m["ruta"] == "herramientas"


def test_on_paso_notifica_cada_nodo_en_orden(usar_modelo):
    usar_modelo(decision("conceptual"), texto("Respuesta"))
    visitados = []

    turno(
        crear_grafo_mantenimiento(),
        "¿Qué es el aceite?",
        on_paso=lambda nodo, cambios: visitados.append(nodo),
    )

    assert visitados == ["enrutador", "nodo_conceptual"]


# -- fallas -------------------------------------------------------------------------------------


def test_ciclo_infinito_se_corta_con_el_limite_de_recursion(usar_modelo):
    usar_modelo(decision("herramientas"), llamada_tool("obtener_fecha"))  # repite la última

    with pytest.raises(TurnoFallido) as fallo:
        turno(crear_grafo_mantenimiento(), "pregunta que cicla")

    assert isinstance(fallo.value.causa, GraphRecursionError)
    assert fallo.value.metricas["ok"] is False
    assert fallo.value.metricas["errores"]


def test_error_del_modelo_devuelve_turno_fallido_con_metricas(monkeypatch):
    class ModeloRoto(ModeloGuionado):
        def _generate(self, *a, **k):
            raise RuntimeError("429 RESOURCE_EXHAUSTED")

    modelo = ModeloRoto(respuestas=[texto("x")])
    monkeypatch.setattr(llm_factory, "obtener_modelo", lambda temperature: modelo)

    with pytest.raises(TurnoFallido) as fallo:
        turno(crear_grafo_mantenimiento(), "hola")

    assert "RESOURCE_EXHAUSTED" in str(fallo.value.causa)
    assert fallo.value.metricas["ruta"] == "error" and not fallo.value.metricas["ok"]


def test_fabrica_de_modelos_acepta_la_configuracion_de_gemini():
    """El cliente real se construye (sin llamar a la API) con timeout y reintentos."""
    llm_factory.obtener_modelo.cache_clear()
    modelo = llm_factory.obtener_modelo(0.1)
    assert modelo.max_retries == 2 and modelo.timeout == 60
