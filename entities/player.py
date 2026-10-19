# entities/player.py
import math
import random
from config import (
    COLOR_WHITE, COLOR_AMBER, COLOR_GREEN,
    PLAYER_START_HEALTH, PLAYER_START_SPEED, PLAYER_START_MAGNET,
    get_xp_threshold
)

class Player:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)
        self.radius = 10.0
        
        # Stats
        self.max_health = PLAYER_START_HEALTH
        self.health = self.max_health
        self.base_speed = PLAYER_START_SPEED
        self.speed_mult = 1.0
        self.mining_speed = 1.0
        self.mining_slowdown = False
        self.magnet_radius = PLAYER_START_MAGNET
        self.armor = 0.0  # Flat damage reduction
        self.damage_mult = 1.0 # Percent damage increase
        self.xp_mult = 1.0 # Percent XP increase
        
        # Movement orientation
        self.angle = -math.pi / 2  # Pointing up initially
        self.move_dir_x = 0.0
        self.move_dir_y = -1.0
        self.is_moving = False
        
        # Progression
        self.level = 1
        self.xp = 0
        self.xp_needed = get_xp_threshold(self.level)
        self.kills = 0
        
        # Equipment/Stuff
        self.primary_weapons = []
        self.accessories = []
        self.passives = {} # name -> level
        
        # Projectile & Fire Rate modifiers (Isaac style)
        self.proj_size_mult = 1.0
        self.proj_speed_mult = 1.0
        self.proj_count_mod = 0
        self.proj_homing = 0.0      # Homing strength (e.g. 2.0 to 8.0)
        self.proj_bounce = 0        # Bounces
        self.proj_pierce_mod = 0    # Extra pierce
        self.proj_split = 0         # Split levels (Parasite style)
        self.cooldown_mult = 1.0    # Weapon cooldown multiplier (lower is faster fire rate)
        self.god_mode = False
        self.flame_timer = 0.0
        self.pending_drops = []
        self.hyperspace_energy = 50.0 # start at 50%
        self.hyperspace_active = False
        self.trail_history = []
        self.iframe_timer = 0.0
        self.active_item = None
        self.active_item_level = 0
        self.active_charge = 0.0
        self.previous_kills = 0

    def xp_earned(self, amount, x, y):
        # Translate large enemy score_value (10, 25, 60, 500) to actual progression XP values (1, 3, 8, 50)
        xp_val = 1
        if amount == 25:
            xp_val = 3
        elif amount == 60:
            xp_val = 8
        elif amount == 500:
            xp_val = 50
        elif amount > 1:
            if amount < 10:
                xp_val = amount
            else:
                xp_val = int(amount / 10)
        self.pending_drops.append({"x": float(x), "y": float(y), "type": "xp", "value": xp_val})

    @property
    def weapons(self):
        res = []
        res.extend(self.primary_weapons)
        res.extend(self.accessories)
        return res

    @property
    def speed(self):
        mult = self.speed_mult
        if getattr(self, 'mining_slowdown', False):
            mult *= 0.35  # Apply 65% speed penalty while drilling/mining
        if self.hyperspace_active:
            mult *= 3.0
        return self.base_speed * mult

    def update(self, dt, dx, dy):
        self.flame_timer += dt
        self.iframe_timer = max(0.0, self.iframe_timer - dt)
        
        # Record trail history
        self.trail_history.append((self.x, self.y, self.angle))
        if len(self.trail_history) > 6:
            self.trail_history.pop(0)
        
        # Move
        move_len = math.sqrt(dx * dx + dy * dy)
        if move_len > 0:
            self.is_moving = True
            # Normalize movement
            ndx = dx / move_len
            ndy = dy / move_len
            
            self.x += ndx * self.speed * dt
            self.y += ndy * self.speed * dt
            
            # Update orientation
            self.angle = math.atan2(ndy, ndx)
            self.move_dir_x = ndx
            self.move_dir_y = ndy
        else:
            self.is_moving = False

    def take_damage(self, amount):
        if self.god_mode or self.hyperspace_active or self.iframe_timer > 0.0:
            return
        # Set short invulnerability phase
        self.iframe_timer = 0.5
        # Apply armor reduction (cap at 80% reduction)
        reduced_damage = max(1.0, amount - self.armor)
        self.health -= reduced_damage
        if self.health < 0:
            self.health = 0

    def add_xp(self, amount):
        """Adds XP. Returns True if leveled up."""
        self.xp += int(amount * self.xp_mult)
        leveled_up = False
        while self.xp >= self.xp_needed:
            self.xp -= self.xp_needed
            self.level += 1
            self.xp_needed = get_xp_threshold(self.level)
            leveled_up = True
        return leveled_up

    def draw(self, batch):
        # Blink ship if in invulnerability frames
        if self.iframe_timer > 0.0 and int(self.iframe_timer * 18.0) % 2 == 0:
            return
        from entities.shapes import draw_player_ship
        draw_player_ship(batch, self)
