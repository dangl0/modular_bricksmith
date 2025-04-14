# Modular Bricksmith

Modular Bricksmith is a Windows-friendly layout planner for modular brick mosaics and baseplates.  
Built in Python with PyQt5, it supports accurate 2D placement using real-world stud measurements (8mm per stud).

## 🔧 Features
- Real-scale 2D layout with snapping grid
- Custom brick sizes and colour palette
- Save/load layouts (`.rgl` format)
- Export to PNG
- Image import → converts to 1x1 stud mosaic
- Grid resizing (studs or mm)
- Undo, redo, zoom slider, and more

## 🖥️ How to Run

```bash
python modular_bricksmith.py
```

Requires Python 3.x and PyQt5 installed.

## 📦 Packaging as .EXE (Windows)

```bash
pyinstaller --onefile --windowed modular_bricksmith.py
```

Output will be in `dist/`. No need for Python to run the EXE.

## 🗂️ Folder Structure

```
modular_bricksmith/
├── modular_bricksmith.py
├── ui_main.py
├── ...
├── resources/
│   ├── palette.json
│   └── bricks.json
```

## ✅ Status

Version: 1.8.10  
Next milestone: Export parts list + autosave improvements

## 🔒 License

MIT (you can add LICENSE file or change this)
