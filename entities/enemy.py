# entities/enemy.py
import math
import random
from config import COLOR_GREEN, COLOR_AMBER, COLOR_RED, COLOR_WHITE

class Enemy:
    on_killed_callback = None

    def __init__(self, x, y, enemy_type="swarmer", wave_multiplier=1.0):
        self.x = float(x)
        self.y = float(y)
        self.enemy_type = enemy_type
        self.active = True
        self.angle = 0.0
        self.rotation = random.uniform(0.0, math.pi * 2.0)
        self.rot_speed = random.uniform(2.0, 5.0)

        # Import config specifications
        from entities.enemy_config import (
            PREFIXES_STD, PREFIX_TRANSLATIONS, SUFFIX_TRANSLATIONS,
            ENEMY_TEMPLATES, apply_prefix_modifiers
        )

        template = ENEMY_TEMPLATES.get(enemy_type, ENEMY_TEMPLATES["swarmer"])

        # Base Stats
        base_hp = template["base_hp"]
        base_speed = template["base_speed"]
        base_damage = template["base_damage"]
        base_score = template["base_score"]
        base_radius = template["base_radius"]
        self.color = template["color"]
        self.is_spaceship = template["is_spaceship"]
        self.squadron_id = None
        self.weapon_type = template["weapon_type"]
        self.modifiers = template["modifiers"].copy()
        self.shoot_timer = random.uniform(1.2, 3.0)
        self.spawn_timer = 0.0

        if enemy_type == "boss":
            boss_prefixes = ["Cuirasse", "Supreme", "Behemoth", "Leviathan", "Reine de la Ruche", "Sentinelle Omega", "Devastateur du Neant", "Devoreur d'Etoiles"]
            boss_suffixes = ["du Neant", "de l'Eruption Solaire", "de la Nebuleuse Glitch", "de la Matiere Noire", "l'Annihilateur", "le Destructeur de Mondes"]
            self.name = f"{random.choice(boss_prefixes)} {random.choice(boss_suffixes)}"
            self.enemy_class_suffix = "Boss"
        elif template["is_spaceship"]:
            self.name = template["name"]
            self.enemy_class_suffix = template["enemy_class_suffix"]
        else:
            suffix = random.choice(template["suffixes"])
            prefix = random.choice(PREFIXES_STD)
            self.enemy_class_suffix = suffix
            self.name = f"{SUFFIX_TRANSLATIONS[suffix]} {PREFIX_TRANSLATIONS[prefix]}"

        # Apply prefix modifiers to stats and colors
        if not template["is_spaceship"] and enemy_type != "boss":
            self.color, base_hp, base_speed, base_damage, base_radius = apply_prefix_modifiers(
                prefix, self.color, base_hp, base_speed, base_damage, base_radius
            )

        # Final stat scaling
        self.max_health = base_hp * wave_multiplier
        self.speed = base_speed
        self.damage = base_damage
        self.score_value = base_score
        self.radius = base_radius
        self.health = self.max_health

    def update(self, dt, player_x, player_y, other_enemies=None):
        if not self.active:
            return

        self.rotation += self.rot_speed * dt

        # Move toward player (seeking force)
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        target_vx, target_vy = 0.0, 0.0
        if dist > 0:
            target_vx = (dx / dist) * self.speed
            target_vy = (dy / dist) * self.speed

        # Squadron flocking behaviors
        if self.is_spaceship and self.squadron_id is not None and other_enemies is not None:
            sep_x, sep_y = 0.0, 0.0
            align_x, align_y = 0.0, 0.0
            coh_x, coh_y = 0.0, 0.0
            
            sq_count = 0
            near_sq = []
            
            for oe in other_enemies:
                if oe == self or not oe.active or not getattr(oe, 'is_spaceship', False):
                    continue
                if oe.squadron_id == self.squadron_id:
                    odx = oe.x - self.x
                    ody = oe.y - self.y
                    odist = math.sqrt(odx*odx + ody*ody)
                    if odist < 180.0:
                        near_sq.append((oe, odx, ody, odist))
            
            if near_sq:
                for oe, odx, ody, odist in near_sq:
                    # Separation: avoid piling up (weight 2.5)
                    if odist < 45.0:
                        if odist > 0.0:
                            sep_x -= (odx / odist) * (45.0 - odist) * 5.0
                            sep_y -= (ody / odist) * (45.0 - odist) * 5.0
                        else:
                            sep_x += random.uniform(-1.0, 1.0) * 10.0
                            sep_y += random.uniform(-1.0, 1.0) * 10.0
                    
                    # Cohesion: stay close to the center
                    coh_x += oe.x
                    coh_y += oe.y
                    
                    # Alignment: face/fly in the same direction
                    align_x += math.cos(oe.angle)
                    align_y += math.sin(oe.angle)
                    
                    sq_count += 1
                
                if sq_count > 0:
                    coh_x = (coh_x / sq_count - self.x) * 0.4
                    coh_y = (coh_y / sq_count - self.y) * 0.4
                    
                    alen = math.sqrt(align_x*align_x + align_y*align_y)
                    if alen > 0:
                        align_x = (align_x / alen) * self.speed * 0.5
                        align_y = (align_y / alen) * self.speed * 0.5
                    
                    # Combine flocking velocities with seeking player velocity
                    target_vx = target_vx * 0.6 + sep_x * 0.5 + coh_x * 0.2 + align_x * 0.3
                    target_vy = target_vy * 0.6 + sep_y * 0.5 + coh_y * 0.2 + align_y * 0.3
                    
                    # Clamp velocity to max speed
                    tv_len = math.sqrt(target_vx*target_vx + target_vy*target_vy)
                    if tv_len > self.speed:
                        target_vx = (target_vx / tv_len) * self.speed
                        target_vy = (target_vy / tv_len) * self.speed

        if target_vx != 0.0 or target_vy != 0.0:
            self.angle = math.atan2(target_vy, target_vx)
            self.x += target_vx * dt
            self.y += target_vy * dt

    def take_damage(self, amount):
        """Reduces health, returns True if killed."""
        self.health -= amount
        if self.health <= 0:
            self.active = False
            if Enemy.on_killed_callback:
                Enemy.on_killed_callback(self.enemy_type)
            return True
        return False

    def draw(self, batch, hyperspace_active=False):
        if not self.active:
            return
        from entities.shapes import draw_enemy_ship
        draw_enemy_ship(batch, self, hyperspace_active)
