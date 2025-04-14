import json
import os
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QLabel, QStatusBar,
    QListWidget, QListWidgetItem, QGraphicsView, QAction, QFileDialog, QApplication,
    QMessageBox, QPushButton, QDialog, QComboBox, QDialogButtonBox, QFormLayout, QSpinBox,
    QButtonGroup, QRadioButton, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCursor, QColor, QBrush, QFont
from grid_canvas import GridCanvas, mm_to_studs, STUD_SIZE_MM
from brick_item import BrickItem
from file_handler import save_layout, load_layout
from PIL import Image
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QGraphicsPixmapItem
from PyQt5.QtWidgets import QSlider, QLabel, QHBoxLayout
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QPainter
from utils import get_resource_path

APP_VERSION = "1.8.12"

class GridSizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Layout")

        layout = QFormLayout()
        self.combo = QComboBox()
        self.combo.setFont(QFont("Arial", 12))
        self.sizes = {
            "48x48 (default)": (48, 48),
            "32x32": (32, 32),
            "16x16": (16, 16),
            "8x16": (8, 16),
            "8x8": (8, 8),
            "Custom (mm input)": None
        }
        self.combo.addItems(self.sizes.keys())
        self.combo.currentTextChanged.connect(self.toggle_mm_inputs)
        layout.addRow("Baseplate preset:", self.combo)

        self.width_mm = QSpinBox()
        self.width_mm.setRange(8, 2048)
        self.width_mm.setValue(384)

        self.height_mm = QSpinBox()
        self.height_mm.setRange(8, 2048)
        self.height_mm.setValue(384)

        layout.addRow("Custom Width (mm):", self.width_mm)
        layout.addRow("Custom Height (mm):", self.height_mm)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.setMinimumWidth(300)

        self.toggle_mm_inputs(self.combo.currentText())

    def toggle_mm_inputs(self, text):
        is_custom = "Custom" in text
        self.width_mm.setEnabled(is_custom)
        self.height_mm.setEnabled(is_custom)

    def get_size(self):
        selected = self.combo.currentText()
        if "Custom" in selected:
            width_mm = self.width_mm.value()
            height_mm = self.height_mm.value()
            return mm_to_studs(width_mm), mm_to_studs(height_mm)
        else:
            return self.sizes[selected]


