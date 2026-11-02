"""Pruebas del módulo de observabilidad (callback, agregados y persistencia)."""

import json

from langchain_core.tools import tool

from core.observability import (
    MetricsCallback,
    guardar_turno,
    percentil,
    resumir,
)
from tests.fakes import ModeloGuionado, texto


def test_callback_registra_tokens_y_latencia_del_modelo():
    modelo = ModeloGuionado(respuestas=[texto("hola", entrada=100, salida=20)])
    cb = MetricsCallback(thread_id="t1", pregunta="¿hola?")

    modelo.invoke("hola", config={"callbacks": [cb]})
    metricas = cb.finalizar(ruta="conceptual")

    assert metricas["llamadas_modelo"] == 1
    assert metricas["tokens_entrada"] == 100
    assert metricas["tokens_salida"] == 20
    assert metricas["tokens_totales"] == 120
    assert metricas["latencia_s"] >= 0 and metricas["ok"] is True


def test_callback_registra_ejecucion_y_errores_de_herramientas():
    @tool
    def sumar(a: int, b: int) -> int:
        """Suma dos números."""
        return a + b

    @tool
    def fallar() -> str:
        """Siempre falla."""
        raise RuntimeError("falla simulada")

    cb = MetricsCallback()
    sumar.invoke({"a": 1, "b": 2}, config={"callbacks": [cb]})
    try:
        fallar.invoke({}, config={"callbacks": [cb]})
    except RuntimeError:
        pass

    metricas = cb.finalizar()
    nombres = {h["nombre"]: h["ok"] for h in metricas["herramientas"]}

    assert nombres == {"sumar": True, "fallar": False}
    assert metricas["ok"] is False
    assert any("falla simulada" in e for e in metricas["errores"])


def test_el_registro_no_guarda_el_texto_de_la_pregunta(tmp_path):
    cb = MetricsCallback(pregunta="mi pregunta privada")
    metricas = cb.finalizar(ruta="conceptual")
    destino = tmp_path / "log.jsonl"

    guardar_turno(metricas, ruta=destino)
    guardar_turno(metricas, ruta=destino)

    lineas = destino.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2
    registro = json.loads(lineas[0])
    assert "pregunta" not in registro
    assert registro["pregunta_caracteres"] == len("mi pregunta privada")


def test_guardar_turno_tolera_rutas_no_escribibles(tmp_path):
    archivo = tmp_path / "bloqueo"
    archivo.write_text("x")
    # El "directorio" padre es un archivo: debe registrarse un aviso, no fallar.
    guardar_turno({"pregunta": "x"}, ruta=archivo / "log.jsonl")


def test_percentil_y_resumen():
    assert percentil([], 95) == 0.0
    assert percentil([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 10
    assert percentil([5], 50) == 5

    turnos = [
        {"ruta": "conceptual", "ok": True, "latencia_s": 1.0, "llamadas_modelo": 2,
         "tokens_entrada": 100, "tokens_salida": 20, "tokens_totales": 120,
         "llamadas_herramientas": 0, "herramientas": []},
        {"ruta": "herramientas", "ok": True, "latencia_s": 3.0, "llamadas_modelo": 3,
         "tokens_entrada": 300, "tokens_salida": 50, "tokens_totales": 350,
         "llamadas_herramientas": 1,
         "herramientas": [{"nombre": "consultar_moto", "latencia_s": 0.01, "ok": True}]},
        {"ruta": "error", "ok": False, "latencia_s": 0.5, "llamadas_modelo": 0,
         "tokens_entrada": 0, "tokens_salida": 0, "tokens_totales": 0,
         "llamadas_herramientas": 0, "herramientas": []},
    ]
    r = resumir(turnos)

    assert r["turnos"] == 3 and r["errores"] == 1
    assert r["latencia_media_s"] == 1.5 and r["latencia_max_s"] == 3.0
    assert r["tokens_totales"] == 470 and r["llamadas_modelo"] == 5
    assert r["tools"] == {"consultar_moto": 1}
    assert r["rutas"] == {"conceptual": 1, "herramientas": 1, "error": 1}
    assert r["tasa_exito"] == 66.7
    assert resumir([])["turnos"] == 0
