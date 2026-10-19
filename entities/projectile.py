# entities/projectile.py
import math
import random
from config import COLOR_GREEN, COLOR_WHITE, COLOR_BLUE

class Projectile:
    def __init__(self, x, y, dx, dy, damage, speed, lifetime, pierce=1, proj_type="laser", color=COLOR_GREEN, radius=4.0,
                 homing=0.0, bounces=0, split_level=0, owner=None, is_enemy=False, thickness=1, size=1.0):
        self.x = float(x)
        self.y = float(y)
        self.dx = float(dx)
        self.dy = float(dy)
        self.damage = damage
        self.speed = speed
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.pierce = pierce
        self.proj_type = proj_type
        self.color = color
        self.thickness = thickness
        self.size = size
        self.radius = radius * size
        self.active = True
        self.is_enemy = is_enemy
        self.hit_enemies = set()  # Track which enemies this projectile has already damaged

        # Synergies and modifiers
        self.homing = homing
        self.bounces = bounces
        self.split_level = split_level
        self.owner = owner  # Reference to the player (for tracking position on blades/slashes)

        # For railguns / lightning: store the endpoints of the beam
        self.beam_start = None
        self.beam_end = None

        # Spiral blade properties
        if self.proj_type == "blade":
            self.blade_angle = math.atan2(dy, dx)
            self.blade_radius = 15.0

    def update(self, dt, enemies=None, camera=None, player=None):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.active = False
            return

        # Magnetic Storm trajectory disturbance
        if player and getattr(player, 'magnetic_storm_active', False) and self.proj_type not in ("shield", "blade", "slash", "lightning", "knife", "vortex"):
            drift_ang = random.uniform(-0.95, 0.95) * dt
            cos_d = math.cos(drift_ang)
            sin_d = math.sin(drift_ang)
            nx = self.dx * cos_d - self.dy * sin_d
            ny = self.dx * sin_d + self.dy * cos_d
            self.dx, self.dy = nx, ny

        # Lump of Coal scaling
        if player and player.passives.get("LUMP OF COAL", 0) > 0:
            time_alive = self.max_lifetime - self.lifetime
            coal_lvl = player.passives.get("LUMP OF COAL", 0)
            if not hasattr(self, 'base_damage'):
                self.base_damage = self.damage
                self.base_radius = self.radius
            self.damage = self.base_damage * (1.0 + time_alive * 0.45 * coal_lvl)
            self.radius = self.base_radius * (1.0 + time_alive * 0.3 * coal_lvl)

        # Homing behavior (Isaac Spoon Bender)
        if self.proj_type in ("laser", "missile") and self.homing > 0.0:
            target_x, target_y = None, None
            if self.is_enemy and player:
                target_x = player.x
                target_y = player.y
            elif not self.is_enemy and enemies:
                closest_enemy = None
                min_dist_sq = 999999.0 * 999999.0
                for e in enemies:
                    if not e.active:
                        continue
                    edx = e.x - self.x
                    edy = e.y - self.y
                    dist_sq = edx * edx + edy * edy
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        closest_enemy = e
                if closest_enemy:
                    target_x = closest_enemy.x
                    target_y = closest_enemy.y
            
            if target_x is not None and target_y is not None:
                tdx = target_x - self.x
                tdy = target_y - self.y
                tdist = math.sqrt(tdx * tdx + tdy * tdy)
                if tdist > 0:
                    tdx /= tdist
                    tdy /= tdist
                    turn_speed = self.homing
                    if self.proj_type == "missile":
                        turn_speed += 4.0  # Missiles turn extra fast
                    
                    lerp_rate = turn_speed * dt
                    self.dx += (tdx - self.dx) * lerp_rate
                    self.dy += (tdy - self.dy) * lerp_rate
                    
                    # Re-normalize direction vector
                    dlen = math.sqrt(self.dx * self.dx + self.dy * self.dy)
                    if dlen > 0:
                        self.dx /= dlen
                        self.dy /= dlen

        # Viewport bouncing behavior (Isaac Rubber Cement)
        if self.bounces > 0 and camera and self.proj_type in ("laser", "missile", "blade", "rainbow", "rainbow_fire", "meteor"):
            import config
            half_w = config.WINDOW_WIDTH * 0.5
            half_h = config.WINDOW_HEIGHT * 0.5
            left = camera.x - half_w
            right = camera.x + half_w
            top = camera.y - half_h
            bottom = camera.y + half_h
            
            bounced = False
            if self.x < left:
                self.x = left
                self.dx = -self.dx
                bounced = True
            elif self.x > right:
                self.x = right
                self.dx = -self.dx
                bounced = True
                
            if self.y < top:
                self.y = top
                self.dy = -self.dy
                bounced = True
            elif self.y > bottom:
                self.y = bottom
                self.dy = -self.dy
                bounced = True
                
            if bounced:
                self.bounces -= 1

        # Type-specific movement update
        if self.proj_type in ("laser", "missile", "flame", "rainbow", "rainbow_fire", "blade"):
            # Check for Tiny Planet passive (player or enemy spaceship owner)
            owner = self.owner
            has_tiny_planet = False
            if owner == player and player and player.passives.get("TINY PLANET", 0) > 0:
                has_tiny_planet = True
            elif owner and getattr(owner, 'is_spaceship', False) and owner.modifiers.get("tiny_planet", False):
                has_tiny_planet = True

            if has_tiny_planet and owner:
                if not hasattr(self, 'spiral_angle'):
                    self.spiral_angle = math.atan2(self.y - owner.y, self.x - owner.x)
                    self.spiral_radius = math.sqrt((self.x - owner.x)**2 + (self.y - owner.y)**2)
                    if self.spiral_radius < 10.0:
                        self.spiral_radius = 15.0
                self.spiral_angle += 5.0 * dt
                self.spiral_radius += 160.0 * dt * (getattr(player, 'proj_speed_mult', 1.0) if owner == player else 1.0)
                self.x = owner.x + self.spiral_radius * math.cos(self.spiral_angle)
                self.y = owner.y + self.spiral_radius * math.sin(self.spiral_angle)
            else:
                self.x += self.dx * self.speed * dt
                self.y += self.dy * self.speed * dt
        elif self.proj_type == "meteor":
            # Ceinture d'Astéroïdes synergy with LAMES SPIRALES
            if player and any(w.name == "LAMES SPIRALES" for w in player.weapons):
                if not hasattr(self, 'spiral_angle'):
                    self.spiral_angle = math.atan2(self.y - player.y, self.x - player.x)
                    self.spiral_radius = math.sqrt((self.x - player.x)**2 + (self.y - player.y)**2)
                    if self.spiral_radius < 20.0:
                        self.spiral_radius = 30.0
                self.spiral_angle += 3.5 * dt
                self.spiral_radius += 100.0 * dt
                self.x = player.x + self.spiral_radius * math.cos(self.spiral_angle)
                self.y = player.y + self.spiral_radius * math.sin(self.spiral_angle)
            elif player and player.passives.get("TINY PLANET", 0) > 0:
                if not hasattr(self, 'spiral_angle'):
                    self.spiral_angle = math.atan2(self.y - player.y, self.x - player.x)
                    self.spiral_radius = math.sqrt((self.x - player.x)**2 + (self.y - player.y)**2)
                    if self.spiral_radius < 10.0:
                        self.spiral_radius = 15.0
                self.spiral_angle += 5.0 * dt
                self.spiral_radius += 160.0 * dt * getattr(player, 'proj_speed_mult', 1.0)
                self.x = player.x + self.spiral_radius * math.cos(self.spiral_angle)
                self.y = player.y + self.spiral_radius * math.sin(self.spiral_angle)
            else:
                self.x += self.dx * self.speed * dt
                self.y += self.dy * self.speed * dt
        elif self.proj_type == "grenade":
            self.x += self.dx * self.speed * dt
            self.y += self.dy * self.speed * dt
            # Friction slows the grenade down
            self.speed = max(0.0, self.speed - 300.0 * dt)
        elif self.proj_type == "blade":
            if self.owner:
                self.blade_angle += 6.0 * dt  # rotate around player
                self.blade_radius += 160.0 * dt  # expand outward
                self.x = self.owner.x + self.blade_radius * math.cos(self.blade_angle)
                self.y = self.owner.y + self.blade_radius * math.sin(self.blade_angle)
            else:
                self.x += self.dx * self.speed * dt
                self.y += self.dy * self.speed * dt
        elif self.proj_type == "slash":
            if self.owner:
                self.x = self.owner.x
                self.y = self.owner.y
        elif self.proj_type == "shield":
            # Position updated externally by weapon/accessory update
            pass
        elif self.proj_type == "ring":
            self.x += self.dx * self.speed * dt
            self.y += self.dy * self.speed * dt
            if not hasattr(self, 'base_ring_radius'):
                self.base_ring_radius = self.radius
            self.radius += 50.0 * dt
        elif self.proj_type == "knife":
            if self.owner:
                if not hasattr(self, 'knife_dist'):
                    self.knife_dist = 20.0
                target_dist = 110.0 if self.owner.is_moving else 25.0
                self.knife_dist += (target_dist - self.knife_dist) * 10.0 * dt
                self.x = self.owner.x + self.knife_dist * math.cos(self.owner.angle)
                self.y = self.owner.y + self.knife_dist * math.sin(self.owner.angle)

    def split(self, projectiles_list):
        if self.split_level <= 0:
            return
        
        # Calculate perpendicular direction
        px = -self.dy
        py = self.dx
        
        # Spawn two smaller projectiles perpendicular to current vector
        for factor in (-1.0, 1.0):
            p = Projectile(
                x=self.x, y=self.y,
                dx=px * factor, dy=py * factor,
                damage=self.damage * 0.5,
                speed=self.speed * 1.2, # speed up shrapnel slightly
                lifetime=0.6,
                projectiles_list=projectiles_list if 'projectiles_list' in locals() else None, # wait, standard pierce has 1
                proj_type=self.proj_type if self.proj_type != "grenade" else "laser", # Grenade splits into lasers
                color=self.color,
                radius=max(1.5, self.radius * 0.6),
                homing=self.homing,
                bounces=self.bounces,
                split_level=self.split_level - 1,
                owner=self.owner,
                thickness=self.thickness,
                size=1.0
            )
            projectiles_list.append(p)

    def draw(self, batch):
        if not self.active:
            return

        if self.proj_type == "laser":
            vel_len = math.sqrt(self.dx * self.dx + self.dy * self.dy)
            if vel_len > 0:
                length = 12.0 * (self.radius / 4.0)
                ux = self.dx / vel_len
                uy = self.dy / vel_len
                px = -uy
                py = ux
                
                t = int(self.thickness)
                if t <= 1:
                    lx1 = self.x - ux * length
                    ly1 = self.y - uy * length
                    batch.add_line(lx1, ly1, self.x, self.y, self.color)
                else:
                    step = 0.8
                    for i in range(t):
                        offset = i - (t - 1) / 2.0
                        ox = px * offset * step
                        oy = py * offset * step
                        lx1 = (self.x + ox) - ux * length
                        ly1 = (self.y + oy) - uy * length
                        batch.add_line(lx1, ly1, self.x + ox, self.y + oy, self.color)
            else:
                batch.add_circle(self.x, self.y, self.radius, self.color, segments=4)

        elif self.proj_type == "shield":
            angle = (self.lifetime * 4.0) % (math.pi * 2)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            points = [
                (0.0, -self.radius),
                (self.radius, 0.0),
                (0.0, self.radius),
                (-self.radius, 0.0)
            ]
            rot_points = []
            for px, py in points:
                rx = px * cos_a - py * sin_a
                ry = px * sin_a + py * cos_a
                rot_points.append((self.x + rx, self.y + ry))
            batch.add_polygon(rot_points, self.color, closed=True)

        elif self.proj_type == "rail":
            if self.beam_start and self.beam_end:
                fade_pct = self.lifetime / self.max_lifetime
                r, g, b = self.color
                dim_color = (r * fade_pct, g * fade_pct, b * fade_pct)
                white_dim = (fade_pct, fade_pct, fade_pct)
                
                # Draw thicker rail beam using parallel lines
                dx = self.beam_end[0] - self.beam_start[0]
                dy = self.beam_end[1] - self.beam_start[1]
                beam_len = math.hypot(dx, dy)
                if beam_len > 0:
                    px = -dy / beam_len
                    py = dx / beam_len
                    t = int(self.thickness)
                    if t <= 1:
                        batch.add_line(self.beam_start[0], self.beam_start[1], self.beam_end[0], self.beam_end[1], dim_color)
                        batch.add_line(self.beam_start[0], self.beam_start[1], self.beam_end[0], self.beam_end[1], white_dim)
                    else:
                        step = 0.8
                        for i in range(t):
                            offset = i - (t - 1) / 2.0
                            ox = px * offset * step
                            oy = py * offset * step
                            batch.add_line(self.beam_start[0] + ox, self.beam_start[1] + oy, self.beam_end[0] + ox, self.beam_end[1] + oy, dim_color)
                            batch.add_line(self.beam_start[0] + ox, self.beam_start[1] + oy, self.beam_end[0] + ox, self.beam_end[1] + oy, white_dim)

        elif self.proj_type == "shockwave":
            fade_pct = self.lifetime / self.max_lifetime
            current_radius = self.radius * (1.0 - fade_pct)
            r, g, b = self.color
            dim_color = (r * fade_pct, g * fade_pct, b * fade_pct)
            batch.add_circle(self.x, self.y, current_radius, dim_color, segments=24)

        elif self.proj_type == "grenade":
            # Amber circular bomb with visual inner crosshair
            batch.add_circle(self.x, self.y, self.radius, self.color, segments=8)
            batch.add_line(self.x - self.radius, self.y, self.x + self.radius, self.y, self.color)
            batch.add_line(self.x, self.y - self.radius, self.x, self.y + self.radius, self.color)

        elif self.proj_type == "vortex":
            fade_pct = self.lifetime / self.max_lifetime
            # Radial expanding swirling triangles
            current_radius = self.radius * (1.0 - fade_pct)
            angle = (self.lifetime * 10.0) % (math.pi * 2)
            for offset in (0.0, math.pi / 3.0, 2.0 * math.pi / 3.0):
                c_ang = angle + offset
                p1 = (self.x + current_radius * math.cos(c_ang), self.y + current_radius * math.sin(c_ang))
                p2 = (self.x + current_radius * math.cos(c_ang + 2.0*math.pi/3.0), self.y + current_radius * math.sin(c_ang + 2.0*math.pi/3.0))
                p3 = (self.x + current_radius * math.cos(c_ang + 4.0*math.pi/3.0), self.y + current_radius * math.sin(c_ang + 4.0*math.pi/3.0))
                batch.add_polygon([p1, p2, p3], self.color, closed=True)

        elif self.proj_type == "flame":
            fade_pct = self.lifetime / self.max_lifetime
            r, g, b = self.color
            dim_color = (r * fade_pct, g * fade_pct, b * fade_pct)
            flame_size = self.radius * (0.4 + 0.6 * fade_pct)
            batch.add_circle(self.x, self.y, flame_size, dim_color, segments=6)

        elif self.proj_type == "blade":
            # Spinning circular vector sawblade
            angle = (self.lifetime * 15.0) % (math.pi * 2)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            points = []
            for i in range(8):
                ang_step = i * (math.pi / 4.0)
                rad = self.radius if i % 2 == 0 else self.radius * 0.4
                points.append((rad * math.cos(ang_step), rad * math.sin(ang_step)))
            rot_points = []
            for px, py in points:
                rx = px * cos_a - py * sin_a
                ry = px * sin_a + py * cos_a
                rot_points.append((self.x + rx, self.y + ry))
            batch.add_polygon(rot_points, self.color, closed=True)

        elif self.proj_type == "missile":
            # Draw missile arrowhead facing its velocity direction
            vel_len = math.sqrt(self.dx * self.dx + self.dy * self.dy)
            if vel_len > 0:
                vx = self.dx / vel_len
                vy = self.dy / vel_len
                cos_a = vx
                sin_a = vy
                
                nose = (self.radius * 1.8, 0.0)
                left = (-self.radius, -self.radius * 0.7)
                right = (-self.radius, self.radius * 0.7)
                aft = (-self.radius * 0.4, 0.0)
                
                points = [nose, right, aft, left]
                rot_points = []
                for px, py in points:
                    rx = px * cos_a - py * sin_a
                    ry = px * sin_a + py * cos_a
                    rot_points.append((self.x + rx, self.y + ry))
                batch.add_polygon(rot_points, self.color, closed=True)
                
                # Flickering thrust trail
                flame_len = self.radius * (0.8 + random.uniform(0.0, 0.7))
                f_tip = (-self.radius - flame_len, 0.0)
                f_left = (-self.radius, -self.radius * 0.3)
                f_right = (-self.radius, self.radius * 0.3)
                flame_pts = [f_left, f_tip, f_right]
                rot_flame = []
                for px, py in flame_pts:
                    rx = px * cos_a - py * sin_a
                    ry = px * sin_a + py * cos_a
                    rot_flame.append((self.x + rx, self.y + ry))
                from config import COLOR_AMBER
                batch.add_polygon(rot_flame, COLOR_AMBER, closed=True)
            else:
                batch.add_circle(self.x, self.y, self.radius, self.color)

        elif self.proj_type == "slash":
            # Melee energy sweep arc
            fade_pct = self.lifetime / self.max_lifetime
            r, g, b = self.color
            dim_color = (r * fade_pct, g * fade_pct, b * fade_pct)
            base_angle = math.atan2(self.dy, self.dx)
            sweep = math.radians(65.0)
            steps = 12
            arc_pts = []
            for i in range(steps + 1):
                angle = base_angle - sweep + (i / steps) * (sweep * 2.0)
                arc_pts.append((
                    self.x + self.radius * math.cos(angle),
                    self.y + self.radius * math.sin(angle)
                ))
            # Draw arc outline
            for i in range(len(arc_pts) - 1):
                batch.add_line(arc_pts[i][0], arc_pts[i][1], arc_pts[i+1][0], arc_pts[i+1][1], dim_color)
            # Wedge shape borders pointing to player
            batch.add_line(self.x, self.y, arc_pts[0][0], arc_pts[0][1], dim_color)
            batch.add_line(self.x, self.y, arc_pts[-1][0], arc_pts[-1][1], dim_color)

        elif self.proj_type == "lightning":
            if self.beam_start and self.beam_end:
                fade_pct = self.lifetime / self.max_lifetime
                r, g, b = self.color
                dim_color = (r * fade_pct, g * fade_pct, b * fade_pct)
                white_dim = (fade_pct, fade_pct, fade_pct)
                
                # Electric jagged lines
                x1, y1 = self.beam_start
                x2, y2 = self.beam_end
                dx = x2 - x1
                dy = y2 - y1
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 0:
                    nx = -dy / dist
                    ny = dx / dist
                    mid1 = (x1 + dx * 0.25, y1 + dy * 0.25)
                    mid2 = (x1 + dx * 0.5, y1 + dy * 0.5)
                    mid3 = (x1 + dx * 0.75, y1 + dy * 0.75)
                    
                    offset1 = random.uniform(-15.0, 15.0)
                    offset2 = random.uniform(-15.0, 15.0)
                    offset3 = random.uniform(-15.0, 15.0)
                    
                    pts = [
                        (x1, y1),
                        (mid1[0] + nx * offset1, mid1[1] + ny * offset1),
                        (mid2[0] + nx * offset2, mid2[1] + ny * offset2),
                        (mid3[0] + nx * offset3, mid3[1] + ny * offset3),
                        (x2, y2)
                    ]
                    
                    t = int(self.thickness)
                    if t <= 1:
                        for i in range(len(pts) - 1):
                            batch.add_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], dim_color)
                            batch.add_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], white_dim)
                    else:
                        step = 0.8
                        for i in range(len(pts) - 1):
                            px = -(pts[i+1][1] - pts[i][1]) / dist
                            py = (pts[i+1][0] - pts[i][0]) / dist
                            for k in range(t):
                                offset = k - (t - 1) / 2.0
                                ox = px * offset * step
                                oy = py * offset * step
                                batch.add_line(pts[i][0] + ox, pts[i][1] + oy, pts[i+1][0] + ox, pts[i+1][1] + oy, dim_color)
                                batch.add_line(pts[i][0] + ox, pts[i][1] + oy, pts[i+1][0] + ox, pts[i+1][1] + oy, white_dim)

        elif self.proj_type == "laser_drone":
            vel_len = math.sqrt(self.dx * self.dx + self.dy * self.dy)
            cos_a, sin_a = (self.dx / vel_len, self.dy / vel_len) if vel_len > 0 else (1.0, 0.0)
            
            r = self.radius
            points = [(r * 1.5, 0.0), (-r, -r), (-r * 0.4, 0.0), (-r, r)]
            rot_points = []
            for px, py in points:
                rx = px * cos_a - py * sin_a
                ry = px * sin_a + py * cos_a
                rot_points.append((self.x + rx, self.y + ry))
            batch.add_polygon(rot_points, self.color, closed=True)
            batch.add_line(self.x + r * 1.5 * cos_a, self.y + r * 1.5 * sin_a, self.x + r * 2.2 * cos_a, self.y + r * 2.2 * sin_a, COLOR_WHITE)

        elif self.proj_type == "rocket_drone":
            vel_len = math.sqrt(self.dx * self.dx + self.dy * self.dy)
            cos_a, sin_a = (self.dx / vel_len, self.dy / vel_len) if vel_len > 0 else (1.0, 0.0)
            
            r = self.radius
            points = [(r, 0.0), (r * 0.5, -r * 0.8), (-r * 0.5, -r * 0.8), (-r, 0.0), (-r * 0.5, r * 0.8), (r * 0.5, r * 0.8)]
            rot_points = []
            for px, py in points:
                rx = px * cos_a - py * sin_a
                ry = px * sin_a + py * cos_a
                rot_points.append((self.x + rx, self.y + ry))
            batch.add_polygon(rot_points, self.color, closed=True)
            for side in (-1.0, 1.0):
                lx1 = (-r * 0.6) * cos_a - (r * 0.9 * side) * sin_a
                ly1 = (-r * 0.6) * sin_a + (r * 0.9 * side) * cos_a
                lx2 = (r * 0.6) * cos_a - (r * 0.9 * side) * sin_a
                ly2 = (r * 0.6) * sin_a + (r * 0.9 * side) * cos_a
                batch.add_line(self.x + lx1, self.y + ly1, self.x + lx2, self.y + ly2, self.color)

        elif self.proj_type == "heal_drone":
            r = self.radius
            batch.add_circle(self.x, self.y, r, self.color, segments=12)
            batch.add_line(self.x - r * 0.6, self.y, self.x + r * 0.6, self.y, (0.2, 1.0, 0.4))
            batch.add_line(self.x, self.y - r * 0.6, self.x, self.y + r * 0.6, (0.2, 1.0, 0.4))

        elif self.proj_type == "brimstone":
            if self.beam_start and self.beam_end:
                fade_pct = self.lifetime / self.max_lifetime
                r, g, b = self.color
                dim_color = (r * fade_pct, g * fade_pct, b * fade_pct)
                x1, y1 = self.beam_start
                x2, y2 = self.beam_end
                dx = x2 - x1
                dy = y2 - y1
                dist = math.sqrt(dx*dx + dy*dy)
                if dist > 0:
                    px = -dy / dist * self.radius
                    py = dx / dist * self.radius
                    p1 = (x1 - px, y1 - py)
                    p2 = (x1 + px, y1 + py)
                    p3 = (x2 + px, y2 + py)
                    p4 = (x2 - px, y2 - py)
                    batch.add_polygon([p1, p2, p3, p4], dim_color, closed=True)
                    batch.add_line(x1, y1, x2, y2, (fade_pct, fade_pct, fade_pct))

        elif self.proj_type == "ring":
            batch.add_circle(self.x, self.y, self.radius, self.color, segments=24)
            batch.add_circle(self.x, self.y, max(1.0, self.radius - 2.0), (1.0, 1.0, 1.0), segments=16)

        elif self.proj_type == "knife":
            if self.owner:
                cos_a = math.cos(self.owner.angle)
                sin_a = math.sin(self.owner.angle)
                pts = [
                    (15.0, 0.0),    # Tip
                    (-10.0, 4.0),   # Base left
                    (-10.0, -4.0),  # Base right
                ]
                rot_pts = []
                for px, py in pts:
                    rx = px * cos_a - py * sin_a
                    ry = px * sin_a + py * cos_a
                    rot_pts.append((self.x + rx, self.y + ry))
                batch.add_polygon(rot_pts, self.color, closed=True)
                batch.add_line(rot_pts[1][0], rot_pts[1][1], rot_pts[0][0], rot_pts[0][1], (1.0, 1.0, 1.0))

        elif self.proj_type in ("rainbow", "rainbow_fire"):
            batch.add_circle(self.x, self.y, self.radius, self.color, segments=12)
            batch.add_circle(self.x, self.y, max(1.0, self.radius * 0.45), (1.0, 1.0, 1.0), segments=8)

        elif self.proj_type == "meteor":
            # Draw main burning rock body
            batch.add_circle(self.x, self.y, self.radius, self.color, segments=16)
            batch.add_circle(self.x, self.y, self.radius * 0.6, (1.0, 0.9, 0.2), segments=12)
            # Add cometary flame tails trailing behind velocity direction
            vel_len = math.sqrt(self.dx * self.dx + self.dy * self.dy)
            if vel_len > 0:
                ux = self.dx / vel_len
                uy = self.dy / vel_len
                r = self.radius
                # Draw three flame tail lines trailing behind
                batch.add_line(self.x - ux * r, self.y - uy * r, self.x - ux * r * 2.5, self.y - uy * r * 2.5, (1.0, 0.3, 0.0))
                batch.add_line(self.x - ux * r + uy * r * 0.5, self.y - uy * r + ux * r * 0.5, self.x - ux * r * 2.0, self.y - uy * r * 2.0, (1.0, 0.5, 0.0))
                batch.add_line(self.x - ux * r - uy * r * 0.5, self.y - uy * r - ux * r * 0.5, self.x - ux * r * 2.0, self.y - uy * r * 2.0, (1.0, 0.5, 0.0))

