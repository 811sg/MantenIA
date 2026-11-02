"""Vista «Observabilidad»: métricas de ejecución de la sesión.

Tiempos de respuesta, consumo de tokens, invocaciones al modelo, uso de
herramientas, rutas del grafo y errores, a partir de los registros que genera
`core/observability.py` en cada turno.
"""

import json

import pandas as pd
import streamlit as st

from core.observability import resumir
from ui import components as ui

COLOR_ACENTO = "#8FA3BF"
COLOR_INFO = "#5E6B7D"


def _tabla_turnos(turnos: list[dict]) -> pd.DataFrame:
    filas = []
    for numero, turno in enumerate(turnos, start=1):
        filas.append(
            {
                "turno": numero,
                "hora (UTC)": turno["timestamp"][11:19],
                "ruta": turno["ruta"],
                "latencia_s": turno["latencia_s"],
                "llamadas_modelo": turno["llamadas_modelo"],
                "tokens_entrada": turno["tokens_entrada"],
                "tokens_salida": turno["tokens_salida"],
                "tokens_totales": turno["tokens_totales"],
                "herramientas": ", ".join(h["nombre"] for h in turno["herramientas"]) or "—",
                "estado": "OK" if turno["ok"] else "Error",
            }
        )
    return pd.DataFrame(filas)


def _latencia_por_nodo(turnos: list[dict]) -> pd.DataFrame:
    filas = [
        {"nodo": n["nodo"], "latencia_s": n["latencia_s"]} for t in turnos for n in t["nodos"]
    ]
    if not filas:
        return pd.DataFrame()
    return pd.DataFrame(filas).groupby("nodo", as_index=True)[["latencia_s"]].mean().round(3)


def render() -> None:
    turnos: list[dict] = st.session_state.metricas

    ui.hero(
        "Observabilidad",
        "Cómo se comportó el agente en esta sesión: tiempos de respuesta, tokens, llamadas al modelo, herramientas y errores.",
    )

    if not turnos:
        ui.estado_vacio(
            "Aún no hay métricas",
            "Haz una pregunta en la sección Asistente y aquí verás el análisis de su ejecución.",
        )
        return

    r = resumir(turnos)
    ui.fila_kpis(
        [
            ("Consultas", r["turnos"], f"{r['tasa_exito']} % exitosas"),
            ("Latencia media", f"{r['latencia_media_s']:.2f} s", f"p95 {r['latencia_p95_s']:.2f} s · máx {r['latencia_max_s']:.2f} s"),
            ("Tokens totales", f"{r['tokens_totales']:,}".replace(",", "."), f"{r['tokens_entrada']} entrada · {r['tokens_salida']} salida"),
            ("Llamadas al modelo", r["llamadas_modelo"], f"{r['llamadas_modelo'] / r['turnos']:.1f} por consulta"),
            ("Tools ejecutadas", r["llamadas_herramientas"], f"{r['errores']} consulta(s) con error"),
        ]
    )

    tabla = _tabla_turnos(turnos)

    ui.seccion("Tiempos y consumo por consulta")
    izquierda, derecha = st.columns(2)
    with izquierda:
        st.caption("Latencia total por consulta (s)")
        st.line_chart(tabla.set_index("turno")[["latencia_s"]], color=COLOR_ACENTO)
    with derecha:
        st.caption("Tokens por consulta")
        st.bar_chart(
            tabla.set_index("turno")[["tokens_entrada", "tokens_salida"]],
            color=[COLOR_INFO, COLOR_ACENTO],
        )

    ui.seccion("Uso del grafo")
    col_nodos, col_tools, col_rutas = st.columns(3)
    with col_nodos:
        st.caption("Latencia media por nodo (s)")
        por_nodo = _latencia_por_nodo(turnos)
        if por_nodo.empty:
            st.caption("Sin datos de nodos.")
        else:
            st.bar_chart(por_nodo, color=COLOR_ACENTO, horizontal=True)
    with col_tools:
        st.caption("Invocaciones por herramienta")
        if r["tools"]:
            st.bar_chart(pd.DataFrame({"invocaciones": r["tools"]}), color=COLOR_INFO, horizontal=True)
        else:
            st.caption("Aún no se han usado herramientas.")
    with col_rutas:
        st.caption("Consultas por ruta")
        st.bar_chart(pd.DataFrame({"consultas": r["rutas"]}), color=COLOR_ACENTO, horizontal=True)

    ui.seccion("Detalle de consultas")
    st.dataframe(tabla, hide_index=True, width="stretch")

    with st.expander("Detalle técnico de la última consulta"):
        st.json(turnos[-1], expanded=False)

    errores = [(i, e) for i, t in enumerate(turnos, start=1) for e in t["errores"]]
    if errores:
        ui.seccion("Errores registrados")
        for numero, mensaje in errores:
            st.markdown(ui.badge(f"consulta {numero}", "danger") + f" `{mensaje}`", unsafe_allow_html=True)

    ui.seccion("Exportar")
    csv, js, limpiar = st.columns(3)
    csv.download_button(
        "Descargar CSV", tabla.to_csv(index=False), "metricas_mantenia.csv", "text/csv",
        icon=":material/download:", width="stretch",
    )
    js.download_button(
        "Descargar JSON", json.dumps(turnos, ensure_ascii=False, indent=2),
        "metricas_mantenia.json", "application/json", icon=":material/data_object:", width="stretch",
    )
    if limpiar.button("Limpiar métricas", icon=":material/delete:", width="stretch"):
        st.session_state.metricas = []
        st.rerun()
