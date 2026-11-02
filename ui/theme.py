"""Tema visual de MantenIA: tokens de color/tipografía y CSS inyectado.

Identidad: taller mecánico moderno — grafito oscuro con acento naranja y
tipografía Inter. El CSS es responsivo (breakpoints a 900 px y 640 px).
"""

import streamlit as st

COLORES = {
    "fondo": "#0E1013",
    "superficie": "#15181D",
    "superficie_2": "#1B1F26",
    "borde": "rgba(255,255,255,0.07)",
    "texto": "#E4E6EA",
    "texto_suave": "#8A919C",
    "acento": "#8FA3BF",
    "ok": "#5FAE92",
    "alerta": "#C9A55C",
    "peligro": "#C77B7B",
    "info": "#8FA3BF",
}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --mi-bg: __fondo__; --mi-surface: __superficie__; --mi-surface-2: __superficie_2__;
  --mi-border: __borde__; --mi-text: __texto__; --mi-muted: __texto_suave__;
  --mi-accent: __acento__; --mi-ok: __ok__; --mi-warn: __alerta__;
  --mi-danger: __peligro__; --mi-info: __info__;
}

/* Tipografía: se excluyen los iconos Material para no romper su fuente. */
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp button, .stApp input, .stApp textarea, .stApp a,
.stApp span:not([data-testid="stIconMaterial"]):not([class*="material"]) {
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
}
code, pre, .mi-mono { font-family: 'JetBrains Mono', ui-monospace, Consolas, monospace !important; }

/* Estructura general */
.block-container { padding-top: 2.2rem; padding-bottom: 5rem; max-width: 1180px; }
footer { visibility: hidden; }
h1, h2, h3 { letter-spacing: -0.01em; }
[data-testid="stSidebar"] { background: var(--mi-surface); border-right: 1px solid var(--mi-border); }
[data-testid="stSidebar"] .block-container { padding-top: 1.2rem; }

/* Cabecera */
.mi-hero {
  display: flex; align-items: center; gap: 1rem; padding: 1.1rem 1.3rem; margin-bottom: 1.1rem;
  background: var(--mi-surface);
  border: 1px solid var(--mi-border); border-radius: 16px;
}
.mi-hero h1 { margin: 0; font-size: 1.4rem; font-weight: 600; line-height: 1.2; padding: 0; }
.mi-hero p { margin: 0.15rem 0 0; color: var(--mi-muted); font-size: 0.92rem; }

/* Chips, badges y tarjetas */
.mi-chip, .mi-badge {
  display: inline-flex; align-items: center; gap: .35rem; padding: .18rem .62rem; margin: 0 .3rem .3rem 0;
  border-radius: 999px; font-size: .76rem; font-weight: 500; border: 1px solid var(--mi-border);
  background: var(--mi-surface-2); color: var(--mi-text); white-space: nowrap;
}
.mi-badge-ok     { color: var(--mi-ok);     border-color: rgba(95,174,146,.35);  background: rgba(95,174,146,.10); }
.mi-badge-warn   { color: var(--mi-warn);   border-color: rgba(201,165,92,.35);  background: rgba(201,165,92,.10); }
.mi-badge-danger { color: var(--mi-danger); border-color: rgba(199,123,123,.35);  background: rgba(199,123,123,.10); }
.mi-badge-info   { color: var(--mi-info);   border-color: rgba(143,163,191,.35);  background: rgba(143,163,191,.10); }
.mi-badge-accent { color: var(--mi-accent); border-color: rgba(143,163,191,.40);  background: rgba(143,163,191,.10); }

.mi-card {
  background: var(--mi-surface); border: 1px solid var(--mi-border); border-radius: 14px;
  padding: 1rem 1.15rem; margin-bottom: .8rem;
}
.mi-card h4 { margin: 0 0 .15rem; font-size: 1rem; }
.mi-card .mi-sub { color: var(--mi-muted); font-size: .82rem; margin-bottom: .5rem; }

