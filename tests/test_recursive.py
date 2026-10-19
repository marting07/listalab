"""Comprueba resultados y las restricciones del ejercicio de recursividad."""

import ast
from pathlib import Path

import pytest

from listalab import model as m
from listalab import recursive as r


def test_core_has_no_libraries_loops_comprehensions_or_list_utilities():
    tree = ast.parse(Path(r.__file__).read_text(encoding="utf-8"))
    forbidden = (ast.Import, ast.ImportFrom, ast.For, ast.While, ast.AsyncFor,
                 ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.Slice)
    assert not any(isinstance(node, forbidden) for node in ast.walk(tree))
    forbidden_calls = {"len", "sum", "max", "min", "map", "filter", "reversed", "sorted",
                       "list", "deepcopy", "copy", "eval", "exec", "__import__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            assert not isinstance(node.func, ast.Attribute), "No métodos ni utilidades de objetos"
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    for name in ("crear_lista_lineal", "crear_lista_ramificada"):
        assert any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                   and node.func.id == name for node in ast.walk(functions[name]))


@pytest.mark.parametrize("value,expected", [(7, True), ("hola", True), (None, True),
                                           (False, True), ([], False), ([[1]], False)])
def test_atom_distinguishes_atomic_values_from_lists(value, expected):
    assert r.atom(value) is expected
    assert m.operation("atom", value) is expected


@pytest.mark.parametrize("value,expected", [([], True), (None, True), ([[]], False),
                                           (0, False), (False, False), ("", False)])
def test_null_distinguishes_empty_from_false_or_zero(value, expected):
    assert m.operation("null", value) is expected


def test_eq_is_atomic_and_preserves_types():
    assert m.operation("eq", 7, 7) is True
    assert m.operation("eq", 7, "7") is False
    assert m.operation("eq", 1, True) is False
    assert m.operation("eq", m.Symbol("a"), "a") is False
    assert m.operation("eq", m.Symbol("a"), m.Symbol("a")) is True
    assert m.operation("eq", None, None) is True
    with pytest.raises(ValueError, match="átomos"):
        m.operation("eq", [], [])


def test_primitives_empty_cases_and_no_mutation():
    items = [1, [2, 3]]
    assert r.car(items) == 1
    assert r.cdr(items) == [[2, 3]]
    assert r.cons(0, items) == [0, 1, [2, 3]]
    assert r.car([]) == []
    assert r.cdr([]) == []
    assert items == [1, [2, 3]]
    with pytest.raises(ValueError):
        r.cons(1, 2)
    for fn in (r.car, r.cdr, r.length, r.reverse, r.flatten):
        with pytest.raises(ValueError):
            fn(7)


def test_two_generators_have_distinct_recursive_structures():
    assert r.crear_lista_lineal(1) == [1]
    assert r.crear_lista_lineal(3) == [1, [2, [3]]]
    assert r.crear_lista_ramificada(1) == [1]
    assert r.crear_lista_ramificada(3) == [1, [2, [4], [5]], [3, [6], [7]]]
    for levels in range(1, 7):
        assert r.stats(m.generate(levels, "lineal")) == [levels, levels, levels]
        nodes = 2 ** levels - 1
        assert r.stats(m.generate(levels, "ramificada")) == [nodes, nodes, levels]
    branched = r.crear_lista_ramificada(3)
    branched[1][1].append(99)
    assert branched[2] == [3, [6], [7]]


@pytest.mark.parametrize("levels", [0, -1, 7, 1.5, "3", True])
def test_generators_reject_invalid_levels(levels):
    for fn in (r.crear_lista_lineal, r.crear_lista_ramificada):
        with pytest.raises(ValueError):
            fn(levels)


def test_recursive_copy_concat_length_and_order():
    data = [1, [2, [3]], [], None]
    copied = r.copy_value(data)
    copied[1][1].append(99)
    assert data == [1, [2, [3]], [], None]
    assert r.concat([1, [2]], [3]) == [1, [2], 3]
    assert r.length(data) == 4
    assert m.operation("length", data) == 4
    assert r.length([]) == 0
    assert r.reverse(data) == [None, [], [2, [3]], 1]
    assert r.flatten(data) == [1, 2, 3, None]
    assert r.stats(data) == [4, 4, 3]


def test_full_visual_limit_works_with_recursive_algorithms():
    data = m.parse("(" + "1 " * 499 + ")")
    assert r.length(data) == 499
    assert r.stats(data) == [1, 499, 1]
    assert r.reverse(data) == data
    assert r.flatten(data) == data
    doc = m.Document(data)
    with pytest.raises(ValueError, match="500"):
        m.replace(data, [498], [2])
    doc.commit(m.replace(data, [498], 2))
    assert doc.undo() and doc.data == data
    assert m.parse(m.to_lisp(doc.data)) == data


def test_history_limit_is_still_fifty_snapshots():
    doc = m.Document([0])
    for value in range(1, 56):
        doc.commit([value])
    assert r.length(doc.undo_stack) == 50
    for _ in range(50):
        assert doc.undo()
    assert doc.data == [5]
    assert not doc.undo()
    for _ in range(50):
        assert doc.redo()
    assert doc.data == [55]
