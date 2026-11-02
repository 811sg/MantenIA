# Pruebas, hallazgos y correcciones (Fase 2)

Estado: **85 pruebas automáticas, todas pasan** (`python -m pytest`).
Salida completa: [`evidencias/02_pytest_despues.txt`](evidencias/02_pytest_despues.txt).
Diagnóstico previo a los ajustes: [`evidencias/01_diagnostico_inicial.txt`](evidencias/01_diagnostico_inicial.txt).

## Cómo se prueba

- **Offline (automático):** el grafo REAL se ejecuta con un modelo simulado (`tests/fakes.py`) que dispara los mismos callbacks que Gemini. Verifica enrutamiento, ciclo de herramientas, memoria, estado, métricas e interfaz sin gastar cuota.
- **Con Gemini real:** `python -m scripts.evaluar_agente` ejecuta 11 escenarios y genera `docs/evidencias/evaluacion_gemini.md/.json` con latencia, tokens y llamadas reales. Debe ejecutarse con tu API key y su resultado se adjunta al repositorio.

## Matriz de pruebas

| Funcionalidad | Componente | Resultado esperado | Resultado obtenido | Archivo |
|---|---|---|---|---|
| Grafo compila con 4 nodos y arista cíclica herramientas→agente | LangGraph | Nodos y arista presentes | ✔ | `test_graph_integration.py` |
| Ruta conceptual sin herramientas | Router / nodo conceptual | pasos `enrutador → nodo_conceptual`, 0 tools | ✔ | ídem |
| Ciclo agente → tools → agente | LangGraph / ToolNode | 4 pasos, ToolMessage con datos reales | ✔ | ídem |
| Varias tools en un turno | Tools | Ambas ejecutadas y registradas en orden | ✔ | ídem |
| Tool con argumentos inválidos | ToolNode | ToolMessage `error`, el turno no se rompe | ✔ | ídem |
| Estado de la moto en el prompt del agente | Estado | Marca/modelo/km llegan al system prompt | ✔ | ídem |
| Memoria entre turnos del mismo hilo | MemorySaver | El 2.º turno ve el 1.º | ✔ | ídem |
| Aislamiento entre hilos | MemorySaver | Hilo B no ve mensajes del A | ✔ | ídem |
| Traza reiniciada cada turno | Estado | pasos/tools del turno anterior no se acumulan | ✔ | ídem |
| Límite de recursión | LangGraph | `TurnoFallido(GraphRecursionError)` con métricas | ✔ | ídem |
| Error del modelo (cuota 429) | Manejo de errores | `TurnoFallido`, ruta `error`, `ok=False` | ✔ | ídem |
| 7 Tools sobre datos JSON (recuperación) | Tools | Conteos y filtros correctos, integridad referencial | ✔ | `test_tools.py` |
| Chain de priorización | LangChain | Solo alertas pendientes llegan al prompt | ✔ | ídem |
| Tokens, latencia, tools, nodos, errores | Observabilidad | Métricas exactas del turno | ✔ | `test_observability.py` |
| No se guarda el texto de la pregunta en el log | Privacidad | Solo longitud en `metricas.jsonl` | ✔ | ídem |
| Clasificación de errores y no filtrar la API key | Errores | cuota/credenciales/red/modelo/ciclo | ✔ | `test_errors.py` |
| Chat completo, sugerencias, reinicio, reintento, sin API key | Interfaz | Flujo sin excepciones | ✔ | `test_ui_smoke.py` |
| Render de Garaje y Observabilidad | Interfaz | Sin excepciones | ✔ | ídem |

## Hallazgos y acciones correctivas

| ID | Hallazgo (detectado en el diagnóstico inicial) | Impacto | Acción correctiva | Verificación |
|---|---|---|---|---|
| H1 | Las Tools buscaban la consulta completa como subcadena de un solo campo: `"Yamaha MT-03"`, `"moto_001 frenos"`, `"SOAT moto_001"` devolvían **0 resultados** | El agente respondía «no hay datos» ante consultas naturales | `tools/_busqueda.py`: consulta dividida en términos que deben aparecer entre los campos del registro | `test_hallazgo_h1_*` (3 pruebas) |
| H2 | Búsqueda sensible a tildes y sinónimos: `"revision"` no hallaba «Revisión…» y `"tecnomecánica"` no hallaba «Técnico-Mecánica» | Documentos y alertas no encontrados | Normalización sin tildes, plural simplificado y sinónimo `tecnomecánica/RTM` | `test_hallazgo_h2_*` (5 pruebas) |
| H3 | El extractor guardaba `modelo 2022` (año) o `modelo de mi AKT` → «DE» como modelo | Estado de la moto incorrecto en el prompt del agente | `core/moto_parser.py`: descarta años y palabras de enlace; admite `NKD 125`, `Ninja 400` | `test_hallazgo_h3_*`, `test_modelos_validos` |
| H4 | Cifras hipotéticas o decimales sobrescribían el kilometraje: «¿sirve a los **5000 km**?» → km = 5000; `12,5 km` → 5 | Kilometraje actual falso y recomendaciones erróneas | Se ignoran cifras tras «cada / a los / al llegar a…» y decimales | `test_hallazgo_h4_*` (4 pruebas) |
| H5 | Marca detectada por subcadena (sin límite de palabra) | Falsos positivos | Coincidencia por palabra completa | `test_marca_solo_como_palabra_completa` |
| H6 | Cualquier excepción mostraba un texto técnico crudo y no había reintento ni métricas del fallo | Mala experiencia y sin trazabilidad | `core/errors.py` + tarjeta de error con «Reintentar» + métricas del turno fallido | `test_error_de_cuota_*`, `test_clasificacion` |
| H7 | Cliente Gemini creado en dos sitios, sin tiempo límite y con 6 reintentos por defecto | Esperas largas ante cuota agotada | `core/llm_factory.py` único, `timeout=60`, `max_retries=2` | `test_fabrica_de_modelos_*` |
| H8 | La clave solo se leía de `.env`, lo que no funciona con los Secrets de otros despliegues | Fallos al desplegar | Lectura también desde `st.secrets` | `config/settings.py` |

Reproducir el «antes» de H1–H4: `docs/evidencias/01_diagnostico_inicial.txt`. El «después» son las mismas entradas convertidas en pruebas que ahora pasan.

## Pendiente de tu parte (requiere tu API key)

1. `python -m scripts.evaluar_agente` y confirmar el resultado en `evidencias/evaluacion_gemini.md`.
2. Probar en el despliegue real los flujos de la demostración y agregar capturas.
