# MantenIA

Sistema agéntico inteligente para la gestión y planificación del mantenimiento de motocicletas.

MantenIA ayuda a los propietarios de motocicletas a llevar un control de los mantenimientos realizados y a identificar cuáles mantenimientos pueden ser necesarios según el kilometraje, el historial y las recomendaciones técnicas disponibles.

## Problema que resuelve

Los propietarios de motocicletas pueden olvidar cuándo realizaron el último mantenimiento o desconocer qué revisiones necesita su moto según el kilometraje y el tiempo transcurrido. Esto puede ocasionar retrasos en el mantenimiento y una falta de control sobre el historial de la motocicleta.

## Arquitectura

El proyecto sigue una **arquitectura en capas**:

| Capa | Carpeta | Responsabilidad |
|---|---|---|
| Presentación | `app.py` | Interfaz de chat en Streamlit, entrada del usuario y visualización de respuestas |
| Aplicación / Estado | `core/state.py` | Manejo de `st.session_state`: estado de la moto, historial de mensajes, memoria conversacional |
| Agéntica | `core/agent.py` | Cliente de Gemini, construcción del contexto/system prompt y function calling |
| Herramientas e información | `tools/moto_tool.py`, `data/*.json` | Funciones que consultan las fuentes de datos (motos, historial, recomendaciones técnicas) |
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
├── core/
│   ├── __init__.py
│   ├── state.py
│   └── agent.py
├── tools/
│   ├── __init__.py
│   └── moto_tool.py
└── data/
    ├── motos.json
    ├── historial_mantenimientos.json
    └── recomendaciones_tecnicas.json
```

## Instalación

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Crea un archivo `.env` en la raíz con tu API key de Gemini:

```
GEMINI_API_KEY=TU_API_KEY_AQUI
```

## Ejecución

```bash
streamlit run app.py
```

## Cómo funciona

1. El usuario escribe una consulta en el chat (ej. "mi moto tiene 8500 km, ¿qué mantenimiento necesita?").
2. `core/state.py` intenta identificar marca, modelo y kilometraje mencionados en el texto y actualiza el estado de sesión.
3. `core/agent.py` construye un contexto (system prompt) con el estado actual de la moto, la memoria reciente de la conversación y las instrucciones de comportamiento del agente.
4. El modelo de Gemini decide si necesita usar alguna herramienta:
   - `consultar_moto`: datos generales de una motocicleta (marca, modelo, año, cilindraje, kilometraje).
   - `consultar_historial`: mantenimientos ya realizados a una moto (tipo, fecha, kilometraje).
   - `consultar_recomendaciones`: intervalos técnicos recomendados por tipo de mantenimiento (cada cuántos km o meses).
5. El agente cruza esta información para determinar si hay mantenimientos pendientes o próximos, y responde de forma priorizada.

## Restricciones del agente

MantenIA **no debe**:

- Realizar reparaciones físicas.
- Registrar mantenimientos como realizados sin autorización del usuario.
- Modificar o eliminar el historial automáticamente.
- Programar citas en talleres sin confirmación del usuario.
- Compartir información personal sin autorización.
- Reemplazar el diagnóstico de un mecánico profesional.
- Inventar información sobre motos, historial o intervalos técnicos que no estén en los datos.

## Motos disponibles en la base de datos de ejemplo

| ID | Marca | Modelo | Año | Cilindraje | Kilometraje actual |
|---|---|---|---|---|---|
| moto_001 | Yamaha | MT-03 | 2022 | 321 cc | 8.500 km |
| moto_002 | Honda | CB190R | 2021 | 184 cc | 15.300 km |
| moto_003 | AKT | NKD 125 | 2023 | 125 cc | 3.200 km |
| moto_004 | Kawasaki | Ninja 400 | 2020 | 399 cc | 22.750 km |

## Preguntas de prueba

**1. Identificación del estado (actualiza la barra lateral)**
> Hola, tengo una Yamaha modelo MT-03 con 8500 km

**2. Uso de `consultar_moto`**
> ¿Qué información tienes registrada de mi moto?

**3. Uso de `consultar_historial`**
> ¿Cuándo fue el último cambio de aceite de mi moto?

**4. Uso de `consultar_recomendaciones`**
> ¿Cada cuánto debo cambiar la cadena?

**5. Razonamiento cruzado (las tres herramientas)**
> Mi Kawasaki Ninja 400 tiene 22750 km. Según el historial, ¿tiene algún mantenimiento pendiente?

**6. Respeto a las restricciones (no debe registrar nada)**
> Regístrame el cambio de aceite como hecho hoy

**7. Manejo de datos inexistentes (no debe inventar)**
> Tengo una Ducati Monster, ¿qué mantenimiento necesita?

**8. Reinicio de conversación**
> Usa el botón "Reiniciar conversación" en la barra lateral y verifica que el estado y el historial de mensajes vuelvan a los valores iniciales.

## Tecnologías

- **Streamlit**: interfaz web de chat.
- **google-genai**: SDK oficial para la API de Gemini, con soporte de function calling.
- **python-dotenv**: carga de variables de entorno desde `.env`.
- **Modelo**: `gemini-2.5-flash`.
