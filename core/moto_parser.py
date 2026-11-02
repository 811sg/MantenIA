"""Extracción de marca, modelo y kilometraje desde el texto del usuario.

Son funciones puras (sin Streamlit) para poder probarlas de forma aislada.
`core/session.py` las usa para mantener el estado visible de la motocicleta.
"""

import re

MARCAS = ["yamaha", "honda", "suzuki", "kawasaki", "bajaj", "akt", "ktm", "tvs"]

# Palabras que pueden seguir a "modelo" sin ser un modelo de moto.
_NO_MODELO = {
    "de", "del", "la", "el", "mi", "tu", "su", "es", "que", "un", "una",
    "y", "o", "con", "para", "en", "a", "por", "se", "lo", "los", "las",
}

# "modelo MT-03", "modelo es CB190R", "modelo Ninja 400" (un número corto
# final forma parte del nombre, salvo que sea el kilometraje: "... 400 km").
_PATRON_MODELO = re.compile(
    r"\bmodelo\s+(?:es\s+|:\s*)?"
    r"([A-Za-zÁÉÍÓÚáéíóúÑñ0-9\-]+(?:\s+\d{2,3}(?![\d.,]|\s*(?:km|kil)))?)",
    re.IGNORECASE,
)

# Kilometraje: miles con separador ("8.500", "22,750") o número simple.
# Se descartan decimales ("12,5 km") mediante lookarounds.
_PATRON_KM = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:[.,]\d{3})+|\d+)(?![.,]\d)\s*(?:km|kil[oó]metros)\b"
)

# Cifras hipotéticas: "cada 3000 km", "a los 5000 km" no son el odómetro.
_CONTEXTO_HIPOTETICO = re.compile(
    r"\b(cada|a los|al llegar a|cuando llegue a|despu[eé]s de|hasta los)\b"
)


def detectar_marca(texto: str) -> str | None:
    texto_lower = texto.lower()
    for marca in MARCAS:
        if re.search(rf"\b{marca}\b", texto_lower):
            return marca.capitalize()
    return None


def detectar_modelo(texto: str) -> str | None:
    coincidencia = _PATRON_MODELO.search(texto)
    if not coincidencia:
        return None

    candidato = coincidencia.group(1).strip()
    primera_palabra = candidato.split()[0].lower()

    if primera_palabra in _NO_MODELO:
        return None

    # Un año suelto ("modelo 2022") es el año de la moto, no su modelo.
    if re.fullmatch(r"(19|20)\d{2}", candidato):
        return None

    return candidato.upper()


def detectar_kilometraje(texto: str) -> int | None:
    texto_lower = texto.lower()

    for coincidencia in _PATRON_KM.finditer(texto_lower):
        ventana = texto_lower[max(0, coincidencia.start() - 25) : coincidencia.start()]
        if _CONTEXTO_HIPOTETICO.search(ventana):
            continue
        return int(coincidencia.group(1).replace(".", "").replace(",", ""))

    return None


def extraer_datos_moto(texto: str) -> dict:
    """Devuelve solo los datos detectados: `marca`, `modelo` y/o `kilometraje_actual`."""
    datos: dict = {}

    marca = detectar_marca(texto)
    if marca:
        datos["marca"] = marca

    modelo = detectar_modelo(texto)
    if modelo:
        datos["modelo"] = modelo

    kilometraje = detectar_kilometraje(texto)
    if kilometraje is not None:
        datos["kilometraje_actual"] = kilometraje

    return datos
