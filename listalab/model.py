"""Modelo sin Qt: los datos son listas de Python, nunca nodos de un árbol.

Las rutas también son listas: [1, 2] accede a data[1][2]. El árbol gráfico
es una proyección descartable de estos datos, no su representación principal.
"""

from __future__ import annotations

import json
import math
import re
from typing import Union

from . import recursive as r


class Symbol(str):
    """Un símbolo Lisp se muestra sin las comillas de una cadena."""


Value = Union[list["Value"], Symbol, str, int, float, bool, None]
MAX_DEPTH = 12
MAX_NODES = 500
MAX_SOURCE = 32_000
SYMBOL = re.compile(r"[^\s()\"';]+\Z")
INTEGER = re.compile(r"[+-]?\d+\Z")
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


def validate(value: Value, *, root_list: bool = True) -> None:
    if root_list and not isinstance(value, list):
        raise ValueError("La raíz debe ser una lista: utiliza paréntesis, por ejemplo (1 (2 3)).")
    count = 0

    def visit(node: Value, depth: int) -> None:
        nonlocal count
        count += 1
        if count > MAX_NODES:
            raise ValueError(f"El límite visual es de {MAX_NODES} nodos.")
        if depth > MAX_DEPTH:
            raise ValueError(f"El límite es de {MAX_DEPTH} niveles de listas.")
        if isinstance(node, list):
            visit_items(node, depth)
        elif isinstance(node, Symbol):
            if not SYMBOL.fullmatch(node) or node in {"nil", "#t", "#f"} or NUMBER.fullmatch(node):
                raise ValueError("Símbolo no válido.")
        elif node is not None and type(node) not in (str, int, float, bool):
            raise ValueError("Solo se admiten listas, símbolos, cadenas, números, booleanos y nil.")
        elif isinstance(node, float) and not math.isfinite(node):
            raise ValueError("Los números deben ser finitos.")

    def visit_items(items: list, depth: int) -> None:
        if r.null(items):
            return
        child = r.car(items)
        visit(child, depth + int(isinstance(child, list)))
        visit_items(r.cdr(items), depth)

    visit(value, 1 if isinstance(value, list) else 0)
    if len(to_lisp(value)) > MAX_SOURCE:
        raise ValueError(f"El documento no puede superar {MAX_SOURCE} caracteres.")


def parse(source: str, *, root_list: bool = True) -> Value:
    """Lee una expresión de datos; jamás ejecuta código ni utiliza eval."""
    if len(source) > MAX_SOURCE:
        raise ValueError(f"El documento no puede superar {MAX_SOURCE} caracteres.")
    pos, count = 0, 0
    decoder = json.JSONDecoder()

    def whitespace() -> None:
        nonlocal pos
        while pos < len(source):
            if source[pos].isspace():
                pos += 1
            elif source[pos] == ";":
                end = source.find("\n", pos)
                pos = len(source) if end < 0 else end + 1
            else:
                break

    def expression(depth: int) -> Value:
        nonlocal pos, count
        whitespace()
        count += 1
        if count > MAX_NODES:
            raise ValueError(f"El límite visual es de {MAX_NODES} nodos.")
        if pos >= len(source):
            raise ValueError("Falta una expresión o un paréntesis de cierre.")
        char = source[pos]
        if char == "(":
            if depth >= MAX_DEPTH:
                raise ValueError(f"El límite es de {MAX_DEPTH} niveles de listas.")
            pos += 1
            return sequence(depth + 1)
        if char == ")":
            raise ValueError(f"Paréntesis de cierre inesperado en la posición {pos + 1}.")
        if char == '"':
            try:
                value, consumed = decoder.raw_decode(source[pos:])
            except json.JSONDecodeError as exc:
                raise ValueError("Cadena inválida: usa comillas dobles y escapes JSON.") from exc
            pos += consumed
            if pos < len(source) and not (source[pos].isspace() or source[pos] in ");"):
                raise ValueError("Separa los elementos con espacios.")
            return value
        start = pos
        while pos < len(source) and not source[pos].isspace() and source[pos] not in "();":
            pos += 1
        token = source[start:pos]
        if token == "nil":
            return None
        if token in ("#t", "#f"):
            return token == "#t"
        if INTEGER.fullmatch(token):
            return int(token)
        if NUMBER.fullmatch(token):
            return float(token)
        if not SYMBOL.fullmatch(token):
            raise ValueError("Símbolo inválido. Usa comillas dobles para cadenas de texto.")
        return Symbol(token)

    def sequence(depth: int) -> list:
        nonlocal pos
        whitespace()
        if pos >= len(source):
            raise ValueError("Falta un paréntesis de cierre: ).")
        if source[pos] == ")":
            pos += 1
            return []
        head = expression(depth)
        return r.cons(head, sequence(depth))

    whitespace()
    # Se acepta una comilla inicial como notación de datos, sin evaluar quote.
    if pos < len(source) and source[pos] == "'":
        pos += 1
    result = expression(0)
    whitespace()
    if pos != len(source):
        raise ValueError(f"Hay contenido extra en la posición {pos + 1}. Escribe una sola expresión.")
    validate(result, root_list=root_list)
    return result


