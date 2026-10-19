# systems/weapon.py
import math
import random
from config import COLOR_GREEN, COLOR_BLUE, COLOR_AMBER, COLOR_WHITE, COLOR_RED, WINDOW_WIDTH, WINDOW_HEIGHT
from entities.projectile import Projectile

class Weapon:
    def __init__(self, name, damage, cooldown):
        self.name = name
        self.level = 1
        self.max_level = 8
        self.damage = damage
        self.cooldown = cooldown
        self.cooldown_timer = 0.0
        self.is_accessory = False
        self.modifiers = {
            "spread": 0,
            "homing": 0.0,
            "bounce": 0,
            "pierce": 0,
            "thickness": 0,
            "size": 0.0,
            "speed": 0.0
        }

    def update(self, dt, player, enemies, projectiles):
        rate_mult = 0.8 if getattr(player, 'solar_storm_active', False) else 1.0
        if getattr(self, 'is_accessory', False):
            rate_mult *= (1.0 + player.passives.get("DRONE ASSEMBLY", 0) * 0.22)
        self.cooldown_timer -= dt * rate_mult
        if self.cooldown_timer <= 0:
            fired = self.fire(player, enemies, projectiles)
            if fired:
                # Apply player cooldown multiplier (higher fire rate means lower cooldown)
                self.cooldown_timer = self.cooldown * getattr(player, 'cooldown_mult', 1.0)

    def fire(self, player, enemies, projectiles):
        # To be implemented by subclasses
        return False

    def level_up(self):
        self.level += 1
        self.upgrade_stats()

    def upgrade_stats(self):
        pass

    def update_autonomous_drones(self, dt, player, enemies, projectiles, num_drones, color, proj_type="laser_drone", radius=5.0):
        # 1. Initialize or resize drone states
        if not hasattr(self, 'drone_states') or len(self.drone_states) != num_drones:
            self.drone_states = []
            for i in range(num_drones):
                offset_angle = self.angle + i * (2.0 * math.pi / num_drones)
                self.drone_states.append({
                    "x": player.x + self.orbit_radius * math.cos(offset_angle),
                    "y": player.y + self.orbit_radius * math.sin(offset_angle),
                    "vx": 0.0,
                    "vy": 0.0
                })
                
        active_enemies = [e for e in enemies if e.active]
        speed_boost = 1.0 + player.passives.get("HEAVY DRONES", 0) * 0.30
        
        self.drone_positions = []
        for i, drone in enumerate(self.drone_states):
            offset_angle = self.angle + i * (2.0 * math.pi / num_drones)
            # Default orbit position
            tox = player.x + self.orbit_radius * math.cos(offset_angle)
            toy = player.y + self.orbit_radius * math.sin(offset_angle)
            
            fx = 0.0
            fy = 0.0
            
            # Orbit attraction
            p_dx = tox - drone["x"]
            p_dy = toy - drone["y"]
            fx += p_dx * 3.5
            fy += p_dy * 3.5
            
            # Enemy attraction (free roaming following)
            if active_enemies:
                closest_e = None
                min_edist_sq = 300.0 * 300.0
                for e in active_enemies:
                    edx = e.x - drone["x"]
                    edy = e.y - drone["y"]
                    edist_sq = edx * edx + edy * edy
                    if edist_sq < min_edist_sq:
                        min_edist_sq = edist_sq
                        closest_e = e
                
                if closest_e:
                    edx = closest_e.x - drone["x"]
                    edy = closest_e.y - drone["y"]
                    fx += edx * 5.0
                    fy += edy * 5.0
            
            # Separation from other drones of this weapon
            for j, other in enumerate(self.drone_states):
                if i != j:
                    odx = other["x"] - drone["x"]
                    ody = other["y"] - drone["y"]
                    odist_sq = odx * odx + ody * ody
                    if odist_sq < 900.0:  # 30.0 ** 2
                        odist = math.sqrt(odist_sq)
                        repulse = 30.0 - odist
                        if odist > 0:
                            fx -= (odx / odist) * repulse * 15.0
                            fy -= (ody / odist) * repulse * 15.0
                            
            # Hard limit distance leash from player (never drift away and get lost)
            p_x_diff = player.x - drone["x"]
            p_y_diff = player.y - drone["y"]
            tot_p_dist_sq = p_x_diff * p_x_diff + p_y_diff * p_y_diff
            if tot_p_dist_sq > 62500.0:  # 250.0 ** 2
                fx += p_x_diff * 8.0
                fy += p_y_diff * 8.0
                
            # Physics integration
            drone["vx"] += fx * dt
            drone["vy"] += fy * dt
            drone["vx"] *= 0.88
            drone["vy"] *= 0.88
            
            # Speed clamping
            speed_sq = drone["vx"] * drone["vx"] + drone["vy"] * drone["vy"]
            max_speed = 350.0 * speed_boost
            if speed_sq > max_speed * max_speed:
                speed = math.sqrt(speed_sq)
                drone["vx"] = (drone["vx"] / speed) * max_speed
                drone["vy"] = (drone["vy"] / speed) * max_speed
                
            # Position update
            drone["x"] += drone["vx"] * dt
            drone["y"] += drone["vy"] * dt
            
            # Screen clamping (using camera_ref and zoom_ref)
            camera = getattr(player, 'camera_ref', None)
            zoom = getattr(player, 'zoom_ref', 1.0)
            if camera:
                pad = 20.0
                half_w = (WINDOW_WIDTH * 0.5 - pad) / zoom
                half_h = (WINDOW_HEIGHT * 0.5 - pad) / zoom
                left = camera.x - half_w
                right = camera.x + half_w
                top = camera.y - half_h
                bottom = camera.y + half_h
                
                drone["x"] = max(left, min(right, drone["x"]))
                drone["y"] = max(top, min(bottom, drone["y"]))
                
            # Record position for rendering & firing reference
            self.drone_positions.append((drone["x"], drone["y"], offset_angle))
            
            # Spawn stylized drone body representation projectile
            projectiles.append(Projectile(
                x=drone["x"], y=drone["y"], dx=math.cos(offset_angle), dy=math.sin(offset_angle),
                damage=0, speed=0, lifetime=dt * 1.5, pierce=9999,
                proj_type=proj_type, color=color, radius=radius
            ))
# ==========================================
# PRIMARY WEAPONS
# ==========================================

class LaserWeapon(Weapon):
    def __init__(self):
        super().__init__("AUTO-LASER", damage=10, cooldown=0.45)
        self.projectiles_count = 2
        self.is_accessory = False

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 15
            self.cooldown = 0.42
        elif self.level == 3:
            self.projectiles_count = 3
        elif self.level == 4:
            self.damage = 22
            self.cooldown = 0.38
        elif self.level == 5:
            self.projectiles_count = 4
        elif self.level == 6:
            self.damage = 30
            self.cooldown = 0.32
        elif self.level == 7:
            self.projectiles_count = 5
        elif self.level == 8:
            self.damage = 45
            self.cooldown = 0.25
            self.projectiles_count = 6

    def fire(self, player, enemies, projectiles):
        active_enemies = [e for e in enemies if e.active]
        if not active_enemies:
            return False

        # Find closest enemies
        enemies_by_dist = []
        for e in active_enemies:
            dx = e.x - player.x
            dy = e.y - player.y
            dist_sq = dx * dx + dy * dy
            enemies_by_dist.append((dist_sq, e))

        enemies_by_dist.sort(key=lambda item: item[0])
        
        # Multi-shot modifier adds extra targets to Laser
        total_shots = self.projectiles_count + getattr(player, 'proj_count_mod', 0)
        targets = [item[1] for item in enemies_by_dist[:total_shots]]

        # Calculate head/front tip position of player ship
        hx = player.x + math.cos(player.angle) * player.radius
        hy = player.y + math.sin(player.angle) * player.radius

        for target in targets:
            dx = target.x - hx
            dy = target.y - hy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                vx = dx / dist
                vy = dy / dist
                # Spawn laser bullet with player modifier stats starting at the front tip
                projectiles.append(Projectile(
                    x=hx, y=hy,
                    dx=vx, dy=vy,
                    damage=self.damage,
                    speed=600.0 * getattr(player, 'proj_speed_mult', 1.0),
                    lifetime=1.5,
                    pierce=1 + getattr(player, 'proj_pierce_mod', 0),
                    proj_type="laser",
                    color=COLOR_GREEN,
                    radius=4.0 * getattr(player, 'proj_size_mult', 1.0),
                    homing=getattr(player, 'proj_homing', 0.0),
                    bounces=getattr(player, 'proj_bounce', 0),
                    split_level=getattr(player, 'proj_split', 0),
                    owner=player
                ))
        return True