.mi-kpi { background: var(--mi-surface); border: 1px solid var(--mi-border); border-radius: 14px; padding: .85rem 1rem; height: 100%; }
.mi-kpi .mi-kpi-label { color: var(--mi-muted); font-size: .74rem; text-transform: uppercase; letter-spacing: .06em; }
.mi-kpi .mi-kpi-value { font-size: 1.55rem; font-weight: 700; line-height: 1.25; }
.mi-kpi .mi-kpi-hint  { color: var(--mi-muted); font-size: .76rem; }

.mi-section { font-size: .78rem; font-weight: 600; text-transform: uppercase; letter-spacing: .08em;
  color: var(--mi-muted); margin: 1.2rem 0 .5rem; }

/* Sidebar */
.mi-brand { display: flex; align-items: center; gap: .6rem; margin-bottom: .6rem; }
.mi-brand .mi-brand-logo { width: 34px; height: 34px; border-radius: 9px; background: var(--mi-surface-2); border: 1px solid var(--mi-border); display: grid; place-items: center; font-weight: 700; color: var(--mi-accent); }
.mi-brand b { font-size: 1.1rem; } .mi-brand span { display: block; color: var(--mi-muted); font-size: .72rem; }
.mi-moto-row { display: flex; justify-content: space-between; padding: .28rem 0; font-size: .86rem; border-bottom: 1px dashed var(--mi-border); }
.mi-moto-row:last-child { border-bottom: 0; } .mi-moto-row span { color: var(--mi-muted); }
.mi-flow { display: flex; flex-wrap: wrap; align-items: center; gap: .25rem; margin: .3rem 0 .5rem; }
.mi-flow .mi-step { padding: .15rem .5rem; border-radius: 8px; font-size: .72rem; background: var(--mi-surface-2); border: 1px solid var(--mi-border); }
.mi-flow .mi-arrow { color: var(--mi-muted); font-size: .8rem; }

/* Chat */
[data-testid="stChatMessage"] { border: 1px solid var(--mi-border); border-radius: 14px; padding: .8rem 1rem; background: var(--mi-surface); }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { background: var(--mi-surface-2); }
.mi-meta { margin-top: .5rem; padding-top: .45rem; border-top: 1px dashed var(--mi-border); }
.mi-empty { text-align: center; padding: 1.6rem 1rem .6rem; }
.mi-empty h3 { margin-bottom: .2rem; } .mi-empty p { color: var(--mi-muted); }
.mi-error { border-left: 4px solid var(--mi-danger); }

/* Botones y entrada */
.stButton > button, .stDownloadButton > button { border-radius: 10px; font-weight: 500; border: 1px solid var(--mi-border); }
.stButton > button:hover { border-color: var(--mi-accent); color: var(--mi-accent); }
[data-testid="stChatInput"] { border-radius: 14px; }

/* Tablas */
[data-testid="stDataFrame"] { border: 1px solid var(--mi-border); border-radius: 12px; overflow: hidden; }

/* Responsivo */
@media (max-width: 900px) {
  .block-container { padding-left: 1rem; padding-right: 1rem; }
  .mi-hero { padding: .9rem 1rem; } .mi-hero h1 { font-size: 1.3rem; }
}
@media (max-width: 640px) {
  .block-container { padding-top: 1.2rem; }
  .mi-hero { flex-direction: row; gap: .7rem; }   .mi-hero p { font-size: .82rem; } .mi-kpi .mi-kpi-value { font-size: 1.25rem; }
}
</style>
"""


def aplicar_tema() -> None:
    """Inyecta el CSS global (se llama una vez por ejecución en `app.py`)."""
    css = _CSS
    for nombre, valor in COLORES.items():
        css = css.replace(f"__{nombre}__", valor)
    st.markdown(css, unsafe_allow_html=True)