def to_lisp(value: Value) -> str:
    if isinstance(value, list):
        return "(" + _lisp_items(value) + ")"
    if isinstance(value, Symbol):
        return str(value)
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "#t" if value else "#f"
    return json.dumps(value, ensure_ascii=False)


def _lisp_items(items: list) -> str:
    if r.null(items):
        return ""
    head = to_lisp(r.car(items))
    tail = r.cdr(items)
    return head if r.null(tail) else head + " " + _lisp_items(tail)


def at(data: list, path: list[int]) -> Value:
    return r.at(data, path)


def replace(data: list, path: list[int], value: Value) -> list:
    result = r.replace_path(data, path, value)
    validate(result)
    return result


def append(data: list, path: list[int], value: Value) -> list:
    target = at(data, path)
    if not isinstance(target, list):
        raise ValueError("Selecciona una lista para añadir elementos.")
    return replace(data, path, r.concat(target, r.cons(value, [])))


def remove(data: list, path: list[int]) -> list:
    result = r.remove_path(data, path)
    validate(result)
    return result


def flatten(value: list) -> list:
    return r.flatten(value)


def operation(name: str, target: Value, argument: Value = None) -> Value:
    if name == "atom":
        return r.atom(target)
    if name == "null":
        return r.null(target)
    if name == "eq":
        return r.eq(target, argument)
    if not isinstance(target, list):
        raise ValueError("Esta operación necesita una lista seleccionada.")
    if name == "car":
        result = r.car(target)
    elif name == "cdr":
        result = r.cdr(target)
    elif name == "cons":
        result = r.cons(argument, target)
    elif name == "reverse":
        result = r.reverse(target)
    elif name == "flatten":
        result = flatten(target)
    elif name == "length":
        result = r.length(target)
    else:
        raise ValueError("Operación desconocida.")
    return r.copy_value(result)


def stats(value: Value) -> list[int]:
    """[cantidad de listas, cantidad de átomos, niveles de listas]."""
    return r.stats(value)


def generate(levels: int, mode: str = "lineal") -> list:
    if mode == "lineal":
        result = r.crear_lista_lineal(levels)
    elif mode == "ramificada":
        result = r.crear_lista_ramificada(levels)
    else:
        raise ValueError("Elige un generador lineal o ramificado.")
    validate(result)
    return result


# El catálogo también utiliza una lista de listas: [título, descripción, datos].
EXAMPLES = [
    ["Primeros pasos", "Átomos y sublistas · 3 niveles", parse('(1 (2 3) (4 (5 6)) "hola")')],
    ["Matriz 3 × 3", "Una lista de filas · 2 niveles", parse("((1 2 3) (4 5 6) (7 8 9))")],
    ["Árbol de categorías", "Clasificar con listas · 3 niveles", parse('(vida (plantas (árboles pino roble) flores) (animales gato perro))')],
    ["Código como datos", "Una expresión simbólica · 2 niveles", parse("(define (cuadrado x) (* x x))")],
    ["Listas vacías", "El vacío también es una lista", parse("(() (1 ()) ((2) ()) nil)")],
    ["Seis niveles", "Explora una estructura profunda", generate(6)],
]


class Document:
    """Historial de instantáneas de listas para deshacer y rehacer."""

    def __init__(self, data: list):
        validate(data)
        self.data = r.copy_value(data)
        self.undo_stack: list[list] = []
        self.redo_stack: list[list] = []

    def commit(self, data: list) -> None:
        validate(data)
        self.undo_stack = r.cons(self.data, r.take(self.undo_stack, 49))
        self.redo_stack = []
        self.data = r.copy_value(data)

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.redo_stack = r.cons(self.data, self.redo_stack)
        self.data = r.car(self.undo_stack)
        self.undo_stack = r.cdr(self.undo_stack)
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        self.undo_stack = r.cons(self.data, self.undo_stack)
        self.data = r.car(self.redo_stack)
        self.redo_stack = r.cdr(self.redo_stack)
        return True
