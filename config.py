# config.py

# Window Settings
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
TARGET_FPS = 60

# Colors (Float values 0.0 to 1.0 for OpenGL shaders)
COLOR_BLACK = (0.0, 0.0, 0.0)
COLOR_GREEN = (0.1, 1.0, 0.2)
COLOR_GREEN_DIM = (0.05, 0.35, 0.08)
COLOR_AMBER = (1.0, 0.65, 0.0)
COLOR_RED = (1.0, 0.1, 0.1)
COLOR_WHITE = (1.0, 1.0, 1.0)
COLOR_BLUE = (0.2, 0.6, 1.0)

# Gameplay Constants
PLAYER_START_HEALTH = 100
PLAYER_START_SPEED = 200.0  # Pixels per second
PLAYER_START_MAGNET = 80.0   # Pickup radius in pixels

# Spawn Settings
SPAWN_INTERVAL = 1.5  # Seconds between spawns
MAX_ENEMIES = 400

# Experience thresholds: fast early leveling, progressive scaling later
def get_xp_threshold(level):
    if level == 1:
        return 5
    elif level == 2:
        return 12
    elif level == 3:
        return 22
    elif level == 4:
        return 35
    elif level == 5:
        return 50
    elif level == 6:
        return 70
    elif level == 7:
        return 95
    elif level == 8:
        return 125
    elif level == 9:
        return 160
    elif level == 10:
        return 200
    # Progressive quadratic scaling after level 10 to match massive late-game swarms
    return int(200 + (level - 10) * 45 + (level - 10)**2 * 2.5)