class Railgun(Weapon):
    def __init__(self):
        super().__init__("CANON ELECTROMAGNETIQUE", damage=35, cooldown=1.2)
        self.beam_length = 500.0
        self.beam_width = 8.0
        self.is_accessory = False

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 50
            self.cooldown = 1.15
        elif self.level == 3:
            self.beam_length = 650.0
        elif self.level == 4:
            self.damage = 75
            self.cooldown = 1.05
        elif self.level == 5:
            self.beam_width = 12.0
        elif self.level == 6:
            self.damage = 110
            self.cooldown = 0.95
        elif self.level == 7:
            self.beam_length = 800.0
        elif self.level == 8:
            self.damage = 180
            self.cooldown = 0.80
            self.beam_width = 16.0

    def fire(self, player, enemies, projectiles):
        vx = player.move_dir_x
        vy = player.move_dir_y
        
        if vx == 0 and vy == 0:
            vx = math.cos(player.angle)
            vy = math.sin(player.angle)
            
        length = math.sqrt(vx * vx + vy * vy)
        if length > 0:
            vx /= length
            vy /= length

        # Support Multi-shot (extra beams spread in a cone)
        num_beams = 1 + getattr(player, 'proj_count_mod', 0)
        spread = math.radians(8.0)
        base_angle = math.atan2(vy, vx)

        # Scale size/thickness based on projectile size multiplier
        scaled_width = self.beam_width * getattr(player, 'proj_size_mult', 1.0)
        scaled_length = self.beam_length * getattr(player, 'proj_speed_mult', 1.0) # range scales with speed

        for idx in range(num_beams):
            angle = base_angle + (idx - (num_beams - 1) / 2.0) * spread
            rx = math.cos(angle)
            ry = math.sin(angle)
            
            # Calculate head/front tip position of player ship
            hx = player.x + math.cos(player.angle) * player.radius
            hy = player.y + math.sin(player.angle) * player.radius
            
            x1, y1 = hx, hy
            x2 = hx + rx * scaled_length
            y2 = hy + ry * scaled_length

            p = Projectile(
                x=x1, y=y1,
                dx=rx, dy=ry,
                damage=self.damage,
                speed=0.0,
                lifetime=0.2,
                pierce=9999,
                proj_type="rail",
                color=COLOR_AMBER,
                radius=scaled_width * 0.5,
                bounces=0,
                split_level=0,
                owner=player
            )
            p.beam_start = (x1, y1)
            p.beam_end = (x2, y2)
            
            # Apply damage (accounting for player damage multiplier)
            dmg = self.damage * player.damage_mult
            for enemy in enemies:
                if not enemy.active:
                    continue
                seg_x = x2 - x1
                seg_y = y2 - y1
                elem_x = enemy.x - x1
                elem_y = enemy.y - y1
                
                seg_len_sq = seg_x * seg_x + seg_y * seg_y
                if seg_len_sq > 0:
                    t = (elem_x * seg_x + elem_y * seg_y) / seg_len_sq
                    t = max(0.0, min(1.0, t))
                    closest_x = x1 + t * seg_x
                    closest_y = y1 + t * seg_y
                    
                    dx = enemy.x - closest_x
                    dy = enemy.y - closest_y
                    dist = math.sqrt(dx * dx + dy * dy)
                    
                    if dist < (scaled_width * 0.5 + enemy.radius):
                        if enemy.take_damage(dmg):
                            player.kills += 1
                            player.xp_earned(enemy.score_value, enemy.x, enemy.y)
            projectiles.append(p)
        return True


class RadialShockwave(Weapon):
    def __init__(self):
        super().__init__("ONDE DE CHOC", damage=20, cooldown=2.2)
        self.max_radius = 100.0
        self.is_accessory = False

    def upgrade_stats(self):
        if self.level == 2:
            self.max_radius = 130.0
            self.damage = 30
        elif self.level == 3:
            self.cooldown = 2.1
        elif self.level == 4:
            self.max_radius = 160.0
            self.damage = 45
        elif self.level == 5:
            self.cooldown = 1.9
        elif self.level == 6:
            self.max_radius = 200.0
            self.damage = 65
        elif self.level == 7:
            self.cooldown = 1.7
        elif self.level == 8:
            self.max_radius = 260.0
            self.damage = 95
            self.cooldown = 1.5

    def fire(self, player, enemies, projectiles):
        # Scale range/radius based on projectile size multiplier
        scaled_radius = self.max_radius * getattr(player, 'proj_size_mult', 1.0)
        
        # Double ripple visual if player has multi-shot
        ripples = 1 + min(2, getattr(player, 'proj_count_mod', 0))
        for r_idx in range(ripples):
            p = Projectile(
                x=player.x, y=player.y,
                dx=0, dy=0,
                damage=self.damage,
                speed=0.0,
                lifetime=0.3 + r_idx * 0.1,  # staggered expansion
                pierce=9999,
                proj_type="shockwave",
                color=COLOR_WHITE,
                radius=scaled_radius,
                bounces=0,
                split_level=0,
                owner=player
            )
            projectiles.append(p)

        # Apply damage and pushback to all enemies in range immediately
        dmg = self.damage * player.damage_mult
        for enemy in enemies:
            if not enemy.active:
                continue
            dx = enemy.x - player.x
            dy = enemy.y - player.y
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < scaled_radius:
                push_force = (scaled_radius - dist) * 1.5
                if dist > 0:
                    enemy.x += (dx / dist) * push_force
                    enemy.y += (dy / dist) * push_force
                else:
                    enemy.x += random.choice([-1, 1]) * push_force
                    enemy.y += random.choice([-1, 1]) * push_force
                
                if enemy.take_damage(dmg):
                    player.kills += 1
                    player.xp_earned(enemy.score_value, enemy.x, enemy.y)
        return True


class FlameThrower(Weapon):
    def __init__(self):
        super().__init__("LANCE-FLAMMES", damage=5, cooldown=0.07) # Rapid fire continuous stream
        self.cone_angle = math.radians(22)
        self.is_accessory = False

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 7
            self.cone_angle = math.radians(24)
        elif self.level == 3:
            self.cooldown = 0.08
        elif self.level == 4:
            self.damage = 10
            self.cone_angle = math.radians(26)
        elif self.level == 5:
            self.cooldown = 0.07
        elif self.level == 6:
            self.damage = 14
            self.cone_angle = math.radians(28)
        elif self.level == 7:
            self.cooldown = 0.06
        elif self.level == 8:
            self.damage = 20
            self.cone_angle = math.radians(30)

    def fire(self, player, enemies, projectiles):
        vx = player.move_dir_x
        vy = player.move_dir_y
        
        if vx == 0 and vy == 0:
            vx = math.cos(player.angle)
            vy = math.sin(player.angle)
            
        length = math.sqrt(vx * vx + vy * vy)
        if length > 0:
            vx /= length
            vy /= length

        base_angle = math.atan2(vy, vx)

        # Calculate head/front tip position of player ship
        hx = player.x + math.cos(player.angle) * player.radius
        hy = player.y + math.sin(player.angle) * player.radius

        # Multi-shot increases density of flames
        num_flames = 1 + getattr(player, 'proj_count_mod', 0)
        for _ in range(num_flames):
            # Spray within a randomized cone
            angle = base_angle + random.uniform(-self.cone_angle, self.cone_angle)
            fdx = math.cos(angle)
            fdy = math.sin(angle)

            # Fire flame particles
            projectiles.append(Projectile(
                x=hx, y=hy,
                dx=fdx, dy=fdy,
                damage=self.damage,
                speed=260.0 * getattr(player, 'proj_speed_mult', 1.0),
                lifetime=0.45,
                pierce=999, # pierces enemies
                proj_type="flame",
                color=COLOR_RED,
                radius=8.0 * getattr(player, 'proj_size_mult', 1.0),
                homing=getattr(player, 'proj_homing', 0.0) * 0.5, # flame homes slightly
                bounces=getattr(player, 'proj_bounce', 0),
                split_level=getattr(player, 'proj_split', 0),
                owner=player
            ))
        return True


