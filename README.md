# MantenIA v2

Sistema agéntico inteligente para la gestión y planificación del mantenimiento de motocicletas, construido con **LangChain** sobre la API de Gemini.

MantenIA ayuda a los propietarios de motocicletas a llevar un control de los mantenimientos realizados y a identificar cuáles mantenimientos, alertas o documentos pueden requerir atención según el kilometraje, el historial y las recomendaciones técnicas disponibles.

## Problema que resuelve

Los propietarios de motocicletas pueden olvidar cuándo realizaron el último mantenimiento, desconocer qué revisiones necesita su moto según el kilometraje y el tiempo transcurrido, o perder de vista el vencimiento de documentos como el SOAT o la revisión técnico-mecánica. Esto puede ocasionar retrasos en el mantenimiento y una falta de control sobre la motocicleta.

## Evolución v01 → v02

La v01 usaba llamadas directas al SDK `google-genai`, con un único flujo monolítico donde todas las preguntas (incluso las conceptuales) pasaban por el agente completo con herramientas, y el system prompt embebido en `core/agent.py`.

La v02 migra a **LangChain** e introduce:

- **Router Chain**: clasifica cada consulta como `chain` (respuesta directa, económica, sin herramientas) o `agent` (requiere datos externos y herramientas), evitando invocar el agente completo para preguntas conceptuales.
- **Chains deterministas**: `response_chain` para respuestas conceptuales, `prioritization_chain` para priorizar alertas de forma estructurada.
- **Prompts centralizados** en `prompts/`, desacoplados de `core/agent.py`.
- **`create_agent`** de LangChain en vez de `generate_content` directo, con 7 herramientas disponibles.
- **Panel de trazabilidad en vivo** en la barra lateral: qué ruta se eligió, por qué, y qué herramientas se usaron en la última consulta.

## Arquitectura

El proyecto sigue una **arquitectura en capas**:

| Capa | Carpeta | Responsabilidad |
|---|---|---|
| Presentación | `app.py` | Interfaz de chat en Streamlit, estado de la moto y panel de trazabilidad |
| Aplicación / Estado | `core/state.py` | Manejo de `st.session_state`: estado de la moto, historial de mensajes, memoria conversacional, última ejecución |
| Prompts | `prompts/mantenimiento_prompt.py` | System prompts centralizados (router, respuesta general, agente) |
| Composición (Chains) | `chains/` | Router Chain, Response Chain y Prioritization Chain (LCEL) |
| Agéntica | `core/agent.py` | Despacho entre Chain y Agent, construcción del contexto y ejecución con LangChain |
| Herramientas e información | `tools/*.py`, `data/*.json` | Funciones (`@tool`) que consultan las fuentes de datos |
| Configuración | `config/settings.py` | Carga de variables de entorno y validación de la API key |

```
MantenIA/
├── venv/
├── .env
├── .gitignore
├── requirements.txt
├── app.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── prompts/
│   ├── __init__.py
│   └── mantenimiento_prompt.py
├── chains/
│   ├── __init__.py
│   ├── router_chain.py
│   ├── response_chain.py
│   └── prioritization_chain.py
├── core/
│   ├── __init__.py
│   ├── state.py
│   └── agent.py
├── tools/
│   ├── __init__.py
│   ├── moto_tool.py
│   ├── fecha_tool.py
│   ├── alertas_tool.py
│   └── documentos_tool.py
└── data/
    ├── motos.json
    ├── historial_mantenimientos.json
    ├── recomendaciones_tecnicas.json
    ├── alertas.json
    └── documentos_vehiculo.json
```

## Instalación

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

`requirements.txt`:
```
streamlit
python-dotenv
langchain
langchain-google-genai
pydantic
```

Crea un archivo `.env` en la raíz:

```
GEMINI_API_KEY=TU_API_KEY_AQUI
GEMINI_MODEL=gemini-2.5-flash
```

> **Nota sobre cuotas**: cada consulta del usuario implica al menos 2 llamadas al modelo (Router Chain + Response/Agent), por lo que modelos con cuota gratuita baja (como versiones preview recientes de Gemini 3) se agotan rápido en pruebas intensivas. `gemini-2.5-flash` tiene una cuota gratuita considerablemente más generosa y es la opción recomendada para desarrollo y sustentación.

## Ejecución

```bash
streamlit run app.py
```

## Cómo funciona

