"""Vista «Garaje»: motos, alertas, documentos e intervalos (solo lectura).

Muestra en pantalla las mismas fuentes JSON que consultan las Tools del agente
(a través de `core/repositorio.py`). No modifica ningún dato.
"""

from datetime import date

import pandas as pd
import streamlit as st

from core import analitica, repositorio
from ui import components as ui

_TONO = {"vencido": "danger", "por_vencer": "warn", "vigente": "ok"}
_COLOR = {"vencido": "#C77B7B", "por_vencer": "#C9A55C", "vigente": "#5FAE92"}


def _plazo(fecha_iso: str, hoy: date) -> tuple[int, str]:
    dias = analitica.dias_restantes(fecha_iso, hoy)
    estado = analitica.clasificar_vencimiento(dias)
    return dias, analitica.etiqueta_vencimiento(dias)


def _color_plazo(valor: str) -> str:
    if valor.startswith("Vencido"):
        return f"color: {_COLOR['vencido']}; font-weight: 600"
    if valor.startswith("Vence"):
        return f"color: {_COLOR['por_vencer']}; font-weight: 600"
    return f"color: {_COLOR['vigente']}"


def _tarjetas_motos(hoy: date) -> None:
    alertas = [a for a in repositorio.cargar_alertas() if a["estado"].lower() == "pendiente"]
    historial = repositorio.cargar_historial()
    columnas = st.columns(2)

    for indice, moto in enumerate(repositorio.cargar_motos()):
        propias = [a for a in alertas if a["moto_id"] == moto["id"]]
        ultimo = max((h["fecha"] for h in historial if h["moto_id"] == moto["id"]), default=None)

        estados = [
            analitica.clasificar_vencimiento(analitica.dias_restantes(a["fecha_limite"], hoy))
            for a in propias
        ]
        peor = "vencido" if "vencido" in estados else "por_vencer" if "por_vencer" in estados else "vigente"

        chips = [
            ui.badge(f"{moto['cilindraje']} cc"),
            ui.badge(f"{moto['kilometraje_actual']:,} km".replace(",", ".")),
            ui.badge(moto["id"]),
        ]
        if propias:
            chips.append(ui.badge(f"{len(propias)} alerta(s) pendiente(s)", _TONO[peor]))
        else:
            chips.append(ui.badge("Sin alertas", "ok"))

        with columnas[indice % 2]:
            ui.tarjeta(
                analitica.nombre_moto(moto),
                f"Año {moto['año']} · último mantenimiento: {ultimo or 'sin registros'}",
                chips,
            )


def _tabla_alertas(hoy: date) -> None:
    motos = {m["id"]: analitica.nombre_moto(m) for m in repositorio.cargar_motos()}
    filas = []
    for alerta in repositorio.cargar_alertas():
        dias, plazo = _plazo(alerta["fecha_limite"], hoy)
        filas.append(
            {
                "Moto": motos.get(alerta["moto_id"], alerta["moto_id"]),
                "Alerta": alerta["alerta"],
                "Fecha límite": alerta["fecha_limite"],
                "Plazo": plazo,
                "Prioridad": alerta["prioridad"].capitalize(),
                "Estado": alerta["estado"].capitalize(),
                "_dias": dias,
            }
        )
    tabla = pd.DataFrame(filas).sort_values("_dias").drop(columns="_dias")
    st.dataframe(tabla.style.map(_color_plazo, subset=["Plazo"]), hide_index=True, width="stretch")


def _tabla_documentos(hoy: date) -> None:
    motos = {m["id"]: analitica.nombre_moto(m) for m in repositorio.cargar_motos()}
    filas = []
    for doc in repositorio.cargar_documentos():
        dias, plazo = _plazo(doc["fecha_vencimiento"], hoy)
        filas.append(
            {
                "Moto": motos.get(doc["moto_id"], doc["moto_id"]),
                "Documento": doc["documento"],
                "Vence": doc["fecha_vencimiento"],
                "Plazo": plazo,
                "Descripción": doc["descripcion"],
                "_dias": dias,
            }
        )
    tabla = pd.DataFrame(filas).sort_values("_dias").drop(columns="_dias")
    st.dataframe(tabla.style.map(_color_plazo, subset=["Plazo"]), hide_index=True, width="stretch")


def _tabla_historial() -> None:
    motos = repositorio.cargar_motos()
    elegida = st.selectbox(
        "Motocicleta",
        motos,
        format_func=lambda m: f"{analitica.nombre_moto(m)} ({m['id']})",
    )
    registros = [h for h in repositorio.cargar_historial() if h["moto_id"] == elegida["id"]]

    if not registros:
        st.info("Esta moto aún no tiene mantenimientos registrados.")
        return

    tabla = pd.DataFrame(registros).sort_values("fecha", ascending=False)
    tabla["tipo"] = tabla["tipo"].str.replace("_", " ").str.capitalize()
    st.dataframe(
        tabla[["fecha", "tipo", "kilometraje"]].rename(
            columns={"fecha": "Fecha", "tipo": "Mantenimiento", "kilometraje": "Kilometraje"}
        ),
        hide_index=True,
        width="stretch",
    )


def _tabla_intervalos() -> None:
    tabla = pd.DataFrame(repositorio.cargar_recomendaciones())
    tabla["tipo"] = tabla["tipo"].str.replace("_", " ").str.capitalize()
    st.dataframe(
        tabla.rename(
            columns={
                "tipo": "Mantenimiento",
                "intervalo_km": "Cada (km)",
                "intervalo_meses": "Cada (meses)",
                "descripcion": "Descripción",
            }
        ),
        hide_index=True,
        width="stretch",
    )


def render() -> None:
    hoy = date.today()
    resumen = analitica.resumen_garaje(hoy)

    ui.hero(
        "Garaje",
        "Resumen de tus motos, con sus alertas y documentos por vencer. Es solo de consulta.",
        chips=[ui.badge(f"Hoy: {hoy:%d/%m/%Y}")],
    )

    ui.fila_kpis(
        [
            ("Motos registradas", resumen["motos"], "en el garaje"),
            ("Alertas pendientes", resumen["alertas_pendientes"], f"{resumen['alertas_vencidas']} con plazo vencido"),
            ("Documentos vencidos", resumen["documentos_vencidos"], "SOAT o tecnomecánica"),
            ("Por vencer (30 d)", resumen["documentos_por_vencer"], "documentos"),
        ]
    )

    ui.seccion("Motocicletas")
    _tarjetas_motos(hoy)

    ui.seccion("Detalle (elige una pestaña)")
    pestana_alertas, pestana_docs, pestana_hist, pestana_int = st.tabs(
        ["Alertas", "Documentos", "Historial", "Intervalos técnicos"]
    )
    with pestana_alertas:
        _tabla_alertas(hoy)
    with pestana_docs:
        _tabla_documentos(hoy)
    with pestana_hist:
        _tabla_historial()
    with pestana_int:
        _tabla_intervalos()
