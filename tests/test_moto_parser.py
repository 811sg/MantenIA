"""Pruebas del extractor de marca, modelo y kilometraje."""

import pytest

from core.moto_parser import (
    detectar_kilometraje,
    detectar_marca,
    detectar_modelo,
    extraer_datos_moto,
)


def test_caso_feliz_completo():
    datos = extraer_datos_moto("Tengo una Yamaha modelo MT-03 con 8500 km")
    assert datos == {"marca": "Yamaha", "modelo": "MT-03", "kilometraje_actual": 8500}


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("tiene 8.500 km", 8500),
        ("tiene 8,500 km", 8500),
        ("tiene 8500km", 8500),
        ("tiene 22.750 kilómetros", 22750),
        ("no menciono kilometraje", None),
    ],
)
def test_formatos_de_kilometraje(texto, esperado):
    assert detectar_kilometraje(texto) == esperado


def test_hallazgo_h3_el_ano_no_es_el_modelo():
    """H3: 'modelo 2022' se guardaba como modelo '2022'."""
    assert detectar_modelo("mi moto es modelo 2022 y tiene 8.500 km") is None


def test_hallazgo_h3_palabras_de_enlace_no_son_modelo():
    """H3: 'modelo de mi AKT...' se guardaba como modelo 'DE'."""
    assert detectar_modelo("el modelo de mi AKT es NKD 125") is None


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("modelo es CB190R", "CB190R"),
        ("una AKT modelo NKD 125 con 3200 km", "NKD 125"),
        ("una Kawasaki modelo Ninja 400 con 22.750 km", "NINJA 400"),
        ("modelo MT-03 con 8500 km", "MT-03"),
        ("modelo MT-03 8500 km", "MT-03"),
    ],
)
def test_modelos_validos(texto, esperado):
    assert detectar_modelo(texto) == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "¿cada cuántos km se cambia el aceite? ¿sirve cambiarlo a los 5000 km?",
        "cambiar el aceite cada 3000 km",
        "tengo 12,5 km de ruta diaria",
    ],
)
def test_hallazgo_h4_km_hipoteticos_o_decimales_no_sobrescriben_el_odometro(texto):
    """H4: una cifra hipotética o decimal se guardaba como kilometraje actual."""
    assert detectar_kilometraje(texto) is None


def test_h4_se_conserva_el_km_real_aunque_haya_cifras_hipoteticas():
    texto = "mi moto tiene 8500 km, ¿cada cuántos km cambio el aceite, cada 3000 km?"
    assert detectar_kilometraje(texto) == 8500


def test_marca_solo_como_palabra_completa():
    assert detectar_marca("la tecnomecánica de mi Honda vence pronto") == "Honda"
    assert detectar_marca("mi moto es una Pulsar") is None
    assert detectar_marca("el aktivador no funciona") is None
