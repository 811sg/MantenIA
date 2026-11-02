# Despliegue en Streamlit Community Cloud (Fase 3)

## Antes de subir

1. Verifica que `.env` y `venv/` **no** estén en el repositorio (`.gitignore` ya los excluye).
2. Si tu API key viajó en un `.zip` o se subió alguna vez a un repositorio, **revócala** en Google AI Studio y crea otra.
3. `python -m pytest` debe pasar en local.

## Pasos

1. Sube el proyecto a GitHub (repositorio público para que el docente acceda):
   ```bash
   git init && git add . && git commit -m "MantenIA v3.1: interfaz, observabilidad y pruebas"
   git branch -M main && git remote add origin https://github.com/<usuario>/<repo>.git && git push -u origin main
   ```
2. En https://share.streamlit.io → **Create app** → elige el repositorio, rama `main` y archivo principal `app.py`.
3. *Advanced settings*: Python **3.12** y en **Secrets** pega:
   ```toml
   GEMINI_API_KEY = "tu_clave"
   GEMINI_MODEL = "gemini-3.8-flash"
   ```
4. **Deploy**. Copia la URL pública (`https://<app>.streamlit.app`): es el segundo entregable.

## Verificación en el entorno desplegado (guion de demostración)

| # | Acción en la app | Qué se comprueba |
|---|---|---|
| 1 | «¿Para qué sirve lubricar la cadena?» | Ruta `conceptual`, sin tools |
| 2 | «Mi Yamaha modelo MT-03 tiene 8500 km, ¿qué mantenimiento necesita?» | Estado de la moto, tools, ciclo ReAct |
| 3 | «¿Qué alertas pendientes tengo y cuál es la más urgente?» | `consultar_alertas` / `priorizar_alertas` |
| 4 | «¿Cuándo vence el SOAT de mis motos?» | `consultar_documentos_vehiculo` |
| 5 | «¿y la cadena?» (seguimiento) | Memoria por `thread_id` |
| 6 | Vista **Observabilidad** | Latencia, tokens, tools, errores |
| 7 | Barra lateral | Tipo de consulta, nodos recorridos y tools de la última consulta |

## Limitaciones conocidas

- La memoria (`MemorySaver`) vive en el proceso: se pierde al reiniciar la app.
- El plan gratuito de Gemini tiene cuotas; ante un 429 la app muestra un aviso con «Reintentar».