class VortexGrenade(Weapon):
    def __init__(self):
        super().__init__("GRENADE VORTEX", damage=35, cooldown=1.4)
        self.vortex_radius = 120.0
        self.is_accessory = False

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 50
            self.cooldown = 2.2
        elif self.level == 3:
            self.vortex_radius = 140.0
        elif self.level == 4:
            self.damage = 70
            self.cooldown = 2.0
        elif self.level == 5:
            self.vortex_radius = 160.0
        elif self.level == 6:
            self.damage = 100
            self.cooldown = 1.8
        elif self.level == 7:
            self.vortex_radius = 180.0
        elif self.level == 8:
            self.damage = 150
            self.cooldown = 1.5
            self.vortex_radius = 210.0

    def fire(self, player, enemies, projectiles):
        active_enemies = [e for e in enemies if e.active]
        if not active_enemies:
            return False

        # Find closest enemy to target
        closest_enemy = None
        min_dist_sq = 999999.0 * 999999.0
        for e in active_enemies:
            dx = e.x - player.x
            dy = e.y - player.y
            dist_sq = dx * dx + dy * dy
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = e

        if not closest_enemy:
            return False

        dx = closest_enemy.x - player.x
        dy = closest_enemy.y - player.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            vx = dx / dist
            vy = dy / dist
        else:
            vx, vy = 1.0, 0.0

        # Calculate head/front tip position of player ship
        hx = player.x + math.cos(player.angle) * player.radius
        hy = player.y + math.sin(player.angle) * player.radius

        # Support Multi-shot (fires extra grenades spread out)
        num_grenades = 1 + getattr(player, 'proj_count_mod', 0)
        spread = math.radians(12.0)
        base_angle = math.atan2(vy, vx)

        for idx in range(num_grenades):
            angle = base_angle + (idx - (num_grenades - 1) / 2.0) * spread
            gdx = math.cos(angle)
            gdy = math.sin(angle)

            # Grenade projectile. When it expires (lifetime=0), it turns into a vortex.
            projectiles.append(Projectile(
                x=hx, y=hy,
                dx=gdx, dy=gdy,
                damage=self.damage,
                speed=350.0 * getattr(player, 'proj_speed_mult', 1.0),
                lifetime=0.8, # grenade travels for 0.8s
                pierce=9999, # doesn't hit enemies directly on path
                proj_type="grenade",
                color=COLOR_AMBER,
                radius=6.0 * getattr(player, 'proj_size_mult', 1.0),
                homing=0.0, # grenade itself does not home
                bounces=getattr(player, 'proj_bounce', 0),
                split_level=getattr(player, 'proj_split', 0),
                owner=player
            ))
        return True


class SpiralBlades(Weapon):
    def __init__(self):
        super().__init__("LAMES SPIRALES", damage=15, cooldown=0.9)
        self.blade_count = 3
        self.is_accessory = False

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 22
            self.blade_count = 4
        elif self.level == 3:
            self.cooldown = 1.4
        elif self.level == 4:
            self.damage = 30
            self.blade_count = 5
        elif self.level == 5:
            self.cooldown = 1.2
        elif self.level == 6:
            self.damage = 42
            self.blade_count = 6
        elif self.level == 7:
            self.cooldown = 1.0
        elif self.level == 8:
            self.damage = 60
            self.blade_count = 8
            self.cooldown = 0.8

    def fire(self, player, enemies, projectiles):
        total_blades = self.blade_count + getattr(player, 'proj_count_mod', 0)
        base_angle = random.uniform(0, math.pi * 2)

        for i in range(total_blades):
            angle = base_angle + i * (math.pi * 2 / total_blades)
            bdx = math.cos(angle)
            bdy = math.sin(angle)

            # Spiral blade projectile.
            # Its position update tracks the player's position and spirals outwards.
            projectiles.append(Projectile(
                x=player.x, y=player.y,
                dx=bdx, dy=bdy,
                damage=self.damage,
                speed=120.0 * getattr(player, 'proj_speed_mult', 1.0),
                lifetime=2.5,
                pierce=9999, # slices through all
                proj_type="blade",
                color=COLOR_BLUE,
                radius=10.0 * getattr(player, 'proj_size_mult', 1.0),
                homing=getattr(player, 'proj_homing', 0.0),
                bounces=getattr(player, 'proj_bounce', 0),
                split_level=getattr(player, 'proj_split', 0),
                owner=player
            ))
        return True


class SeekerMissile(Weapon):
    def __init__(self):
        super().__init__("MISSILE TETE CHERCHEUSE", damage=28, cooldown=0.8)
        self.missiles_count = 1
        self.is_accessory = False

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 38
            self.cooldown = 1.4
        elif self.level == 3:
            self.missiles_count = 2
        elif self.level == 4:
            self.damage = 50
            self.cooldown = 1.3
        elif self.level == 5:
            self.missiles_count = 3
        elif self.level == 6:
            self.damage = 70
            self.cooldown = 1.1
        elif self.level == 7:
            self.missiles_count = 4
        elif self.level == 8:
            self.damage = 100
            self.cooldown = 0.9
            self.missiles_count = 5

    def fire(self, player, enemies, projectiles):
        active_enemies = [e for e in enemies if e.active]
        if not active_enemies:
            return False

        # Multi-shot shoots additional missiles
        total_missiles = self.missiles_count + getattr(player, 'proj_count_mod', 0)

        # Target closest enemies
        enemies_by_dist = []
        for e in active_enemies:
            dx = e.x - player.x
            dy = e.y - player.y
            dist_sq = dx * dx + dy * dy
            enemies_by_dist.append((dist_sq, e))
        enemies_by_dist.sort(key=lambda item: item[0])
        
        targets = [item[1] for item in enemies_by_dist[:total_missiles]]
        if not targets:
            return False

        # Calculate head/front tip position of player ship
        hx = player.x + math.cos(player.angle) * player.radius
        hy = player.y + math.sin(player.angle) * player.radius

        for idx, target in enumerate(targets):
            dx = target.x - hx
            dy = target.y - hy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                vx = dx / dist
                vy = dy / dist
            else:
                vx, vy = 1.0, 0.0

            # Slight initial spread
            spread_ang = (idx - (len(targets) - 1) / 2.0) * math.radians(15.0)
            cos_s = math.cos(spread_ang)
            sin_s = math.sin(spread_ang)
            rx = vx * cos_s - vy * sin_s
            ry = vx * sin_s + vy * cos_s

            projectiles.append(Projectile(
                x=hx, y=hy,
                dx=rx, dy=ry,
                damage=self.damage,
                speed=300.0 * getattr(player, 'proj_speed_mult', 1.0),
                lifetime=2.5,
                pierce=1, # explodes on first hit
                proj_type="missile",
                color=COLOR_AMBER,
                radius=5.0 * getattr(player, 'proj_size_mult', 1.0),
                homing=5.0 + getattr(player, 'proj_homing', 0.0), # inherently homing
                bounces=getattr(player, 'proj_bounce', 0),
                split_level=getattr(player, 'proj_split', 0),
                owner=player
            ))
        return True


