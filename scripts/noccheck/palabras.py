"""La regla de idioma: lo que lee una persona esta escrito en espanol.

Se comprueba solo donde el texto lo lee alguien: el summary y la description de
una alerta, los nombres de receiver y de route de Alertmanager, y los titulos,
descripciones, textos y enlaces de los dashboards. Los nombres de metrica, de
etiqueta y de job quedan fuera a proposito, porque son identificadores
referenciados desde las consultas y traducirlos rompe cada expresion que los
nombre.

La lista es de clase cerrada: articulos, pronombres, auxiliares, preposiciones y
conjunciones que el espanol no tiene. Es una decision y no un descuido. Con una
lista de palabras de contenido (host, status, file, check) el validador Finde
avisos legitimos, porque el espanol de este proyecto usa esos anglicismos a
proposito, y un aviso que se repite acaba ignorandose. Lo que se pierde es una
cadena inglesa corta sin palabras de clase cerrada, del tipo "Poco espacio en
disco": esa la pilla la revision, no la maquina. Lo que no se pierde es una
frase inglesa, que siempre lleva the, is, and u of.

Vive en su propio modulo y no en estilo.py porque el presupuesto de lineas no
tiene nada que ver con un diccionario, y los dos juntos no cabian en 100 lineas.
"""

from __future__ import annotations

import re

from .base import error

INGLES = set(
    """
    the and or but nor so yet of to in on at by for with without from into onto
    upon over under about is are was were be been being am it its this that
    these those they them their there what which who whom whose when where why
    how if then than while because as not only just also still can could will
    would shall should may might must have has had do does did one some any all
    both each every either neither none other another such very too own same
    until since during between through after before even again always never
    however therefore whether
    """.split()
)

CODE_SPAN = re.compile(r"`[^`]*`")
# {{ $labels.x }} se renderiza antes de que nadie lo lea, asi que es una
# directiva y no prosa. Sin esta excepcion toda alerta que nombre una etiqueta
# se leeria como texto ingles.
PLANTILLA = re.compile(r"\{\{.*?\}\}")
# Se tokeniza por \w entero y no por una clase [A-Za-z]. El viejo no estaba
# roto: como \w es Unicode-aware, el acento bloqueaba las dos mitades de "Caído"
# y la palabra no aparecia, sin perder ningun ingles. La diferencia es
# que ahora las palabras acentuadas si se ven, que es lo que una comprobacion por
# palabras necesita para tener sentido, y que se filtran digitos e identificadores
# con un isalpha() en vez de apoyarse en esa asimetria. "archivo_sd" y "2000" salen
# enteros y se descartan, sin una lista de identificadores que mantener.
PALABRA = re.compile(r"(?<!\w)\w+(?!\w)")


def palabras_inglesas(texto: str) -> set[str]:
    """Palabras inglesas de clase cerrada en un texto.

    Las dos excepciones apartan lo que se cita a proposito: ni
    `promtool check rules` ni {{ $labels.instance }} son una frase en ingles.
    """
    limpio = PLANTILLA.sub(" ", CODE_SPAN.sub(" ", texto))
    return {p for p in PALABRA.findall(limpio) if p.isalpha() and p.lower() in INGLES}


def check_ingles(etiqueta: str, texto: str) -> None:
    encontradas = palabras_inglesas(texto)
    if encontradas:
        error(f"{etiqueta}: texto en ingles ({', '.join(sorted(encontradas))})")