class ResizeGridDialog(QDialog):
    def __init__(self, current_width_studs, current_height_studs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resize Grid")
        layout = QFormLayout()

        self.unit_group = QButtonGroup(self)
        self.radio_mm = QRadioButton("Millimetres (mm)")
        self.radio_studs = QRadioButton("Studs")
        self.radio_mm.setChecked(True)
        self.unit_group.addButton(self.radio_mm)
        self.unit_group.addButton(self.radio_studs)
        unit_layout = QHBoxLayout()
        unit_layout.addWidget(self.radio_mm)
        unit_layout.addWidget(self.radio_studs)
        layout.addRow("Unit:", unit_layout)

        self.width_mm = QSpinBox()
        self.width_mm.setRange(8, 2048)
        self.width_mm.setValue(current_width_studs * STUD_SIZE_MM)
        self.height_mm = QSpinBox()
        self.height_mm.setRange(8, 2048)
        self.height_mm.setValue(current_height_studs * STUD_SIZE_MM)

        self.width_studs = QSpinBox()
        self.width_studs.setRange(1, 256)
        self.width_studs.setValue(current_width_studs)
        self.height_studs = QSpinBox()
        self.height_studs.setRange(1, 256)
        self.height_studs.setValue(current_height_studs)

        layout.addRow("Width (mm):", self.width_mm)
        layout.addRow("Height (mm):", self.height_mm)
        layout.addRow("Width (studs):", self.width_studs)
        layout.addRow("Height (studs):", self.height_studs)

        self.radio_mm.toggled.connect(self.toggle_fields)
        self.toggle_fields()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        # Add just before buttons.accepted.connect(...)
        warning_label = QLabel("⚠️ Resizing trims from the bottom and right edges.\nBricks outside the new area may be lost.")
        warning_label.setStyleSheet("color: orange; font-size: 10pt;")
        layout.addRow(warning_label)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.setMinimumWidth(320)

    def toggle_fields(self):
        use_mm = self.radio_mm.isChecked()
        self.width_mm.setEnabled(use_mm)
        self.height_mm.setEnabled(use_mm)
        self.width_studs.setEnabled(not use_mm)
        self.height_studs.setEnabled(not use_mm)

    def get_new_size(self):
        if self.radio_mm.isChecked():
            return mm_to_studs(self.width_mm.value()), mm_to_studs(self.height_mm.value())
        else:
            return self.width_studs.value(), self.height_studs.value()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modular Bricksmith")
        self.resize(1000, 800)
        self.current_color = "#C91A09"
        self.selected_colour_item = None
        self.current_file = None
        self.unsaved_changes = False
        self.brick_offset_counter = 0

        self._init_ui()
        self._load_colours()

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_timer.start(5 * 60 * 1000)
        self.autosave_prompt_shown = False

        self.show_startup_dialog()

    def _init_ui(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        self.custom_bricks_path = get_resource_path(os.path.join("resources", "custom_bricks.json"))

        # Menu actions
        save_action = QAction("Save", self)
        load_action = QAction("Load", self)
        resize_action = QAction("Resize Grid", self)
        new_action = QAction("New", self)
        import_action = QAction("Import Image", self)
        export_action = QAction("Export as PNG", self)
        toolbar.addAction(export_action)
        export_action.triggered.connect(self.export_as_png)


        toolbar.addAction(save_action)
        toolbar.addAction(load_action)
        toolbar.addAction(resize_action)
        toolbar.addAction(new_action)
        toolbar.addAction(import_action)

        # 🔍 Zoom slider widget
        zoom_label = QLabel("Zoom:")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(25)
        self.zoom_slider.setMaximum(400)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(100)
        self.zoom_slider.setToolTip("Zoom level")

        zoom_widget = QWidget()
        zoom_layout = QHBoxLayout()
        zoom_layout.setContentsMargins(10, 0, 10, 0)
        zoom_layout.setSpacing(5)
        zoom_layout.addWidget(zoom_label)
        zoom_layout.addWidget(self.zoom_slider)
        zoom_widget.setLayout(zoom_layout)
        toolbar.addWidget(zoom_widget)

        # Connect actions
        save_action.triggered.connect(self.save_layout)
        load_action.triggered.connect(self.load_layout)
        resize_action.triggered.connect(self.show_resize_dialog)
        new_action.triggered.connect(self.new_layout)
        import_action.triggered.connect(self.import_image)
        self.zoom_slider.valueChanged.connect(self.apply_zoom)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout()
        central_widget.setLayout(layout)

        self.brick_palette = QListWidget()
        self.brick_palette.addItem("2x2 Brick")
        self.brick_palette.addItem("2x4 Brick")
        self.brick_palette.itemClicked.connect(self.add_brick_to_scene)
        self.load_custom_bricks()
        add_button = QPushButton("Add Brick")
        remove_button = QPushButton("Remove Brick")
        add_button.clicked.connect(self.add_custom_brick)
        remove_button.clicked.connect(self.remove_custom_brick)
        # Brick palette + buttons container
        brick_layout = QVBoxLayout()
        brick_layout.addWidget(self.brick_palette)
        brick_layout.addWidget(add_button)
        brick_layout.addWidget(remove_button)
        brick_container = QWidget()
        brick_container.setLayout(brick_layout)
        layout.addWidget(brick_container, 1)

        self.scene = GridCanvas(grid_width=48, grid_height=48)
        self.canvas = QGraphicsView(self.scene)
        self.canvas.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.canvas.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.canvas.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        layout.addWidget(self.canvas, 4)

        colour_layout = QVBoxLayout()
        self.colour_palette = QListWidget()
        self.colour_palette.itemClicked.connect(self.select_colour)
        colour_layout.addWidget(self.colour_palette)

        reset_button = QPushButton("Reset Colour")
        reset_button.clicked.connect(self.reset_colour_selection)
        colour_layout.addWidget(reset_button)

        colour_container = QWidget()
        colour_container.setLayout(colour_layout)
        layout.addWidget(colour_container, 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")
        self.version_label = QLabel(f"v{APP_VERSION}")
        self.status.addPermanentWidget(self.version_label)

    def show_startup_dialog(self):
        reply = QMessageBox.question(
            self, "Load or New",
            "Do you want to load an existing file?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.load_layout()
        else:
            self.show_grid_size_dialog()
            
    def show_image_placement_dialog_and_return_offset(self, img_width, img_height):
        dialog = QDialog(self)
        dialog.setWindowTitle("Choose Image Placement")
        layout = QVBoxLayout()

        placements = {
            "Top-Left": (0, 0),
            "Top-Right": (self.scene.grid_width - img_width, 0),
            "Bottom-Left": (0, self.scene.grid_height - img_height),
            "Bottom-Right": (self.scene.grid_width - img_width, self.scene.grid_height - img_height)
        }

        selected = {"offset": (0, 0)}

        def select(pos):
            selected["offset"] = pos
            dialog.accept()

        for label, pos in placements.items():
            button = QPushButton(label)
            
            def make_handler(p):
                return lambda _: select(p)

            button.clicked.connect(make_handler(pos))
            layout.addWidget(button)

        dialog.setLayout(layout)
        dialog.exec_()

        return selected["offset"]
     
    def import_image(self):
        print("Starting image import...")  # Debugging message

        # Open file dialog and get file path
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Image", "", "Images (*.png *.jpg *.jpeg)")
        print(f"Selected file path: {file_path}")  # Debug: Check the file path

        if not file_path:
            print("No file selected!")
            return

        # Try to open and downscale the image
        try:
            img = Image.open(file_path).convert('RGB')
            print(f"Image opened: {file_path}, size: {img.size}")  # Debug: Image opened successfully
        except Exception as e:
            print(f"Error opening image: {e}")  # Debug: Error opening image
            self.status.showMessage(f"Error opening image: {e}")
            return

        # If image opened, proceed to resize
        print(f"Image opened: {file_path}, size: {img.size}")
        
        # Ask for grid fit size
        width, ok = QInputDialog.getInt(self, "Resize Image", "How many studs wide?", value=48, min=1, max=256)
        if not ok:
            return
        
        aspect = img.height / img.width
        height = round(width * aspect)

        # Check if it will overflow the current grid
        if width > self.scene.grid_width or height > self.scene.grid_height:
            QMessageBox.warning(
                self,
                "Grid Too Small",
                f"The current grid is {self.scene.grid_width}×{self.scene.grid_height} studs.\n"
                f"The image needs {width}×{height} studs.\n\n"
                "Bricks may be placed outside the visible area.\n"
                "This might lead to missing parts or strange layout behaviour.",
                QMessageBox.Ok
            )
        
        print(f"Calculated width: {width}, height: {height}")  # Debug: Show grid dimensions

        # Resize the image
        img = img.resize((width, height))  # ✅ correctly resizes to 48x48 brick grid
        print(f"Resized to {width * 30}x{height * 30}, importing pixels...")  # Debug: Confirm resize worked

        # Ask where to place the image
        placement = self.show_image_placement_dialog_and_return_offset(width, height)
        offset_x = placement[0]
        offset_y = placement[1]

        print(f"Placement offset: ({offset_x}, {offset_y})") #debug for image placement

        # Generate 1x1 bricks from the image pixels
        for y in range(height):
            for x in range(width):
                r, g, b = img.getpixel((x, y))
                hex_color = self.find_closest_palette_colour(r, g, b)
                brick = BrickItem(size=(1, 1), color=hex_color)

                px = (offset_x + x) * 30
                py = (offset_y + y) * 30
                brick.setPos(px, py)
                self.scene.addItem(brick)
        
        self.status.showMessage(f"Imported image as {width}x{height} grid of bricks")
        self.unsaved_changes = True
        
    def place_image_on_grid(self, position, dialog):
        self.image_position = position
        print(f"Image placed at: {position}")

        # Move the image layer to the specified position
        self.imported_image.setPos(position[0], position[1])

        # Add the image to the scene
        self.scene.addItem(self.imported_image)

        # Close the dialog after placement
        dialog.accept()
        
    
def find_closest_palette_colour(self, r, g, b):
        min_dist = float('inf')
        closest_hex = "#C91A09"  # fallback red
        for hex_code, (lr, lg, lb) in self.palette_rgb_map.items():
            dist = (lr - r)**2 + (lg - g)**2 + (lb - b)**2
            if dist < min_dist:
                min_dist = dist
                closest_hex = hex_code
        return closest_hex

    def show_grid_size_dialog(self):
        dialog = GridSizeDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            width, height = dialog.get_size()
            width += 1
            height += 1
            self.scene = GridCanvas(grid_width=width, grid_height=height)
            self.canvas.setScene(self.scene)
            self.canvas.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # Force anchor left-top
            scene_center = self.scene.sceneRect().center()
            self.canvas.centerOn(scene_center)
            self.canvas.horizontalScrollBar().setValue(self.canvas.horizontalScrollBar().maximum() // 2)
            self.canvas.verticalScrollBar().setValue(self.canvas.verticalScrollBar().maximum() // 2)

            usable_width = width - 1
            usable_height = height - 1

            if usable_width <= 48 and usable_height <= 48:
                self.canvas.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            else:
                self.canvas.setAlignment(Qt.AlignLeft | Qt.AlignTop)

            # ✅ Force scene centering and redraw
            self.canvas.centerOn(self.scene.width() / 2, self.scene.height() / 2)
            self.canvas.viewport().update()
            self.canvas.update()


    def show_resize_dialog(self):
        current_w = self.scene.grid_width
        current_h = self.scene.grid_height
        dialog = ResizeGridDialog(current_w, current_h, self)

        if dialog.exec_() == QDialog.Accepted:
            width, height = dialog.get_new_size()
            width += 1
            height += 1
            
            # 🧱 Brick cropping warning
            will_crop = False
            for item in self.scene.items():
                if isinstance(item, BrickItem):
                    x_studs = round(item.x() / 30)
                    y_studs = round(item.y() / 30)
                    w, h = item.size
                    if x_studs + w > width or y_studs + h > height:
                        will_crop = True
                        break

            if will_crop:
                reply = QMessageBox.warning(
                    self,
                    "Resize Warning",
                    "Some bricks will fall outside the new grid area. Continue anyway?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

            # 🧩 Finally resize
            self.scene.resize_grid(width, height)
            # Force scroll to center after resize
            self.canvas.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # needed for scrollbars to work predictably
            scene_center = self.scene.sceneRect().center()
            self.canvas.centerOn(scene_center)
            self.canvas.horizontalScrollBar().setValue(self.canvas.horizontalScrollBar().maximum() // 2)
            self.canvas.verticalScrollBar().setValue(self.canvas.verticalScrollBar().maximum() // 2)
            self.canvas.centerOn(self.scene.width() / 2, self.scene.height() / 2)
            self.canvas.viewport().update()
            self.canvas.update()
            self.unsaved_changes = True

            usable_width = width - 1
            usable_height = height - 1

            if usable_width <= 48 and usable_height <= 48:
                self.canvas.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            else:
                self.canvas.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                
                # ✅ Force re-center after scene change
            self.canvas.centerOn(self.scene.width() / 2, self.scene.height() / 2)
            
    def export_as_png(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Layout as PNG", "", "PNG Files (*.png)")
        if not file_path:
            return

        # Create image with same size as scene
        rect = self.scene.sceneRect()
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format_ARGB32)
        image.fill(Qt.white)  # Optional: background colour

        painter = QPainter(image)
        self.scene.render(painter)
        painter.end()

        image.save(file_path)
        self.status.showMessage(f"Exported layout to: {file_path}")     
                       
    def _load_colours(self):
        try:
            self.palette_rgb_map = {}  # hex → (r, g, b)

            with open(get_resource_path("resources/palette.json"), "r") as f:
                colours = json.load(f)
                for name, hex_code in colours.items():
                    item = QListWidgetItem(f"{name} ({hex_code})")
                    color = QColor(hex_code)

                    # Store RGB tuple for matching
                    rgb = color.getRgb()[:3]  # (r, g, b)
                    self.palette_rgb_map[hex_code] = rgb

                    # UI styling
                    item.setBackground(QBrush(color))
                    text_color = Qt.white if color.lightness() < 128 else Qt.black
                    item.setForeground(QBrush(text_color))
                    if hex_code == self.current_color:
                        item.setText(f"✔️ {item.text()}")
                        self.selected_colour_item = item
                    self.colour_palette.addItem(item)

        except Exception as e:
            self.status.showMessage(f"Error loading colours: {e}")


    def select_colour(self, item):
        for i in range(self.colour_palette.count()):
            list_item = self.colour_palette.item(i)
            text = list_item.text().replace("✔️ ", "")
            list_item.setText(text)
            hex_code = text.split('(')[-1].replace(')', '')
            color = QColor(hex_code)
            list_item.setBackground(QBrush(color))
            text_color = Qt.white if color.lightness() < 128 else Qt.black
            list_item.setForeground(QBrush(text_color))

        if '(' in item.text():
            self.current_color = item.text().split('(')[-1].replace(')', '')
            color = QColor(self.current_color)
            item.setBackground(QBrush(color))
            text_color = Qt.white if color.lightness() < 128 else Qt.black
            item.setForeground(QBrush(text_color))
            item.setText(f"✔️ {item.text().replace('✔️ ', '')}")
            self.selected_colour_item = item
            self.status.showMessage(f"Selected colour: {self.current_color}")

    def reset_colour_selection(self):
        for i in range(self.colour_palette.count()):
            list_item = self.colour_palette.item(i)
            text = list_item.text().replace("✔️ ", "")
            list_item.setText(text)
            hex_code = text.split('(')[-1].replace(')', '')
            color = QColor(hex_code)
            list_item.setBackground(QBrush(color))
            text_color = Qt.white if color.lightness() < 128 else Qt.black
            list_item.setForeground(QBrush(text_color))

            if hex_code == "#C91A09":
                list_item.setText(f"✔️ {text}")
                self.selected_colour_item = list_item

        self.current_color = "#C91A09"
        self.status.showMessage("Colour reset to default")

    def add_brick_to_scene(self, item):
        name = item.text()
        try:
            dims = name.split(" ")[0]  # "2x4 Brick" → "2x4"
            w, h = map(int, dims.split("x"))
            size = (w, h)
        except:
            size = (2, 2)  # fallback

        brick = BrickItem(size=size, color=self.current_color)
              
        grid_w = self.scene.grid_width
        grid_h = self.scene.grid_height
        brick_w, brick_h = size
        
        x = ((grid_w - brick_w) // 2) * 30
        y = ((grid_h - brick_h) // 2) * 30
        
        brick.setPos(x, y)

        self.scene.addItem(brick)
        self.unsaved_changes = True
        self.brick_offset_counter += 1

    def save_layout(self, path_override=None):
        filename = path_override or self.current_file
        if not filename:
            filename, _ = QFileDialog.getSaveFileName(self, "Save Layout", "", "RGL Files (*.rgl)")
            if not filename:
                return
            if not filename.endswith(".rgl"):
                filename += ".rgl"

        QApplication.setOverrideCursor(Qt.WaitCursor)
        save_layout(filename, self.scene)
        QApplication.restoreOverrideCursor()
        self.status.showMessage(f"Saved to {filename}")
        self.current_file = filename
        self.setWindowTitle(f"Modular Bricksmith – {os.path.basename(filename)}")
        self.unsaved_changes = False

    def load_layout(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Layout", "", "RGL Files (*.rgl)")
        if filename:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            load_layout(filename, self.scene, BrickItem)
            QApplication.restoreOverrideCursor()
            self.status.showMessage(f"Loaded {filename}")
            self.current_file = filename
            self.setWindowTitle(f"Modular Bricksmith – {os.path.basename(filename)}")
            self.unsaved_changes = False
            
    def new_layout(self):
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save before starting a new layout?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if reply == QMessageBox.Yes:
                self.save_layout(path_override=self.current_file)
            elif reply == QMessageBox.Cancel:
                return  # User cancelled

        # Reset state
        self.current_file = None
        self.unsaved_changes = False
        self.setWindowTitle("Modular Bricksmith")
        
        self.show_grid_size_dialog()  # Reuse the existing dialog            

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_R:
            for item in self.scene.selectedItems():
                if isinstance(item, BrickItem):
                    item.setTransformOriginPoint(item.boundingRect().center())
                    item.rotate90()
                    item.snap_to_grid()
                    self.unsaved_changes = True
        elif event.key() == Qt.Key_Delete:
            for item in self.scene.selectedItems():
                if isinstance(item, BrickItem):
                    self.scene.removeItem(item)
                    self.unsaved_changes = True
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )

            if reply == QMessageBox.Yes:
                self.save_layout(path_override=self.current_file)
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def autosave(self):
        if not self.unsaved_changes:
            return

        if self.current_file:
            self.save_layout(path_override=self.current_file)
        elif not self.autosave_prompt_shown:
            filename, _ = QFileDialog.getSaveFileName(self, "Autosave – Select Save Location", "", "RGL Files (*.rgl)")
            if filename:
                if not filename.endswith(".rgl"):
                    filename += ".rgl"
                self.save_layout(path_override=filename)
                self.current_file = filename
                self.setWindowTitle(f"Modular Bricksmith – {os.path.basename(filename)}")
            else:
                self.autosave_prompt_shown = True
                
    def load_custom_bricks(self):
        if not os.path.exists(self.custom_bricks_path):
            with open(self.custom_bricks_path, "w") as f:
                json.dump([], f)

        try:
            with open(self.custom_bricks_path, "r") as f:
                bricks = json.load(f)
                for brick in bricks:
                    name = brick["name"]
                    self.brick_palette.addItem(name)
        except Exception as e:
            if hasattr(self, "status"):
                self.status.showMessage(f"Error loading custom bricks: {e}")
            else:
                print(f"Error loading custom bricks: {e}")
            
    def add_custom_brick(self):
        width, ok1 = QInputDialog.getInt(self, "New Brick", "Width (studs):", 1, 1, 16)
        if not ok1:
            return
        height, ok2 = QInputDialog.getInt(self, "New Brick", "Height (studs):", 1, 1, 16)
        if not ok2:
            return

        name = f"{width}x{height} Brick"
        self.brick_palette.addItem(name)

        try:
            with open(self.custom_bricks_path, "r") as f:
                bricks = json.load(f)
            bricks.append({"name": name, "width": width, "height": height})
            with open(self.custom_bricks_path, "w") as f:
                json.dump(bricks, f, indent=2)
        except Exception as e:
            self.status.showMessage(f"Error saving custom brick: {e}")

    def remove_custom_brick(self):
        item = self.brick_palette.currentItem()
        if not item:
            return

        name = item.text()
        if name in ["2x2 Brick", "2x4 Brick"]:
            QMessageBox.information(self, "Can't Remove", "Built-in bricks can't be removed.")
            return

        self.brick_palette.takeItem(self.brick_palette.row(item))

        try:
            with open(self.custom_bricks_path, "r") as f:
                bricks = json.load(f)
            bricks = [b for b in bricks if b["name"] != name]
            with open(self.custom_bricks_path, "w") as f:
                json.dump(bricks, f, indent=2)
        except Exception as e:
            self.status.showMessage(f"Error updating brick list: {e}")
            
    def apply_zoom(self, value):
        scale_factor = value / 100.0  # Convert percentage to scale
        self.canvas.resetTransform()  # Reset any previous zoom
        self.canvas.scale(scale_factor, scale_factor)
        self.status.showMessage(f"Zoom: {value}%")