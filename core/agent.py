"""Integración del asistente MantenIA con la API de Gemini.

Este módulo configura el cliente de Gemini y proporciona las funciones
necesarias para construir el contexto del asistente y generar respuestas
a partir de los mensajes del usuario.

El asistente utiliza información de la motocicleta, memoria reciente de
la conversación y herramientas externas para responder consultas sobre
mantenimiento.
"""

from typing import TypedDict

from google import genai
from google.genai import types

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from tools.moto_tool import (
    consultar_historial,
    consultar_moto,
    consultar_recomendaciones,
)


class Moto(TypedDict):
    """Representa la información básica de la motocicleta del usuario."""

    marca: str
    modelo: str
    kilometraje_actual: str


# Cliente utilizado para realizar solicitudes a la API de Gemini.
client = genai.Client(api_key=GEMINI_API_KEY)


def construir_contexto(moto: Moto, memoria: str) -> str:
    """Construye las instrucciones de contexto para el asistente MantenIA.

    Combina la información actual de la motocicleta con la memoria
    reciente de la conversación y las instrucciones que determinan el
    comportamiento del modelo.

    El contexto también indica cuándo deben utilizarse las herramientas
    ``consultar_moto``, ``consultar_historial`` y
    ``consultar_recomendaciones``, y establece las restricciones que el
    agente debe respetar.

    Args:
        moto: Información actual de la motocicleta del usuario.
        memoria: Representación textual de los mensajes recientes de la
            conversación.

    Returns:
        Instrucción de sistema que se enviará al modelo Gemini como contexto.
    """
    return f"""
Eres MantenIA, un asistente experto en mantenimiento de motocicletas.

Ayudas al usuario a identificar mantenimientos pendientes o próximos según
el kilometraje y el historial de su motocicleta.

ESTADO ACTUAL DE LA MOTOCICLETA:
Marca: {moto["marca"]}
Modelo: {moto["modelo"]}
Kilometraje actual: {moto["kilometraje_actual"]}

MEMORIA RECIENTE:
{memoria}

Dispones de las herramientas consultar_moto, consultar_historial y
consultar_recomendaciones.

Usa consultar_moto cuando necesites datos generales de la motocicleta
(marca, modelo, año, cilindraje o kilometraje).

Usa consultar_historial cuando el usuario pregunte por mantenimientos
realizados, fechas o kilometrajes de mantenimientos anteriores.

Usa consultar_recomendaciones cuando el usuario pregunte cada cuánto se
debe hacer un mantenimiento o cuál es el intervalo técnico recomendado.

Para determinar si un mantenimiento está pendiente, compara el
kilometraje actual y la fecha del último mantenimiento de ese tipo
(consultar_historial) contra el intervalo recomendado
(consultar_recomendaciones).

Si puedes responder usando el estado o la memoria, responde directamente.
No inventes información de mantenimientos, de la motocicleta ni de
intervalos técnicos.

Restricciones que debes respetar siempre:
- No realices reparaciones físicas.
- No registres mantenimientos como realizados sin autorización del usuario.
- No modifiques ni elimines el historial automáticamente.
- No programes citas en talleres sin confirmación del usuario.
- No compartas información personal sin autorización.
- No reemplaces el diagnóstico de un mecánico profesional.

Sé breve, claro y cordial.
""".strip()


def responder(
    mensaje_usuario: str,
    moto: Moto,
    memoria: str,
) -> str:
    """Genera una respuesta del asistente MantenIA mediante Gemini.

    Construye el contexto de la conversación y envía el mensaje del
    usuario al modelo configurado de Gemini. El modelo puede utilizar las
    herramientas ``consultar_moto``, ``consultar_historial`` y
    ``consultar_recomendaciones`` cuando la consulta requiere información
    relacionada con la motocicleta, su historial o los intervalos
    técnicos de mantenimiento.

    Args:
        mensaje_usuario: Mensaje enviado por el usuario.
        moto: Información actual de la motocicleta del usuario.
        memoria: Representación textual de los mensajes recientes de la
            conversación.

    Returns:
        Respuesta textual generada por Gemini. Si el modelo no devuelve
        contenido textual, se retorna un mensaje predeterminado.
    """
    contexto = construir_contexto(moto, memoria)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=mensaje_usuario,
        config=types.GenerateContentConfig(
            system_instruction=contexto,
            tools=[consultar_moto, consultar_historial, consultar_recomendaciones],
        ),
    )

    return response.text or "No fue posible generar una respuesta."