# utils/drawing.py
import math

# Vector font definitions. Each character fits in a box of width 1.0, height 1.5.
# Segment coordinates are (x, y) where x in [0, 1] and y in [0, 1.5] (0 at top, 1.5 at bottom).
VECTOR_FONT = {
    'A': [((0, 1.5), (0, 0.5)), ((0, 0.5), (0.5, 0)), ((0.5, 0), (1, 0.5)), ((1, 0.5), (1, 1.5)), ((0, 0.8), (1, 0.8))],
    'B': [((0, 0), (0, 1.5)), ((0, 0), (0.8, 0)), ((0.8, 0), (0.8, 0.7)), ((0.8, 0.7), (0, 0.7)), ((0, 0.7), (0.9, 0.7)), ((0.9, 0.7), (0.9, 1.5)), ((0.9, 1.5), (0, 1.5))],
    'C': [((1, 0), (0, 0)), ((0, 0), (0, 1.5)), ((0, 1.5), (1, 1.5))],
    'D': [((0, 0), (0, 1.5)), ((0, 0), (0.7, 0)), ((0.7, 0), (1, 0.4)), ((1, 0.4), (1, 1.1)), ((1, 1.1), (0.7, 1.5)), ((0.7, 1.5), (0, 1.5))],
    'E': [((1, 0), (0, 0)), ((0, 0), (0, 1.5)), ((0, 1.5), (1, 1.5)), ((0, 0.75), (0.8, 0.75))],
    'F': [((0, 0), (0, 1.5)), ((0, 1.5), (1, 1.5)), ((0, 0.75), (0.8, 0.75))],  # Flip standard layout so y=0 is bottom or keep standard. Let's keep 0 as top, 1.5 as bottom.
    'G': [((1, 0.4), (1, 0)), ((1, 0), (0, 0)), ((0, 0), (0, 1.5)), ((0, 1.5), (1, 1.5)), ((1, 1.5), (1, 0.8)), ((1, 0.8), (0.5, 0.8))],
    'H': [((0, 0), (0, 1.5)), ((1, 0), (1, 1.5)), ((0, 0.75), (1, 0.75))],
    'I': [((0.2, 0), (0.8, 0)), ((0.2, 1.5), (0.8, 1.5)), ((0.5, 0), (0.5, 1.5))],
    'J': [((0, 1.1), (0, 1.5)), ((0, 1.5), (0.8, 1.5)), ((0.8, 1.5), (0.8, 0)), ((0.5, 0), (1, 0))],
    'K': [((0, 0), (0, 1.5)), ((0, 0.75), (0.9, 0)), ((0, 0.75), (0.9, 1.5))],
    'L': [((0, 0), (0, 1.5)), ((0, 1.5), (1, 1.5))],
    'M': [((0, 1.5), (0, 0)), ((0, 0), (0.5, 0.6)), ((0.5, 0.6), (1, 0)), ((1, 0), (1, 1.5))],
    'N': [((0, 1.5), (0, 0)), ((0, 0), (1, 1.5)), ((1, 1.5), (1, 0))],
    'O': [((0, 0), (1, 0)), ((1, 0), (1, 1.5)), ((1, 1.5), (0, 1.5)), ((0, 1.5), (0, 0))],
    'P': [((0, 1.5), (0, 0)), ((0, 0), (1, 0)), ((1, 0), (1, 0.75)), ((1, 0.75), (0, 0.75))],
    'Q': [((0, 0), (1, 0)), ((1, 0), (1, 1.2)), ((1, 1.2), (0, 1.2)), ((0, 1.2), (0, 0)), ((0.6, 0.8), (1.1, 1.5))],
    'R': [((0, 1.5), (0, 0)), ((0, 0), (1, 0)), ((1, 0), (1, 0.75)), ((1, 0.75), (0, 0.75)), ((0.4, 0.75), (1, 1.5))],
    'S': [((1, 0), (0, 0)), ((0, 0), (0, 0.75)), ((0, 0.75), (1, 0.75)), ((1, 0.75), (1, 1.5)), ((1, 1.5), (0, 1.5))],
    'T': [((0, 0), (1, 0)), ((0.5, 0), (0.5, 1.5))],
    'U': [((0, 0), (0, 1.5)), ((0, 1.5), (1, 1.5)), ((1, 1.5), (1, 0))],
    'V': [((0, 0), (0.5, 1.5)), ((0.5, 1.5), (1, 0))],
    'W': [((0, 0), (0.2, 1.5)), ((0.2, 1.5), (0.5, 0.7)), ((0.5, 0.7), (0.8, 1.5)), ((0.8, 1.5), (1, 0))],
    'X': [((0, 0), (1, 1.5)), ((0, 1.5), (1, 0))],
    'Y': [((0, 0), (0.5, 0.75)), ((1, 0), (0.5, 0.75)), ((0.5, 0.75), (0.5, 1.5))],
    'Z': [((0, 0), (1, 0)), ((1, 0), (0, 1.5)), ((0, 1.5), (1, 1.5))],
    '0': [((0, 0), (1, 0)), ((1, 0), (1, 1.5)), ((1, 1.5), (0, 1.5)), ((0, 1.5), (0, 0)), ((0, 1.5), (1, 0))],
    '1': [((0.3, 0.3), (0.5, 0)), ((0.5, 0), (0.5, 1.5)), ((0.2, 1.5), (0.8, 1.5))],
    '2': [((0, 0), (1, 0)), ((1, 0), (1, 0.75)), ((1, 0.75), (0, 1.5)), ((0, 1.5), (1, 1.5))],
    '3': [((0, 0), (1, 0)), ((1, 0), (1, 1.5)), ((1, 1.5), (0, 1.5)), ((0.3, 0.75), (1, 0.75))],
    '4': [((0, 0), (0, 0.75)), ((0, 0.75), (1, 0.75)), ((1, 0), (1, 1.5))],
    '5': [((1, 0), (0, 0)), ((0, 0), (0, 0.75)), ((0, 0.75), (1, 0.75)), ((1, 0.75), (1, 1.5)), ((1, 1.5), (0, 1.5))],
    '6': [((1, 0), (0, 0)), ((0, 0), (0, 1.5)), ((0, 1.5), (1, 1.5)), ((1, 1.5), (1, 0.75)), ((1, 0.75), (0, 0.75))],
    '7': [((0, 0), (1, 0)), ((1, 0), (0.5, 1.5))],
    '8': [((0, 0), (1, 0)), ((1, 0), (1, 1.5)), ((1, 1.5), (0, 1.5)), ((0, 1.5), (0, 0)), ((0, 0.75), (1, 0.75))],
    '9': [((0, 0), (1, 0)), ((1, 0), (1, 1.5)), ((1, 1.5), (0, 1.5)), ((0, 0.75), (1, 0.75)), ((0, 0), (0, 0.75))],
    '-': [((0.2, 0.75), (0.8, 0.75))],
    '+': [((0.2, 0.75), (0.8, 0.75)), ((0.5, 0.35), (0.5, 1.15))],
    '/': [((0.1, 1.5), (0.9, 0))],
    ':': [((0.5, 0.4), (0.5, 0.45)), ((0.5, 1.1), (0.5, 1.15))],
    '.': [((0.45, 1.4), (0.55, 1.4)), ((0.55, 1.4), (0.55, 1.5)), ((0.55, 1.5), (0.45, 1.5)), ((0.45, 1.5), (0.45, 1.4))],
    '>': [((0.2, 0.25), (0.8, 0.75)), ((0.8, 0.75), (0.2, 1.25))],
    '<': [((0.8, 0.25), (0.2, 0.75)), ((0.2, 0.75), (0.8, 1.25))],
    '_': [((0, 1.5), (1, 1.5))],
    '%': [((0.1, 1.5), (0.9, 0)), ((0.2, 0.3), (0.3, 0.4)), ((0.7, 1.1), (0.8, 1.2))],
    '#': [((0.3, 0), (0.3, 1.5)), ((0.7, 0), (0.7, 1.5)), ((0, 0.5), (1, 0.5)), ((0, 1.0), (1, 1.0))],
    '(': [((0.7, 0), (0.3, 0.4)), ((0.3, 0.4), (0.3, 1.1)), ((0.3, 1.1), (0.7, 1.5))],
    ')': [((0.3, 0), (0.7, 0.4)), ((0.7, 0.4), (0.7, 1.1)), ((0.7, 1.1), (0.3, 1.5))],
    '!': [((0.5, 0), (0.5, 1.0)), ((0.5, 1.3), (0.5, 1.5))],
    ' ': []
}