class ScytheSlash(Weapon):
    def __init__(self):
        super().__init__("COUP DE FAUX", damage=45, cooldown=0.8)
        self.slash_range = 140.0
        self.is_accessory = False

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 65
            self.cooldown = 1.4
        elif self.level == 3:
            self.slash_range = 165.0
        elif self.level == 4:
            self.damage = 90
            self.cooldown = 1.3
        elif self.level == 5:
            self.slash_range = 190.0
        elif self.level == 6:
            self.damage = 130
            self.cooldown = 1.1
        elif self.level == 7:
            self.slash_range = 220.0
        elif self.level == 8:
            self.damage = 200
            self.cooldown = 0.9
            self.slash_range = 250.0

    def fire(self, player, enemies, projectiles):
        vx = player.move_dir_x
        vy = player.move_dir_y
        
        if vx == 0 and vy == 0:
            vx = math.cos(player.angle)
            vy = math.sin(player.angle)
            
        length = math.sqrt(vx * vx + vy * vy)
        if length > 0:
            vx /= length
            vy /= length

        base_angle = math.atan2(vy, vx)

        # Scale range with projectile size and speed multipliers
        scaled_range = self.slash_range * getattr(player, 'proj_size_mult', 1.0)
        
        # Fire slash visual sweeps
        # If multi-shot is present, we swing multiple scythes in slightly different directions
        num_slashes = 1 + getattr(player, 'proj_count_mod', 0)
        spread = math.radians(15.0)

        # Calculate head/front tip position of player ship
        hx = player.x + math.cos(player.angle) * player.radius
        hy = player.y + math.sin(player.angle) * player.radius

        for idx in range(num_slashes):
            angle = base_angle + (idx - (num_slashes - 1) / 2.0) * spread
            sdx = math.cos(angle)
            sdy = math.sin(angle)

            p = Projectile(
                x=hx, y=hy,
                dx=sdx, dy=sdy,
                damage=self.damage,
                speed=0.0,
                lifetime=0.15,
                pierce=9999,
                proj_type="slash",
                color=COLOR_WHITE,
                radius=scaled_range,
                bounces=0,
                split_level=0,
                owner=player
            )
            projectiles.append(p)

            # Direct damage to enemies in a 120-degree wedge sector
            dmg = self.damage * player.damage_mult
            for enemy in enemies:
                if not enemy.active:
                    continue
                edx = enemy.x - player.x
                edy = enemy.y - player.y
                dist_sq = edx * edx + edy * edy
                rad_sum = scaled_range + enemy.radius
                if dist_sq < rad_sum * rad_sum:
                    dist = math.sqrt(dist_sq)
                    # Check angle difference
                    enemy_ang = math.atan2(edy, edx)
                    ang_diff = (enemy_ang - angle + math.pi) % (math.pi * 2) - math.pi
                    if abs(ang_diff) < math.radians(60.0): # 120-degree cone
                        # High pushback
                        push = 200.0 * player.proj_speed_mult
                        if dist > 0:
                            enemy.x += (edx / dist) * push * 0.1
                            enemy.y += (edy / dist) * push * 0.1
                        else:
                            enemy.x += sdx * push * 0.1
                            enemy.y += sdy * push * 0.1

                        if enemy.take_damage(dmg):
                            player.kills += 1
                            player.xp_earned(enemy.score_value, enemy.x, enemy.y)
        return True


# ==========================================
# ORBITING ACCESSORIES (DRONES & ORBITALS)
# ==========================================

class DroneShield(Weapon):
    def __init__(self):
        super().__init__("BOUCLIER ORBITAL", damage=12, cooldown=0.0) # always active
        self.orbit_radius = 60.0
        self.rot_speed = 3.0
        self.angle = 0.0
        self.shields_count = 1
        self.is_accessory = True

    def upgrade_stats(self):
        if self.level == 2:
            self.shields_count = 2
            self.damage = 16
        elif self.level == 3:
            self.orbit_radius = 80.0
            self.rot_speed = 3.5
        elif self.level == 4:
            self.shields_count = 3
            self.damage = 22
        elif self.level == 5:
            self.orbit_radius = 100.0
            self.rot_speed = 4.0
        elif self.level == 6:
            self.shields_count = 4
            self.damage = 30
        elif self.level == 7:
            self.orbit_radius = 120.0
            self.rot_speed = 4.5
        elif self.level == 8:
            self.shields_count = 6
            self.damage = 42
            self.rot_speed = 5.0

    def update(self, dt, player, enemies, projectiles):
        self.angle += self.rot_speed * dt
        if self.angle > math.pi * 2:
            self.angle -= math.pi * 2

        # Spawn temporary collision nodes each frame
        scaled_radius = self.orbit_radius * getattr(player, 'proj_speed_mult', 1.0) # radius scales with proj speed mult
        scaled_size = 6.0 * getattr(player, 'proj_size_mult', 1.0)
        
        # Shield count can be increased by multi-shot modifier
        total_shields = self.shields_count + getattr(player, 'proj_count_mod', 0)

        for i in range(total_shields):
            offset = i * (2.0 * math.pi / total_shields)
            sx = player.x + scaled_radius * math.cos(self.angle + offset)
            sy = player.y + scaled_radius * math.sin(self.angle + offset)
            
            p = Projectile(
                x=sx, y=sy,
                dx=0, dy=0,
                damage=self.damage * dt * 4.0, # continuous DPS
                speed=0,
                lifetime=dt * 1.5,
                pierce=9999,
                proj_type="shield",
                color=COLOR_BLUE,
                radius=scaled_size,
                bounces=0,
                split_level=0,
                owner=player
            )
            projectiles.append(p)


class LaserDrone(Weapon):
    def __init__(self):
        super().__init__("DRONE LASER", damage=8, cooldown=1.2)
        self.orbit_radius = 45.0
        self.rot_speed = 2.0
        self.angle = 0.0
        self.is_accessory = True

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 12
            self.cooldown = 1.0
        elif self.level == 3:
            self.orbit_radius = 55.0
        elif self.level == 4:
            self.damage = 18
            self.cooldown = 0.8
        elif self.level == 5:
            self.orbit_radius = 65.0
        elif self.level == 6:
            self.damage = 25
            self.cooldown = 0.6
        elif self.level == 7:
            self.orbit_radius = 75.0
        elif self.level == 8:
            self.damage = 40
            self.cooldown = 0.45

    def update(self, dt, player, enemies, projectiles):
        num_drones = 1 + (self.level - 1) // 2 + player.passives.get("DRONE ASSEMBLY", 0)
        self.update_autonomous_drones(dt, player, enemies, projectiles, num_drones, COLOR_GREEN, proj_type="laser_drone", radius=5.5)
        super().update(dt, player, enemies, projectiles)

    def fire(self, player, enemies, projectiles):
        active_enemies = [e for e in enemies if e.active]
        if not active_enemies:
            return False

        fired_any = False
        # Each drone fires independently towards the nearest enemy from its position
        for dx, dy, dang in getattr(self, 'drone_positions', []):
            closest_enemy = None
            min_dist_sq = 999999.0 * 999999.0
            for e in active_enemies:
                edx = e.x - dx
                edy = e.y - dy
                dist_sq = edx * edx + edy * edy
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_enemy = e

            if closest_enemy:
                edx = closest_enemy.x - dx
                edy = closest_enemy.y - dy
                dist = math.sqrt(edx * edx + edy * edy)
                if dist > 0:
                    vx = edx / dist
                    vy = edy / dist
                    projectiles.append(Projectile(
                        x=dx, y=dy,
                        dx=vx, dy=vy,
                        damage=self.damage * (1.0 + player.passives.get("HEAVY DRONES", 0) * 0.15),
                        speed=500.0 * getattr(player, 'proj_speed_mult', 1.0),
                        lifetime=1.2,
                        pierce=1 + getattr(player, 'proj_pierce_mod', 0),
                        proj_type="laser",
                        color=COLOR_GREEN,
                        radius=3.5 * getattr(player, 'proj_size_mult', 1.0),
                        homing=getattr(player, 'proj_homing', 0.0),
                        bounces=getattr(player, 'proj_bounce', 0),
                        split_level=getattr(player, 'proj_split', 0),
                        owner=player
                    ))
                    fired_any = True
        return fired_any


