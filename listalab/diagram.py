"""Proyección de listas en un lienzo Qt; cada elemento conserva su ruta."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QBrush, QPen, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsSimpleTextItem,
)

from .model import to_lisp

COLORS = ["#16856b", "#387bb5", "#8662b8", "#b77b24", "#bd596b", "#458d8a"]


class Node(QGraphicsRectItem):
    def __init__(self, value, path, level, callback):
        super().__init__(0, 0, 142, 62)
        self.path = path[:]
        self.callback = callback
        self.color = QColor(COLORS[level % len(COLORS)])
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setPen(QPen(self.color, 1.5))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{'raíz' if not path else str(path)}\n{to_lisp(value)}")
        title = f"Lista · {len(value)}" if isinstance(value, list) else to_lisp(value)
        if len(title) > 17:
            title = title[:15] + "…"
        label = QGraphicsSimpleTextItem(title, self)
        label.setFont(QFont("DejaVu Sans", 10, QFont.Weight.DemiBold))
        label.setBrush(QBrush(QColor("#213b42")))
        label.setPos(12, 10)
        label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        subtitle = "RAÍZ · NIVEL 1" if not path else f"{''.join(f'[{n}]' for n in path)}  ·  {'LISTA' if isinstance(value, list) else 'ÁTOMO'}"
        if len(subtitle) > 24:
            subtitle = "…" + subtitle[-23:]
        caption = QGraphicsSimpleTextItem(subtitle, self)
        caption.setFont(QFont("DejaVu Sans", 7))
        caption.setBrush(QBrush(self.color))
        caption.setPos(12, 37)
        caption.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback(self.path[:])
        super().mousePressEvent(event)

    def highlight(self, selected):
        self.setPen(QPen(self.color, 3 if selected else 1.5))
        self.setBrush(QBrush(QColor("#e8f5ee") if selected else QColor("#ffffff")))


class Diagram(QGraphicsView):
    selected = Signal(list)

    def __init__(self):
        super().__init__()
        self.canvas = QGraphicsScene(self)
        self.setScene(self.canvas)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor("#f8faf8")))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.nodes = []

    def render_data(self, data):
        self.canvas.clear()
        self.nodes.clear()

        def width(value):
            if not isinstance(value, list) or not value:
                return 164
            return max(164, sum(width(child) for child in value))

        def draw(value, path, x, depth):
            span = width(value)
            center = x + span / 2
            y = depth * 112
            node = Node(value, path, depth, self.selected.emit)
            node.setPos(center - 71, y)
            self.canvas.addItem(node)
            self.nodes.append(node)
            if isinstance(value, list):
                child_x = x
                for i, child in enumerate(value):
                    child_span = width(child)
                    child_center = child_x + child_span / 2
                    line = QPainterPath()
                    line.moveTo(center, y + 62)
                    line.cubicTo(center, y + 90, child_center, y + 84, child_center, y + 112)
                    edge = self.canvas.addPath(line, QPen(QColor("#c8d7d2"), 1.5))
                    edge.setZValue(-1)
                    draw(child, path + [i], child_x, depth + 1)
                    child_x += child_span

        draw(data, [], 0, 0)
        self.canvas.setSceneRect(self.canvas.itemsBoundingRect().adjusted(-35, -35, 35, 35))

    def select_path(self, path):
        for node in self.nodes:
            node.highlight(node.path == path)

    def fit(self):
        self.fitInView(self.canvas.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        if self.transform().m11() > 1.25:
            self.resetTransform()
            self.scale(1.25, 1.25)

    def zoom(self, factor):
        scale = self.transform().m11() * factor
        if 0.003 <= scale <= 3:
            self.scale(factor, factor)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)
            event.accept()
        else:
            super().wheelEvent(event)
