"""Interfaz de ListaLab. Ejecuta con python -m listalab."""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path
from pprint import pformat

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont, QKeySequence, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QPlainTextEdit,
    QLineEdit, QComboBox, QSpinBox, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QFileDialog, QMessageBox, QAbstractItemView, QScrollArea,
)

from . import model as m
from .diagram import Diagram, COLORS
from .style import STYLE


def label(text, name=None):
    widget = QLabel(text)
    widget.setWordWrap(True)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    if primary:
        widget.setObjectName("primary")
    widget.clicked.connect(callback)
    return widget


def card():
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(9)
    return frame, layout


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ListaLab · Laboratorio de listas anidadas")
        self.resize(1440, 920)
        self.setMinimumSize(1080, 720)
        self.doc = m.Document(m.EXAMPLES[0][2])
        self.saved_source = m.to_lisp(self.doc.data)
        self.path = []
        self.preview_value = None
        self.has_preview = False
        self.tree_items = []
        self.current_title = "Primeros pasos"
        self._build_ui()
        self._build_menu()
        self._refresh()
        self.examples.blockSignals(True)
        self.examples.setCurrentRow(0)
        self.examples.blockSignals(False)
        QTimer.singleShot(0, self.diagram.fit)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(16, 16, 16, 12)
        outer.setSpacing(18)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(226)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(17, 23, 17, 18)
        side.setSpacing(12)
        side.addWidget(label("( ListaLab )", "brand"))
        side.addWidget(label("PIENSA EN LISTAS\nExplora. Anida. Aprende."))
        side.addSpacing(20)
        side.addWidget(label("EJEMPLOS PARA EXPLORAR"))
        self.examples = QListWidget()
        for title, description, _ in m.EXAMPLES:
            self.examples.addItem(title)
            self.examples.item(self.examples.count() - 1).setToolTip(description)
        self.examples.currentRowChanged.connect(self.load_example)
        side.addWidget(self.examples, 1)
        side.addWidget(label("CREA MÁS NIVELES"))
        generator = QHBoxLayout()
        self.levels = QSpinBox()
        self.levels.setRange(1, 6)
        self.levels.setValue(4)
        self.levels.setSuffix(" niveles")
        self.levels.setAccessibleName("Número de niveles del generador")
        generator.addWidget(self.levels)
        generator.addWidget(button("Crear", self.generate))
        side.addLayout(generator)
        side.addSpacing(12)
        side.addWidget(button("Abrir .lisp", self.open_file))
        side.addWidget(button("Guardar .lisp", self.save_file))
        side.addSpacing(12)
        side.addWidget(label("Python + PySide6\nLos datos son listas de listas."))
        outer.addWidget(sidebar)

        body = QVBoxLayout()
        body.setSpacing(12)
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label("LABORATORIO INTERACTIVO / 01", "eyebrow"))
        titles.addWidget(label("Una lista dentro de otra.", "heading"))
        titles.addWidget(label("Haz clic en un nodo para descubrir su ruta y transformar sus datos.", "muted"))
        head.addLayout(titles, 1)
        self.undo_button = button("↶ Deshacer", self.undo)
        self.redo_button = button("↷ Rehacer", self.redo)
        head.addWidget(self.undo_button)
        head.addWidget(self.redo_button)
        body.addLayout(head)

        metrics = QHBoxLayout()
        self.metrics = []
        for caption in ("LISTAS", "ÁTOMOS", "NIVELES"):
            frame, layout = card()
            row = QHBoxLayout()
            metric = label("0", "metric")
            self.metrics.append(metric)
            row.addWidget(metric)
            row.addWidget(label(caption, "section"))
            row.addStretch()
            layout.addLayout(row)
            metrics.addWidget(frame)
        body.addLayout(metrics)

        source_card, source_layout = card()
        source_head = QHBoxLayout()
        self.source_title = label("EXPRESIÓN LISP", "section")
        source_head.addWidget(self.source_title, 1)
        source_head.addWidget(button("Visualizar  ·  Ctrl+Enter", self.apply_source, True))
        source_layout.addLayout(source_head)
        self.source = QPlainTextEdit()
        self.source.setAccessibleName("Editor de la lista en notación Lisp")
        self.source.setFixedHeight(76)
        self.source.setPlaceholderText('(1 (2 3) (4 (5 6)) "hola")')
        self.source.textChanged.connect(self._source_changed)
        source_layout.addWidget(self.source)
        self.error = label("Paréntesis = lista · espacios = elementos · comillas dobles = texto", "muted")
        source_layout.addWidget(self.error)
        body.addWidget(source_card)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        viz = QWidget()
        viz_layout = QVBoxLayout(viz)
        viz_layout.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.context_title = label(self.current_title, "section")
        bar.addWidget(self.context_title, 1)
        bar.addWidget(button("−", lambda: self.diagram.zoom(1 / 1.2)))
        bar.addWidget(button("+", lambda: self.diagram.zoom(1.2)))
        bar.addWidget(button("Ajustar", lambda: self.diagram.fit()))
        viz_layout.addLayout(bar)
        self.tabs = QTabWidget()
        self.diagram = Diagram()
        self.diagram.selected.connect(self.select)
        self.tabs.addTab(self.diagram, "Árbol visual")
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Estructura", "Valor / elementos"])
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.currentItemChanged.connect(self._tree_selected)
        self.tabs.addTab(self.tree, "Listas por niveles")
        self.python_view = QPlainTextEdit()
        self.python_view.setReadOnly(True)
        self.python_view.setAccessibleName("Representación de las listas de Python")
        self.tabs.addTab(self.python_view, "Python")
        viz_layout.addWidget(self.tabs, 1)
        viz_layout.addWidget(label("Arrastra para desplazarte · Ctrl + rueda para acercar · cada color indica un nivel", "muted"))
        splitter.addWidget(viz)

        inspector_scroll = QScrollArea()
        inspector_scroll.setWidgetResizable(True)
        inspector_scroll.setFrameShape(QFrame.Shape.NoFrame)
        inspector_scroll.setMinimumWidth(275)
        inspector = QWidget()
        inspector_scroll.setWidget(inspector)
        panel = QVBoxLayout(inspector)
        panel.setContentsMargins(4, 0, 0, 0)
        panel.setSpacing(10)
        edit_card, edit = card()
        edit.addWidget(label("NODO SELECCIONADO", "section"))
        self.path_label = label("raíz")
        self.path_label.setFont(QFont("DejaVu Sans Mono", 11, QFont.Weight.Bold))
        edit.addWidget(self.path_label)
        self.node_info = label("")
        edit.addWidget(self.node_info)
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText('Ej.: 7, "hola" o (a b)')
        self.value_input.setAccessibleName("Valor para editar o añadir")
        edit.addWidget(self.value_input)
        edit.addWidget(label("Valor en notación Lisp.", "muted"))
        edit_row = QHBoxLayout()
        edit_row.addWidget(button("Reemplazar", self.replace_node))
        self.add_button = button("Añadir", self.append_node)
        self.add_button.setToolTip("Añadir el valor al final de la lista seleccionada")
        edit_row.addWidget(self.add_button)
        edit.addLayout(edit_row)
        row = QHBoxLayout()
        row.addWidget(button("Anidar", self.wrap_node))
        self.remove_button = button("Eliminar", self.remove_node)
        self.remove_button.setObjectName("danger")
        row.addWidget(self.remove_button)
        edit.addLayout(row)
        panel.addWidget(edit_card)

        op_card, op = card()
        op.addWidget(label("OPERACIONES SOBRE LISTAS", "section"))
        self.op_combo = QComboBox()
        for title, code in [["car · primer elemento", "car"], ["cdr · resto de la lista", "cdr"],
                            ["cons · insertar al inicio", "cons"], ["reverse · invertir", "reverse"],
                            ["flatten · aplanar", "flatten"]]:
            self.op_combo.addItem(title, code)
        self.op_combo.currentIndexChanged.connect(self._operation_changed)
        op.addWidget(self.op_combo)
        self.argument = QLineEdit("0")
        self.argument.setAccessibleName("Elemento que cons insertará al inicio")
        self.argument.textChanged.connect(self._clear_preview)
        op.addWidget(self.argument)
        self.argument.hide()
        self.preview_button = button("Calcular resultado", self.preview)
        op.addWidget(self.preview_button)
        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        self.result.setFixedHeight(60)
        self.result.setPlaceholderText("Aquí aparecerá el resultado.")
        self.result.setAccessibleName("Resultado de la operación")
        op.addWidget(self.result)
        self.apply_result_button = button("Aplicar al nodo", self.apply_result, True)
        self.apply_result_button.setEnabled(False)
        op.addWidget(self.apply_result_button)
        self.operation_hint = label("car obtiene el primer elemento de la lista.", "muted")
        op.addWidget(self.operation_hint)
        panel.addWidget(op_card)
        panel.addStretch()
        splitter.addWidget(inspector_scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([700, 285])
        body.addWidget(splitter, 1)
        outer.addLayout(body, 1)
        self.statusBar().showMessage("Todo empieza con una lista. Selecciona un ejemplo para explorar.")

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("Archivo")
        edit_menu = self.menuBar().addMenu("Editar")
        help_menu = self.menuBar().addMenu("Ayuda")
        entries = [
            [file_menu, "Abrir…", "Ctrl+O", self.open_file],
            [file_menu, "Guardar como…", "Ctrl+S", self.save_file],
            [edit_menu, "Visualizar expresión", "Ctrl+Return", self.apply_source],
            [edit_menu, "Deshacer cambio de datos", "Ctrl+Alt+Z", self.undo],
            [edit_menu, "Rehacer cambio de datos", "Ctrl+Alt+Y", self.redo],
            [help_menu, "Guía rápida", "F1", self.help],
        ]
        for menu, text, shortcut, callback in entries:
            action = QAction(text, self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(callback)
            menu.addAction(action)

    def _source_changed(self):
        dirty = self.source.toPlainText() != m.to_lisp(self.doc.data)
        self.source_title.setText("EXPRESIÓN LISP · CAMBIOS SIN VISUALIZAR" if dirty else "EXPRESIÓN LISP")

    def _clean(self):
        if self.source.toPlainText() != m.to_lisp(self.doc.data):
            raise ValueError("Hay cambios en el editor. Pulsa Visualizar antes de continuar.")

    def _run(self, task):
        try:
            task()
        except (ValueError, OSError, UnicodeError, RecursionError) as exc:
            self.error.setText(str(exc))
            self.error.setStyleSheet("color: #ac444d;")
            self.statusBar().showMessage(str(exc))

    def _commit(self, data, message, path=None):
        self.doc.commit(data)
        self.path = path if path is not None else self.path
        try:
            m.at(self.doc.data, self.path)
        except ValueError:
            self.path = []
        self._refresh()
        self.statusBar().showMessage(message)

    def _refresh(self):
        self.source.setPlainText(m.to_lisp(self.doc.data))
        self.error.setText("Paréntesis = lista · espacios = elementos · comillas dobles = texto")
        self.error.setStyleSheet("")
        for metric, value in zip(self.metrics, m.stats(self.doc.data)):
            metric.setText(str(value))
        self.context_title.setText(self.current_title.upper())
        self.undo_button.setEnabled(bool(self.doc.undo_stack))
        self.redo_button.setEnabled(bool(self.doc.redo_stack))
        self.diagram.render_data(self.doc.data)
        self._populate_tree()
        self.python_view.setPlainText(pformat(self.doc.data, width=60, sort_dicts=False))
        self.select(self.path)
        QTimer.singleShot(0, self.diagram.fit)

    def _populate_tree(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        self.tree_items.clear()

        def add(value, path, parent):
            title = "raíz" if not path else f"[{path[-1]}]"
            text = f"Lista de {len(value)} elementos" if isinstance(value, list) else m.to_lisp(value)
            item = QTreeWidgetItem([title, text])
            item.setData(0, Qt.ItemDataRole.UserRole, path[:])
            item.setForeground(0, QColor(COLORS[len(path) % len(COLORS)]))
            item.setToolTip(1, m.to_lisp(value))
            parent.addChild(item) if parent is not None else self.tree.addTopLevelItem(item)
            self.tree_items.append(item)
            if isinstance(value, list):
                for index, child in enumerate(value):
                    add(child, path + [index], item)

        add(self.doc.data, [], None)
        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)
        self.tree.blockSignals(False)

    def _tree_selected(self, item, previous):
        if item:
            self.select(item.data(0, Qt.ItemDataRole.UserRole))

    def select(self, path):
        self.path = path[:]
        value = m.at(self.doc.data, path)
        self.path_label.setText("data" + "".join(f"[{i}]" for i in path))
        self.node_info.setText(f"Lista · {len(value)} elementos" if isinstance(value, list) else f"Átomo · {type(value).__name__}")
        self.value_input.setText(m.to_lisp(value))
        self.value_input.setCursorPosition(0)
        self.add_button.setEnabled(isinstance(value, list))
        self.remove_button.setEnabled(bool(path))
        self.preview_button.setEnabled(isinstance(value, list))
        self.diagram.select_path(path)
        self.tree.blockSignals(True)
        for item in self.tree_items:
            if item.data(0, Qt.ItemDataRole.UserRole) == path:
                self.tree.setCurrentItem(item)
                break
        self.tree.blockSignals(False)
        self._clear_preview()

    def apply_source(self):
        def task():
            data = m.parse(self.source.toPlainText())
            self.current_title = "Tu lista"
            self._commit(data, "Expresión visualizada. Los datos son listas de Python.", [])
        self._run(task)

    def load_example(self, index):
        if index < 0:
            return
        def task():
            self._clean()
            self.current_title = m.EXAMPLES[index][0]
            self._commit(deepcopy(m.EXAMPLES[index][2]), m.EXAMPLES[index][1], [])
        self._run(task)

    def generate(self):
        def task():
            self._clean()
            self.current_title = f"Lista generada · {self.levels.value()} niveles"
            self._commit(m.generate(self.levels.value()), "Nueva lista creada. Explora cada nivel.", [])
        self._run(task)

    def replace_node(self):
        def task():
            self._clean()
            value = m.parse(self.value_input.text(), root_list=not self.path)
            self._commit(m.replace(self.doc.data, self.path, value), "Nodo reemplazado.")
        self._run(task)

    def append_node(self):
        def task():
            self._clean()
            value = m.parse(self.value_input.text(), root_list=False)
            data = m.append(self.doc.data, self.path, value)
            self._commit(data, "Elemento añadido al final de la lista.")
        self._run(task)

    def wrap_node(self):
        def task():
            self._clean()
            value = m.at(self.doc.data, self.path)
            self._commit(m.replace(self.doc.data, self.path, [value]), "Nodo envuelto en una nueva lista.")
        self._run(task)

    def remove_node(self):
        def task():
            self._clean()
            data = m.remove(self.doc.data, self.path)
            self._commit(data, "Nodo eliminado. Puedes deshacer este cambio.", self.path[:-1])
        self._run(task)

    def _clear_preview(self, *_):
        self.has_preview = False
        self.result.clear()
        self.apply_result_button.setEnabled(False)

    def _operation_changed(self, *_):
        code = self.op_combo.currentData()
        self.argument.setVisible(code == "cons")
        hints = {
            "car": "Obtiene el primer elemento. En una lista vacía devuelve ().",
            "cdr": "Obtiene una lista con todos los elementos excepto el primero.",
            "cons": "Inserta el argumento como un solo elemento al principio.",
            "reverse": "Invierte el orden del nivel seleccionado, conservando las sublistas.",
            "flatten": "Recorre todas las sublistas y reúne sus átomos en una lista plana.",
        }
        self.operation_hint.setText(hints[code])
        self._clear_preview()

    def preview(self):
        def task():
            self._clean()
            code = self.op_combo.currentData()
            target = m.at(self.doc.data, self.path)
            argument = m.parse(self.argument.text(), root_list=False) if code == "cons" else None
            result = m.operation(code, target, argument)
            m.validate(result, root_list=False)
            self.preview_value = result
            self.has_preview = True
            self.result.setPlainText(m.to_lisp(result))
            can_apply = bool(self.path) or isinstance(result, list)
            self.apply_result_button.setEnabled(can_apply)
            self.statusBar().showMessage(f"{code} calculado. Pulsa Aplicar al nodo para guardar el cambio." if can_apply else "El resultado es un átomo. La raíz debe conservarse como lista.")
        self._clear_preview()
        self._run(task)

    def apply_result(self):
        def task():
            self._clean()
            if self.has_preview:
                self._commit(m.replace(self.doc.data, self.path, self.preview_value), "Resultado aplicado al nodo seleccionado.")
        self._run(task)

    def undo(self):
        def task():
            self._clean()
            if self.doc.undo():
                self.path = []
                self._refresh()
                self.statusBar().showMessage("Cambio de datos deshecho.")
        self._run(task)

    def redo(self):
        def task():
            self._clean()
            if self.doc.redo():
                self.path = []
                self._refresh()
                self.statusBar().showMessage("Cambio de datos rehecho.")
        self._run(task)

    def open_file(self):
        def task():
            self._clean()
            filename, _ = QFileDialog.getOpenFileName(self, "Abrir lista", "", "Listas Lisp (*.lisp *.lsp);;Texto (*.txt)")
            if filename:
                with Path(filename).open(encoding="utf-8") as stream:
                    source = stream.read(m.MAX_SOURCE + 1)
                data = m.parse(source)
                self.current_title = Path(filename).name
                self._commit(data, f"Lista abierta: {filename}", [])
                self.saved_source = m.to_lisp(data)
        self._run(task)

    def save_file(self):
        def task():
            self._clean()
            filename, _ = QFileDialog.getSaveFileName(self, "Guardar lista", "mi-lista.lisp", "Listas Lisp (*.lisp)")
            if filename:
                if not Path(filename).suffix:
                    filename += ".lisp"
                Path(filename).write_text(m.to_lisp(self.doc.data) + "\n", encoding="utf-8")
                self.saved_source = m.to_lisp(self.doc.data)
                self.statusBar().showMessage(f"Lista guardada: {filename}")
        self._run(task)

    def help(self):
        QMessageBox.information(self, "Guía rápida · ListaLab",
            "1. Selecciona un ejemplo o genera entre 1 y 6 niveles.\n"
            "2. Escribe una lista en el editor y pulsa Visualizar.\n"
            "3. Selecciona un nodo en el árbol o en Listas por niveles.\n"
            "4. Reemplaza, añade, anida o elimina elementos.\n"
            "5. Calcula car, cdr, cons, reverse o flatten y aplica el resultado.\n\n"
            "Sintaxis: (1 (2 3) símbolo \"texto\" #t #f nil).\n"
            "Admite comentarios con ; y una comilla inicial opcional.\n"
            "No ejecuta código Lisp. nil y () se representan por separado para aprender.\n"
            "La pestaña Python muestra las listas reales; los símbolos se ven como str.\n\n"
            "Ctrl+O: abrir · Ctrl+S: guardar · Ctrl+Enter: visualizar.\n"
            "Ctrl+Z en un editor deshace texto. Ctrl+Alt+Z deshace datos.\n"
            "Guarda tu trabajo en .lisp antes de cerrar la aplicación.")

    def closeEvent(self, event):
        if (m.to_lisp(self.doc.data) != self.saved_source
                or self.source.toPlainText() != m.to_lisp(self.doc.data)):
            choice = QMessageBox.question(self, "Cerrar ListaLab",
                "¿Cerrar la aplicación? Guarda primero en .lisp si quieres conservar tu lista.",
                QMessageBox.StandardButton.Close | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if choice != QMessageBox.StandardButton.Close:
                event.ignore()
                return
        event.accept()


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("ListaLab")
    app.setOrganizationName("marting07")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
