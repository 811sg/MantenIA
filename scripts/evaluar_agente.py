"""Evaluación del agente contra Gemini REAL (Fase 2: pruebas, métricas y evidencias).

Ejecuta una batería de escenarios sobre el grafo de producción, mide latencia,
tokens, llamadas al modelo y herramientas, y compara el resultado con lo
esperado. Genera dos archivos en `docs/evidencias/`:

- `evaluacion_gemini.json`  (datos crudos por escenario)
- `evaluacion_gemini.md`    (tabla lista para pegar en el informe)

Uso (desde la raíz del proyecto, con GEMINI_API_KEY en .env):

    python -m scripts.evaluar_agente
    python -m scripts.evaluar_agente --pausa 4     # espera entre escenarios (cuota gratuita)
"""

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config.settings import GEMINI_MODEL, validar_configuracion
from core.errors import clasificar_error
from core.observability import resumir
from core.session import TurnoFallido, invocar_grafo
from graph.workflow import crear_grafo_mantenimiento

SALIDA = Path(__file__).resolve().parents[1] / "docs" / "evidencias"

MOTO = {"marca": "Yamaha", "modelo": "MT-03", "kilometraje_actual": 8500}

# (id, componente, pregunta, ruta esperada, tools que deben aparecer, hilo)
# Los escenarios con el mismo hilo comparten memoria (prueba de MemorySaver).
ESCENARIOS = [
    ("E01", "Router + nodo conceptual", "¿Qué es la tecnomecánica?", "conceptual", [], "a"),
    ("E02", "Tool consultar_moto", "¿Qué datos tiene la Yamaha MT-03 registrada?", "herramientas", ["consultar_moto"], "b"),
    ("E03", "Tool consultar_historial", "Muéstrame el historial de mantenimientos de moto_001.", "herramientas", ["consultar_historial"], "c"),
    ("E04", "Tool consultar_recomendaciones", "¿Cada cuántos kilómetros se cambia el aceite según los intervalos técnicos?", "herramientas", ["consultar_recomendaciones"], "d"),
    ("E05", "Tool consultar_documentos_vehiculo", "¿Cuándo vence el SOAT de moto_001?", "herramientas", ["consultar_documentos_vehiculo"], "e"),
    ("E06", "Tool consultar_alertas", "¿Qué alertas pendientes tengo?", "herramientas", ["consultar_alertas"], "f"),
    ("E07", "Tool priorizar_alertas (Chain)", "Prioriza mis alertas pendientes.", "herramientas", ["priorizar_alertas"], "g"),
    ("E08", "Tool obtener_fecha", "¿Qué día es hoy?", "herramientas", ["obtener_fecha"], "h"),
    ("E09", "Ciclo ReAct con varias tools", "¿Qué documentos de mis motos están vencidos hoy?", "herramientas", ["obtener_fecha", "consultar_documentos_vehiculo"], "i"),
    ("E10a", "Memoria (turno 1)", "¿Para qué sirve la cadena de transmisión?", "conceptual", [], "m"),
    ("E10b", "Memoria (turno 2, seguimiento)", "¿y cada cuánto se revisa?", None, [], "m"),
]


def ejecutar(pausa: float) -> list[dict]:
    grafo = crear_grafo_mantenimiento()
    hilos: dict[str, str] = {}
    resultados = []

    for id_, componente, pregunta, ruta_esp, tools_esp, hilo in ESCENARIOS:
        thread_id = hilos.setdefault(hilo, str(uuid.uuid4()))
        print(f"[{id_}] {componente} ... ", end="", flush=True)

        try:
            r = invocar_grafo(grafo, thread_id, pregunta, MOTO)
            m = r["metricas"]
            ruta_ok = ruta_esp is None or r["ruta"] == ruta_esp
            tools_ok = set(tools_esp) <= set(r["tools"]) and (tools_esp or ruta_esp != "conceptual" or not r["tools"])
            veredicto = "CUMPLE" if ruta_ok and tools_ok and m["ok"] else "REVISAR"
            fila = {
                "id": id_, "componente": componente, "pregunta": pregunta,
                "ruta_esperada": ruta_esp, "tools_esperadas": tools_esp,
                "ruta_obtenida": r["ruta"], "tools_obtenidas": r["tools"],
                "pasos": r["pasos"], "latencia_s": m["latencia_s"],
                "llamadas_modelo": m["llamadas_modelo"], "tokens_totales": m["tokens_totales"],
                "tokens_entrada": m["tokens_entrada"], "tokens_salida": m["tokens_salida"],
                "respuesta": r["respuesta"][:400], "veredicto": veredicto, "metricas": m,
            }
        except TurnoFallido as fallo:
            info = clasificar_error(fallo.causa)
            fila = {
                "id": id_, "componente": componente, "pregunta": pregunta,
                "ruta_esperada": ruta_esp, "tools_esperadas": tools_esp,
                "ruta_obtenida": "error", "tools_obtenidas": [], "pasos": [],
                "latencia_s": fallo.metricas["latencia_s"], "llamadas_modelo": 0,
                "tokens_totales": 0, "tokens_entrada": 0, "tokens_salida": 0,
                "respuesta": f"{info.titulo}: {info.detalle}", "veredicto": "ERROR",
                "metricas": fallo.metricas,
            }

        print(f"{fila['veredicto']} ({fila['latencia_s']:.1f} s, {fila['tokens_totales']} tokens)")
        resultados.append(fila)
        time.sleep(pausa)

    return resultados


def escribir_informe(resultados: list[dict]) -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    resumen = resumir([r["metricas"] for r in resultados])
    cumple = sum(1 for r in resultados if r["veredicto"] == "CUMPLE")
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")

    (SALIDA / "evaluacion_gemini.json").write_text(
        json.dumps({"fecha": ahora, "modelo": GEMINI_MODEL, "resumen": resumen,
                    "escenarios": resultados}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lineas = [
        "# Evaluación con Gemini real",
        "",
        f"- Fecha (UTC): {ahora}",
        f"- Modelo: `{GEMINI_MODEL}`",
        f"- Escenarios que cumplen: **{cumple}/{len(resultados)}**",
        f"- Latencia media: {resumen['latencia_media_s']} s · p95: {resumen['latencia_p95_s']} s",
        f"- Tokens totales: {resumen['tokens_totales']} · Llamadas al modelo: {resumen['llamadas_modelo']}"
        f" · Tools ejecutadas: {resumen['llamadas_herramientas']}",
        "",
        "| ID | Componente | Ruta esp. → obt. | Tools obtenidas | Latencia (s) | Llamadas LLM | Tokens | Veredicto |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for r in resultados:
        lineas.append(
            f"| {r['id']} | {r['componente']} | {r['ruta_esperada'] or 'cualquiera'} → {r['ruta_obtenida']} | "
            f"{', '.join(r['tools_obtenidas']) or '—'} | {r['latencia_s']:.2f} | {r['llamadas_modelo']} | "
            f"{r['tokens_totales']} | {r['veredicto']} |"
        )
    (SALIDA / "evaluacion_gemini.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"\nInforme: {SALIDA / 'evaluacion_gemini.md'}  ({cumple}/{len(resultados)} cumplen)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pausa", type=float, default=2.0, help="segundos entre escenarios")
    args = parser.parse_args()

    validar_configuracion()
    escribir_informe(ejecutar(args.pausa))


if __name__ == "__main__":
    main()
