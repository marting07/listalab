from copy import deepcopy

import pytest

from listalab import model as m


@pytest.mark.parametrize("source", [
    '(1 (2 3) (4 (5 6)) "hola")',
    '(define (cuadrado x) (* x x))',
    '(() (()) nil #t #f -2 1.25 1e3 "áβ\\ntexto")',
    '("a\\\"b" "" símbolo)',
])
def test_parser_roundtrip_keeps_types_and_structure(source):
    data = m.parse(source)
    restored = m.parse(m.to_lisp(data))
    assert restored == data
    assert [type(x) for x in restored] == [type(x) for x in data]
    assert isinstance(data, list)


def test_comments_quote_and_symbol_vs_string():
    value = m.parse("; comentario\n'(hola \"hola\" ; otro\n (2))")
    assert type(value[0]) is m.Symbol
    assert type(value[1]) is str
    assert m.to_lisp(value) == '(hola "hola" (2))'


@pytest.mark.parametrize("source", [
    "", "(1", "(1))", "1", "(1) (2)", '("sin cerrar)',
    "({'a': 1})", "('a)", '("a"b)', "(1e999)", "(" * 13 + ")" * 13,
    "(" + "1 " * 500 + ")", " " * (m.MAX_SOURCE + 1),
])
def test_invalid_data_is_rejected(source):
    with pytest.raises(ValueError):
        m.parse(source)


def test_nested_list_operations_copy_instead_of_mutating():
    original = [1, [2, [3, 4]], [], 5]
    snapshot = deepcopy(original)
    assert m.operation("car", original) == 1
    assert m.operation("cdr", original) == [[2, [3, 4]], [], 5]
    assert m.operation("flatten", original) == [1, 2, 3, 4, 5]
    assert m.operation("reverse", original) == [5, [], [2, [3, 4]], 1]
    argument = [8, 9]
    result = m.operation("cons", original, argument)
    assert result == [[8, 9], 1, [2, [3, 4]], [], 5]
    result[0].append(10)
    result[2][1].append(6)
    assert original == snapshot
    assert argument == [8, 9]


def test_empty_list_semantics_and_atom_rejection():
    assert m.operation("car", []) == []
    assert m.operation("cdr", []) == []
    assert m.operation("cons", [], []) == [[]]
    with pytest.raises(ValueError):
        m.operation("car", 1)


def test_nested_editing_paths_and_unchanged_original():
    data = [1, [2, [3]]]
    assert m.at(data, [1, 1, 0]) == 3
    assert m.replace(data, [1, 1], [4, 5]) == [1, [2, [4, 5]]]
    assert m.append(data, [1], [8]) == [1, [2, [3], [8]]]
    assert m.remove(data, [1, 0]) == [1, [[3]]]
    assert data == [1, [2, [3]]]
    for path in [[-1], [5], [0, 0]]:
        with pytest.raises(ValueError):
            m.at(data, path)
        with pytest.raises(ValueError):
            m.replace(data, path, [9])
        with pytest.raises(ValueError):
            m.remove(data, path)
    with pytest.raises(ValueError):
        m.replace(data, [], 1)
    with pytest.raises(ValueError):
        m.remove(data, [])


def test_document_undo_redo_branching_and_snapshot_isolation():
    initial = [[1], 2]
    doc = m.Document(initial)
    initial[0].append(99)
    doc.commit([[3], 4])
    assert doc.undo() and doc.data == [[1], 2]
    assert doc.redo() and doc.data == [[3], 4]
    assert doc.undo()
    doc.commit([5])
    assert not doc.redo()
    assert doc.undo() and doc.data == [[1], 2]
    assert not doc.undo()


def test_limits_apply_to_edits_too_and_keep_document():
    doc = m.Document(m.parse("(" * 12 + "1" + ")" * 12))
    with pytest.raises(ValueError):
        doc.commit([doc.data])
    assert m.stats(doc.data) == [12, 1, 12]
    assert not doc.undo_stack
    with pytest.raises(ValueError):
        m.validate([float("nan")])


def test_generator_depth_and_examples():
    for levels in range(1, 7):
        value = m.generate(levels)
        assert m.stats(value)[2] == levels
        assert m.parse(m.to_lisp(value)) == value
    for _, _, value in m.EXAMPLES:
        m.validate(value)
