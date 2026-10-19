"""Modelo sin Qt: los datos son listas de Python, nunca nodos de un árbol.

Las rutas también son listas: [1, 2] accede a data[1][2]. El árbol gráfico
es una proyección descartable de estos datos, no su representación principal.
"""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from typing import Union


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
            for child in node:
                visit(child, depth + int(isinstance(child, list)))
        elif isinstance(node, Symbol):
            if not SYMBOL.fullmatch(node) or node in {"nil", "#t", "#f"} or NUMBER.fullmatch(node):
                raise ValueError("Símbolo no válido.")
        elif node is not None and type(node) not in (str, int, float, bool):
            raise ValueError("Solo se admiten listas, símbolos, cadenas, números, booleanos y nil.")
        elif isinstance(node, float) and not math.isfinite(node):
            raise ValueError("Los números deben ser finitos.")

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
            result = []
            while True:
                whitespace()
                if pos >= len(source):
                    raise ValueError("Falta un paréntesis de cierre: ).")
                if source[pos] == ")":
                    pos += 1
                    return result
                result.append(expression(depth + 1))
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
        return "(" + " ".join(to_lisp(child) for child in value) + ")"
    if isinstance(value, Symbol):
        return str(value)
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "#t" if value else "#f"
    return json.dumps(value, ensure_ascii=False)


def at(data: list, path: list[int]) -> Value:
    value = data
    for index in path:
        if not isinstance(value, list) or not 0 <= index < len(value):
            raise ValueError("La ruta seleccionada ya no existe.")
        value = value[index]
    return value


def replace(data: list, path: list[int], value: Value) -> list:
    at(data, path)
    result = deepcopy(data)
    if path:
        at(result, path[:-1])[path[-1]] = deepcopy(value)
    else:
        result = deepcopy(value)
    validate(result)
    return result


def append(data: list, path: list[int], value: Value) -> list:
    target = at(data, path)
    if not isinstance(target, list):
        raise ValueError("Selecciona una lista para añadir elementos.")
    return replace(data, path, target + [deepcopy(value)])


def remove(data: list, path: list[int]) -> list:
    if not path:
        raise ValueError("La raíz no se elimina. Puedes sustituirla por ().")
    at(data, path)
    parent = at(data, path[:-1])
    return replace(data, path[:-1], parent[:path[-1]] + parent[path[-1] + 1:])


def flatten(value: list) -> list:
    result = []
    for child in value:
        if isinstance(child, list):
            result.extend(flatten(child))
        else:
            result.append(child)
    return result


def operation(name: str, target: Value, argument: Value = None) -> Value:
    if not isinstance(target, list):
        raise ValueError("Esta operación necesita una lista seleccionada.")
    if name == "car":
        result = target[0] if target else []
    elif name == "cdr":
        result = target[1:]
    elif name == "cons":
        result = [argument] + target
    elif name == "reverse":
        result = target[::-1]
    elif name == "flatten":
        result = flatten(target)
    else:
        raise ValueError("Operación desconocida.")
    return deepcopy(result)


def stats(value: Value) -> list[int]:
    """[cantidad de listas, cantidad de átomos, niveles de listas]."""
    if not isinstance(value, list):
        return [0, 1, 0]
    children = [stats(child) for child in value]
    return [1 + sum(s[0] for s in children), sum(s[1] for s in children),
            1 + max((s[2] for s in children), default=0)]


def generate(levels: int) -> list:
    if not 1 <= levels <= 6:
        raise ValueError("El generador admite entre 1 y 6 niveles.")
    result = [1, 2, 3]
    for level in range(2, levels + 1):
        result = [Symbol(f"nivel-{levels - level + 1}"), result, [level, level * 10]]
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
        self.data = deepcopy(data)
        self.undo_stack: list[list] = []
        self.redo_stack: list[list] = []

    def commit(self, data: list) -> None:
        validate(data)
        self.undo_stack.append(deepcopy(self.data))
        self.undo_stack = self.undo_stack[-50:]
        self.redo_stack.clear()
        self.data = deepcopy(data)

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.redo_stack.append(self.data)
        self.data = self.undo_stack.pop()
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        self.undo_stack.append(self.data)
        self.data = self.redo_stack.pop()
        return True
