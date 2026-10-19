# systems/camera.py

class Camera:
    def __init__(self, start_x=0.0, start_y=0.0):
        # Coordinates in world space representing the center of the screen
        self.x = float(start_x)
        self.y = float(start_y)

    def update(self, target_x, target_y, lerp_factor=0.1):
        """Smoothly moves the camera toward the target position."""
        self.x += (float(target_x) - self.x) * lerp_factor
        self.y += (float(target_y) - self.y) * lerp_factor