class RocketDrone(Weapon):
    def __init__(self):
        super().__init__("DRONE ROQUETTE", damage=20, cooldown=1.2)
        self.orbit_radius = 70.0
        self.rot_speed = -1.5 # orbits backward
        self.angle = math.pi
        self.is_accessory = True

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 30
            self.cooldown = 2.0
        elif self.level == 3:
            self.orbit_radius = 80.0
        elif self.level == 4:
            self.damage = 45
            self.cooldown = 1.7
        elif self.level == 5:
            self.orbit_radius = 90.0
        elif self.level == 6:
            self.damage = 65
            self.cooldown = 1.4
        elif self.level == 7:
            self.orbit_radius = 100.0
        elif self.level == 8:
            self.damage = 95
            self.cooldown = 1.1

    def update(self, dt, player, enemies, projectiles):
        num_drones = 1 + (self.level - 1) // 2 + player.passives.get("DRONE ASSEMBLY", 0)
        self.update_autonomous_drones(dt, player, enemies, projectiles, num_drones, COLOR_AMBER, proj_type="rocket_drone", radius=6.5)
        super().update(dt, player, enemies, projectiles)

    def fire(self, player, enemies, projectiles):
        active_enemies = [e for e in enemies if e.active]
        if not active_enemies:
            return False

        fired_any = False
        # Each drone fires independently
        for dx, dy, dang in getattr(self, 'drone_positions', []):
            closest_enemy = None
            min_dist_sq = 999999.0 * 999999.0
            for e in active_enemies:
                edx = e.x - dx
                edy = e.y - dy
                dist_sq = edx * edx + edy * edy
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_enemy = e

            if closest_enemy:
                edx = closest_enemy.x - dx
                edy = closest_enemy.y - dy
                dist = math.sqrt(edx * edx + edy * edy)
                if dist > 0:
                    vx = edx / dist
                    vy = edy / dist
                    projectiles.append(Projectile(
                        x=dx, y=dy,
                        dx=vx, dy=vy,
                        damage=self.damage,
                        speed=280.0 * getattr(player, 'proj_speed_mult', 1.0),
                        lifetime=2.5,
                        pierce=1,
                        proj_type="missile",
                        color=COLOR_AMBER,
                        radius=4.5 * getattr(player, 'proj_size_mult', 1.0),
                        homing=5.0 + getattr(player, 'proj_homing', 0.0),
                        bounces=getattr(player, 'proj_bounce', 0),
                        split_level=getattr(player, 'proj_split', 0),
                        owner=player
                    ))
                    fired_any = True
        return fired_any


class BlackHoleOrbital(Weapon):
    def __init__(self):
        super().__init__("TROU NOIR", damage=10, cooldown=0.0) # Continuous gravity pull and contact damage
        self.orbit_radius = 85.0
        self.rot_speed = 1.2
        self.angle = math.pi / 2.0
        self.pull_range = 130.0
        self.is_accessory = True

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 15
            self.pull_range = 150.0
        elif self.level == 3:
            self.orbit_radius = 95.0
            self.rot_speed = 1.4
        elif self.level == 4:
            self.damage = 22
            self.pull_range = 170.0
        elif self.level == 5:
            self.orbit_radius = 105.0
        elif self.level == 6:
            self.damage = 32
            self.pull_range = 200.0
        elif self.level == 7:
            self.rot_speed = 1.7
        elif self.level == 8:
            self.damage = 48
            self.pull_range = 240.0
            self.orbit_radius = 120.0

    def update(self, dt, player, enemies, projectiles):
        self.angle += self.rot_speed * dt
        self.x = player.x + self.orbit_radius * math.cos(self.angle)
        self.y = player.y + self.orbit_radius * math.sin(self.angle)

        # Draw swirling purple singularity orbital
        p = Projectile(
            x=self.x, y=self.y,
            dx=0, dy=0,
            damage=0, speed=0,
            lifetime=dt * 1.5,
            pierce=9999,
            proj_type="vortex",
            color=(0.5, 0.1, 1.0), # Purple
            radius=15.0 * getattr(player, 'proj_size_mult', 1.0)
        )
        projectiles.append(p)

        # Pull nearby enemies and deal tick damage
        dmg = self.damage * player.damage_mult * dt * 4.0
        scaled_pull_range = self.pull_range * getattr(player, 'proj_speed_mult', 1.0)

        for enemy in enemies:
            if not enemy.active:
                continue
            edx = self.x - enemy.x
            edy = self.y - enemy.y
            dist_sq = edx * edx + edy * edy
            if dist_sq < scaled_pull_range * scaled_pull_range:
                dist = math.sqrt(dist_sq)
                # Gravity force (stronger closer)
                force = (scaled_pull_range - dist) * 1.6 * dt
                if dist > 5.0:
                    enemy.x += (edx / dist) * force
                    enemy.y += (edy / dist) * force
                
                # Contact damage
                if dist < (15.0 + enemy.radius):
                    if enemy.take_damage(dmg):
                        player.kills += 1
                        player.xp_earned(enemy.score_value, enemy.x, enemy.y)


class LightningCoil(Weapon):
    def __init__(self):
        super().__init__("BOBINE TESLA", damage=25, cooldown=3.0)
        self.orbit_radius = 55.0
        self.rot_speed = 2.4
        self.angle = 3.0 * math.pi / 2.0
        self.chain_jumps = 3
        self.is_accessory = True

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 35
            self.cooldown = 2.8
        elif self.level == 3:
            self.chain_jumps = 4
        elif self.level == 4:
            self.damage = 50
            self.cooldown = 2.5
        elif self.level == 5:
            self.chain_jumps = 5
        elif self.level == 6:
            self.damage = 75
            self.cooldown = 2.2
        elif self.level == 7:
            self.chain_jumps = 6
        elif self.level == 8:
            self.damage = 110
            self.cooldown = 1.8
            self.chain_jumps = 8

    def update(self, dt, player, enemies, projectiles):
        self.angle += self.rot_speed * dt
        self.x = player.x + self.orbit_radius * math.cos(self.angle)
        self.y = player.y + self.orbit_radius * math.sin(self.angle)

        # Draw lightning spark drone (yellow dot)
        p = Projectile(
            x=self.x, y=self.y,
            dx=0, dy=0,
            damage=0, speed=0, lifetime=dt * 1.5, pierce=9999,
            proj_type="laser", color=COLOR_AMBER, radius=3.2
        )
        projectiles.append(p)

        super().update(dt, player, enemies, projectiles)

    def fire(self, player, enemies, projectiles):
        active_enemies = [e for e in enemies if e.active]
        if not active_enemies:
            return False

        # Find closest enemy to drone
        enemies_by_dist = []
        for e in active_enemies:
            dx = e.x - self.x
            dy = e.y - self.y
            dist_sq = dx * dx + dy * dy
            enemies_by_dist.append((dist_sq, e))
        enemies_by_dist.sort(key=lambda item: item[0])

        zap_range = 220.0 * getattr(player, 'proj_speed_mult', 1.0)
        
        # Check if first enemy is in range
        if not enemies_by_dist or enemies_by_dist[0][0] > zap_range * zap_range:
            return False

        # Zap chain logic
        curr_x, curr_y = self.x, self.y
        hit_list = set()
        damage_applied = False
        
        dmg = self.damage * player.damage_mult
        
        # Jump from target to target
        for jump_idx in range(self.chain_jumps):
            # Find closest enemy to (curr_x, curr_y) that hasn't been hit yet
            next_target = None
            min_dist_sq = zap_range * zap_range
            
            for e in active_enemies:
                if e in hit_list:
                    continue
                edx = e.x - curr_x
                edy = e.y - curr_y
                dist_sq = edx * edx + edy * edy
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    next_target = e
            
            if next_target:
                hit_list.add(next_target)
                
                # Spawn a lightning visual line projectile between current node and next target
                p = Projectile(
                    x=curr_x, y=curr_y,
                    dx=0, dy=0,
                    damage=self.damage,
                    speed=0.0,
                    lifetime=0.12, # quick flash
                    pierce=9999,
                    proj_type="lightning",
                    color=COLOR_BLUE,
                    radius=2.0,
                    bounces=0,
                    split_level=0,
                    owner=player
                )
                p.beam_start = (curr_x, curr_y)
                p.beam_end = (next_target.x, next_target.y)
                projectiles.append(p)
                
                # Apply damage to enemy
                if next_target.take_damage(dmg):
                    player.kills += 1
                    player.xp_earned(next_target.score_value, next_target.x, next_target.y)
                
                damage_applied = True
                curr_x, curr_y = next_target.x, next_target.y
            else:
                break
                
        return damage_applied


