"""Observabilidad: métricas por turno, trazas del grafo y registro persistente.

`MetricsCallback` es un *callback handler* de LangChain que se pasa en la
configuración de cada ejecución del grafo. Sin tocar los nodos, registra:

- llamadas al modelo (latencia, tokens de entrada/salida, nodo de origen),
- ejecución de herramientas (nombre, latencia, éxito o error),
- duración de cada nodo del grafo,
- errores y latencia total del turno.

Cada turno produce un diccionario plano y serializable (ver `finalizar`), que
la interfaz grafica y se guarda como una línea en `logs/metricas.jsonl`.
"""

from __future__ import annotations

import json
import logging
import math
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from config.settings import LOG_LEVEL, METRICS_LOG_PATH

logger = logging.getLogger("mantenia")

NODOS_GRAFO = ("enrutador", "nodo_conceptual", "agente_mantenimiento", "herramientas")
_MAX_PREGUNTA = 90


def configurar_logging() -> None:
    """Configura el logger de la aplicación una sola vez."""
    if logger.handlers:
        return

    manejador = logging.StreamHandler()
    manejador.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(manejador)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.propagate = False


def _extraer_tokens(respuesta: Any) -> tuple[int, int, int]:
    """Obtiene (entrada, salida, total) de un `LLMResult` de LangChain."""
    entrada = salida = total = 0

    for generaciones in getattr(respuesta, "generations", []) or []:
        for generacion in generaciones:
            uso = getattr(getattr(generacion, "message", None), "usage_metadata", None)
            if uso:
                entrada += int(uso.get("input_tokens", 0) or 0)
                salida += int(uso.get("output_tokens", 0) or 0)
                total += int(uso.get("total_tokens", 0) or 0)

    if not total:
        uso_llm = (getattr(respuesta, "llm_output", None) or {}).get("token_usage") or {}
        entrada = int(uso_llm.get("prompt_tokens", entrada) or 0)
        salida = int(uso_llm.get("completion_tokens", salida) or 0)
        total = int(uso_llm.get("total_tokens", 0) or 0)

    return entrada, salida, total or (entrada + salida)


class MetricsCallback(BaseCallbackHandler):
    """Recoge métricas de una ejecución (un turno) del grafo."""

    raise_error = False  # una falla de observabilidad nunca debe romper el agente

    def __init__(self, thread_id: str = "", pregunta: str = "") -> None:
        self.thread_id = thread_id
        self.pregunta = pregunta
        self._inicio = time.perf_counter()
        self._fecha = datetime.now(timezone.utc)
        self._candado = threading.Lock()
        self._abiertos: dict[Any, dict] = {}
        self.llamadas_modelo: list[dict] = []
        self.llamadas_herramientas: list[dict] = []
        self.nodos: list[dict] = []
        self.errores: list[str] = []

    # -- utilidades internas -------------------------------------------------

    def _abrir(self, run_id: Any, tipo: str, **datos: Any) -> None:
        with self._candado:
            self._abiertos[run_id] = {"tipo": tipo, "t0": time.perf_counter(), **datos}

    def _cerrar(self, run_id: Any) -> tuple[dict, float] | None:
        with self._candado:
            abierto = self._abiertos.pop(run_id, None)
        if abierto is None:
            return None
        return abierto, round(time.perf_counter() - abierto["t0"], 3)

    def registrar_error(self, error: BaseException | str) -> None:
        mensaje = error if isinstance(error, str) else f"{type(error).__name__}: {error}"
        self.errores.append(mensaje[:300])

    # -- modelo ----------------------------------------------------------------

    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs):
        self._abrir(run_id, "llm", origen=(metadata or {}).get("langgraph_node", "-"))

    def on_llm_start(self, serialized, prompts, *, run_id, metadata=None, **kwargs):
        self._abrir(run_id, "llm", origen=(metadata or {}).get("langgraph_node", "-"))

    def on_llm_end(self, response, *, run_id, **kwargs):
        cierre = self._cerrar(run_id)
        if cierre is None:
            return
        abierto, latencia = cierre
        entrada, salida, total = _extraer_tokens(response)
        self.llamadas_modelo.append(
            {
                "origen": abierto["origen"],
                "latencia_s": latencia,
                "tokens_entrada": entrada,
                "tokens_salida": salida,
                "tokens_totales": total,
            }
        )

    def on_llm_error(self, error, *, run_id, **kwargs):
        cierre = self._cerrar(run_id)
        if cierre is not None:
            abierto, latencia = cierre
            self.llamadas_modelo.append(
                {
                    "origen": abierto["origen"],
                    "latencia_s": latencia,
                    "tokens_entrada": 0,
                    "tokens_salida": 0,
                    "tokens_totales": 0,
                    "error": True,
                }
            )
        self.registrar_error(error)

    # -- herramientas ----------------------------------------------------------

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        nombre = kwargs.get("name") or (serialized or {}).get("name") or "desconocida"
        self._abrir(run_id, "tool", nombre=nombre)

    def on_tool_end(self, output, *, run_id, **kwargs):
        cierre = self._cerrar(run_id)
        if cierre is not None:
            abierto, latencia = cierre
            self.llamadas_herramientas.append(
                {"nombre": abierto["nombre"], "latencia_s": latencia, "ok": True}
            )

    def on_tool_error(self, error, *, run_id, **kwargs):
        cierre = self._cerrar(run_id)
        if cierre is not None:
            abierto, latencia = cierre
            self.llamadas_herramientas.append(
                {"nombre": abierto["nombre"], "latencia_s": latencia, "ok": False}
            )
        self.registrar_error(error)

    # -- nodos del grafo -------------------------------------------------------

    def on_chain_start(self, serialized, inputs, *, run_id, **kwargs):
        nombre = kwargs.get("name") or (serialized or {}).get("name")
        if nombre in NODOS_GRAFO:
            self._abrir(run_id, "nodo", nombre=nombre)

    def on_chain_end(self, outputs, *, run_id, **kwargs):
        cierre = self._cerrar(run_id)
        if cierre is not None and cierre[0]["tipo"] == "nodo":
            abierto, latencia = cierre
            self.nodos.append({"nodo": abierto["nombre"], "latencia_s": latencia})

    def on_chain_error(self, error, *, run_id, **kwargs):
        cierre = self._cerrar(run_id)
        if cierre is not None and cierre[0]["tipo"] == "nodo":
            abierto, latencia = cierre
            self.nodos.append(
                {"nodo": abierto["nombre"], "latencia_s": latencia, "error": True}
            )

    # -- cierre del turno ------------------------------------------------------

    def finalizar(self, ruta: str = "", motivo: str = "", ok: bool = True) -> dict:
        """Cierra el turno y devuelve el registro plano de métricas."""
        entrada = sum(c["tokens_entrada"] for c in self.llamadas_modelo)
        salida = sum(c["tokens_salida"] for c in self.llamadas_modelo)
        total = sum(c["tokens_totales"] for c in self.llamadas_modelo)

        registro = {
            "id": uuid.uuid4().hex[:8],
            "timestamp": self._fecha.isoformat(timespec="seconds"),
            "thread_id": self.thread_id,
            "pregunta": self.pregunta[:_MAX_PREGUNTA],
            "ruta": ruta or "desconocida",
            "motivo": motivo,
            "ok": ok and not self.errores,
            "latencia_s": round(time.perf_counter() - self._inicio, 3),
            "llamadas_modelo": len(self.llamadas_modelo),
            "tokens_entrada": entrada,
            "tokens_salida": salida,
            "tokens_totales": total,
            "llamadas_herramientas": len(self.llamadas_herramientas),
            "herramientas": list(self.llamadas_herramientas),
            "nodos": list(self.nodos),
            "llm": list(self.llamadas_modelo),
            "errores": list(self.errores),
        }
        logger.info(
            "turno=%s ruta=%s ok=%s latencia=%.2fs llm=%d tokens=%d tools=%d errores=%d",
            registro["id"], registro["ruta"], registro["ok"], registro["latencia_s"],
            registro["llamadas_modelo"], registro["tokens_totales"],
            registro["llamadas_herramientas"], len(registro["errores"]),
        )
        return registro


