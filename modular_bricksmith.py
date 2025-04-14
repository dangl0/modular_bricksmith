# lego_planner.py - Main Launcher
# Version: 2.0.0

import os
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from ui_main import MainWindow

from utils import get_resource_path  # Make sure this is at the top

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()