class HealDrone(Weapon):
    def __init__(self):
        super().__init__("DRONE DE SOIN", damage=0, cooldown=5.0) # heals periodically
        self.orbit_radius = 35.0
        self.rot_speed = -2.2
        self.angle = 0.0
        self.is_accessory = True

    def upgrade_stats(self):
        if self.level == 2:
            self.cooldown = 4.7
        elif self.level == 3:
            self.cooldown = 4.4
        elif self.level == 4:
            self.cooldown = 4.0
        elif self.level == 5:
            self.cooldown = 3.6
        elif self.level == 6:
            self.cooldown = 3.2
        elif self.level == 7:
            self.cooldown = 2.8
        elif self.level == 8:
            self.cooldown = 2.4

    def update(self, dt, player, enemies, projectiles):
        speed_boost = 1.0 + player.passives.get("HEAVY DRONES", 0) * 0.30
        self.angle += self.rot_speed * speed_boost * dt
        
        # Calculate active drone fleet size
        num_drones = 1 + (self.level - 1) // 2 + player.passives.get("DRONE ASSEMBLY", 0)
        
        self.drone_positions = []
        for i in range(num_drones):
            offset_angle = self.angle + i * (2.0 * math.pi / num_drones)
            dx = player.x + self.orbit_radius * math.cos(offset_angle)
            dy = player.y + self.orbit_radius * math.sin(offset_angle)
            self.drone_positions.append((dx, dy, offset_angle))
            
            # Spawn stylized heal drone projectile
            projectiles.append(Projectile(
                x=dx, y=dy, dx=math.cos(offset_angle), dy=math.sin(offset_angle),
                damage=0, speed=0, lifetime=dt * 1.5, pierce=9999,
                proj_type="heal_drone", color=COLOR_WHITE, radius=5.0
            ))

        # Boost player flat passive regen based on drone level
        # Heal drone gives a constant passive health regeneration boost: +0.2 HP/sec per level
        player.health = min(player.max_health, player.health + (0.2 * self.level) * dt)

        super().update(dt, player, enemies, projectiles)

    def fire(self, player, enemies, projectiles):
        # Active pulse healing: heals player immediately
        heal_amt = 5.0 * self.level
        player.health = min(player.max_health, player.health + heal_amt)

        # Spawn a green radial visual wave expanding from each heal drone location
        for dx, dy, dang in getattr(self, 'drone_positions', []):
            p = Projectile(
                x=dx, y=dy,
                dx=0, dy=0,
                damage=0,
                speed=0.0,
                lifetime=0.25,
                pierce=9999,
                proj_type="shockwave",
                color=(0.1, 1.0, 0.4), # bright green healing wave
                radius=80.0
            )
            projectiles.append(p)
        return True


class BrimstoneWeapon(Weapon):
    def __init__(self):
        super().__init__("BRIMSTONE", damage=45, cooldown=1.8)
        self.beam_width = 16.0
        self.beam_length = 500.0
        self.is_accessory = False

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 60
            self.cooldown = 1.6
        elif self.level == 3:
            self.beam_length = 600.0
        elif self.level == 4:
            self.damage = 80
            self.beam_width = 22.0
        elif self.level == 5:
            self.cooldown = 1.4
        elif self.level == 6:
            self.damage = 110
            self.beam_length = 700.0
        elif self.level == 7:
            self.beam_width = 28.0
        elif self.level == 8:
            self.damage = 150
            self.cooldown = 1.2
            self.beam_width = 35.0

    def fire(self, player, enemies, projectiles):
        vx = player.move_dir_x
        vy = player.move_dir_y
        if vx == 0 and vy == 0:
            vx = math.cos(player.angle)
            vy = math.sin(player.angle)
            
        length = math.sqrt(vx * vx + vy * vy)
        if length > 0:
            vx /= length
            vy /= length

        scaled_width = self.beam_width * getattr(player, 'proj_size_mult', 1.0)
        scaled_length = self.beam_length * getattr(player, 'proj_speed_mult', 1.0)

        # Trigger Brimstone projectile (beam that lasts for 0.8 seconds)
        p = Projectile(
            x=player.x, y=player.y,
            dx=vx, dy=vy,
            damage=self.damage,
            speed=0.0,
            lifetime=0.8,
            pierce=9999,
            proj_type="brimstone",
            color=(0.9, 0.1, 0.1), # Bright blood red
            radius=scaled_width * 0.5,
            bounces=0,
            split_level=0,
            owner=player
        )
        p.radius_length = scaled_length
        p.beam_start = (player.x, player.y)
        p.beam_end = (player.x + vx * scaled_length, player.y + vy * scaled_length)
        projectiles.append(p)
        return True


class TechXRingWeapon(Weapon):
    def __init__(self):
        super().__init__("TECH X", damage=25, cooldown=1.2)
        self.is_accessory = False

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 35
            self.cooldown = 1.0
        elif self.level == 3:
            self.damage = 45
        elif self.level == 4:
            self.cooldown = 0.9
        elif self.level == 5:
            self.damage = 60
        elif self.level == 6:
            self.cooldown = 0.8
        elif self.level == 7:
            self.damage = 80
        elif self.level == 8:
            self.damage = 110
            self.cooldown = 0.65

    def fire(self, player, enemies, projectiles):
        vx = player.move_dir_x
        vy = player.move_dir_y
        if vx == 0 and vy == 0:
            vx = math.cos(player.angle)
            vy = math.sin(player.angle)
            
        length = math.sqrt(vx * vx + vy * vy)
        if length > 0:
            vx /= length
            vy /= length

        # Support Multi-shot (extra rings)
        num_rings = 1 + getattr(player, 'proj_count_mod', 0)
        spread = math.radians(10.0)
        base_angle = math.atan2(vy, vx)

        # Scale size based on player size multiplier
        size_mult = getattr(player, 'proj_size_mult', 1.0)

        for idx in range(num_rings):
            angle = base_angle + (idx - (num_rings - 1) / 2.0) * spread
            rx = math.cos(angle)
            ry = math.sin(angle)

            hx = player.x + math.cos(player.angle) * player.radius
            hy = player.y + math.sin(player.angle) * player.radius

            p = Projectile(
                x=hx, y=hy,
                dx=rx, dy=ry,
                damage=self.damage,
                speed=220.0 * getattr(player, 'proj_speed_mult', 1.0),
                lifetime=2.5,
                pierce=9999, # pierces all
                proj_type="ring",
                color=(0.1, 0.8, 1.0), # Cyber Cyan
                radius=18.0 * size_mult,
                bounces=getattr(player, 'proj_bounce', 0),
                split_level=0,
                owner=player
            )
            p.base_ring_radius = p.radius
            projectiles.append(p)
        return True


class MomsKnifeWeapon(Weapon):
    def __init__(self):
        super().__init__("COUTEAU DE MAMAN", damage=28, cooldown=1.0)
        self.knife_projectile = None
        self.is_accessory = False

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 38
        elif self.level == 3:
            self.damage = 50
        elif self.level == 4:
            self.damage = 65
        elif self.level == 5:
            self.damage = 85
        elif self.level == 6:
            self.damage = 110
        elif self.level == 7:
            self.damage = 145
        elif self.level == 8:
            self.damage = 200

    def update(self, dt, player, enemies, projectiles):
        # Ensure knife projectile exists and is active in the world
        if self.knife_projectile is None or not self.knife_projectile.active or self.knife_projectile not in projectiles:
            self.knife_projectile = Projectile(
                x=player.x, y=player.y,
                dx=math.cos(player.angle), dy=math.sin(player.angle),
                damage=self.damage,
                speed=0.0,
                lifetime=999999.0, # Infinite
                pierce=9999,
                proj_type="knife",
                color=(0.9, 0.9, 0.9), # Metallic silver/white
                radius=10.0 * getattr(player, 'proj_size_mult', 1.0),
                bounces=0,
                split_level=0,
                owner=player
            )
            projectiles.append(self.knife_projectile)
            
        # Update damage and size to match upgrades and multipliers
        self.knife_projectile.damage = self.damage
        self.knife_projectile.radius = 10.0 * getattr(player, 'proj_size_mult', 1.0)

    def fire(self, player, enemies, projectiles):
        # Firing is handled continuously by update()
        return False


