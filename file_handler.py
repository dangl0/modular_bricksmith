# file_handler.py - Save/Load .rgl Layout Files
# Version: 1.0.0

import json
import os


def save_layout(filepath, scene, grid_size=(50, 50)):
    layout_data = {
        "version": "1.0",
        "grid_size": list(grid_size),
        "layers": [
            {
                "id": "layer_001",
                "name": "Default",
                "visible": True,
                "bricks": []
            }
        ]
    }

    for item in scene.items():
        if hasattr(item, 'size'):
            layout_data["layers"][0]["bricks"].append({
                "id": f"brick_{id(item)}",
                "position": [round(item.x() / 30), round(item.y() / 30)],
                "size": list(item.size),
                "rotation": item.rotation(),
                "color": item.brush().color().name()
            })

    with open(filepath, 'w') as f:
        json.dump(layout_data, f, indent=2)


def load_layout(filepath, scene, BrickItem):
    with open(filepath, 'r') as f:
        layout_data = json.load(f)

    scene.clear()

    for brick_data in layout_data["layers"][0]["bricks"]:
        brick = BrickItem(size=tuple(brick_data["size"]), color=brick_data["color"])
        brick.setRotation(brick_data["rotation"])
        x = brick_data["position"][0] * 30
        y = brick_data["position"][1] * 30
        brick.setPos(x, y)
        scene.addItem(brick)

    return layout_data.get("grid_size", [50, 50])
