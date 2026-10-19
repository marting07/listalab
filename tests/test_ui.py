"""Pruebas con widgets y eventos Qt reales; no necesitan una pantalla."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QFileDialog

from listalab import model as m
from listalab.app import MainWindow
from listalab.style import STYLE


@pytest.fixture(scope="session")
def app():
    application = QApplication.instance() or QApplication([])
    application.setStyle("Fusion")
    application.setStyleSheet(STYLE)
    return application


@pytest.fixture
def window(app):
    widget = MainWindow()
    widget.show()
    app.processEvents()
    yield widget
    widget.hide()
    widget.deleteLater()
    app.processEvents()


def click(window, text):
    found = [b for b in window.findChildren(QPushButton) if b.text() == text]
    assert len(found) == 1, text
    QTest.mouseClick(found[0], Qt.MouseButton.LeftButton)
    QApplication.processEvents()


def test_editor_diagram_selection_edit_and_undo(window):
    assert not window.doc.undo_stack
    window.source.setPlainText("((1 2) (3 (4 5)))")
    click(window, "Visualizar  ·  Ctrl+Enter")
    assert window.doc.data == [[1, 2], [3, [4, 5]]]
    node = next(n for n in window.diagram.nodes if n.path == [1, 1])
    point = window.diagram.mapFromScene(node.sceneBoundingRect().center())
    QTest.mouseClick(window.diagram.viewport(), Qt.MouseButton.LeftButton, pos=point)
    assert window.path == [1, 1]
    assert window.path_label.text() == "data[1][1]"
    window.value_input.setText("(8 9)")
    click(window, "Añadir")
    assert window.doc.data == [[1, 2], [3, [4, 5, [8, 9]]]]
    click(window, "↶ Deshacer")
    assert window.doc.data == [[1, 2], [3, [4, 5]]]
    click(window, "↷ Rehacer")
    assert window.doc.data[1][1][-1] == [8, 9]


def test_cons_preview_apply_and_root_atom_guard(window):
    window.source.setPlainText("(1 (2 3))")
    window.apply_source()
    window.op_combo.setCurrentIndex(2)
    window.argument.setText("(a b)")
    click(window, "Calcular resultado")
    assert window.result.toPlainText() == "((a b) 1 (2 3))"
    assert window.doc.data == [1, [2, 3]]
    click(window, "Aplicar al nodo")
    assert window.doc.data[0] == [m.Symbol("a"), m.Symbol("b")]
    window.select([0])
    window.op_combo.setCurrentIndex(0)
    window.preview()
    assert window.apply_result_button.isEnabled()
    window.apply_result()
    assert isinstance(window.doc.data[0], m.Symbol)
    window.select([])
    window.preview()
    assert not window.apply_result_button.isEnabled()


def test_invalid_source_and_dirty_editor_preserve_data(window):
    original = m.to_lisp(window.doc.data)
    window.source.setPlainText("(1 (2)")
    window.apply_source()
    assert m.to_lisp(window.doc.data) == original
    assert "Falta" in window.error.text()
    window.wrap_node()
    assert m.to_lisp(window.doc.data) == original
    assert "Visualizar" in window.error.text()


def test_file_roundtrip_and_import_error(window, tmp_path, monkeypatch):
    target = tmp_path / "lista.lisp"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(target), ""))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(target), ""))
    window.save_file()
    original = window.doc.data[:]
    window.source.setPlainText("()")
    window.apply_source()
    window.open_file()
    assert window.doc.data == original
    target.write_text("(1", encoding="utf-8")
    window.open_file()
    assert window.doc.data == original
    assert "Falta" in window.error.text()


def test_all_examples_and_levels_render(window, app):
    for index in range(len(m.EXAMPLES)):
        window.load_example(index)
        app.processEvents()
        assert window.doc.data == m.EXAMPLES[index][2]
        lists, atoms, _ = m.stats(window.doc.data)
        assert len(window.diagram.nodes) == lists + atoms
        window.tabs.setCurrentIndex(1)
        item = window.tree_items[-1]
        window.tree.setCurrentItem(item)
        assert window.path == item.data(0, Qt.ItemDataRole.UserRole)
    for mode in ("lineal", "ramificada"):
        window.generator_mode.setCurrentIndex(window.generator_mode.findData(mode))
        for level in range(1, 7):
            window.levels.setValue(level)
            click(window, "Crear")
            assert window.doc.data == m.generate(level, mode)
            assert m.stats(window.doc.data)[2] == level


def test_atomic_operations_on_selected_nodes(window):
    window.source.setPlainText('(7 () nil "7")')
    window.apply_source()
    window.select([0])
    for code, expected in [("atom", "#t"), ("null", "#f"), ("eq", "#t")]:
        window.op_combo.setCurrentIndex(window.op_combo.findData(code))
        window.argument.setText("7")
        assert window.preview_button.isEnabled()
        click(window, "Calcular resultado")
        assert window.result.toPlainText() == expected
    window.argument.setText('"7"')
    window.preview()
    assert window.result.toPlainText() == "#f"
    window.select([1])
    window.op_combo.setCurrentIndex(window.op_combo.findData("null"))
    window.preview()
    assert window.result.toPlainText() == "#t"
    window.select([2])
    window.preview()
    assert window.result.toPlainText() == "#t"
    window.select([])
    window.op_combo.setCurrentIndex(window.op_combo.findData("length"))
    window.preview()
    assert window.result.toPlainText() == "4"
    assert not window.apply_result_button.isEnabled()
    window.select([0])
    assert not window.preview_button.isEnabled()
    assert "Caso base" in window.recursion_view.toPlainText()
