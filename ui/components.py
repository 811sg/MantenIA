"""Componentes visuales reutilizables (HTML seguro sobre Streamlit).

Todo texto dinámico pasa por `html.escape` antes de insertarse en HTML.
"""

from html import escape

import streamlit as st

TONOS = {"ok", "warn", "danger", "info", "accent"}


def _html(contenido: str) -> None:
    st.markdown(contenido, unsafe_allow_html=True)


def badge(texto: str, tono: str = "") -> str:
    """Devuelve el HTML de una insignia (`tono`: ok, warn, danger, info, accent)."""
    clase = f"mi-badge mi-badge-{tono}" if tono in TONOS else "mi-chip"
    return f'<span class="{clase}">{escape(str(texto))}</span>'


def hero(titulo: str, subtitulo: str, chips: list[str] | None = None) -> None:
    extra = f'<div style="margin-top:.5rem">{"".join(chips)}</div>' if chips else ""
    _html(
        f'<div class="mi-hero"><div><h1>{escape(titulo)}</h1>'
        f"<p>{escape(subtitulo)}</p>{extra}</div></div>"
    )


def seccion(titulo: str) -> None:
    _html(f'<div class="mi-section">{escape(titulo)}</div>')


def kpi(etiqueta: str, valor: str | int | float, pista: str = "") -> None:
    _html(
        f'<div class="mi-kpi"><div class="mi-kpi-label">{escape(etiqueta)}</div>'
        f'<div class="mi-kpi-value">{escape(str(valor))}</div>'
        f'<div class="mi-kpi-hint">{escape(pista) or "&nbsp;"}</div></div>'
    )


def fila_kpis(items: list[tuple[str, str | int | float, str]]) -> None:
    """Fila de tarjetas KPI; Streamlit las apila solo en pantallas estrechas."""
    columnas = st.columns(len(items))
    for columna, (etiqueta, valor, pista) in zip(columnas, items):
        with columna:
            kpi(etiqueta, valor, pista)


def tarjeta(titulo: str, subtitulo: str = "", chips: list[str] | None = None, cuerpo: str = "") -> None:
    _html(
        f'<div class="mi-card"><h4>{escape(titulo)}</h4>'
        f'<div class="mi-sub">{escape(subtitulo)}</div>'
        f'{"".join(chips or [])}{cuerpo}</div>'
    )


def flujo_nodos(pasos: list[str]) -> str:
    """HTML del recorrido START → nodos → END."""
    piezas = ["START", *pasos, "END"]
    html = '<span class="mi-arrow">→</span>'.join(
        f'<span class="mi-step mi-mono">{escape(p)}</span>' for p in piezas
    )
    return f'<div class="mi-flow">{html}</div>'


def tono_ruta(ruta: str) -> str:
    return {"conceptual": "info", "herramientas": "accent", "error": "danger"}.get(ruta, "")


def meta_respuesta(meta: dict) -> str:
    """Chips bajo cada respuesta: tipo de consulta, herramientas, tiempo y tokens."""
    ruta = meta.get("ruta", "-")
    etiqueta = {"conceptual": "Consulta conceptual", "herramientas": "Consulta con datos"}.get(ruta, ruta)
    chips = [badge(etiqueta, tono_ruta(ruta))]

    for nombre in meta.get("tools", []):
        chips.append(badge(nombre))
    if meta.get("latencia_s") is not None:
        chips.append(badge(f"{meta['latencia_s']:.1f} s"))
    if meta.get("tokens"):
        chips.append(badge(f"{meta['tokens']:,} tokens".replace(",", ".")))

    return f'<div class="mi-meta">{"".join(chips)}</div>'


def estado_vacio(titulo: str, texto: str) -> None:
    _html(f'<div class="mi-empty"><h3>{escape(titulo)}</h3><p>{escape(texto)}</p></div>')


def tarjeta_error(titulo: str, sugerencia: str, detalle: str = "") -> None:
    extra = f'<div class="mi-sub mi-mono">{escape(detalle)}</div>' if detalle else ""
    _html(
        f'<div class="mi-card mi-error"><h4>{escape(titulo)}</h4>'
        f'<div class="mi-sub" style="font-size:.9rem">{escape(sugerencia)}</div>{extra}</div>'
    )