# ---------------------------------------------------------------------------
# Persistencia y agregados
# ---------------------------------------------------------------------------


def guardar_turno(metricas: dict, ruta: Path | None = None) -> None:
    """Agrega el turno a un archivo JSONL (sin guardar el texto de la pregunta)."""
    destino = Path(ruta or METRICS_LOG_PATH)
    registro = {k: v for k, v in metricas.items() if k != "pregunta"}
    registro["pregunta_caracteres"] = len(metricas.get("pregunta", ""))

    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except OSError as error:  # el sistema de archivos puede ser de solo lectura
        logger.warning("No se pudo escribir el registro de métricas: %s", error)


def percentil(valores: list[float], p: float) -> float:
    """Percentil por rango más cercano (p entre 0 y 100)."""
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    indice = max(0, math.ceil(p / 100 * len(ordenados)) - 1)
    return float(ordenados[indice])


def resumir(turnos: list[dict]) -> dict:
    """Indicadores agregados de una lista de turnos."""
    if not turnos:
        return {
            "turnos": 0, "errores": 0, "latencia_media_s": 0.0, "latencia_p95_s": 0.0,
            "latencia_max_s": 0.0, "llamadas_modelo": 0, "tokens_entrada": 0,
            "tokens_salida": 0, "tokens_totales": 0, "llamadas_herramientas": 0,
            "tools": {}, "rutas": {}, "tasa_exito": 0.0,
        }

    latencias = [t["latencia_s"] for t in turnos]
    tools: dict[str, int] = {}
    rutas: dict[str, int] = {}

    for turno in turnos:
        rutas[turno["ruta"]] = rutas.get(turno["ruta"], 0) + 1
        for herramienta in turno.get("herramientas", []):
            tools[herramienta["nombre"]] = tools.get(herramienta["nombre"], 0) + 1

    fallidos = sum(1 for t in turnos if not t["ok"])

    return {
        "turnos": len(turnos),
        "errores": fallidos,
        "latencia_media_s": round(sum(latencias) / len(latencias), 3),
        "latencia_p95_s": round(percentil(latencias, 95), 3),
        "latencia_max_s": round(max(latencias), 3),
        "llamadas_modelo": sum(t["llamadas_modelo"] for t in turnos),
        "tokens_entrada": sum(t["tokens_entrada"] for t in turnos),
        "tokens_salida": sum(t["tokens_salida"] for t in turnos),
        "tokens_totales": sum(t["tokens_totales"] for t in turnos),
        "llamadas_herramientas": sum(t["llamadas_herramientas"] for t in turnos),
        "tools": dict(sorted(tools.items(), key=lambda par: -par[1])),
        "rutas": rutas,
        "tasa_exito": round(100 * (len(turnos) - fallidos) / len(turnos), 1),
    }
