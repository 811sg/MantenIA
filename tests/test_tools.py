"""Pruebas funcionales de las 7 Tools y de las fuentes de datos (recuperación)."""

import re

import pytest

from core import repositorio
from tools import TOOLS_MANTENIMIENTO
from tools.alertas_tool import consultar_alertas, priorizar_alertas
from tools.documentos_tool import consultar_documentos_vehiculo
from tools.fecha_tool import obtener_fecha
from tools.moto_tool import (
    consultar_historial,
    consultar_moto,
    consultar_recomendaciones,
)


def cantidad(herramienta, **argumentos) -> int:
    return herramienta.invoke(argumentos)["cantidad"]


# -- catálogo -----------------------------------------------------------------


def test_catalogo_tiene_las_7_tools():
    nombres = {t.name for t in TOOLS_MANTENIMIENTO}
    assert nombres == {
        "obtener_fecha", "consultar_moto", "consultar_historial",
        "consultar_recomendaciones", "consultar_documentos_vehiculo",
        "consultar_alertas", "priorizar_alertas",
    }


def test_todas_las_tools_tienen_descripcion_para_el_modelo():
    assert all(t.description.strip() for t in TOOLS_MANTENIMIENTO)


# -- obtener_fecha --------------------------------------------------------------


def test_obtener_fecha_formato():
    resultado = obtener_fecha.invoke({})
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", resultado["fecha"])
    assert re.fullmatch(r"\d{2}:\d{2}", resultado["hora"])
    assert resultado["dia"] in {
        "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"
    }


# -- consultar_moto ---------------------------------------------------------------


@pytest.mark.parametrize(
    "consulta, esperado",
    [("moto_001", 1), ("yamaha", 1), ("MT-03", 1), ("ninja", 1), ("inexistente", 0)],
)
def test_consultar_moto_por_id_marca_o_modelo(consulta, esperado):
    assert cantidad(consultar_moto, consulta=consulta) == esperado


def test_hallazgo_h1_consulta_moto_con_varios_terminos():
    """H1: 'Yamaha MT-03' devolvía 0 resultados antes de la corrección."""
    resultado = consultar_moto.invoke({"consulta": "Yamaha MT-03"})
    assert resultado["cantidad"] == 1
    assert resultado["resultados"][0]["id"] == "moto_001"


# -- consultar_historial -------------------------------------------------------------


def test_consultar_historial_devuelve_solo_la_moto_pedida():
    resultado = consultar_historial.invoke({"moto_id": "moto_001"})
    assert resultado["cantidad"] >= 1
    assert all(m["moto_id"] == "moto_001" for m in resultado["resultados"])


def test_consultar_historial_id_inexistente():
    assert cantidad(consultar_historial, moto_id="moto_999") == 0


# -- consultar_recomendaciones -----------------------------------------------------------


def test_recomendaciones_sin_filtro_devuelve_todas():
    assert cantidad(consultar_recomendaciones, tipo="") == len(
        repositorio.cargar_recomendaciones()
    )


@pytest.mark.parametrize("tipo", ["aceite", "cambio de aceite", "cambio_aceite"])
def test_recomendaciones_por_tipo(tipo):
    resultado = consultar_recomendaciones.invoke({"tipo": tipo})
    assert resultado["cantidad"] == 1
    assert resultado["resultados"][0]["intervalo_km"] == 3000


# -- consultar_alertas -----------------------------------------------------------------


def test_alertas_pendientes_por_defecto():
    resultado = consultar_alertas.invoke({})
    assert resultado["cantidad"] == 4
    assert all(a["estado"] == "pendiente" for a in resultado["resultados"])


@pytest.mark.parametrize("consulta", ["todas", "todo", "*"])
def test_alertas_todas(consulta):
    assert cantidad(consultar_alertas, consulta=consulta) == len(
        repositorio.cargar_alertas()
    )


def test_hallazgo_h1_alertas_con_varios_terminos():
    """H1: 'moto_001 frenos' devolvía 0 resultados antes de la corrección."""
    resultado = consultar_alertas.invoke({"consulta": "moto_001 frenos"})
    assert resultado["cantidad"] == 1
    assert resultado["resultados"][0]["moto_id"] == "moto_001"


def test_hallazgo_h2_alertas_sin_tildes():
    """H2: 'revision' no encontraba 'Revisión de frenos...'."""
    assert cantidad(consultar_alertas, consulta="revision") == 1


def test_alertas_por_prioridad():
    assert cantidad(consultar_alertas, consulta="alta") == 2


# -- consultar_documentos_vehiculo --------------------------------------------------------


def test_documentos_por_tipo():
    assert cantidad(consultar_documentos_vehiculo, consulta="SOAT") == 3


def test_hallazgo_h1_documentos_con_varios_terminos():
    """H1: 'SOAT moto_001' devolvía 0 resultados antes de la corrección."""
    resultado = consultar_documentos_vehiculo.invoke({"consulta": "SOAT moto_001"})
    assert resultado["cantidad"] == 1
    assert resultado["resultados"][0]["documento"] == "SOAT"


@pytest.mark.parametrize(
    "consulta", ["tecnomecánica", "tecnomecanica", "técnico-mecánica", "RTM"]
)
def test_hallazgo_h2_tecnomecanica_con_sinonimos_y_tildes(consulta):
    """H2: 'tecnomecánica' no coincidía con 'Revisión Técnico-Mecánica'."""
    assert cantidad(consultar_documentos_vehiculo, consulta=consulta) == 2


# -- priorizar_alertas (Chain determinista) --------------------------------------------------


def test_priorizar_alertas_envia_solo_pendientes_a_la_chain(monkeypatch):
    from langchain_core.runnables import RunnableLambda

    from core import llm_factory
    from tests.fakes import ModeloGuionado, texto

    modelo = ModeloGuionado(respuestas=[texto("1. Frenos (alta)")])
    monkeypatch.setattr(llm_factory, "obtener_modelo", lambda temperature: modelo)

    respuesta = priorizar_alertas.invoke({"contexto": "uso diario"})

    assert respuesta == "1. Frenos (alta)"
    prompt_humano = modelo.entradas[0][-1].content
    assert "moto_001" in prompt_humano and "uso diario" in prompt_humano


# -- integridad referencial de las fuentes JSON --------------------------------------------------


def test_datos_referencian_motos_existentes():
    ids = {m["id"] for m in repositorio.cargar_motos()}
    for fuente in (
        repositorio.cargar_historial(),
        repositorio.cargar_alertas(),
        repositorio.cargar_documentos(),
    ):
        assert {r["moto_id"] for r in fuente} <= ids