class RoboBabyDrone(Weapon):
    def __init__(self):
        super().__init__("ROBO-BABY", damage=10, cooldown=1.2)
        self.orbit_radius = 50.0
        self.rot_speed = -1.5 # orbits opposite direction of standard drone!
        self.angle = math.pi
        self.is_accessory = True

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 14
            self.cooldown = 1.0
        elif self.level == 3:
            self.orbit_radius = 60.0
        elif self.level == 4:
            self.damage = 20
            self.cooldown = 0.85
        elif self.level == 5:
            self.orbit_radius = 70.0
        elif self.level == 6:
            self.damage = 28
            self.cooldown = 0.7
        elif self.level == 7:
            self.orbit_radius = 80.0
        elif self.level == 8:
            self.damage = 40
            self.cooldown = 0.55

    def update(self, dt, player, enemies, projectiles):
        num_drones = 1 + (self.level - 1) // 2 + player.passives.get("DRONE ASSEMBLY", 0)
        self.update_autonomous_drones(dt, player, enemies, projectiles, num_drones, (0.8, 0.2, 0.2), proj_type="laser_drone", radius=5.0)
        super().update(dt, player, enemies, projectiles)

    def fire(self, player, enemies, projectiles):
        active_enemies = [e for e in enemies if e.active]
        if not active_enemies:
            return False

        fired_any = False
        for dx, dy, angle in getattr(self, 'drone_positions', []):
            closest_enemy = None
            min_dist_sq = 99999.0 * 99999.0
            for e in active_enemies:
                edx = e.x - dx
                edy = e.y - dy
                dist_sq = edx*edx + edy*edy
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_enemy = e
                    
            if closest_enemy:
                ldx = closest_enemy.x - dx
                ldy = closest_enemy.y - dy
                dist = math.sqrt(ldx*ldx + ldy*ldy)
                if dist > 0:
                    ldx /= dist
                    ldy /= dist
                    
                    dmg = self.damage * (1.0 + player.passives.get("HEAVY DRONES", 0) * 0.15)
                    p = Projectile(
                        x=dx, y=dy, dx=ldx, dy=ldy,
                        damage=dmg,
                        speed=550.0 * getattr(player, 'proj_speed_mult', 1.0),
                        lifetime=1.0,
                        pierce=1 + player.passives.get("DRILL TIP", 0),
                        proj_type="laser",
                        color=(0.9, 0.1, 0.1), # Red laser
                        radius=3.5 * getattr(player, 'proj_size_mult', 1.0),
                        homing=player.passives.get("SMART TARGETING", 0) * 1.5,
                        bounces=player.passives.get("BOUNCING MATRIX", 0),
                        split_level=player.passives.get("SHRAPNEL SHELLS", 0),
                        owner=player
                    )
                    projectiles.append(p)
                    fired_any = True
        return fired_any


class FlyDrone(Weapon):
    def __init__(self):
        super().__init__("DRONE INFESTATEUR", damage=15, cooldown=3.0)
        self.orbit_radius = 55.0
        self.rot_speed = 1.0
        self.angle = 0.0
        self.is_accessory = True

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 22
            self.cooldown = 2.7
        elif self.level == 3:
            self.orbit_radius = 65.0
        elif self.level == 4:
            self.damage = 30
            self.cooldown = 2.4
        elif self.level == 5:
            self.orbit_radius = 75.0
        elif self.level == 6:
            self.damage = 42
            self.cooldown = 2.0
        elif self.level == 7:
            self.orbit_radius = 85.0
        elif self.level == 8:
            self.damage = 60
            self.cooldown = 1.6

    def update(self, dt, player, enemies, projectiles):
        num_drones = 1 + (self.level - 1) // 2 + player.passives.get("DRONE ASSEMBLY", 0)
        self.update_autonomous_drones(dt, player, enemies, projectiles, num_drones, (0.1, 0.6, 0.9), proj_type="laser_drone", radius=4.0)
        super().update(dt, player, enemies, projectiles)

    def fire(self, player, enemies, projectiles):
        for dx, dy, angle in getattr(self, 'drone_positions', []):
            dmg = self.damage * (1.0 + player.passives.get("HEAVY DRONES", 0) * 0.15)
            p = Projectile(
                x=dx, y=dy, dx=math.cos(angle), dy=math.sin(angle),
                damage=dmg,
                speed=250.0 * getattr(player, 'proj_speed_mult', 1.0),
                lifetime=3.5,
                pierce=1,
                proj_type="missile", # explodes on contact
                color=(0.1, 0.7, 1.0), # Cyber blue fly
                radius=3.0 * getattr(player, 'proj_size_mult', 1.0),
                homing=12.0, # Extreme homing
                bounces=0,
                split_level=0,
                owner=player
            )
            projectiles.append(p)
        return True


class DryDrone(Weapon):
    def __init__(self):
        super().__init__("DRONE SEC", damage=25, cooldown=1.0)
        self.orbit_radius = 35.0 # orbits very close to player ship!
        self.rot_speed = 2.5
        self.angle = 0.0
        self.is_accessory = True

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 35
        elif self.level == 3:
            self.orbit_radius = 30.0 # orbit even closer for better protection
        elif self.level == 4:
            self.damage = 50
        elif self.level == 5:
            self.damage = 70
        elif self.level == 6:
            self.damage = 100
        elif self.level == 7:
            self.damage = 140
        elif self.level == 8:
            self.damage = 200

    def update(self, dt, player, enemies, projectiles):
        speed_boost = 1.0 + player.passives.get("HEAVY DRONES", 0) * 0.30
        self.angle += self.rot_speed * speed_boost * dt
        
        num_drones = 1 + (self.level - 1) // 3 + player.passives.get("DRONE ASSEMBLY", 0)
        self.drone_positions = []
        for i in range(num_drones):
            offset_angle = self.angle + i * (2.0 * math.pi / num_drones)
            dx = player.x + self.orbit_radius * math.cos(offset_angle)
            dy = player.y + self.orbit_radius * math.sin(offset_angle)
            self.drone_positions.append((dx, dy, offset_angle))
            
            # Draw bone shield-like body (grey skull circle)
            projectiles.append(Projectile(
                x=dx, y=dy, dx=0, dy=0,
                damage=0, speed=0, lifetime=dt * 1.5, pierce=9999,
                proj_type="laser_drone", color=(0.6, 0.6, 0.6), radius=6.0
            ))


# ==========================================
# NEON ABYSS WEAPONS
# ==========================================

