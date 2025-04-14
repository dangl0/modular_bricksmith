# brick_item.py - Brick QGraphicsItem Definition
# Version: 1.4.1

from PyQt5.QtWidgets import QGraphicsRectItem, QMenu
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtCore import QRectF, Qt

GRID_SPACING = 30  # pixels per stud


class BrickItem(QGraphicsRectItem):
    def __init__(self, size=(2, 4), color="#C91A09"):
        width, height = size
        rect = QRectF(0, 0, width * GRID_SPACING, height * GRID_SPACING)
        super().__init__(rect)

        self.size = size
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(Qt.black))

        self.setFlags(
            QGraphicsRectItem.ItemIsSelectable |
            QGraphicsRectItem.ItemIsMovable
        )
        self.setAcceptHoverEvents(True)

    def rotate90(self):
        self.setRotation((self.rotation() + 90) % 360)

    def snap_to_grid(self):
        x = round(self.x() / GRID_SPACING) * GRID_SPACING
        y = round(self.y() / GRID_SPACING) * GRID_SPACING
        self.setPos(x, y)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.snap_to_grid()

    def contextMenuEvent(self, event):
        menu = QMenu()
        rotate_action = menu.addAction("Rotate 90°")
        recolour_action = menu.addAction("Recolour")
        delete_action = menu.addAction("Delete")

        action = menu.exec_(event.screenPos())
        if action == rotate_action:
            self.setTransformOriginPoint(self.boundingRect().center())
            self.rotate90()
            self.snap_to_grid()
        elif action == recolour_action:
            main_window = self.scene().views()[0].window()
            new_color = main_window.current_color
            self.setBrush(QBrush(QColor(new_color)))
        elif action == delete_action:
            self.scene().removeItem(self)