class LineBatch:
    def __init__(self):
        # A list of floats: [x, y, r, g, b, ...]
        self.vertices = []

    def clear(self):
        self.vertices.clear()

    def add_line(self, x1, y1, x2, y2, color):
        r, g, b = color
        self.vertices.extend([
            float(x1), float(y1), float(r), float(g), float(b),
            float(x2), float(y2), float(r), float(g), float(b)
        ])

    def add_rect(self, x, y, w, h, color):
        self.add_line(x, y, x + w, y, color)
        self.add_line(x + w, y, x + w, y + h, color)
        self.add_line(x + w, y + h, x, y + h, color)
        self.add_line(x, y + h, x, y, color)

    def add_circle(self, cx, cy, radius, color, segments=16):
        prev_x = cx + radius
        prev_y = cy
        for i in range(1, segments + 1):
            angle = (i / segments) * math.pi * 2
            curr_x = cx + radius * math.cos(angle)
            curr_y = cy + radius * math.sin(angle)
            self.add_line(prev_x, prev_y, curr_x, curr_y, color)
            prev_x, prev_y = curr_x, curr_y

    def add_polygon(self, points, color, closed=True):
        if len(points) < 2:
            return
        for i in range(len(points) - 1):
            self.add_line(points[i][0], points[i][1], points[i+1][0], points[i+1][1], color)
        if closed:
            self.add_line(points[-1][0], points[-1][1], points[0][0], points[0][1], color)

    def add_text(self, text, x, y, scale, color, spacing=1.3):
        text = text.upper()
        current_x = x
        char_w = 8 * scale
        char_h = 12 * scale
        
        for char in text:
            if char in VECTOR_FONT:
                lines = VECTOR_FONT[char]
                for p1, p2 in lines:
                    x1 = current_x + p1[0] * char_w
                    # Y goes down: standard coordinates have 0 at top, so add to Y
                    y1 = y + p1[1] * char_w  # scaling matches width proportion
                    x2 = current_x + p2[0] * char_w
                    y2 = y + p2[1] * char_w
                    self.add_line(x1, y1, x2, y2, color)
            current_x += char_w * spacing

    def get_vertex_count(self):
        return len(self.vertices) // 5


def draw_grid(cam_x, cam_y, screen_w, screen_h, grid_size, color, batch):
    """Draws an infinite scrolling grid in world coordinates."""
    left = cam_x - screen_w / 2
    right = cam_x + screen_w / 2
    top = cam_y - screen_h / 2
    bottom = cam_y + screen_h / 2

    # Find the starting coordinates for lines
    start_x = (left // grid_size) * grid_size
    end_x = (right // grid_size + 1) * grid_size
    start_y = (top // grid_size) * grid_size
    end_y = (bottom // grid_size + 1) * grid_size

    # Vertical grid lines
    curr_x = start_x
    while curr_x <= end_x:
        batch.add_line(curr_x, top, curr_x, bottom, color)
        curr_x += grid_size

    # Horizontal grid lines
    curr_y = start_y
    while curr_y <= end_y:
        batch.add_line(left, curr_y, right, curr_y, color)
        curr_y += grid_size
