# Observabilidad y métricas

## Qué se mide (por consulta)

| Métrica | Fuente |
|---|---|
| Tiempo de respuesta total y por nodo | `MetricsCallback` (callbacks de LangChain, sin tocar los nodos) |
| Invocaciones al modelo (incluye enrutador y Chain de priorización) | `on_chat_model_start / on_llm_end` |
| Tokens de entrada, salida y totales | `usage_metadata` de cada respuesta de Gemini |
| Herramientas ejecutadas, su latencia y éxito/error | `on_tool_start / end / error` |
| Ruta del grafo y nodos recorridos | Estado de LangGraph + callbacks |
| Errores | `on_*_error` y excepciones del turno (clasificadas en `core/errors.py`) |

## Dónde verlas

- **Vista Observabilidad** de la app: KPIs (consultas, latencia media/p95/máx, tokens, llamadas al modelo, tools, tasa de éxito), gráficos por consulta y por nodo/tool/ruta, tabla de detalle, errores y exportación CSV/JSON.
- **Chips bajo cada respuesta** y **barra lateral**: ruta, tools, latencia y tokens de la última consulta.
- **Registro persistente** `logs/metricas.jsonl` (una línea por consulta; no guarda el texto de la pregunta) y logs de consola con el logger `mantenia`.
- **Evaluación reproducible:** `python -m scripts.evaluar_agente` → `docs/evidencias/evaluacion_gemini.md`.

## Cómo demostrar una mejora

1. Ejecuta `python -m scripts.evaluar_agente` y guarda el resultado como «antes/después» al cambiar prompts o configuración.
2. Compara latencia media/p95, tokens y número de llamadas al modelo por escenario.

> En Streamlit Community Cloud el sistema de archivos es efímero: `logs/` se reinicia al reiniciar la app. Para conservar métricas, descarga el CSV/JSON desde la vista.
