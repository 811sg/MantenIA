# Arquitectura de MantenIA

## Estructura de carpetas

```
MantenIA/
├── app.py                    # Punto de entrada: página, tema, navegación entre vistas
├── config/settings.py        # Variables de entorno / Secrets (nada de prompts)
├── core/                     # Lógica de aplicación sin UI
│   ├── session.py            # Estado de Streamlit, thread_id y ejecución de turnos (stream)
│   ├── moto_parser.py        # Extracción pura de marca / modelo / km
│   ├── observability.py      # Callback de métricas, agregados y registro JSONL
│   ├── errors.py             # Errores técnicos → mensajes para el usuario
│   ├── analitica.py          # Vencimientos y resumen del garaje
│   ├── repositorio.py        # Único acceso a los JSON de data/
│   └── llm_factory.py        # Único lugar donde se crea el cliente Gemini
├── graph/                    # LangGraph: state.py · nodes.py · workflow.py
├── prompts/                  # Prompts por nodo
├── tools/                    # 7 Tools + _busqueda.py (búsqueda tolerante)
├── data/                     # Fuentes JSON (motos, historial, alertas, documentos, intervalos)
├── ui/                       # Presentación
│   ├── theme.py · components.py · sidebar.py
│   └── views/                # chat · garaje · observabilidad
├── tests/                    # 85 pruebas (pytest)
├── scripts/evaluar_agente.py # Evaluación contra Gemini real → docs/evidencias
├── docs/                     # Documentación y evidencias
└── .streamlit/config.toml    # Tema y servidor
```

## Capas y reglas de dependencia

| Capa | Responsabilidad | Regla |
|---|---|---|
| `ui/` | Pintar y capturar eventos | No contiene lógica del agente; solo llama a `core/` |
| `core/` | Sesión, métricas, errores, datos | Solo `session.py` importa Streamlit |
| `graph/` | Nodos, aristas y estado de LangGraph | No importa Streamlit |
| `tools/` | Consultas a las fuentes de datos | Acceden a datos solo vía `core/repositorio.py` |
| `config/` | Entorno | Sin prompts |

Dependencias: `ui → core → graph → tools → core.repositorio`.

## Flujo del grafo

`START → enrutador → (conceptual → nodo_conceptual → END | herramientas → agente_mantenimiento ⇄ herramientas → END)`

El recorrido de nodos de la última consulta se muestra en la barra lateral de la app.

## Componentes que exige la actividad

| Componente | Dónde vive |
|---|---|
| LangChain | `tools/` (`@tool`, Chain de priorización), `prompts/`, mensajes y modelo |
| LangGraph | `graph/` (StateGraph cíclico, ToolNode, conditional edges) |
| Memoria | `MemorySaver` + `thread_id` por sesión (`core/session.py`) |
| Estado | `MantenimientoState` + estado visible de la moto (`moto_parser`) |
| Recuperación (RAG) | Recuperación por herramientas sobre fuentes JSON (documentos, intervalos, historial); no hay base vectorial |
| Tools | 7 herramientas en `tools/` |