class RainbowGatling(Weapon):
    def __init__(self):
        super().__init__("GATLING ARC-EN-CIEL", damage=6, cooldown=0.15)
        self.spread = 0.15
        self.color_idx = 0
        self.colors = [
            (1.0, 0.1, 0.1), # Red
            (1.0, 0.6, 0.1), # Orange
            (1.0, 0.9, 0.1), # Yellow
            (0.1, 1.0, 0.2), # Green
            (0.1, 0.9, 1.0), # Cyan
            (0.2, 0.5, 1.0), # Blue
            (0.8, 0.1, 1.0)  # Purple
        ]

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 8
            self.cooldown = 0.14
        elif self.level == 3:
            self.spread = 0.12
        elif self.level == 4:
            self.damage = 11
            self.cooldown = 0.12
        elif self.level == 5:
            self.spread = 0.08
        elif self.level == 6:
            self.damage = 15
            self.cooldown = 0.10
        elif self.level == 7:
            self.damage = 20
            self.cooldown = 0.08
        elif self.level == 8:
            self.damage = 30
            self.cooldown = 0.06
            self.spread = 0.05

    def fire(self, player, enemies, projectiles):
        active_enemies = [e for e in enemies if e.active]
        if not active_enemies:
            return False

        # Find closest enemy to aim at
        closest_enemy = None
        min_dist_sq = 999999.0 * 999999.0
        for e in active_enemies:
            dx = e.x - player.x
            dy = e.y - player.y
            dist_sq = dx*dx + dy*dy
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = e

        if not closest_enemy:
            return False

        # Direction vector
        edx = closest_enemy.x - player.x
        edy = closest_enemy.y - player.y
        dist = math.sqrt(edx*edx + edy*edy)
        if dist == 0:
            return False
        
        vx = edx / dist
        vy = edy / dist

        # Apply random spread
        angle = math.atan2(vy, vx) + random.uniform(-self.spread, self.spread)
        dx = math.cos(angle)
        dy = math.sin(angle)

        # Get next color in rainbow cycle
        color = self.colors[self.color_idx]
        self.color_idx = (self.color_idx + 1) % len(self.colors)

        # Check synergy: GATLING ARC-EN-CIEL + LANCE-FLAMMES
        has_flame = any(w.name == "LANCE-FLAMMES" for w in player.weapons)
        proj_type = "rainbow_fire" if has_flame else "rainbow"

        # Spawn colorful projectile
        p = Projectile(
            x=player.x, y=player.y,
            dx=dx, dy=dy,
            damage=self.damage * getattr(player, 'proj_damage_mult', 1.0),
            speed=600.0 * getattr(player, 'proj_speed_mult', 1.0),
            lifetime=1.5,
            pierce=1 + getattr(player, 'proj_pierce_mod', 0),
            proj_type=proj_type,
            color=color,
            radius=3.0 * getattr(player, 'proj_size_mult', 1.0),
            homing=getattr(player, 'proj_homing', 0.0),
            bounces=getattr(player, 'proj_bounce', 0),
            split_level=getattr(player, 'proj_split', 0),
            owner=player
        )
        projectiles.append(p)
        return True


class MeteorLauncher(Weapon):
    def __init__(self):
        super().__init__("LANCEUR METEORE", damage=60, cooldown=1.8)
        self.proj_radius = 8.0
        self.proj_speed = 180.0

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 85
            self.cooldown = 1.6
        elif self.level == 3:
            self.proj_radius = 11.0
        elif self.level == 4:
            self.damage = 120
            self.cooldown = 1.4
        elif self.level == 5:
            self.proj_speed = 220.0
        elif self.level == 6:
            self.damage = 170
            self.cooldown = 1.2
        elif self.level == 7:
            self.proj_radius = 15.0
        elif self.level == 8:
            self.damage = 250
            self.cooldown = 1.0
            self.proj_radius = 20.0

    def fire(self, player, enemies, projectiles):
        active_enemies = [e for e in enemies if e.active]
        if not active_enemies:
            return False

        # Target closest enemy
        closest_enemy = None
        min_dist_sq = 999999.0 * 999999.0
        for e in active_enemies:
            dx = e.x - player.x
            dy = e.y - player.y
            dist_sq = dx*dx + dy*dy
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = e

        if not closest_enemy:
            return False

        edx = closest_enemy.x - player.x
        edy = closest_enemy.y - player.y
        dist = math.sqrt(edx*edx + edy*edy)
        if dist == 0:
            return False

        vx = edx / dist
        vy = edy / dist

        # Spawn large bouncing meteor with bounces + 1 minimum bounce for meteor bounce feel!
        p = Projectile(
            x=player.x, y=player.y,
            dx=vx, dy=vy,
            damage=self.damage * getattr(player, 'proj_damage_mult', 1.0),
            speed=self.proj_speed * getattr(player, 'proj_speed_mult', 1.0),
            lifetime=3.0,
            pierce=1, # explodes on first impact
            proj_type="meteor",
            color=(1.0, 0.5, 0.0), # Bright orange meteor
            radius=self.proj_radius * getattr(player, 'proj_size_mult', 1.0),
            homing=getattr(player, 'proj_homing', 0.0),
            bounces=max(1, getattr(player, 'proj_bounce', 0)), # meteors ALWAYS bounce at least once
            split_level=getattr(player, 'proj_split', 0),
            owner=player
        )
        projectiles.append(p)
        return True


class NeonThunderbolt(Weapon):
    def __init__(self):
        super().__init__("ECLAIR DE NEON", damage=15, cooldown=0.9)
        self.chain_jumps = 3

    def upgrade_stats(self):
        if self.level == 2:
            self.damage = 22
            self.cooldown = 0.8
        elif self.level == 3:
            self.chain_jumps = 4
        elif self.level == 4:
            self.damage = 32
            self.cooldown = 0.7
        elif self.level == 5:
            self.chain_jumps = 5
        elif self.level == 6:
            self.damage = 45
            self.cooldown = 0.6
        elif self.level == 7:
            self.chain_jumps = 6
        elif self.level == 8:
            self.damage = 65
            self.cooldown = 0.5
            self.chain_jumps = 8

    def fire(self, player, enemies, projectiles):
        active_enemies = [e for e in enemies if e.active]
        if not active_enemies:
            return False

        # Check synergy: ECLAIR DE NEON + GRENADE VORTEX
        has_vortex_w = any(w.name == "GRENADE VORTEX" for w in player.weapons)
        vortex_proj = None
        if has_vortex_w:
            active_vort = [pr for pr in projectiles if pr.active and pr.proj_type == "vortex"]
            if active_vort:
                vortex_proj = active_vort[0]

        if vortex_proj:
            curr_x, curr_y = vortex_proj.x, vortex_proj.y
            jumps = self.chain_jumps * 2
            zap_range = 450.0 * getattr(player, 'proj_speed_mult', 1.0)
            dmg = self.damage * 1.5 * getattr(player, 'proj_damage_mult', 1.0)
        else:
            # Standard lightning from player
            enemies_by_dist = []
            for e in active_enemies:
                dx = e.x - player.x
                dy = e.y - player.y
                dist_sq = dx * dx + dy * dy
                enemies_by_dist.append((dist_sq, e))
            enemies_by_dist.sort(key=lambda item: item[0])

            zap_range = 250.0 * getattr(player, 'proj_speed_mult', 1.0)
            if not enemies_by_dist or enemies_by_dist[0][0] > zap_range * zap_range:
                return False

            curr_x, curr_y = player.x, player.y
            jumps = self.chain_jumps
            dmg = self.damage * getattr(player, 'proj_damage_mult', 1.0)

        hit_list = set()
        damage_applied = False
        
        for jump_idx in range(jumps):
            next_target = None
            min_dist_sq = zap_range * zap_range
            
            for e in active_enemies:
                if e in hit_list:
                    continue
                edx = e.x - curr_x
                edy = e.y - curr_y
                dist_sq = edx * edx + edy * edy
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    next_target = e
            
            if next_target:
                hit_list.add(next_target)
                
                # Apply damage to target
                if next_target.take_damage(dmg):
                    player.kills += 1
                    player.xp_earned(next_target.score_value, next_target.x, next_target.y)
                
                # Spawn a lightning visual line projectile between current node and next target
                p = Projectile(
                    x=curr_x, y=curr_y,
                    dx=0, dy=0,
                    damage=0,
                    speed=0.0,
                    lifetime=0.12,
                    pierce=9999,
                    proj_type="lightning",
                    color=(1.0, 0.1, 0.9), # Magenta neon lightning
                    radius=2.0 * getattr(player, 'proj_size_mult', 1.0),
                    bounces=0,
                    split_level=0,
                    owner=player
                )
                p.beam_start = (curr_x, curr_y)
                p.beam_end = (next_target.x, next_target.y)
                projectiles.append(p)
                
                curr_x, curr_y = next_target.x, next_target.y
                damage_applied = True
            else:
                break
                
        return damage_applied
