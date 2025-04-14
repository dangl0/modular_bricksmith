from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtGui import QPen, QColor
from PyQt5.QtCore import Qt

STUD_SIZE_MM = 8
GRID_SPACING = 30  # pixels per stud for UI scale


def mm_to_studs(mm):
    return max(1, mm // STUD_SIZE_MM)  # ensure minimum of 1 stud


class GridCanvas(QGraphicsScene):
    def __init__(self, grid_width=50, grid_height=50):
        super().__init__()
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.setSceneRect(0, 0, self.grid_width * GRID_SPACING, self.grid_height * GRID_SPACING)

        # Draw persistent grid border at the outer edge (1 stud beyond)
        self.border_pen = QPen(Qt.black)
        self.border_pen.setWidth(2)
        self.border_rect = self.addRect(
            0, 0,
            (self.grid_width - 1) * GRID_SPACING,
            (self.grid_height - 1) * GRID_SPACING,
            self.border_pen
        )

    def drawBackground(self, painter, rect):
        pen = QPen(QColor(220, 220, 220))
        pen.setWidth(1)
        painter.setPen(pen)

        left = int(rect.left()) - (int(rect.left()) % GRID_SPACING)
        top = int(rect.top()) - (int(rect.top()) % GRID_SPACING)

        for x in range(left, int(rect.right()), GRID_SPACING):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))

        for y in range(top, int(rect.bottom()), GRID_SPACING):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)

    def snap_to_grid(self, x, y):
        return (
            round(x / GRID_SPACING) * GRID_SPACING,
            round(y / GRID_SPACING) * GRID_SPACING
        )

    def resize_grid(self, new_width, new_height):
        self.grid_width = new_width
        self.grid_height = new_height
        self.setSceneRect(0, 0, self.grid_width * GRID_SPACING, self.grid_height * GRID_SPACING)

        # Remove and redraw the border at new size (subtract 1 to keep it 1-stud inside)
        self.removeItem(self.border_rect)
        self.border_rect = self.addRect(
            0, 0,
            (self.grid_width - 1) * GRID_SPACING,
            (self.grid_height - 1) * GRID_SPACING,
            self.border_pen
        )

        self.update()  # Trigger a full redraw
