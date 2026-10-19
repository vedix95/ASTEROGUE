# entities/item.py
import math
import random
from config import COLOR_BLUE, COLOR_RED, COLOR_AMBER

class Item:
    def __init__(self, x, y, item_type="xp", value=1):
        self.x = float(x)
        self.y = float(y)
        self.item_type = item_type
        self.value = value
        self.active = True
        self.magnetized = False
        self.rotation = random.uniform(0, math.pi * 2)
        self.rotation_speed = random.uniform(1.0, 3.0)
        self.speed = 0.0
        self.max_speed = 450.0
        self.acceleration = 600.0

    def update(self, dt, player_x, player_y, magnet_radius):
        if not self.active:
            return

        self.rotation += self.rotation_speed * dt
        
        # Calculate distance to player
        dx = player_x - self.x
        dy = player_y - self.y
        dist_sq = dx * dx + dy * dy
        
        if not self.magnetized:
            if dist_sq < magnet_radius * magnet_radius:
                self.magnetized = True
        
        if self.magnetized:
            dist = math.sqrt(dist_sq)
            # Fly toward player
            self.speed = min(self.max_speed, self.speed + self.acceleration * dt)
            if dist > 0:
                self.x += (dx / dist) * self.speed * dt
                self.y += (dy / dist) * self.speed * dt
            
            # Check for pickup collision
            if dist < 12.0:
                self.active = False
                # Return pickup event
                return True
        return False

    def draw(self, batch):
        if not self.active:
            return

        cos_r = math.cos(self.rotation)
        sin_r = math.sin(self.rotation)

        if self.item_type == "xp":
            # XP is a rotating diamond of varying sizes and colors based on value
            if self.value <= 1:
                size_mult = 1.0
                color = COLOR_BLUE # Blue for easy (value = 1)
            elif self.value <= 4:
                size_mult = 1.6
                color = (0.2, 0.9, 0.4) # Green for medium (value = 2-4)
            elif self.value <= 8:
                size_mult = 2.4
                color = (1.0, 0.7, 0.0) # Amber for hard (value = 5-8)
            else:
                size_mult = 4.0
                color = (0.7, 0.15, 1.0) # Purple/magenta for boss/epic (value > 8)

            points = [
                (0.0, -6.0 * size_mult),
                (4.0 * size_mult, 0.0),
                (0.0, 6.0 * size_mult),
                (-4.0 * size_mult, 0.0)
            ]
            rot_points = []
            for px, py in points:
                rx = px * cos_r - py * sin_r
                ry = px * sin_r + py * cos_r
                rot_points.append((self.x + rx, self.y + ry))
            
            batch.add_polygon(rot_points, color, closed=True)

        elif self.item_type == "health":
            # Health pack is a cross
            size = 5.0
            # Draw horizontal line
            batch.add_line(self.x - size, self.y, self.x + size, self.y, COLOR_RED)
            # Draw vertical line
            batch.add_line(self.x, self.y - size, self.x, self.y + size, COLOR_RED)

        elif self.item_type == "fuel":
            # Hyperspace Fuel: glowing magenta hourglass shape
            size = 6.0
            color = (1.0, 0.1, 0.8) # Neon Magenta
            
            p_top = [(0.0, 0.0), (-size * 0.7, -size), (size * 0.7, -size)]
            p_bot = [(0.0, 0.0), (-size * 0.7, size), (size * 0.7, size)]
            
            def draw_poly_item(pts):
                rot_pts = []
                for px, py in pts:
                    rx = px * cos_r - py * sin_r
                    ry = px * sin_r + py * cos_r
                    rot_pts.append((self.x + rx, self.y + ry))
                batch.add_polygon(rot_pts, color, closed=True)
                
            draw_poly_item(p_top)
            draw_poly_item(p_bot)

        elif self.item_type == "magnet":
            # Horse shoe shape: U-shape
            color_red = (1.0, 0.1, 0.1)
            color_blue = (0.1, 0.4, 1.0)
            
            pts_red = [(-4.0, -5.0), (-4.0, 0.0), (0.0, 0.0)]
            pts_blue = [(4.0, -5.0), (4.0, 0.0), (0.0, 0.0)]
            
            def draw_relative_lines(pts, color):
                for i in range(len(pts) - 1):
                    p1x, p1y = pts[i]
                    p2x, p2y = pts[i+1]
                    rx1 = p1x * cos_r - p1y * sin_r
                    ry1 = p1x * sin_r + p1y * cos_r
                    rx2 = p2x * cos_r - p2y * sin_r
                    ry2 = p2x * sin_r + p2y * cos_r
                    batch.add_line(self.x + rx1, self.y + ry1, self.x + rx2, self.y + ry2, color)
                    
            draw_relative_lines(pts_red, color_red)
            draw_relative_lines(pts_blue, color_blue)

        elif self.item_type == "bomb":
            r = 7.0
            # Grey core circle
            batch.add_circle(self.x, self.y, r, (0.5, 0.5, 0.5), segments=12)
            # Fuse line
            fx1 = 0.0
            fy1 = -r
            fx2 = 5.0 * cos_r
            fy2 = -r - 5.0 * sin_r
            batch.add_line(self.x + fx1, self.y + fy1, self.x + fx2, self.y + fy2, (0.7, 0.6, 0.4))
            # Spark cross
            scolor = (1.0, 0.5, 0.0)
            batch.add_line(self.x + fx2 - 2, self.y + fy2, self.x + fx2 + 2, self.y + fy2, scolor)
            batch.add_line(self.x + fx2, self.y + fy2 - 2, self.x + fx2, self.y + fy2 + 2, scolor)

        elif self.item_type == "credit":
            # Amber octagon nugget
            size = 4.0
            points = [
                (size, size * 2), (size * 2, size), (size * 2, -size), (size, -size * 2),
                (-size, -size * 2), (-size * 2, -size), (-size * 2, size), (-size, size * 2)
            ]
            rot_points = []
            for px, py in points:
                rx = px * cos_r - py * sin_r
                ry = px * sin_r + py * cos_r
                rot_points.append((self.x + rx, self.y + ry))
            batch.add_polygon(rot_points, COLOR_AMBER, closed=True)

        elif self.item_type == "plasma":
            # Purple/magenta crystal diamond
            size = 5.0
            points = [
                (0.0, -size * 1.5),
                (size, 0.0),
                (0.0, size * 1.5),
                (-size, 0.0)
            ]
            rot_points = []
            for px, py in points:
                rx = px * cos_r - py * sin_r
                ry = px * sin_r + py * cos_r
                rot_points.append((self.x + rx, self.y + ry))
            batch.add_polygon(rot_points, (0.8, 0.2, 1.0), closed=True)

        elif self.item_type == "core":
            # Neon cyan glowing core star shape
            size = 6.0
            points = [
                (0.0, -size), (size * 0.4, -size * 0.4),
                (size, 0.0), (size * 0.4, size * 0.4),
                (0.0, size), (-size * 0.4, size * 0.4),
                (-size, 0.0), (-size * 0.4, -size * 0.4)
            ]
            rot_points = []
            for px, py in points:
                rx = px * cos_r - py * sin_r
                ry = px * sin_r + py * cos_r
                rot_points.append((self.x + rx, self.y + ry))
            batch.add_polygon(rot_points, (0.2, 0.9, 1.0), closed=True)