1. El usuario escribe una consulta en el chat.
2. `core/state.py` intenta identificar marca, modelo y kilometraje mencionados en el texto y actualiza el estado de sesión (independiente de la ruta que se elija después).
3. `core/agent.py` invoca el **Router Chain**, que clasifica la consulta:
   - **`chain`**: preguntas conceptuales o genéricas que no requieren datos externos. Se responde directo con la Response Chain, sin usar herramientas.
   - **`agent`**: preguntas que requieren datos reales de la moto, su historial, alertas o documentos. Se crea un `Agent` de LangChain con acceso a las 7 herramientas.
4. Si la ruta es `agent`, el modelo decide autónomamente qué herramienta(s) invocar, pudiendo encadenar varias en un mismo turno:
   - `consultar_moto`: datos generales de una motocicleta.
   - `consultar_historial`: mantenimientos ya realizados a una moto.
   - `consultar_recomendaciones`: intervalos técnicos recomendados por tipo de mantenimiento.
   - `consultar_alertas`: alertas de mantenimiento pendientes por moto.
   - `priorizar_alertas`: prioriza las alertas pendientes mediante una Chain determinista anidada.
   - `consultar_documentos_vehiculo`: vencimientos de SOAT, revisión técnico-mecánica, etc.
   - `obtener_fecha`: fecha y día actual.
5. `core/state.py → registrar_ejecucion()` guarda la ruta elegida, el motivo del router y las herramientas usadas, que se muestran en tiempo real en la barra lateral bajo **"Última ejecución"**.

## Restricciones del agente

MantenIA **no debe**:

- Realizar reparaciones físicas.
- Registrar mantenimientos como realizados sin autorización del usuario.
- Modificar o eliminar el historial automáticamente.
- Programar citas en talleres sin confirmación del usuario.
- Compartir información personal sin autorización.
- Reemplazar el diagnóstico de un mecánico profesional.
- Inventar información sobre motos, historial, alertas, documentos o intervalos técnicos que no estén en los datos.

## Motos disponibles en la base de datos de ejemplo

| ID | Marca | Modelo | Año | Cilindraje | Kilometraje actual |
|---|---|---|---|---|---|
| moto_001 | Yamaha | MT-03 | 2022 | 321 cc | 8.500 km |
| moto_002 | Honda | CB190R | 2021 | 184 cc | 15.300 km |
| moto_003 | AKT | NKD 125 | 2023 | 125 cc | 3.200 km |
| moto_004 | Kawasaki | Ninja 400 | 2020 | 399 cc | 22.750 km |

## Preguntas de prueba

| Consulta | Ruta esperada | Tools esperadas |
|---|---|---|
| ¿Qué es la tecnomecánica? | Chain | Ninguna |
| Explícame en qué consiste un cambio de aceite | Chain | Ninguna |
| Hola, tengo una Yamaha modelo MT-03 con 8500 km | Chain/Agent | Ninguna (actualiza estado en la UI siempre) |
| ¿Cuándo fue el último cambio de aceite de mi Yamaha MT-03? | Agent | `consultar_moto`, `consultar_historial` |
| ¿Tengo alertas pendientes en mi moto? | Agent | `consultar_alertas` |
| ¿Qué día es hoy y cuándo vence el SOAT de mi moto? | Agent | `obtener_fecha`, `consultar_documentos_vehiculo` |
| Organiza mis alertas por prioridad | Agent | `priorizar_alertas` |
| ¿Cada cuánto se cambia la cadena y cuándo vence mi revisión técnico-mecánica? | Agent | `consultar_recomendaciones`, `consultar_documentos_vehiculo` |
| Tengo una Ducati Monster, ¿qué mantenimiento necesita? | Agent | `consultar_moto` (sin resultados, sin inventar) |
| Regístrame el cambio de aceite como hecho hoy | Agent | Ninguna herramienta de escritura disponible; debe negarse |

Al final de cada prueba, usa el botón **"Reiniciar conversación"** y verifica que el estado de la moto, el historial de mensajes y la última ejecución vuelvan a sus valores iniciales.

## Tecnologías

- **Streamlit**: interfaz web de chat.
- **LangChain** (`langchain`, `langchain-google-genai`): composición de Chains (LCEL), Router estructurado con Pydantic y `create_agent` con múltiples herramientas.
- **Pydantic**: esquema estructurado (`RutaConsulta`) para la clasificación del router.
- **python-dotenv**: carga de variables de entorno desde `.env`.
- **Modelo**: configurable vía `GEMINI_MODEL` en `.env` (recomendado `gemini-2.5-flash` por su cuota gratuita más amplia).
