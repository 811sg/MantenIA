"""Búsqueda tolerante para las Tools: sin tildes, sin mayúsculas y multi-término.

Antes cada Tool comprobaba que la consulta completa fuera una subcadena de un
único campo, por lo que "Yamaha MT-03" o "SOAT moto_001" no devolvían nada.
Ahora la consulta se divide en términos y todos deben aparecer entre los
campos del registro.
"""

import re
import unicodedata

_PALABRAS_VACIAS = {
    "de", "la", "el", "los", "las", "del", "y", "en", "mi", "para", "a", "un", "una",
}

# Sinónimos habituales en Colombia → forma presente en los datos.
_SINONIMOS = {
    "tecnomecanica": "tecnico mecanica",
    "tecnomecanicas": "tecnico mecanica",
    "rtm": "tecnico mecanica",
}


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con guiones/signos convertidos en espacios."""
    texto = unicodedata.normalize("NFD", str(texto).lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9_\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def terminos(consulta: str) -> list[str]:
    """Divide la consulta en términos significativos (con plural simplificado)."""
    normalizada = normalizar(consulta)
    for origen, destino in _SINONIMOS.items():
        normalizada = re.sub(rf"\b{origen}\b", destino, normalizada)

    resultado = []
    for termino in normalizada.split():
        if termino in _PALABRAS_VACIAS:
            continue
        if len(termino) > 3 and termino.endswith("s"):
            termino = termino[:-1]
        resultado.append(termino)
    return resultado


def coincide(consulta: str, *campos: str) -> bool:
    """`True` si todos los términos de la consulta aparecen en los campos.

    Una consulta vacía coincide con todo (comportamiento original).
    """
    texto = normalizar(" ".join(str(c) for c in campos))
    return all(termino in texto for termino in terminos(consulta))
