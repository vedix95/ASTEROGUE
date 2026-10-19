# main.py
import pygame
import moderngl
import numpy as np
import math
import random
import sys
import json
import os


SAVE_FILE = "save_data.json"

def load_save_data():
    default_data = {
        "credits": 0,
        "plasma": 0,
        "cores": 0,
        "upgrades": {
            "hull": 0,
            "engine": 0,
            "damage": 0,
            "magnet": 0,
            "scanner": 0,
            "mining": 0
        }
    }
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                # Ensure all keys exist
                for k, v in default_data.items():
                    if k not in data:
                        data[k] = v
                for k, v in default_data["upgrades"].items():
                    if k not in data["upgrades"]:
                        data["upgrades"][k] = v
                return data
        except Exception as e:
            print("Failed to load save data:", e)
            return default_data
    return default_data

def save_save_data(data):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("Failed to save data:", e)

# Configurations & Assets
from config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, TARGET_FPS,
    COLOR_BLACK, COLOR_GREEN, COLOR_GREEN_DIM, COLOR_AMBER, COLOR_RED, COLOR_WHITE, COLOR_BLUE,
    SPAWN_INTERVAL, MAX_ENEMIES
)
from utils.drawing import LineBatch, draw_grid
from systems.shaders import (
    LINE_VERTEX_SHADER, LINE_FRAGMENT_SHADER,
    POST_PROCESS_VERTEX_SHADER, POST_PROCESS_FRAGMENT_SHADER
)
from systems.camera import Camera

# Highly visible neon cyan color for Asteroids classic vector look
COLOR_CYAN = (0.2, 0.9, 1.0)
camera_rotation_angle = 0.0

UPGRADE_METADATA = {
    "hull": {
        "name": "BLINDAGE DE LA COQUE",
        "desc": "+10% PV Max de base par niveau.",
        "max_lvl": 10
    },
    "engine": {
        "name": "MOTEURS SURCHARGES",
        "desc": "+5% vitesse de deplacement par niveau.",
        "max_lvl": 10
    },
    "damage": {
        "name": "NOYAU DE PUISSANCE",
        "desc": "+5% degats des armes par niveau.",
        "max_lvl": 10
    },
    "magnet": {
        "name": "RECEPTEUR FLUX-MAGNETIQUE",
        "desc": "+15% rayon d'attraction des collectibles par niveau.",
        "max_lvl": 10
    },
    "scanner": {
        "name": "SCANNER DE FLUX XP",
        "desc": "+8% XP gagnee par niveau.",
        "max_lvl": 10
    },
    "mining": {
        "name": "LASER DE FORAGE RAPIDE",
        "desc": "+25% vitesse d'extraction des asteroides par niveau.",
        "max_lvl": 10
    }
}

def get_upgrade_cost(upgrade_key, current_lvl):
    if current_lvl >= 10:
        return None
    credits = 100 + current_lvl * 150 + current_lvl**2 * 75
    plasma = 0 if current_lvl == 0 else int(3 + current_lvl * 5 + current_lvl**2 * 1.5)
    cores = 0 if current_lvl < 3 else int(current_lvl - 2)
    return {"credits": credits, "plasma": plasma, "cores": cores}


# =====================================================================
# SPACE EVENT SYSTEM (OBJECT-ORIENTED STATE PATTERN)
# =====================================================================

class GameContext:
    def __init__(self, player, enemies, projectiles, items, debris, camera, damage_numbers, asteroids, WINDOW_WIDTH, WINDOW_HEIGHT, game_time, spawn_asteroid_fn):
        self.player = player
        self.enemies = enemies
        self.projectiles = projectiles
        self.items = items
        self.debris = debris
        self.camera = camera
        self.damage_numbers = damage_numbers
        self.asteroids = asteroids
        self.WINDOW_WIDTH = WINDOW_WIDTH
        self.WINDOW_HEIGHT = WINDOW_HEIGHT
        self.game_time = game_time
        self.spawn_asteroid_fn = spawn_asteroid_fn

class SpaceEvent:
    def __init__(self, name, duration, announcement):
        self.name = name
        self.duration = duration
        self.announcement = announcement
        
    def start(self, ctx):
        pass
        
    def update(self, dt, ctx):
        pass
        
    def end(self, ctx):
        pass

class AsteroidFieldEvent(SpaceEvent):
    def __init__(self):
        super().__init__("Champ d'asteroides", 24.0, "ATTENTION : ENTREE DANS UN CHAMP D'ASTEROIDES !")
        self.wave_cooldown = 0.0
        
    def spawn_wave(self, ctx, count):
        for i in range(count):
            # Distribute angles evenly around the 360-degree circle
            angle = (i / count) * 2.0 * math.pi + random.uniform(-0.12, 0.12)
            dist = 1150.0 # Spawns just beyond the zoomed-out view boundaries
            ax = ctx.camera.x + math.cos(angle) * dist
            ay = ctx.camera.y + math.sin(angle) * dist
            
            # Select random tier
            choice = random.random()
            if choice < 0.4:
                tier = 3 # Large
            elif choice < 0.75:
                tier = 2 # Medium
            else:
                tier = 1 # Small
                
            ast = ctx.spawn_asteroid_fn(ax, ay, tier=tier)
            ctx.asteroids.append(ast)

    def start(self, ctx):
        ctx.asteroids.clear()
        # Spawn the first massive wave of incoming asteroids immediately!
        self.spawn_wave(ctx, random.randint(22, 28))
        self.wave_cooldown = 6.5
        
    def update(self, dt, ctx):
        self.wave_cooldown -= dt
        active_count = len([a for a in ctx.asteroids if a["active"]])
        
        # Trigger a new wave when active count drops or cooldown expires
        if active_count < 6 or self.wave_cooldown <= 0.0:
            self.spawn_wave(ctx, random.randint(16, 22))
            self.wave_cooldown = 6.5
            
        for ast in ctx.asteroids:
            if not ast["active"]:
                continue
            
            # Continuous homing/steering towards the player ship
            dx = ctx.player.x - ast["x"]
            dy = ctx.player.y - ast["y"]
            dist = math.sqrt(dx*dx + dy*dy)
            if dist > 0:
                target_vx = (dx / dist) * ast["speed"]
                target_vy = (dy / dist) * ast["speed"]
                # Smooth steering adjustment
                ast["vx"] += (target_vx - ast["vx"]) * 0.55 * dt
                ast["vy"] += (target_vy - ast["vy"]) * 0.55 * dt

            ast["x"] += ast["vx"] * dt
            ast["y"] += ast["vy"] * dt
            ast["rotation"] += ast["rot_speed"] * dt
            
            # Despawn if they drift way too far (e.g. past the player and offscreen)
            adx = ast["x"] - ctx.camera.x
            ady = ast["y"] - ctx.camera.y
            if math.sqrt(adx*adx + ady*ady) > 1400.0:
                ast["active"] = False
                continue
                
            # Collision with Player
            pdx = ctx.player.x - ast["x"]
            pdy = ctx.player.y - ast["y"]
            pdist = math.sqrt(pdx*pdx + pdy*pdy)
            if pdist < (ctx.player.radius * 0.45 + ast["radius"] * 0.55):
                ctx.player.take_damage(25.0)
                ast["active"] = False
                for _ in range(14):
                    ctx.debris.append(Debris(ast["x"], ast["y"], COLOR_WHITE))
                
        ctx.asteroids[:] = [a for a in ctx.asteroids if a["active"]]

    def end(self, ctx):
        ctx.asteroids.clear()

class HiveSwarmEvent(SpaceEvent):
    def __init__(self):
        super().__init__("Essaim de la ruche", 18.0, "ATTENTION : ESSAIM DE LA RUCHE EN APPROCHE !")
        self.spawn_timer = 0.0
        
    def update(self, dt, ctx):
        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0:
            self.spawn_timer = 0.38
            wave_mult = 1.0 + (ctx.game_time / 60.0) * 0.20
            # Cluster spawn 8 bugs surrounding player
            for _ in range(8):
                spawn_angle = random.uniform(0, math.pi * 2)
                spawn_dist = max(ctx.WINDOW_WIDTH, ctx.WINDOW_HEIGHT) * 0.75 + 180.0
                sx = ctx.camera.x + math.cos(spawn_angle) * spawn_dist
                sy = ctx.camera.y + math.sin(spawn_angle) * spawn_dist
                etype = random.choice(["swarmer", "chaser"])
                ctx.enemies.append(Enemy(sx, sy, etype, wave_multiplier=wave_mult))

class SolarStormEvent(SpaceEvent):
    def __init__(self):
        super().__init__("Tempete solaire", 20.0, "ATTENTION : TEMPETE ELECTROMAGNETIQUE SOLAIRE !")
        self.arc_timer = 0.0
        
    def start(self, ctx):
        ctx.player.solar_storm_active = True
        
    def update(self, dt, ctx):
        self.arc_timer -= dt
        if self.arc_timer <= 0.0:
            self.arc_timer = random.uniform(0.12, 0.45)
            # Flashing lightning solar arcs across viewport
            x1 = ctx.camera.x + random.uniform(-ctx.WINDOW_WIDTH*0.5, ctx.WINDOW_WIDTH*0.5)
            y1 = ctx.camera.y + random.uniform(-ctx.WINDOW_HEIGHT*0.5, ctx.WINDOW_HEIGHT*0.5)
            cx, cy = x1, y1
            for _ in range(4):
                nx = cx + random.uniform(-60.0, 60.0)
                ny = cy + random.uniform(-60.0, 60.0)
                p = Debris(cx, cy, (0.2, 0.8, 1.0))
                p.vx = 0
                p.vy = 0
                p.lifetime = 0.16
                p.length = math.sqrt((nx-cx)**2 + (ny-cy)**2)
                p.angle = math.atan2(ny-cy, nx-cx)
                ctx.debris.append(p)
                cx, cy = nx, ny
                
    def end(self, ctx):
        ctx.player.solar_storm_active = False

class MagneticStormEvent(SpaceEvent):
    def __init__(self):
        super().__init__("Orage magnetique", 20.0, "ATTENTION : ORAGE MAGNETIQUE ! TRAJECTOIRES PERTURBEES !")
        self.particles_timer = 0.0
        
    def start(self, ctx):
        ctx.player.magnetic_storm_active = True
        
    def update(self, dt, ctx):
        # Spawn floating cyan magnetic field spark lines
        self.particles_timer -= dt
        if self.particles_timer <= 0.0:
            self.particles_timer = 0.15
            for _ in range(3):
                px = ctx.camera.x + random.uniform(-ctx.WINDOW_WIDTH*0.6, ctx.WINDOW_WIDTH*0.6)
                py = ctx.camera.y + random.uniform(-ctx.WINDOW_HEIGHT*0.6, ctx.WINDOW_HEIGHT*0.6)
                p = Debris(px, py, (0.1, 0.9, 1.0)) # cyan sparks
                p.vx = random.uniform(-50.0, 50.0)
                p.vy = random.uniform(-50.0, 50.0)
                p.lifetime = 0.4
                p.length = random.uniform(8.0, 16.0)
                ctx.debris.append(p)
                
    def end(self, ctx):
        ctx.player.magnetic_storm_active = False

class GravityWellEvent(SpaceEvent):
    def __init__(self):
        super().__init__("Puits de gravite", 22.0, "ATTENTION : PUITS DE SINGULARITE GRAVITATIONNELLE DETECTE !")
        self.gx = 0.0
        self.gy = 0.0
        self.grav_radius = 450.0
        self.pull_force = 110.0
        
    def start(self, ctx):
        ang = random.uniform(0, 2*math.pi)
        dist = random.uniform(250.0, 360.0)
        self.gx = ctx.player.x + math.cos(ang) * dist
        self.gy = ctx.player.y + math.sin(ang) * dist
        
    def update(self, dt, ctx):
        # Sweeping visual singularity vortex (dummy drawing projectiles)
        ctx.projectiles.append(Projectile(
            x=self.gx, y=self.gy, dx=0, dy=0,
            damage=0, speed=0, lifetime=dt*1.5, pierce=9999,
            proj_type="vortex", color=(0.5, 0.1, 1.0), radius=55.0
        ))
        
        # Pull player, enemies, items
        for e in ctx.enemies:
            if not e.active:
                continue
            dx = self.gx - e.x
            dy = self.gy - e.y
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < self.grav_radius:
                if dist > 5.0:
                    pull = (1.0 - dist / self.grav_radius) * self.pull_force * dt
                    e.x += (dx / dist) * pull
                    e.y += (dy / dist) * pull
                if dist < 45.0:
                    if e.take_damage(60.0 * dt):
                        ctx.player.kills += 1
                        val = 1 if e.enemy_type == "swarmer" else (3 if e.enemy_type == "chaser" else (8 if e.enemy_type == "stalker" else 45))
                        ctx.items.append(Item(e.x, e.y, "xp", value=val))
                        
        pdx = self.gx - ctx.player.x
        pdy = self.gy - ctx.player.y
        pdist = math.sqrt(pdx*pdx + pdy*pdy)
        if pdist < self.grav_radius:
            if pdist > 5.0:
                pull = (1.0 - pdist / self.grav_radius) * self.pull_force * dt
                ctx.player.x += (pdx / pdist) * pull
                ctx.player.y += (pdy / pdist) * pull
            if pdist < 40.0:
                ctx.player.take_damage(16.0 * dt)
                
        for it in ctx.items:
            if not it.active:
                continue
            idx = self.gx - it.x
            idy = self.gy - it.y
            idist = math.sqrt(idx*idx + idy*idy)
            if idist < self.grav_radius and idist > 5.0:
                pull = (1.0 - idist / self.grav_radius) * self.pull_force * 1.5 * dt
                it.x += (idx / idist) * pull
                it.y += (idy / idist) * pull

class CameraSpinEvent(SpaceEvent):
    def __init__(self):
        super().__init__("Tourbillon de gravite", 10.0, "ATTENTION : TOURBILLON DE GRAVITE MAGNETIQUE DETECTE !")
        self.elapsed = 0.0
        
    def start(self, ctx):
        global camera_rotation_angle
        camera_rotation_angle = 0.0
        
    def update(self, dt, ctx):
        global camera_rotation_angle
        self.elapsed += dt
        # spin speed ramps up from 0 to 8.5 rad/sec
        spin_speed = self.elapsed * 0.85
        camera_rotation_angle += spin_speed * dt
        
    def end(self, ctx):
        global camera_rotation_angle
        camera_rotation_angle = 0.0

class EventManager:
    def __init__(self):
        self.active_event = None
        self.event_timer = 0.0
        self.event_spawn_timer = 6.0
        self.next_event_idx = 0
        self.events_pool = [
            AsteroidFieldEvent,
            HiveSwarmEvent,
            SolarStormEvent,
            MagneticStormEvent,
            GravityWellEvent,
            CameraSpinEvent
        ]
        self.announcement_text = ""
        self.announcement_timer = 0.0
        
    def reset(self):
        self.active_event = None
        self.event_timer = 0.0
        self.event_spawn_timer = 6.0
        self.next_event_idx = 0
        self.announcement_text = ""
        self.announcement_timer = 0.0
        
    def update(self, dt, ctx):
        if self.announcement_timer > 0.0:
            self.announcement_timer -= dt
            
        self.event_spawn_timer -= dt
        if self.event_spawn_timer <= 0.0 and self.active_event is None:
            event_class = self.events_pool[self.next_event_idx]
            self.next_event_idx = (self.next_event_idx + 1) % len(self.events_pool)
            
            self.active_event = event_class()
            self.event_timer = self.active_event.duration
            self.announcement_text = self.active_event.announcement
            self.announcement_timer = 4.0
            
            self.event_spawn_timer = random.uniform(22.0, 36.0)
            self.active_event.start(ctx)
            
        if self.active_event is not None:
            self.active_event.update(dt, ctx)
            self.event_timer -= dt
            if self.event_timer <= 0.0:
                self.active_event.end(ctx)
                self.active_event = None
from systems.upgrade import get_upgrade_pool, apply_upgrade, PASSIVE_NAMES_FR
from systems.weapon import LaserWeapon

# Entities
from entities.player import Player
from entities.enemy import Enemy
from entities.item import Item
from entities.projectile import Projectile

# Simple Debris Particle class for vector explosions
class Debris:
    def __init__(self, x, y, color):
        self.x = float(x)
        self.y = float(y)
        self.length = random.uniform(5.0, 11.0)
        self.angle = random.uniform(0.0, math.pi * 2.0)
        self.rot_speed = random.uniform(-5.0, 5.0)
        
        # Fast radial expansion
        speed = random.uniform(120.0, 320.0)
        vel_angle = random.uniform(0.0, math.pi * 2.0)
        self.vx = math.cos(vel_angle) * speed
        self.vy = math.sin(vel_angle) * speed
        
        self.lifetime = random.uniform(0.4, 0.75)
        self.max_lifetime = self.lifetime
        self.color = color
        self.active = True
        self.shape_type = random.choice([0, 1])

    def update(self, dt):
        # Space friction / air resistance: particles slow down over time
        self.vx *= 0.92
        self.vy *= 0.92
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.rot_speed * dt
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.active = False

    def draw(self, batch):
        if not self.active:
            return
        fade = self.lifetime / self.max_lifetime
        r, g, b = self.color
        dim_color = (r * fade, g * fade, b * fade)
        
        if self.shape_type == 0:
            # Rotating line shard
            dx = math.cos(self.angle) * (self.length * 0.5)
            dy = math.sin(self.angle) * (self.length * 0.5)
            batch.add_line(self.x - dx, self.y - dy, self.x + dx, self.y + dy, dim_color)
        else:
            # Tiny expanding spark diamond
            sz = self.length * 0.28 * fade
            batch.add_line(self.x - sz, self.y, self.x + sz, self.y, dim_color)
            batch.add_line(self.x, self.y - sz, self.x, self.y + sz, dim_color)


def main():
    global WINDOW_WIDTH, WINDOW_HEIGHT
    # 1. Initialize Pygame & OpenGL Context
    pygame.init()
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)

    global WINDOW_WIDTH, WINDOW_HEIGHT
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE)
    pygame.display.set_caption("VECTOR SURVIVOR")
    clock = pygame.time.Clock()

    ctx = moderngl.create_context()
    ctx.viewport = (0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
    ctx.enable(moderngl.BLEND)
    ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE) # Additive blending for glow look

    # 2. Compile shaders
    line_prog = ctx.program(
        vertex_shader=LINE_VERTEX_SHADER,
        fragment_shader=LINE_FRAGMENT_SHADER
    )
    post_prog = ctx.program(
        vertex_shader=POST_PROCESS_VERTEX_SHADER,
        fragment_shader=POST_PROCESS_FRAGMENT_SHADER
    )

    # 3. Setup offscreen framebuffer (FBO) for glow/bloom pass
    fbo_texture = ctx.texture((WINDOW_WIDTH, WINDOW_HEIGHT), 4)
    fbo_texture.filter = (moderngl.LINEAR, moderngl.LINEAR) # Linear filtering helps with blur smoothing
    fbo = ctx.framebuffer(color_attachments=[fbo_texture])

    # 4. Create GPU buffers and VAOs
    # Dynamic VBO for line rendering (up to 100k vertices = 50k lines)
    max_vertices = 100000
    line_vbo = ctx.buffer(reserve=max_vertices * 5 * 4) # 5 floats per vertex (x, y, r, g, b)
    line_vao = ctx.vertex_array(line_prog, [(line_vbo, '2f 3f', 'in_vert', 'in_color')])

    # Static VBO for full-screen quad (for post-processing)
    quad_vertices = np.array([
        -1.0, -1.0,
         1.0, -1.0,
        -1.0,  1.0,
        -1.0,  1.0,
         1.0, -1.0,
         1.0,  1.0,
    ], dtype='f4')
    quad_vbo = ctx.buffer(quad_vertices.tobytes())
    quad_vao = ctx.vertex_array(post_prog, [(quad_vbo, '2f', 'in_vert')])

    # 5. Game States
    STATE_MENU = 0
    STATE_GAMEPLAY = 1
    STATE_LEVEL_UP = 2
    STATE_GAME_OVER = 3
    STATE_DEBUG = 4
    STATE_VICTORY = 5
    STATE_SKILL_TREE = 6
    STATE_INTRO = 7
    STATE_META_UPGRADES = 8
    STATE_SECTOR_TRANSITION = 9
    game_state = STATE_MENU
    intro_timer = 0.0
    
    # Persistent and run variables
    save_data = load_save_data()
    run_credits = 0
    run_plasma = 0
    run_cores = 0
    run_ended = False
    current_sector = 1
    
    # Menu selections
    main_menu_selection = 0
    meta_menu_selection = 0

    def on_enemy_killed(enemy_type):
        nonlocal run_credits, run_cores
        if enemy_type == "swarmer":
            run_credits += 1
        elif enemy_type == "chaser":
            run_credits += 2
        elif enemy_type == "stalker":
            run_credits += 5
        elif enemy_type == "boss":
            run_credits += 50
            run_cores += 1

    Enemy.on_killed_callback = on_enemy_killed

    # Escape Pod variables
    escape_pod = {"x": 0.0, "y": 0.0, "active": False}

    # Floating combat text & arena spawners
    damage_numbers = []
    powerup_spawn_timer = 8.0 # spawn a powerup every 8 seconds in the arena
    event_manager = EventManager()

    # Space Events
    event_type = 0 # 0=none, 1=asteroids, 2=swarm
    event_timer = 0.0
    event_spawn_timer = 6.0 # first event starts in 10 seconds
    event_announcement_timer = 0.0
    event_announcement_text = ""
    asteroids = []

    # Planets (gravitational fields)
    planets = [
        {"x": 1000.0, "y": 1000.0, "radius": 45.0, "gravity_radius": 280.0, "gravity_pull": 80.0, "color": (0.1, 0.6, 0.9)},
        {"x": -1000.0, "y": -1000.0, "radius": 45.0, "gravity_radius": 280.0, "gravity_pull": 80.0, "color": (0.9, 0.4, 0.1)}
    ]

    # Debug / Cheat Options
    debug_page = 0 # 0: cheats, 1: weapons, 2: accessories, 3: passives
    selected_debug_idx = 0
    debug_scroll_offset = 0

    def get_debug_options():
        nonlocal debug_page
        opts = []
        if debug_page == 0:
            opts.append({"name": "MODE DIEU : ACTIF" if (player and player.god_mode) else "MODE DIEU : INACTIF", "action": "toggle_god"})
            opts.append({"name": "REPARER LA COQUE (+100 PV)", "action": "heal"})
            opts.append({"name": "AJOUTER 250 XP (MONTEE DE NIVEAU)", "action": "add_xp"})
            opts.append({"name": "FAIRE APPARAITRE UN BOSS", "action": "spawn_boss"})
            opts.append({"name": "FAIRE APPARAITRE UN ESCADRON", "action": "spawn_squad"})
            opts.append({"name": "FAIRE APPARAITRE UN PORTE-NEFS (CARRIER)", "action": "spawn_carrier"})
            opts.append({"name": "COMPLETER L'OBJECTIF PRINCIPAL", "action": "complete_objective"})
            opts.append({"name": "ELIMINER TOUS LES ENNEMIS", "action": "clear_enemies"})
            opts.append({"name": "MAXIMISER LES ARMES ACTIVES", "action": "max_weapons"})
            opts.append({"name": "MAXIMISER LES PASSIFS ACTIFS", "action": "max_passives"})
            opts.append({"name": "-> ALLER A LA LISTE DES ARMES", "action": "page_weapons"})
            opts.append({"name": "-> ALLER A LA LISTE DES ACCESSOIRES", "action": "page_accessories"})
            opts.append({"name": "-> ALLER A LA LISTE DES PASSIFS", "action": "page_passives"})
        elif debug_page == 1:
            opts.append({"name": "<< ARMES PRIMAIRES (CLIQUER POUR ECHANGER) >>", "action": "nop"})
            from systems.upgrade import PRIMARY_WEAPONS
            for name in PRIMARY_WEAPONS:
                matched_w = [w for w in player.primary_weapons if w.name == name] if player else []
                active = len(matched_w) > 0
                lvl = matched_w[0].level if active else 0
                status = f" (EQUIPE NIV.{lvl})" if active else ""
                opts.append({"name": f"- {name}{status}", "action": "give_weapon", "target": name})
            opts.append({"name": "<- RETOUR AUX TRICHES", "action": "page_cheats"})
        elif debug_page == 2:
            opts.append({"name": "<< ACCESSOIRES (CLIQUER POUR AJOUTER/AMELIORER) >>", "action": "nop"})
            from systems.upgrade import ACCESSORIES
            for name in ACCESSORIES:
                matched = [a for a in player.accessories if a.name == name] if player else []
                lvl = matched[0].level if matched else 0
                status = f" (NIV.{lvl})" if lvl > 0 else " (NON EQUIPE)"
                opts.append({"name": f"- {name}{status}", "action": "give_accessory", "target": name})
            opts.append({"name": "<- RETOUR AUX TRICHES", "action": "page_cheats"})
        elif debug_page == 3:
            opts.append({"name": "<< AMELIORATIONS PASSIVES (CLIQUER POUR AJOUTER/AMELIORER) >>", "action": "nop"})
            from systems.upgrade import PASSIVE_DESCRIPTIONS
            for name in PASSIVE_DESCRIPTIONS:
                lvl = player.passives.get(name, 0) if player else 0
                status = f" (NIV.{lvl}/5)" if lvl > 0 else " (NON DEVERROUILLE)"
                opts.append({"name": f"- {PASSIVE_NAMES_FR.get(name, name)}{status}", "action": "give_passive", "target": name})
            opts.append({"name": "<- RETOUR AUX TRICHES", "action": "page_cheats"})
            
        opts.append({"name": "REPRENDRE LA PARTIE", "action": "resume"})
        return opts

    # 3D spaceship model definition
    SHIP_3D_VERTICES = [
        (18.0, 0.0, 0.0),       # 0: Nose
        (5.0, 4.0, 0.0),        # 1: Right cockpit side
        (5.0, -4.0, 0.0),       # 2: Left cockpit side
        (5.0, 0.0, 4.0),        # 3: Cockpit top (apex)
        (-10.0, 4.0, -1.0),     # 4: Right rear bottom
        (-10.0, -4.0, -1.0),    # 5: Left rear bottom
        (-10.0, 4.0, 1.0),      # 6: Right rear top
        (-10.0, -4.0, 1.0),     # 7: Left rear top
        (-6.0, 0.0, 0.0),       # 8: Rear center indent
        (-12.0, -15.0, -2.0),   # 9: Left wingtip
        (-12.0, 15.0, -2.0),    # 10: Right wingtip
        (-2.0, -4.0, 0.0),      # 11: Left wing front root
        (-6.0, -4.0, 0.0),      # 12: Left wing rear root
        (-2.0, 4.0, 0.0),       # 13: Right wing front root
        (-6.0, 4.0, 0.0),       # 14: Right wing rear root
        (-12.0, 0.0, 7.0),      # 15: Tail fin tip
        (-8.0, 0.0, 1.0),       # 16: Tail fin root front
    ]

    SHIP_3D_EDGES = [
        # Nose to cockpit area
        (0, 1), (0, 2), (0, 3),
        # Cockpit pyramid
        (1, 3), (2, 3), (1, 2),
        # Fuselage main body lines
        (1, 6), (2, 7), (1, 4), (2, 5),
        # Rear structural box
        (4, 6), (5, 7), (6, 8), (7, 8), (4, 8), (5, 8), (6, 7), (4, 5),
        # Left wing
        (11, 9), (12, 9), (11, 12),
        # Right wing
        (13, 10), (14, 10), (13, 14),
        # Tail fin
        (16, 15), (8, 15), (16, 8),
        # Extra connections for rigid wing look
        (1, 11), (2, 13), (4, 12), (5, 14)
    ]

    def draw_3d_player(batch, x, y, time_accum, intro_timer):
        # Calculate rotation angles based on a single smooth 4.0-second interpolation
        t = max(0.0, min(1.0, intro_timer / 4.0)) # 1.0 (start) down to 0.0 (end)
        # Cubic ease-out
        t_ease = t * t * (3.0 - 2.0 * t)
        
        # We start showing the ship from the rear/side, pitch-tilted and rolled,
        # then smoothly rotate to face forward, leveling out.
        rot_x = 0.4 * t_ease
        rot_y = 0.6 * t_ease
        # starts at player.angle + pi + 1.2 (rear/side view) and rotates to player.angle
        rot_z = player.angle + (math.pi + 1.2) * t_ease
        scale = 1.0 + 6.5 * t_ease

        cos_x, sin_x = math.cos(rot_x), math.sin(rot_x)
        cos_y, sin_y = math.cos(rot_y), math.sin(rot_y)
        cos_z, sin_z = math.cos(rot_z), math.sin(rot_z)

        projected = []
        focal_length = 60.0
        distance = 60.0

        for px, py, pz in SHIP_3D_VERTICES:
            px *= scale
            py *= scale
            pz *= scale

            # Rotate around X axis (roll)
            y1 = py * cos_x - pz * sin_x
            z1 = py * sin_x + pz * cos_x
            x1 = px

            # Rotate around Y axis (pitch)
            x2 = x1 * cos_y + z1 * sin_y
            z2 = -x1 * sin_y + z1 * cos_y
            y2 = y1

            # Rotate around Z axis (yaw)
            x3 = x2 * cos_z - y2 * sin_z
            y3 = x2 * sin_z + y2 * cos_z
            z3 = z2

            # Perspective projection
            factor = focal_length / (distance - z3)
            proj_x = x3 * factor
            proj_y = y3 * factor

            projected.append((x + proj_x, y + proj_y))

        # Draw wireframe edges
        for i, j in SHIP_3D_EDGES:
            batch.add_line(projected[i][0], projected[i][1], projected[j][0], projected[j][1], COLOR_WHITE)

    def draw_hud_panel(batch, x, y, w, h, border_color, fill_color=(0.025, 0.12, 0.04)):
        # Draw horizontal lines for scanline-filled semi-transparent panel background
        for cy in range(int(y + 2), int(y + h - 1), 2):
            batch.add_line(x + 1, cy, x + w - 1, cy, fill_color)
        # Draw border outline
        batch.add_rect(x, y, w, h, border_color)

    def draw_centered_text(batch, text, cx, y, scale, color):
        text_w = len(text) * 8.0 * scale * 1.3
        batch.add_text(text, cx - text_w / 2.0, y, scale, color)

    def draw_item_icon(batch, cx, cy, size, name, scale_factor):
        if name == "AUTO-LASER":
            batch.add_line(cx - size, cy, cx + size, cy, COLOR_RED)
            batch.add_line(cx, cy - size, cx, cy + size, COLOR_RED)
        elif name == "CANON ELECTROMAGNETIQUE":
            batch.add_line(cx - size, cy - 4 * scale_factor, cx + size, cy - 4 * scale_factor, COLOR_BLUE)
            batch.add_line(cx - size, cy + 4 * scale_factor, cx + size, cy + 4 * scale_factor, COLOR_BLUE)
            batch.add_line(cx - size * 0.5, cy, cx + size * 0.8, cy, COLOR_WHITE)
        elif name == "ONDE DE CHOC":
            batch.add_circle(cx, cy, 6 * scale_factor, COLOR_AMBER, segments=12)
            batch.add_circle(cx, cy, 12 * scale_factor, COLOR_AMBER, segments=16)
        elif name == "LANCE-FLAMMES":
            batch.add_polygon([(cx, cy - size), (cx - size*0.5, cy + size*0.5), (cx + size*0.5, cy + size*0.5)], (1.0, 0.4, 0.0))
            batch.add_polygon([(cx, cy - size*0.4), (cx - size*0.3, cy + size*0.5), (cx + size*0.3, cy + size*0.5)], (1.0, 0.8, 0.0))
        elif name == "GRENADE VORTEX":
            batch.add_circle(cx, cy, 4 * scale_factor, (0.5, 0.2, 0.8), segments=8)
            batch.add_line(cx - size, cy - size, cx + size, cy + size, (0.5, 0.2, 0.8))
            batch.add_line(cx - size, cy + size, cx + size, cy - size, (0.5, 0.2, 0.8))
        elif name == "LAMES SPIRALES":
            batch.add_line(cx, cy, cx, cy - size, COLOR_WHITE)
            batch.add_line(cx, cy, cx - size*0.86, cy + size*0.5, COLOR_WHITE)
            batch.add_line(cx, cy, cx + size*0.86, cy + size*0.5, COLOR_WHITE)
            batch.add_circle(cx, cy - size, 2 * scale_factor, (0.8, 0.8, 0.8))
            batch.add_circle(cx - size*0.86, cy + size*0.5, 2 * scale_factor, (0.8, 0.8, 0.8))
            batch.add_circle(cx + size*0.86, cy + size*0.5, 2 * scale_factor, (0.8, 0.8, 0.8))
        elif name == "MISSILE TETE CHERCHEUSE":
            batch.add_polygon([(cx, cy - size), (cx - size*0.4, cy + size*0.6), (cx + size*0.4, cy + size*0.6)], (0.8, 0.2, 0.2))
            batch.add_line(cx - size*0.4, cy + size*0.6, cx - size*0.6, cy + size*0.8, (0.8, 0.2, 0.2))
            batch.add_line(cx + size*0.4, cy + size*0.6, cx + size*0.6, cy + size*0.8, (0.8, 0.2, 0.2))
        elif name == "COUP DE FAUX":
            batch.add_polygon([(cx - size, cy + size), (cx - size*0.2, cy - size*0.2), (cx + size, cy - size), (cx + size*0.2, cy + size*0.2)], (0.7, 0.7, 0.8))
        elif name == "BRIMSTONE":
            batch.add_circle(cx - size*0.4, cy, size*0.5, (1.0, 0.1, 0.1), segments=10)
            batch.add_circle(cx + size*0.4, cy, size*0.5, (1.0, 0.1, 0.1), segments=10)
        elif name == "TECH X":
            batch.add_circle(cx, cy, size*0.6, COLOR_WHITE, segments=12)
            batch.add_polygon([(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)], (0.2, 0.8, 1.0))
        elif name == "COUTEAU DE MAMAN":
            batch.add_polygon([(cx - size*0.25, cy - size), (cx + size*0.25, cy - size), (cx, cy + size*0.4)], (0.8, 0.2, 0.2))
            batch.add_line(cx, cy - size, cx, cy - size - 6 * scale_factor, COLOR_WHITE)
            batch.add_line(cx - size*0.4, cy - size, cx + size*0.4, cy - size, COLOR_WHITE)
        elif name == "GATLING ARC-EN-CIEL":
            batch.add_circle(cx, cy, size * 0.4, (1.0, 0.2, 0.2), segments=8)
            batch.add_circle(cx, cy, size * 0.7, (0.2, 1.0, 0.2), segments=12)
            batch.add_circle(cx, cy, size, (0.2, 0.2, 1.0), segments=16)
        elif name == "LANCEUR METEORE":
            batch.add_polygon([(cx - size*0.5, cy - size*0.4), (cx + size*0.5, cy - size*0.6), (cx + size*0.6, cy + size*0.3), (cx - size*0.3, cy + size*0.7), (cx - size*0.7, cy + size*0.2)], (1.0, 0.5, 0.0))
            batch.add_line(cx - size, cy - size, cx - size*0.6, cy - size*0.4, (1.0, 0.2, 0.0))
            batch.add_line(cx - size, cy - size*0.4, cx - size*0.5, cy - size*0.2, (1.0, 0.2, 0.0))
        elif name == "ECLAIR DE NEON":
            batch.add_polygon([(cx - size*0.5, cy - size), (cx + size*0.3, cy - size*0.1), (cx - size*0.2, cy + size*0.1), (cx + size*0.5, cy + size)], (1.0, 0.1, 0.9), closed=False)
        elif name == "BOUCLIER ORBITAL":
            pts = []
            for angle in [0, 60, 120, 180, 240, 300]:
                rad = math.radians(angle)
                pts.append((cx + size * math.cos(rad), cy + size * math.sin(rad)))
            batch.add_polygon(pts, COLOR_BLUE, closed=True)
        elif name == "DRONE LASER":
            batch.add_rect(cx - size*0.5, cy - size*0.5, size, size, COLOR_BLUE)
            batch.add_line(cx, cy, cx + size, cy, COLOR_RED)
        elif name == "DRONE ROQUETTE":
            batch.add_polygon([(cx, cy - size*0.5), (cx - size*0.5, cy + size*0.5), (cx + size*0.5, cy + size*0.5)], COLOR_BLUE)
            batch.add_rect(cx - size*0.2, cy + size*0.5, size*0.4, size*0.3, COLOR_AMBER)
        elif name == "TROU NOIR":
            batch.add_circle(cx, cy, 3 * scale_factor, (0.5, 0.0, 1.0), segments=8)
            batch.add_circle(cx, cy, 7 * scale_factor, (0.4, 0.0, 0.8), segments=12)
            batch.add_circle(cx, cy, 11 * scale_factor, (0.2, 0.0, 0.5), segments=16)
        elif name == "BOBINE TESLA":
            batch.add_polygon([(cx - size*0.5, cy - size), (cx + size*0.2, cy - size*0.2), (cx - size*0.3, cy + size*0.2), (cx + size*0.4, cy + size)], COLOR_BLUE, closed=False)
        elif name == "DRONE DE SOIN":
            batch.add_rect(cx - size*0.5, cy - size*0.5, size, size, COLOR_GREEN)
            batch.add_line(cx - size*0.3, cy, cx + size*0.3, cy, COLOR_WHITE)
            batch.add_line(cx, cy - size*0.3, cx, cy + size*0.3, COLOR_WHITE)
        elif name == "ROBO-BABY":
            batch.add_rect(cx - size*0.6, cy - size*0.4, size*1.2, size*0.8, COLOR_BLUE)
            batch.add_circle(cx - size*0.3, cy, 2 * scale_factor, COLOR_WHITE)
            batch.add_circle(cx + size*0.3, cy, 2 * scale_factor, COLOR_WHITE)
        elif name == "DRONE INFESTATEUR":
            batch.add_circle(cx, cy, size*0.4, (0.2, 0.9, 0.4))
            batch.add_line(cx, cy, cx - size*0.8, cy - size*0.5, COLOR_WHITE)
            batch.add_line(cx, cy, cx + size*0.8, cy - size*0.5, COLOR_WHITE)
        elif name == "DRONE SEC":
            batch.add_polygon([(cx - size*0.5, cy - size*0.5), (cx + size*0.5, cy - size*0.5), (cx + size*0.5, cy), (cx, cy + size), (cx - size*0.5, cy)], COLOR_WHITE)
        elif name == "THRUSTERS":
            batch.add_line(cx - size*0.5, cy, cx, cy - size*0.6, COLOR_WHITE)
            batch.add_line(cx, cy - size*0.6, cx + size*0.5, cy, COLOR_WHITE)
            batch.add_line(cx - size*0.5, cy + size*0.4, cx, cy - size*0.2, COLOR_WHITE)
            batch.add_line(cx, cy - size*0.2, cx + size*0.5, cy + size*0.4, COLOR_WHITE)
        elif name == "NANO-ARMOR":
            batch.add_polygon([(cx - size*0.6, cy - size*0.6), (cx + size*0.6, cy - size*0.6), (cx + size*0.5, cy + size*0.6), (cx - size*0.5, cy + size*0.6)], (0.7, 0.7, 0.7))
        elif name == "XP MAGNET":
            batch.add_polygon([(cx - size*0.4, cy - size*0.6), (cx - size*0.4, cy + size*0.2), (cx + size*0.4, cy + size*0.2), (cx + size*0.4, cy - size*0.6), (cx + size*0.2, cy - size*0.6), (cx + size*0.2, cy), (cx - size*0.2, cy), (cx - size*0.2, cy - size*0.6)], COLOR_AMBER)
        elif name == "OVERDRIVE CORE":
            batch.add_polygon([(cx, cy - size*0.8), (cx + size*0.8, cy + size*0.6), (cx - size*0.8, cy + size*0.6)], COLOR_AMBER)
            batch.add_circle(cx, cy + size*0.1, size*0.3, COLOR_WHITE)
        elif name == "REPAIR DRONES":
            batch.add_line(cx - size*0.6, cy + size*0.6, cx + size*0.4, cy - size*0.4, COLOR_WHITE)
            batch.add_circle(cx + size*0.4, cy - size*0.4, 4 * scale_factor, COLOR_WHITE)
        elif name == "HULL UPGRADE":
            batch.add_polygon([(cx - size*0.5, cy - size*0.6), (cx + size*0.5, cy - size*0.6), (cx + size*0.5, cy), (cx, cy + size*0.7), (cx - size*0.5, cy)], COLOR_WHITE)
        elif name == "GIANT CELLS":
            batch.add_circle(cx - size*0.3, cy - size*0.2, 5 * scale_factor, COLOR_GREEN)
            batch.add_circle(cx + size*0.3, cy - size*0.2, 5 * scale_factor, COLOR_GREEN)
            batch.add_circle(cx, cy + size*0.3, 5 * scale_factor, COLOR_GREEN)
        elif name == "HYPER DRIVE":
            batch.add_polygon([(cx - size*0.6, cy - size*0.5), (cx - size*0.1, cy), (cx - size*0.6, cy + size*0.5)], COLOR_BLUE, closed=False)
            batch.add_polygon([(cx, cy - size*0.5), (cx + size*0.5, cy), (cx, cy + size*0.5)], COLOR_BLUE, closed=False)
        elif name == "SPLIT FIRE":
            batch.add_line(cx, cy + size*0.6, cx - size*0.8, cy - size*0.6, COLOR_WHITE)
            batch.add_line(cx, cy + size*0.6, cx, cy - size*0.8, COLOR_WHITE)
            batch.add_line(cx, cy + size*0.6, cx + size*0.8, cy - size*0.6, COLOR_WHITE)
        elif name == "SMART TARGETING":
            batch.add_circle(cx, cy, size*0.6, COLOR_AMBER, segments=12)
            batch.add_line(cx - size, cy, cx + size, cy, COLOR_AMBER)
            batch.add_line(cx, cy - size, cx, cy + size, COLOR_AMBER)
            batch.add_circle(cx, cy, 1.5 * scale_factor, COLOR_WHITE)
        elif name == "BOUNCING MATRIX":
            batch.add_polygon([(cx - size*0.8, cy + size*0.8), (cx, cy - size*0.8), (cx + size*0.8, cy + size*0.2)], COLOR_WHITE, closed=False)
        elif name == "DRILL TIP":
            batch.add_polygon([(cx, cy + size*0.8), (cx - size*0.5, cy - size*0.8), (cx + size*0.5, cy - size*0.8)], COLOR_WHITE)
            batch.add_line(cx - size*0.3, cy - size*0.2, cx + size*0.3, cy - size*0.2, COLOR_BLACK)
            batch.add_line(cx - size*0.1, cy + size*0.4, cx + size*0.1, cy + size*0.4, COLOR_BLACK)
        elif name == "SHRAPNEL SHELLS":
            batch.add_circle(cx, cy, size*0.4, COLOR_WHITE)
            batch.add_line(cx - size*0.5, cy - size*0.5, cx - size*0.9, cy - size*0.9, COLOR_WHITE)
            batch.add_line(cx + size*0.5, cy - size*0.5, cx + size*0.9, cy - size*0.9, COLOR_WHITE)
            batch.add_line(cx - size*0.5, cy + size*0.5, cx - size*0.9, cy + size*0.9, COLOR_WHITE)
            batch.add_line(cx + size*0.5, cy + size*0.5, cx + size*0.9, cy + size*0.9, COLOR_WHITE)
        elif name == "HEAVY DRONES":
            batch.add_circle(cx, cy, size*0.8, COLOR_BLUE, segments=12)
            batch.add_rect(cx - size*0.4, cy - size*0.4, size*0.8, size*0.8, COLOR_WHITE)
        elif name == "DRONE ASSEMBLY":
            batch.add_rect(cx - size*0.6, cy - size*0.6, size*0.5, size*0.5, COLOR_BLUE)
            batch.add_rect(cx + size*0.1, cy + size*0.1, size*0.5, size*0.5, COLOR_BLUE)
            batch.add_line(cx - size*0.1, cy - size*0.1, cx + size*0.1, cy + size*0.1, COLOR_WHITE)
        elif name == "PLASMA CORE":
            batch.add_circle(cx, cy, 5 * scale_factor, COLOR_AMBER, segments=8)
            batch.add_circle(cx, cy, size*0.8, COLOR_BLUE, segments=16)
        elif name == "TINY PLANET":
            batch.add_circle(cx, cy, 6 * scale_factor, COLOR_AMBER, segments=10)
            batch.add_circle(cx + size*0.7, cy - size*0.2, 2.5 * scale_factor, COLOR_BLUE)
            batch.add_circle(cx, cy, size*0.8, (0.3, 0.3, 0.5), segments=16)
        elif name == "LUMP OF COAL":
            batch.add_polygon([(cx - size*0.5, cy - size*0.6), (cx + size*0.4, cy - size*0.7), (cx + size*0.7, cy + size*0.2), (cx - size*0.2, cy + size*0.8), (cx - size*0.7, cy + size*0.1)], (0.3, 0.3, 0.3))
        elif name == "SACRED HEART":
            batch.add_polygon([(cx, cy + size*0.7), (cx - size*0.7, cy - size*0.1), (cx - size*0.35, cy - size*0.6), (cx, cy - size*0.25), (cx + size*0.35, cy - size*0.6), (cx + size*0.7, cy - size*0.1)], (1.0, 0.2, 0.2))
            batch.add_line(cx, cy - size*0.6, cx, cy - size, COLOR_WHITE)
            batch.add_line(cx - size*0.25, cy - size*0.8, cx + size*0.25, cy - size*0.8, COLOR_WHITE)
        else:
            batch.add_polygon([(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)], COLOR_WHITE)

    # 6. Instantiate managers/entities
    player = None
    camera = Camera()
    current_zoom = 1.8
    user_zoom_mult = 1.0
    enemies = []
    projectiles = []
    items = []
    debris = []
    stars = []

    # Spawning stats
    spawn_timer = 0.0
    game_time = 0.0
    boss_spawned_milestones = set()

    # Objective tracking (DRG style)
    objective_type = "crystal"
    objective_items = []
    objective_needed = 0
    objective_collected = 0
    objective_completed = False
    objective_reward_given = False

    # Upgrade selection overlay
    upgrade_options = []
    selected_upgrade_idx = 0

    # Line batches
    world_batch = LineBatch()
    hud_batch = LineBatch()

    def spawn_asteroid(x=None, y=None, tier=3, ast_type=None):
        # If coordinates are not specified, spawn just off-screen
        if x is None or y is None:
            angle = random.uniform(0, 2.0*math.pi)
            dist = max(WINDOW_WIDTH, WINDOW_HEIGHT) * 0.75 + 150.0
            ax = camera.x + math.cos(angle) * dist
            ay = camera.y + math.sin(angle) * dist
        else:
            ax = x
            ay = y
            
        # Target vectors fly directly towards the player's ship
        vdx = player.x - ax
        vdy = player.y - ay
        vdist = math.sqrt(vdx*vdx + vdy*vdy)
        speed = random.uniform(140.0, 240.0)
        vx = (vdx / vdist) * speed if vdist > 0 else speed
        vy = (vdy / vdist) * speed if vdist > 0 else 0.0
        
        # radius scales with tier
        if tier == 3:
            radius = random.uniform(32.0, 45.0)
        elif tier == 2:
            radius = random.uniform(18.0, 24.0)
        else:
            radius = random.uniform(8.0, 12.0)
            
        # irregular polygon points (jagged vector look with craters/concavities)
        sides = random.randint(8, 12)
        shape_pts = []
        for i in range(sides):
            sang = i * (2.0 * math.pi / sides)
            # 25% chance of deep indentation (crater)
            if random.random() < 0.25:
                r_mod = radius * random.uniform(0.45, 0.65)
            else:
                r_mod = radius * random.uniform(0.8, 1.2)
            shape_pts.append((r_mod * math.cos(sang), r_mod * math.sin(sang)))
            
        if ast_type is None:
            r = random.random()
            if r < 0.65:
                ast_type = "normal"
            elif r < 0.83:
                ast_type = "gold"
            elif r < 0.97:
                ast_type = "plasma"
            else:
                ast_type = "core"
            
        return {
            "x": ax, "y": ay,
            "vx": vx, "vy": vy,
            "speed": speed,
            "radius": radius,
            "shape_pts": shape_pts,
            "rotation": random.uniform(0.0, math.pi * 2.0),
            "rot_speed": random.uniform(-1.2, 1.2),
            "tier": tier,
            "active": True,
            "type": ast_type,
            "health": tier * 5.0
        }

    def destroy_asteroid(ast):
        if not ast["active"]:
            return
        ast["active"] = False
        
        ast_type = ast.get("type", "normal")
        if ast_type == "normal":
            color = (0.7, 0.7, 0.7)
        elif ast_type == "gold":
            color = COLOR_AMBER
        elif ast_type == "plasma":
            color = (0.8, 0.2, 1.0)
        else: # core
            color = (0.2, 0.9, 1.0)

        # Spawn split/destroy text
        text = "BRISE" if ast["tier"] == 1 else "SCINDE"
        damage_numbers.append({"x": ast["x"], "y": ast["y"], "text": text, "timer": 0.50, "color": color})
        
        # Spray particles
        split_ang = random.uniform(0.0, math.pi * 2.0)
        cx = math.cos(split_ang)
        cy = math.sin(split_ang)
        px = -cy
        py = cx
        plen = math.sqrt(px*px + py*py)
        if plen > 0:
            px /= plen
            py /= plen
            
        for k in range(-6, 7):
            offset_dist = (k / 6.0) * ast["radius"]
            dx = ast["x"] + cx * offset_dist
            dy = ast["y"] + cy * offset_dist
            side = 1.0 if k >= 0 else -1.0
            p_vx = px * side * random.uniform(90.0, 180.0) + ast["vx"] * 0.6
            p_vy = py * side * random.uniform(90.0, 180.0) + ast["vy"] * 0.6
            
            deb = Debris(dx, dy, color)
            deb.vx = p_vx
            deb.vy = p_vy
            deb.length = random.uniform(4.0, 8.0)
            debris.append(deb)
            
        # Split into two smaller ones
        if ast["tier"] > 1:
            new_tier = ast["tier"] - 1
            new_radius = ast["radius"] * 0.55
            split_speed = random.uniform(90.0, 160.0)
            
            for factor in (-1.0, 1.0):
                child_x = ast["x"] + px * ast["radius"] * 0.38 * factor
                child_y = ast["y"] + py * ast["radius"] * 0.38 * factor
                child_vx = ast["vx"] * 0.8 + px * split_speed * factor
                child_vy = ast["vy"] * 0.8 + py * split_speed * factor
                child_speed = math.sqrt(child_vx*child_vx + child_vy*child_vy)
                
                sides = random.randint(8, 11)
                s_pts = []
                for i in range(sides):
                    sang = i * (2.0*math.pi/sides)
                    if random.random() < 0.25:
                        rm = new_radius * random.uniform(0.45, 0.65)
                    else:
                        rm = new_radius * random.uniform(0.8, 1.2)
                    s_pts.append((rm*math.cos(sang), rm*math.sin(sang)))
                    
                asteroids.append({
                    "x": child_x, "y": child_y,
                    "vx": child_vx, "vy": child_vy,
                    "speed": child_speed,
                    "radius": new_radius,
                    "shape_pts": s_pts,
                    "rotation": random.uniform(0.0, math.pi*2.0),
                    "rot_speed": random.uniform(-2.0, 2.0),
                    "tier": new_tier,
                    "active": True,
                    "type": ast_type,
                    "health": new_tier * 5.0
                })
        
        # Drops
        from entities.item import Item
        if ast_type == "gold":
            items.append(Item(ast["x"], ast["y"], "credit", value=random.randint(3, 6)))
        elif ast_type == "plasma":
            items.append(Item(ast["x"], ast["y"], "plasma", value=1))
        elif ast_type == "core":
            items.append(Item(ast["x"], ast["y"], "core", value=1))
        else: # normal
            r = random.random()
            if r < 0.35:
                items.append(Item(ast["x"], ast["y"], "xp", value=1))
            elif r < 0.45:
                items.append(Item(ast["x"], ast["y"], "credit", value=2))
            elif r < 0.50:
                items.append(Item(ast["x"], ast["y"], "plasma", value=1))

    # Generate persistent background stars in world space with 3 depth layers
    def generate_stars():
        stars.clear()
        # Spawn stars in a wide arena area
        for _ in range(350): # Increased star count for richer depth density
            sx = random.uniform(-3000.0, 3000.0)
            sy = random.uniform(-3000.0, 3000.0)
            # Pick a layer: 0 = far, 1 = mid, 2 = close
            layer = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
            if layer == 0:
                brightness = random.uniform(0.08, 0.18)
            elif layer == 1:
                brightness = random.uniform(0.20, 0.40)
            else:
                brightness = random.uniform(0.45, 0.70)
            stars.append((sx, sy, brightness, layer))

    def init_level_objective():
        nonlocal objective_type, objective_items, objective_needed, objective_collected, objective_completed, objective_reward_given
        objective_items.clear()
        objective_collected = 0
        objective_completed = False
        objective_reward_given = False
        
        # Pick random space objective
        objective_type = random.choice(["crystal", "egg", "beacon"])
        
        if objective_type == "crystal":
            objective_needed = 35
            for _ in range(objective_needed):
                cx = random.uniform(-1800.0, 1800.0)
                cy = random.uniform(-1800.0, 1800.0)
                while math.sqrt(cx*cx + cy*cy) < 250.0:
                    cx = random.uniform(-1800.0, 1800.0)
                    cy = random.uniform(-1800.0, 1800.0)
                objective_items.append({
                    "x": cx, "y": cy,
                    "type": "crystal",
                    "active": True
                })
        elif objective_type == "egg":
            objective_needed = 5
            for _ in range(objective_needed):
                ex = random.uniform(-1800.0, 1800.0)
                ey = random.uniform(-1800.0, 1800.0)
                while math.sqrt(ex*ex + ey*ey) < 300.0:
                    ex = random.uniform(-1800.0, 1800.0)
                    ey = random.uniform(-1800.0, 1800.0)
                objective_items.append({
                    "x": ex, "y": ey,
                    "type": "egg",
                    "active": True
                })
                # Spawn 3 guard chasers/stalkers around it
                for _ in range(3):
                    gx = ex + random.uniform(-50.0, 50.0)
                    gy = ey + random.uniform(-50.0, 50.0)
                    enemies.append(Enemy(gx, gy, random.choice(["chaser", "stalker"]), wave_multiplier=1.1))
        elif objective_type == "beacon":
            objective_needed = 3
            for i in range(objective_needed):
                # Spread beacons out at angles
                angle = i * (2.0 * math.pi / 3.0) + random.uniform(-0.3, 0.3)
                radius = random.uniform(700.0, 1200.0)
                bx = radius * math.cos(angle)
                by = radius * math.sin(angle)
                objective_items.append({
                    "x": bx, "y": by,
                    "type": "beacon",
                    "progress": 0.0, # 0.0 to 1.0 (100%)
                    "active": True
                })

        # Always spawn 20 plasma crystals for harvesting, regardless of the objective type
        num_plasma_spawns = 20 if objective_type != "crystal" else 0
        for _ in range(num_plasma_spawns):
            cx = random.uniform(-1800.0, 1800.0)
            cy = random.uniform(-1800.0, 1800.0)
            while math.sqrt(cx*cx + cy*cy) < 250.0:
                cx = random.uniform(-1800.0, 1800.0)
                cy = random.uniform(-1800.0, 1800.0)
            objective_items.append({
                "x": cx, "y": cy,
                "type": "harvest_crystal",
                "active": True
            })

    def reset_game(next_sector=False):
        nonlocal player, enemies, projectiles, items, debris, spawn_timer, game_time, boss_spawned_milestones, objective_type, objective_items, objective_needed, objective_collected, objective_completed, objective_reward_given, escape_pod, asteroids, damage_numbers, powerup_spawn_timer, event_manager, current_zoom, user_zoom_mult, intro_timer, run_credits, run_plasma, run_cores, run_ended, save_data, current_sector
        global camera_rotation_angle
        
        # Load save data
        save_data = load_save_data()
        
        if not next_sector:
            current_sector = 1
            player = Player(0.0, 0.0)
            player.primary_weapons = [LaserWeapon()] # Start weapon
            
            # Apply permanent upgrades
            player.meta_hull_level = save_data["upgrades"].get("hull", 0)
            player.meta_engine_level = save_data["upgrades"].get("engine", 0)
            player.meta_damage_level = save_data["upgrades"].get("damage", 0)
            player.meta_magnet_level = save_data["upgrades"].get("magnet", 0)
            player.meta_scanner_level = save_data["upgrades"].get("scanner", 0)
            player.meta_mining_level = save_data["upgrades"].get("mining", 0)

            player.max_health = 100.0 * (1.0 + 0.10 * player.meta_hull_level)
            player.health = player.max_health
            player.speed_mult = 1.0 + 0.05 * player.meta_engine_level
            player.damage_mult = 1.0 + 0.05 * player.meta_damage_level
            player.magnet_radius = 80.0 * (1.0 + 0.15 * player.meta_magnet_level)
            player.xp_mult = 1.0 + 0.08 * player.meta_scanner_level
            player.mining_speed = 1.0 + 0.25 * player.meta_mining_level
            
            # Reset run variables
            run_credits = 0
            run_plasma = 0
            run_cores = 0
            run_ended = False
        else:
            # Transitioning to next sector - keep player, reset coords to origin
            player.x = 0.0
            player.y = 0.0
            
        player.current_sector = current_sector
        
        camera.x = 0.0
        camera.y = 0.0
        enemies.clear()
        projectiles.clear()
        items.clear()
        debris.clear()
        boss_spawned_milestones.clear()
        spawn_timer = 0.0
        game_time = 0.0
        generate_stars()

        init_level_objective()
        
        # Reset new additions
        escape_pod = {"x": 0.0, "y": 0.0, "active": False}
        asteroids.clear()
        for _ in range(45):
            ax = random.uniform(-1800.0, 1800.0)
            ay = random.uniform(-1800.0, 1800.0)
            while math.sqrt(ax*ax + ay*ay) < 300.0:
                ax = random.uniform(-1800.0, 1800.0)
                ay = random.uniform(-1800.0, 1800.0)
            tier = random.choice([1, 2, 3])
            
            # Asteroid type distribution based on Sector
            if current_sector == 1:
                type_choice = "normal" if random.random() < 0.65 else "gold"
            elif current_sector == 2:
                rv = random.random()
                if rv < 0.45:
                    type_choice = "normal"
                elif rv < 0.80:
                    type_choice = "gold"
                else:
                    type_choice = "plasma"
            else: # Sector 3
                rv = random.random()
                if rv < 0.20:
                    type_choice = "normal"
                elif rv < 0.55:
                    type_choice = "gold"
                elif rv < 0.85:
                    type_choice = "plasma"
                else:
                    type_choice = "core"
            
            ast = spawn_asteroid(ax, ay, tier=tier, ast_type=type_choice)
            ast["vx"] = 0.0
            ast["vy"] = 0.0
            ast["speed"] = 0.0
            asteroids.append(ast)

        damage_numbers.clear()
        powerup_spawn_timer = 8.0
        event_manager.reset()
        intro_timer = 4.0
        camera_rotation_angle = 0.0
        current_zoom = 1.8
        user_zoom_mult = 1.0

    def end_run(victory=False):
        nonlocal run_credits, run_plasma, run_cores, run_ended, save_data, game_state
        if run_ended:
            return
        run_ended = True
        
        # Apply victory bonuses
        if victory:
            run_credits += 150
            run_cores += 2
            
        # Add to persistent totals
        save_data["credits"] += run_credits
        save_data["plasma"] += run_plasma
        save_data["cores"] += run_cores
        
        # Save to disk
        save_save_data(save_data)
        
        # Change state
        if victory:
            game_state = STATE_VICTORY
        else:
            game_state = STATE_GAME_OVER

    def execute_debug_action(opt):
        nonlocal game_state, enemies, debug_page, selected_debug_idx, debug_scroll_offset, objective_collected, objective_needed
        action = opt["action"]
        if action == "nop":
            return
        elif action == "toggle_god":
            player.god_mode = not player.god_mode
        elif action == "heal":
            player.health = player.max_health
        elif action == "add_xp":
            player.add_xp(250)
        elif action == "spawn_boss":
            spawn_angle = random.uniform(0, math.pi * 2)
            spawn_dist = 150.0
            sx = player.x + math.cos(spawn_angle) * spawn_dist
            sy = player.y + math.sin(spawn_angle) * spawn_dist
            enemies.append(Enemy(sx, sy, "boss", wave_multiplier=1.5))
        elif action == "spawn_squad":
            spawn_angle = random.uniform(0, math.pi * 2)
            spawn_dist = 160.0
            sx = player.x + math.cos(spawn_angle) * spawn_dist
            sy = player.y + math.sin(spawn_angle) * spawn_dist
            ship_type = random.choice(["light_fighter", "interceptor", "recon", "corvette", "bomber"])
            squad_id = random.randint(1000, 9999)
            for _ in range(5):
                ox = sx + random.uniform(-35.0, 35.0)
                oy = sy + random.uniform(-35.0, 35.0)
                ship = Enemy(ox, oy, ship_type)
                ship.squadron_id = squad_id
                enemies.append(ship)
        elif action == "spawn_carrier":
            spawn_angle = random.uniform(0, math.pi * 2)
            spawn_dist = 180.0
            sx = player.x + math.cos(spawn_angle) * spawn_dist
            sy = player.y + math.sin(spawn_angle) * spawn_dist
            ship = Enemy(sx, sy, "carrier")
            ship.squadron_id = random.randint(1000, 9999)
            enemies.append(ship)
        elif action == "complete_objective":
            objective_collected = objective_needed
        elif action == "clear_enemies":
            for e in enemies:
                e.active = False
            enemies.clear()
        elif action == "unlock_weapons":
            from systems.upgrade import PRIMARY_WEAPONS, ACCESSORIES
            for name, w_class in PRIMARY_WEAPONS.items():
                if len(player.primary_weapons) < 4:
                    if name not in [w.name for w in player.primary_weapons]:
                        player.primary_weapons.append(w_class())
            for name, acc_class in ACCESSORIES.items():
                if len(player.accessories) < 4:
                    if name not in [a.name for a in player.accessories]:
                        player.accessories.append(acc_class())
        elif action == "max_weapons":
            for w in player.weapons:
                w.level = w.max_level
                w.upgrade_stats()
        elif action == "max_passives":
            passives_list = [
                "THRUSTERS", "NANO-ARMOR", "XP MAGNET", "OVERDRIVE CORE", "REPAIR DRONES", "HULL UPGRADE",
                "GIANT CELLS", "HYPER DRIVE", "SPLIT FIRE", "SMART TARGETING", "BOUNCING MATRIX", "DRILL TIP", "SHRAPNEL SHELLS"
            ]
            for p_name in passives_list:
                player.passives[p_name] = 5
            player.speed_mult = 1.0 + player.passives.get("THRUSTERS", 0) * 0.10
            player.armor = player.passives.get("NANO-ARMOR", 0) * 2.0
            player.magnet_radius = 80.0 * (1.0 + player.passives.get("XP MAGNET", 0) * 0.25)
            
            base_dmg_mult = 1.0 + player.passives.get("OVERDRIVE CORE", 0) * 0.15
            giant_cells_dmg = player.passives.get("GIANT CELLS", 0) * 0.10
            split_fire_reduction = player.passives.get("SPLIT FIRE", 0) * -0.12
            player.damage_mult = max(0.1, base_dmg_mult + giant_cells_dmg + split_fire_reduction)
            
            old_max = player.max_health
            player.max_health = 100.0 + player.passives.get("HULL UPGRADE", 0) * 20.0
            if player.max_health > old_max:
                player.health += (player.max_health - old_max)
                
            player.health_regen = player.passives.get("REPAIR DRONES", 0) * 1.0

            player.proj_size_mult = 1.0 + player.passives.get("GIANT CELLS", 0) * 0.20
            player.proj_speed_mult = 1.0 + player.passives.get("HYPER DRIVE", 0) * 0.20
            player.cooldown_mult = max(0.2, 1.0 - player.passives.get("HYPER DRIVE", 0) * 0.10)
            
            player.proj_count_mod = player.passives.get("SPLIT FIRE", 0)
            player.proj_homing = player.passives.get("SMART TARGETING", 0) * 1.5
            player.proj_bounce = player.passives.get("BOUNCING MATRIX", 0)
            player.proj_pierce_mod = player.passives.get("DRILL TIP", 0)
            player.proj_split = player.passives.get("SHRAPNEL SHELLS", 0)
        elif action == "page_weapons":
            debug_page = 1
            selected_debug_idx = 0
            debug_scroll_offset = 0
        elif action == "page_accessories":
            debug_page = 2
            selected_debug_idx = 0
            debug_scroll_offset = 0
        elif action == "page_passives":
            debug_page = 3
            selected_debug_idx = 0
            debug_scroll_offset = 0
        elif action == "page_cheats":
            debug_page = 0
            selected_debug_idx = 0
            debug_scroll_offset = 0
        elif action == "give_weapon":
            from systems.upgrade import PRIMARY_WEAPONS
            w_name = opt["target"]
            matched = [w for w in player.primary_weapons if w.name == w_name]
            if matched:
                if matched[0].level < matched[0].max_level:
                    matched[0].level_up()
            else:
                player.primary_weapons.append(PRIMARY_WEAPONS[w_name]())
        elif action == "give_accessory":
            from systems.upgrade import ACCESSORIES
            acc_name = opt["target"]
            matched = [a for a in player.accessories if a.name == acc_name]
            if matched:
                if matched[0].level < matched[0].max_level:
                    matched[0].level_up()
            else:
                if len(player.accessories) < 4:
                    player.accessories.append(ACCESSORIES[acc_name]())
        elif action == "give_passive":
            from systems.upgrade import apply_upgrade
            p_name = opt["target"]
            curr_lvl = player.passives.get(p_name, 0)
            if curr_lvl == 0:
                if len(player.passives) < 6:
                    apply_upgrade(player, {"type": "passive_unlock", "target": p_name})
            elif curr_lvl < 5:
                apply_upgrade(player, {"type": "passive_upgrade", "target": p_name})
        elif action == "resume":
            game_state = STATE_GAMEPLAY

    logged_errors = set()
    recent_errors = []

    def log_error(context, e):
        import traceback
        tb = traceback.format_exc()
        log_msg = f"=== {context} ANOMALY DETECTED ===\n{tb}\n"
        print(log_msg)
        if log_msg not in logged_errors:
            logged_errors.add(log_msg)
            try:
                with open("error_log.txt", "a") as f:
                    f.write(log_msg)
            except Exception:
                pass
        # Short message to show on HUD
        recent_errors.append({"msg": f"ANOMALIE dans {context}: {str(e)[:35]}", "timer": 6.0})

    reset_game()
    time_accum = 0.0
    glitch_timer = 0.0

    # 7. Main Loop
    while True:
        dt = clock.tick(TARGET_FPS) / 1000.0
        # Prevent huge dt steps if window is dragged
        dt = min(dt, 0.1)
        time_accum += dt
        if player:
            if player.iframe_timer > 0.35:
                glitch_timer = player.iframe_timer
            elif getattr(player, 'hyperspace_active', False):
                glitch_timer = 0.2
            else:
                glitch_timer = max(0.0, glitch_timer - dt)
        else:
            glitch_timer = max(0.0, glitch_timer - dt)
        scale_factor = min(WINDOW_WIDTH / 1024.0, WINDOW_HEIGHT / 768.0)

        # Handle events
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.VIDEORESIZE:
                WINDOW_WIDTH, WINDOW_HEIGHT = event.w, event.h
                import config
                config.WINDOW_WIDTH = WINDOW_WIDTH
                config.WINDOW_HEIGHT = WINDOW_HEIGHT
                ctx.viewport = (0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
                
                # Recreate offscreen FBO texture and FBO at new resolution
                fbo_texture.release()
                fbo.release()
                fbo_texture = ctx.texture((WINDOW_WIDTH, WINDOW_HEIGHT), 4)
                fbo_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
                fbo = ctx.framebuffer(color_attachments=[fbo_texture])

            if game_state == STATE_MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_z):
                        main_menu_selection = (main_menu_selection - 1) % 3
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        main_menu_selection = (main_menu_selection + 1) % 3
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if main_menu_selection == 0:
                            reset_game()
                            game_state = STATE_INTRO
                            intro_timer = 4.0
                        elif main_menu_selection == 1:
                            game_state = STATE_META_UPGRADES
                            meta_menu_selection = 0
                        elif main_menu_selection == 2:
                            pygame.quit()
                            sys.exit()

            elif game_state == STATE_GAMEPLAY:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Simple pause toggle
                        pass
                    elif event.key == pygame.K_o:
                        # Zoom out
                        user_zoom_mult = max(0.25, user_zoom_mult - 0.05)
                    elif event.key == pygame.K_p:
                        # Zoom in
                        user_zoom_mult = min(3.0, user_zoom_mult + 0.05)
                    elif event.key == pygame.K_TAB:
                        game_state = STATE_SKILL_TREE
                    elif event.key == pygame.K_F3 or (event.key == pygame.K_d and event.mod & pygame.KMOD_SHIFT):
                        game_state = STATE_DEBUG
                        selected_debug_idx = 0
                        debug_scroll_offset = 0
                    elif event.key == pygame.K_e:
                        if player.active_item is not None:
                            from systems.upgrade import ACTIVE_ITEMS
                            item_meta = ACTIVE_ITEMS.get(player.active_item)
                            if item_meta:
                                lvl_mult = max(0.40, 1.0 - (player.active_item_level - 1) * 0.15)
                                max_charge = item_meta["cooldown"] * lvl_mult
                                if player.active_charge >= max_charge:
                                    player.active_charge = 0.0
                                    if player.active_item == "HYPERSAUT":
                                        player.hyperspace_active = True
                                        player.hyperspace_active_timer = 2.0
                                    elif player.active_item == "NECRONOMICON":
                                        for e in enemies:
                                            if e.active:
                                                e.health -= 120.0
                                                damage_numbers.append({"x": e.x, "y": e.y, "text": "120", "timer": 0.75, "color": COLOR_RED})
                                        camera.shake_timer = 0.4
                                        camera.shake_intensity = 8.0
                                    elif player.active_item == "LIVRE DES OMBRES":
                                        player.iframe_timer = 5.0
                                        player.book_of_shadows_timer = 5.0

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 4: # Scroll Up -> Zoom In
                        user_zoom_mult = min(3.0, user_zoom_mult + 0.05)
                    elif event.button == 5: # Scroll Down -> Zoom Out
                        user_zoom_mult = max(0.25, user_zoom_mult - 0.05)

            elif game_state == STATE_LEVEL_UP:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        selected_upgrade_idx = (selected_upgrade_idx + 1) % len(upgrade_options)
                    elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_z): # Support AZERTY 'Z'
                        selected_upgrade_idx = (selected_upgrade_idx - 1) % len(upgrade_options)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        # Apply selected upgrade
                        apply_upgrade(player, upgrade_options[selected_upgrade_idx])
                        game_state = STATE_GAMEPLAY
                    elif event.key == pygame.K_e and player.active_item == "D6" and player.active_charge >= 1.0:
                        player.active_charge = 0.0
                        upgrade_options = get_upgrade_pool(player, pool_size=3)
                        selected_upgrade_idx = 0
                    elif event.key == pygame.K_1 and len(upgrade_options) >= 1:
                        apply_upgrade(player, upgrade_options[0])
                        game_state = STATE_GAMEPLAY
                    elif event.key == pygame.K_2 and len(upgrade_options) >= 2:
                        apply_upgrade(player, upgrade_options[1])
                        game_state = STATE_GAMEPLAY
                    elif event.key == pygame.K_3 and len(upgrade_options) >= 3:
                        apply_upgrade(player, upgrade_options[2])
                        game_state = STATE_GAMEPLAY

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    overlay_cx = WINDOW_WIDTH // 2
                    overlay_cy = WINDOW_HEIGHT // 2
                    
                    # Compute dynamic box_w matching drawing
                    max_width_needed = 0
                    for opt in upgrade_options:
                        name_w = len(opt["name"]) * 10.4 * 1.2
                        desc_w = len(opt["desc"]) * 10.4 * 0.9
                        max_width_needed = max(max_width_needed, name_w, desc_w + 50)
                    box_w = (max_width_needed + 40) * scale_factor
                    box_w = max(540 * scale_factor, box_w)
                    
                    # Check box bounds
                    for idx in range(len(upgrade_options)):
                        box_x = overlay_cx - box_w * 0.5
                        box_y = overlay_cy - 140 * scale_factor + idx * 100 * scale_factor
                        box_h = 80 * scale_factor
                        if box_x <= mx <= box_x + box_w and box_y <= my <= box_y + box_h:
                            apply_upgrade(player, upgrade_options[idx])
                            game_state = STATE_GAMEPLAY
                            break

                elif event.type == pygame.MOUSEMOTION:
                    if event.rel != (0, 0): # Only override if mouse actually moves
                        mx, my = event.pos
                        overlay_cx = WINDOW_WIDTH // 2
                        overlay_cy = WINDOW_HEIGHT // 2

                        # Compute dynamic box_w matching drawing
                        max_width_needed = 0
                        for opt in upgrade_options:
                            name_w = len(opt["name"]) * 10.4 * 1.2
                            desc_w = len(opt["desc"]) * 10.4 * 0.9
                            max_width_needed = max(max_width_needed, name_w, desc_w + 50)
                        box_w = (max_width_needed + 40) * scale_factor
                        box_w = max(540 * scale_factor, box_w)

                        for idx in range(len(upgrade_options)):
                            box_x = overlay_cx - box_w * 0.5
                            box_y = overlay_cy - 140 * scale_factor + idx * 100 * scale_factor
                            box_h = 80 * scale_factor
                            if box_x <= mx <= box_x + box_w and box_y <= my <= box_y + box_h:
                                selected_upgrade_idx = idx

            elif game_state == STATE_DEBUG:
                opts = get_debug_options()
                spacing = 22 if debug_page in (1, 2, 3) else 30
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_F3 or (event.key == pygame.K_d and event.mod & pygame.KMOD_SHIFT):
                        game_state = STATE_GAMEPLAY
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected_debug_idx = (selected_debug_idx + 1) % len(opts)
                        max_visible = 10
                        if selected_debug_idx < debug_scroll_offset:
                            debug_scroll_offset = selected_debug_idx
                        elif selected_debug_idx >= debug_scroll_offset + max_visible:
                            debug_scroll_offset = selected_debug_idx - max_visible + 1
                    elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_z): # Support AZERTY 'Z'
                        selected_debug_idx = (selected_debug_idx - 1) % len(opts)
                        max_visible = 10
                        if selected_debug_idx < debug_scroll_offset:
                            debug_scroll_offset = selected_debug_idx
                        elif selected_debug_idx >= debug_scroll_offset + max_visible:
                            debug_scroll_offset = selected_debug_idx - max_visible + 1
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        execute_debug_action(opts[selected_debug_idx])
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        mx, my = event.pos
                        overlay_cx = WINDOW_WIDTH // 2
                        overlay_cy = WINDOW_HEIGHT // 2
                        max_width_needed = max(len(opt["name"]) * 10.4 * (0.9 if debug_page in (1, 2, 3) else 1.1) for opt in opts)
                        box_w = (max_width_needed + 40) * scale_factor
                        box_w = max(540 * scale_factor, box_w)
                        max_visible = 10
                        num_visible = min(len(opts), max_visible)
                        overlay_h = (55 + num_visible * spacing + 25) * scale_factor
                        overlay_y = overlay_cy - overlay_h * 0.5

                        visible_range = range(debug_scroll_offset, min(len(opts), debug_scroll_offset + max_visible))
                        for idx in visible_range:
                            visible_idx = idx - debug_scroll_offset
                            box_x = overlay_cx - box_w * 0.5
                            box_y = overlay_y + (55 + visible_idx * spacing) * scale_factor
                            box_h = (spacing - 3) * scale_factor
                            if box_x <= mx <= box_x + box_w and box_y <= my <= box_y + box_h:
                                execute_debug_action(opts[idx])
                                break
                    elif event.button == 4: # Mouse Wheel Scroll Up
                        if debug_scroll_offset > 0:
                            debug_scroll_offset -= 1
                    elif event.button == 5: # Mouse Wheel Scroll Down
                        max_visible = 10
                        if debug_scroll_offset + max_visible < len(opts):
                            debug_scroll_offset += 1
                elif event.type == pygame.MOUSEMOTION:
                    if event.rel != (0, 0): # Only override if mouse actually moves
                        mx, my = event.pos
                        overlay_cx = WINDOW_WIDTH // 2
                        overlay_cy = WINDOW_HEIGHT // 2
                        max_width_needed = max(len(opt["name"]) * 10.4 * (0.9 if debug_page in (1, 2, 3) else 1.1) for opt in opts)
                        box_w = (max_width_needed + 40) * scale_factor
                        box_w = max(540 * scale_factor, box_w)
                        max_visible = 10
                        num_visible = min(len(opts), max_visible)
                        overlay_h = (55 + num_visible * spacing + 25) * scale_factor
                        overlay_y = overlay_cy - overlay_h * 0.5

                        visible_range = range(debug_scroll_offset, min(len(opts), debug_scroll_offset + max_visible))
                        for idx in visible_range:
                            visible_idx = idx - debug_scroll_offset
                            box_x = overlay_cx - box_w * 0.5
                            box_y = overlay_y + (55 + visible_idx * spacing) * scale_factor
                            box_h = (spacing - 3) * scale_factor
                            if box_x <= mx <= box_x + box_w and box_y <= my <= box_y + box_h:
                                selected_debug_idx = idx
                                break

            elif game_state == STATE_SKILL_TREE:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_TAB, pygame.K_ESCAPE):
                        game_state = STATE_GAMEPLAY

            elif game_state == STATE_GAME_OVER:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        reset_game()
                        game_state = STATE_INTRO
                        intro_timer = 4.0

            elif game_state == STATE_VICTORY:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        game_state = STATE_MENU

            elif game_state == STATE_META_UPGRADES:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_z):
                        meta_menu_selection = (meta_menu_selection - 1) % len(UPGRADE_METADATA)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        meta_menu_selection = (meta_menu_selection + 1) % len(UPGRADE_METADATA)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        # Purchase selected upgrade
                        keys = list(UPGRADE_METADATA.keys())
                        upgrade_key = keys[meta_menu_selection]
                        current_lvl = save_data["upgrades"].get(upgrade_key, 0)
                        if current_lvl < UPGRADE_METADATA[upgrade_key]["max_lvl"]:
                            cost = get_upgrade_cost(upgrade_key, current_lvl)
                            if cost:
                                if (save_data["credits"] >= cost["credits"] and 
                                    save_data["plasma"] >= cost["plasma"] and 
                                    save_data["cores"] >= cost["cores"]):
                                    # Deduct costs
                                    save_data["credits"] -= cost["credits"]
                                    save_data["plasma"] -= cost["plasma"]
                                    save_data["cores"] -= cost["cores"]
                                    # Increment level
                                    save_data["upgrades"][upgrade_key] = current_lvl + 1
                                    save_save_data(save_data)
                    elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        game_state = STATE_MENU
                    elif event.key == pygame.K_r:
                        # Refund / Respec all upgrades
                        refund_credits = 0
                        refund_plasma = 0
                        refund_cores = 0
                        for k in list(save_data["upgrades"].keys()):
                            lvl = save_data["upgrades"][k]
                            for l in range(lvl):
                                cost = get_upgrade_cost(k, l)
                                if cost:
                                    refund_credits += cost["credits"]
                                    refund_plasma += cost["plasma"]
                                    refund_cores += cost["cores"]
                            save_data["upgrades"][k] = 0
                        save_data["credits"] += refund_credits
                        save_data["plasma"] += refund_plasma
                        save_data["cores"] += refund_cores
                        save_save_data(save_data)

            elif game_state == STATE_SECTOR_TRANSITION:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        current_sector += 1
                        reset_game(next_sector=True)
                        game_state = STATE_INTRO

        # State updates
        # Tick error notifications timers
        for err in recent_errors:
            err["timer"] -= dt
        recent_errors = [e for e in recent_errors if e["timer"] > 0]

        # Update floating combat numbers
        for d in damage_numbers:
            d["timer"] -= dt
            d["y"] -= 35.0 * dt
        damage_numbers = [d for d in damage_numbers if d["timer"] > 0]

        # Tick arena powerup spawner
        if game_state == STATE_GAMEPLAY:
            powerup_spawn_timer -= dt
            if powerup_spawn_timer <= 0:
                powerup_spawn_timer = 12.0
                ang = random.uniform(0, 2*math.pi)
                dist = random.uniform(280.0, 480.0)
                px = player.x + math.cos(ang) * dist
                py = player.y + math.sin(ang) * dist
                ptype = random.choice(["magnet", "bomb", "fuel", "health"])
                val = 25 if ptype == "fuel" else (20 if ptype == "health" else 1)
                items.append(Item(px, py, ptype, value=val))

        # Intro State update
        if game_state == STATE_INTRO:
            intro_timer -= dt
            if intro_timer <= 0.0:
                game_state = STATE_GAMEPLAY
            
            # Center camera immediately on player
            camera.update(player.x, player.y, lerp_factor=1.0)
            
            # Smoothly dezoom camera
            t = intro_timer / 4.0
            base_target_zoom = 1.8 * scale_factor * user_zoom_mult
            current_zoom = base_target_zoom + 3.2 * t

        if game_state == STATE_GAMEPLAY:
            game_time += dt

            # Read keyboard for player movement (supports QWERTY and AZERTY layouts)
            keys = pygame.key.get_pressed()
            dx = 0.0
            dy = 0.0
            if keys[pygame.K_w] or keys[pygame.K_z] or keys[pygame.K_UP]: # W or Z
                dy -= 1.0
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                dy += 1.0
            if keys[pygame.K_a] or keys[pygame.K_q] or keys[pygame.K_LEFT]: # A or Q
                dx -= 1.0
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx += 1.0

            # Active item update
            if player.active_item in ("HYPERSAUT", "LIVRE DES OMBRES"):
                from systems.upgrade import ACTIVE_ITEMS
                lvl_mult = max(0.40, 1.0 - (player.active_item_level - 1) * 0.15)
                max_charge = ACTIVE_ITEMS[player.active_item]["cooldown"] * lvl_mult
                player.active_charge = min(max_charge, player.active_charge + dt)
                
            if getattr(player, 'hyperspace_active_timer', 0.0) > 0.0:
                player.hyperspace_active_timer -= dt
                if player.hyperspace_active_timer <= 0.0:
                    player.hyperspace_active = False
            else:
                player.hyperspace_active = False

            if getattr(player, 'book_of_shadows_timer', 0.0) > 0.0:
                player.book_of_shadows_timer -= dt

            # --- Mining & Asteroid Collision with Player ---
            player.mining_slowdown = False
            for ast in asteroids:
                if not ast["active"]:
                    continue
                adx = player.x - ast["x"]
                ady = player.y - ast["y"]
                dist_sq = adx*adx + ady*ady
                rad_sum = player.radius + ast["radius"]
                if dist_sq < rad_sum * rad_sum:
                    player.mining_slowdown = True
                    # Deal mining ticks
                    ast["health"] -= dt * player.mining_speed * 12.0
                    
                    # Spark debris matching asteroid type color
                    ast_type = ast.get("type", "normal")
                    if ast_type == "gold":
                        ast_color = COLOR_AMBER
                    elif ast_type == "plasma":
                        ast_color = (0.8, 0.2, 1.0)
                    elif ast_type == "core":
                        ast_color = (0.2, 0.9, 1.0)
                    else:
                        ast_color = (0.7, 0.7, 0.7)

                    if random.random() < 0.25:
                        deb = Debris(ast["x"] + random.uniform(-5, 5), ast["y"] + random.uniform(-5, 5), ast_color)
                        deb.vx = random.uniform(-80.0, 80.0)
                        deb.vy = random.uniform(-80.0, 80.0)
                        debris.append(deb)
                        
                    # Spawn forage indicators periodically
                    if '_next_text_timer' not in ast:
                        ast['_next_text_timer'] = 0.0
                    ast['_next_text_timer'] -= dt
                    if ast['_next_text_timer'] <= 0.0:
                        ast['_next_text_timer'] = 0.35
                        damage_numbers.append({"x": ast["x"], "y": ast["y"] + 15, "text": "FORAGE...", "timer": 0.40, "color": ast_color})
                        
                    if ast["health"] <= 0:
                        destroy_asteroid(ast)

            player.update(dt, dx, dy)

            kill_diff = player.kills - player.previous_kills
            if kill_diff > 0:
                player.previous_kills = player.kills
                if player.active_item == "NECRONOMICON":
                    from systems.upgrade import ACTIVE_ITEMS
                    lvl_mult = max(0.40, 1.0 - (player.active_item_level - 1) * 0.15)
                    max_kills = ACTIVE_ITEMS["NECRONOMICON"]["cooldown"] * lvl_mult
                    player.active_charge = min(max_kills, player.active_charge + kill_diff)
            camera.update(player.x, player.y, lerp_factor=0.08)

            # Calculate dynamic camera zoom based on threat count
            threats = len([e for e in enemies if e.active])
            active_asteroids = len([a for a in asteroids if a["active"]])
            if event_manager.active_event and event_manager.active_event.name == "Champ d'asteroides":
                threats += active_asteroids * 3.0 # Highly weight asteroids during the event
            else:
                threats += active_asteroids
                
            # Dynamic zoom formula with wider zoom range (down to 0.45), scaled by user preference
            target_zoom = (1.8 - 1.35 * (1.0 - math.exp(-threats / 35.0))) * scale_factor * user_zoom_mult
            current_zoom += (target_zoom - current_zoom) * 2.0 * dt

            try:
                # Auto-fire weapons
                player.camera_ref = camera
                player.zoom_ref = current_zoom
                for weapon in player.weapons:
                    initial_count = len(projectiles)
                    
                    if not hasattr(weapon, "modifiers"):
                        weapon.modifiers = {
                            "spread": 0, "homing": 0.0, "bounce": 0, "pierce": 0,
                            "thickness": 0, "size": 0.0, "speed": 0.0
                        }
                    
                    # Temporarily inject local spread modifier to player state
                    orig_proj_count_mod = getattr(player, 'proj_count_mod', 0)
                    orig_drone_assembly = player.passives.get("DRONE ASSEMBLY", 0)
                    local_spread = weapon.modifiers.get("spread", 0)
                    if local_spread > 0:
                        player.proj_count_mod = orig_proj_count_mod + local_spread
                        player.passives["DRONE ASSEMBLY"] = orig_drone_assembly + local_spread
                    
                    # Update weapon
                    weapon.update(dt, player, enemies, projectiles)
                    
                    # Restore original player modifiers
                    if local_spread > 0:
                        player.proj_count_mod = orig_proj_count_mod
                        player.passives["DRONE ASSEMBLY"] = orig_drone_assembly
                    
                    # Intercept new projectiles spawned by this weapon and apply local modifiers!
                    new_projectiles = projectiles[initial_count:]
                    for p in new_projectiles:
                        # Skip drone body representation markers (damage=0)
                        if p.proj_type in ("laser_drone", "rocket_drone", "heal_drone", "dry_drone", "fly_drone", "robo_baby_drone") and p.damage == 0:
                            continue
                            
                        # Apply Size
                        if weapon.modifiers.get("size", 0.0) > 0.0:
                            p.radius *= (1.0 + weapon.modifiers["size"] * 0.15)
                            
                        # Apply Speed
                        if weapon.modifiers.get("speed", 0.0) > 0.0:
                            p.speed *= (1.0 + weapon.modifiers["speed"] * 0.15)
                            p.vx *= (1.0 + weapon.modifiers["speed"] * 0.15)
                            p.vy *= (1.0 + weapon.modifiers["speed"] * 0.15)
                            
                        # Apply Homing
                        if weapon.modifiers.get("homing", 0.0) > 0.0:
                            p.homing = getattr(p, "homing", 0.0) + weapon.modifiers["homing"] * 1.5
                            
                        # Apply Bounce
                        if weapon.modifiers.get("bounce", 0) > 0:
                            p.bounces = getattr(p, "bounces", 0) + int(weapon.modifiers["bounce"])
                            
                        # Apply Pierce
                        if weapon.modifiers.get("pierce", 0) > 0:
                            p.pierce = getattr(p, "pierce", 1) + int(weapon.modifiers["pierce"])
                            
                        # Apply Thickness
                        if weapon.modifiers.get("thickness", 0) > 0:
                            p.thickness = getattr(p, "thickness", 1) + int(weapon.modifiers["thickness"])

            except Exception as e:
                log_error('Weapon Update', e)
            # Apply Planet Gravitational attraction
            for planet in planets:
                pdx = planet["x"] - player.x
                pdy = planet["y"] - player.y
                pdist = math.sqrt(pdx*pdx + pdy*pdy)
                if pdist < planet["gravity_radius"]:
                    if pdist > 5.0:
                        pull = (1.0 - pdist / planet["gravity_radius"]) * planet["gravity_pull"] * dt
                        player.x += (pdx / pdist) * pull
                        player.y += (pdy / pdist) * pull
                    if pdist < (player.radius * 0.45 + planet["radius"] * 0.65):
                        player.take_damage(20.0 * dt)
                        
                for e in enemies:
                    if not e.active:
                        continue
                    edx = planet["x"] - e.x
                    edy = planet["y"] - e.y
                    edist = math.sqrt(edx*edx + edy*edy)
                    if edist < planet["gravity_radius"]:
                        if edist > 5.0:
                            pull = (1.0 - edist / planet["gravity_radius"]) * planet["gravity_pull"] * dt
                            e.x += (edx / edist) * pull
                            e.y += (edy / edist) * pull
                        if edist < (e.radius + planet["radius"]):
                            if e.take_damage(40.0 * dt):
                                player.kills += 1
                                val = 1 if e.enemy_type == "swarmer" else (3 if e.enemy_type == "chaser" else (8 if e.enemy_type == "stalker" else 45))
                                items.append(Item(e.x, e.y, "xp", value=val))


                    


            # Escape Pod checks
            if escape_pod.get("active", False):
                pdx = escape_pod["x"] - player.x
                pdy = escape_pod["y"] - player.y
                pdist = math.sqrt(pdx*pdx + pdy*pdy)
                if pdist < (player.radius + 20.0):
                    escape_pod["active"] = False
                    if current_sector < 3:
                        game_state = STATE_SECTOR_TRANSITION
                    else:
                        end_run(victory=True)

            # Rebuilt Space Event Manager Tick
            game_context = GameContext(
                player=player,
                enemies=enemies,
                projectiles=projectiles,
                items=items,
                debris=debris,
                camera=camera,
                damage_numbers=damage_numbers,
                asteroids=asteroids,
                WINDOW_WIDTH=WINDOW_WIDTH,
                WINDOW_HEIGHT=WINDOW_HEIGHT,
                game_time=game_time,
                spawn_asteroid_fn=spawn_asteroid
            )
            event_manager.update(dt, game_context)



            # Spawn enemies off-screen (Event swarm spawns are handled directly inside HiveSwarmEvent class)
            spawn_timer -= dt
            if spawn_timer <= 0 and len([e for e in enemies if e.active]) < MAX_ENEMIES:
                # Highly progressive difficulty: stats scale faster (exponentially/quadratically) as time goes on
                sector_mult = 1.0 + (current_sector - 1) * 0.3
                wave_multiplier = sector_mult * (1.0 + (game_time / 45.0) ** 1.6 * 0.35)
                
                # Check for Boss spawning every 2 minutes
                curr_minute = int(game_time // 120.0)
                if curr_minute > 0 and curr_minute not in boss_spawned_milestones:
                    boss_spawned_milestones.add(curr_minute)
                    # Spawn Boss/Mini-Boss
                    spawn_angle = random.uniform(0, math.pi * 2)
                    spawn_dist = max(WINDOW_WIDTH, WINDOW_HEIGHT) * 0.5 + 80.0
                    sx = camera.x + math.cos(spawn_angle) * spawn_dist
                    sy = camera.y + math.sin(spawn_angle) * spawn_dist
                    
                    if current_sector == 1:
                        enemies.append(Enemy(sx, sy, "destroyer", wave_multiplier=wave_multiplier * 1.4))
                    elif current_sector == 2:
                        enemies.append(Enemy(sx, sy, "carrier", wave_multiplier=wave_multiplier * 1.6))
                    else:
                        enemies.append(Enemy(sx, sy, "boss", wave_multiplier=wave_multiplier * 1.5))
                
                # Highly progressive selection of enemy type based on sector time elapsed
                if game_time < 20.0:
                    etype = "swarmer"
                elif game_time < 45.0:
                    etype = "chaser" if random.random() < 0.40 else "swarmer"
                elif game_time < 75.0:
                    etype = "stalker" if random.random() < 0.35 else "chaser"
                elif game_time < 110.0:
                    etype = random.choice(["stalker", "light_fighter", "interceptor", "recon"])
                elif game_time < 150.0:
                    etype = random.choice(["bomber", "corvette", "frigate", "cruiser"])
                else:
                    etype = random.choice(["destroyer", "dreadnought", "carrier"])

                # Spawn coordinates outside the viewport
                spawn_angle = random.uniform(0, math.pi * 2)
                spawn_dist = max(WINDOW_WIDTH, WINDOW_HEIGHT) * 0.75 + 180.0
                sx = camera.x + math.cos(spawn_angle) * spawn_dist
                sy = camera.y + math.sin(spawn_angle) * spawn_dist
                
                # Squadrons & capital ship spawn rate scales up over time
                squad_chance = min(0.85, 0.15 + (game_time / 120.0) * 0.50)
                if random.random() < squad_chance:
                    # As time passes, spawn heavier capital classes
                    if game_time < 60.0 or random.random() < 0.65:
                        # Spawn squadron of 5 spaceships flying in formation
                        ship_type = random.choice(["light_fighter", "interceptor", "recon"])
                        if game_time >= 90.0:
                            ship_type = random.choice(["light_fighter", "interceptor", "recon", "corvette", "bomber"])
                        squad_id = random.randint(1000, 9999)
                        for _ in range(5):
                            ox = sx + random.uniform(-45.0, 45.0)
                            oy = sy + random.uniform(-45.0, 45.0)
                            ship = Enemy(ox, oy, ship_type, wave_multiplier=wave_multiplier)
                            ship.squadron_id = squad_id
                            enemies.append(ship)
                    else:
                        # Spawn a heavy capital ship
                        ship_type = random.choice(["frigate", "corvette", "cruiser"])
                        if game_time >= 100.0:
                            ship_type = random.choice(["frigate", "cruiser", "destroyer", "dreadnought", "carrier"])
                        ship = Enemy(sx, sy, ship_type, wave_multiplier=wave_multiplier)
                        if ship_type == "carrier":
                            ship.squadron_id = random.randint(1000, 9999)
                        enemies.append(ship)
                else:
                    # Standard enemy spawn
                    enemies.append(Enemy(sx, sy, etype, wave_multiplier=wave_multiplier))
                
                # Faster spawning over time (lower cooldown floor)
                spawn_cooldown = max(0.20, SPAWN_INTERVAL - (game_time / 120.0) * 0.60)
                spawn_timer = spawn_cooldown

            try:
                # Update Projectiles
                for p in projectiles:
                    p.update(dt, enemies, camera, player)

                    # Brimstone continuous tick damage and follow player
                    if p.proj_type == "brimstone" and p.owner:
                        hx = p.owner.x + math.cos(p.owner.angle) * p.owner.radius
                        hy = p.owner.y + math.sin(p.owner.angle) * p.owner.radius
                        p.beam_start = (hx, hy)
                        p.beam_end = (hx + p.dx * p.radius_length, hy + p.dy * p.radius_length)
                        
                        if not hasattr(p, 'tick_timer'):
                            p.tick_timer = 0.0
                        p.tick_timer -= dt
                        if p.tick_timer <= 0.0:
                            p.tick_timer = 0.12
                            p.tick_hit_enemies = set()
                            
                        # Deal tick damage to enemies
                        dmg = p.damage * p.owner.damage_mult * 0.15
                        for enemy in enemies:
                            if not enemy.active or enemy in p.tick_hit_enemies:
                                continue
                            x1, y1 = p.beam_start
                            x2, y2 = p.beam_end
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
                                dist_sq = (enemy.x - closest_x)**2 + (enemy.y - closest_y)**2
                                rad_sum = p.radius + enemy.radius
                                if dist_sq < rad_sum * rad_sum:
                                    p.tick_hit_enemies.add(enemy)
                                    if enemy.take_damage(dmg):
                                        p.owner.kills += 1
                                        p.owner.xp_earned(enemy.score_value, enemy.x, enemy.y)
                                    damage_numbers.append({"x": enemy.x, "y": enemy.y, "text": f"{int(dmg)}", "timer": 0.4, "color": enemy.color})

                    # Tech X ring tick clearing
                    elif p.proj_type == "ring":
                        if not hasattr(p, 'tick_timer'):
                            p.tick_timer = 0.0
                        p.tick_timer -= dt
                        if p.tick_timer <= 0.0:
                            p.tick_timer = 0.20
                            p.hit_enemies.clear()

                    # Knife tick clearing
                    elif p.proj_type == "knife":
                        if not hasattr(p, 'tick_timer'):
                            p.tick_timer = 0.0
                        p.tick_timer -= dt
                        if p.tick_timer <= 0.0:
                            p.tick_timer = 0.15
                            p.hit_enemies.clear()

                    # Apply vortex pull force on enemies
                    if p.proj_type == "vortex":
                        for e in enemies:
                            if not e.active:
                                continue
                            vdx = p.x - e.x
                            vdy = p.y - e.y
                            dist_sq = vdx * vdx + vdy * vdy
                            if 25.0 < dist_sq < p.radius * p.radius:
                                dist = math.sqrt(dist_sq)
                                pull = (p.radius - dist) * 1.7 * dt
                                e.x += (vdx / dist) * pull
                                e.y += (vdy / dist) * pull

                    # Splitting & special triggers upon expiration
                    if not p.active:
                        if p.proj_type == "grenade":
                            v_rad = 120.0 * player.proj_size_mult
                            v = Projectile(
                                x=p.x, y=p.y,
                                dx=0, dy=0,
                                damage=p.damage * 0.45,
                                speed=0.0,
                                lifetime=1.2,
                                pierce=9999,
                                proj_type="vortex",
                                color=COLOR_AMBER,
                                radius=v_rad,
                                bounces=0,
                                split_level=p.split_level,
                                owner=player
                            )
                            projectiles.append(v)
                        elif p.proj_type == "vortex":
                            # final vortex burst
                            dmg = p.damage * player.damage_mult * 2.0
                            for enemy in enemies:
                                if not enemy.active:
                                    continue
                                edx = enemy.x - p.x
                                edy = enemy.y - p.y
                                dist_sq = edx*edx + edy*edy
                                if dist_sq < p.radius * p.radius:
                                    dist = math.sqrt(dist_sq)
                                    if enemy.take_damage(dmg):
                                        player.kills += 1
                                        player.xp_earned(enemy.score_value, enemy.x, enemy.y)
                                    push = (p.radius - dist) * 2.0
                                    if dist > 0:
                                        enemy.x += (edx / dist) * push
                                        enemy.y += (edy / dist) * push
                                    for _ in range(14):
                                        debris.append(Debris(enemy.x, enemy.y, enemy.color))

                        if p.split_level > 0:
                            p.split(projectiles)
                            p.split_level = 0

            except Exception as e:
                log_error('Projectile Update', e)
            try:
                # Update Enemies & Enemy Shooting
                squadrons = {}
                for e in enemies:
                    if e.active and getattr(e, 'is_spaceship', False) and getattr(e, 'squadron_id', None) is not None:
                        squadrons.setdefault(e.squadron_id, []).append(e)

                for e in enemies:
                    sq_list = squadrons.get(e.squadron_id) if (getattr(e, 'is_spaceship', False) and getattr(e, 'squadron_id', None) is not None) else None
                    e.update(dt, player.x, player.y, sq_list)
                    
                    # Enemies weapon firing systems
                    if not hasattr(e, 'shoot_timer'):
                        e.shoot_timer = random.uniform(1.5, 3.5)
                        
                    e.shoot_timer -= dt
                    if e.shoot_timer <= 0.0:
                        cooldown = 4.0
                        if getattr(e, 'is_spaceship', False):
                            # Spaceship weapon fire
                            wt = getattr(e, 'weapon_type', 'laser')
                            if wt == "carrier_spawner":
                                cooldown = random.uniform(4.5, 6.0)
                                # Spawns 2 mini support ships
                                for _ in range(2):
                                    sa = random.uniform(0.0, math.pi * 2)
                                    sx = e.x + math.cos(sa) * 45.0
                                    sy = e.y + math.sin(sa) * 45.0
                                    mini_t = random.choice(["swarmer", "light_fighter", "interceptor"])
                                    mini = Enemy(sx, sy, mini_t)
                                    mini.squadron_id = e.squadron_id if e.squadron_id else id(e)
                                    enemies.append(mini)
                            else:
                                cooldown = random.uniform(1.4, 2.5)
                                edx = player.x - e.x
                                edy = player.y - e.y
                                dist = math.sqrt(edx*edx + edy*edy)
                                if 5.0 < dist < 700.0:
                                    base_ang = math.atan2(edy, edx)
                                    dmg = e.damage
                                    spd = 180.0
                                    r = 3.0
                                    if wt == "missile":
                                        spd = 120.0
                                        r = 4.5
                                    elif wt == "meteor":
                                        spd = 90.0
                                        r = 8.5
                                    elif wt == "flame":
                                        spd = 140.0
                                        r = 6.0
                                    elif wt == "vortex":
                                        spd = 80.0
                                        r = 12.0
                                    elif wt == "blade":
                                        spd = 150.0
                                        r = 5.0
                                    
                                    # Spread shots
                                    spread = e.modifiers.get("spread", 1)
                                    angles = [base_ang]
                                    if spread == 2:
                                        angles = [base_ang - 0.12, base_ang + 0.12]
                                    elif spread == 3:
                                        angles = [base_ang - 0.22, base_ang, base_ang + 0.22]
                                    elif spread == 4:
                                        angles = [base_ang - 0.35, base_ang - 0.12, base_ang + 0.12, base_ang + 0.35]
                                    
                                    for ang in angles:
                                        projectiles.append(Projectile(
                                            x=e.x, y=e.y, dx=math.cos(ang), dy=math.sin(ang),
                                            damage=dmg, speed=spd * e.modifiers.get("speed_mult", 1.0), lifetime=4.5,
                                            proj_type=wt, color=e.color, radius=r,
                                            is_enemy=True,
                                            bounces=e.modifiers.get("bounce", 0),
                                            homing=e.modifiers.get("homing", 0.0),
                                            pierce=e.modifiers.get("pierce", 1),
                                            owner=e,
                                            thickness=e.modifiers.get("thickness", 1),
                                            size=e.modifiers.get("size", 1.0)
                                        ))
                        elif e.enemy_type == "chaser":
                            cooldown = random.uniform(0.6, 1.1)
                            edx = player.x - e.x
                            edy = player.y - e.y
                            dist = math.sqrt(edx*edx + edy*edy)
                            if 5.0 < dist < 580.0:
                                dx = edx / dist
                                dy = edy / dist
                                projectiles.append(Projectile(
                                    x=e.x, y=e.y, dx=dx, dy=dy,
                                    damage=8.0, speed=230.0, lifetime=3.5,
                                    proj_type="laser", color=COLOR_RED, radius=3.0,
                                    is_enemy=True
                                ))
                        elif e.enemy_type == "stalker":
                            cooldown = random.uniform(1.0, 1.5)
                            edx = player.x - e.x
                            edy = player.y - e.y
                            dist = math.sqrt(edx*edx + edy*edy)
                            if 5.0 < dist < 620.0:
                                dx = edx / dist
                                dy = edy / dist
                                projectiles.append(Projectile(
                                    x=e.x, y=e.y, dx=dx, dy=dy,
                                    damage=14.0, speed=130.0, lifetime=4.5,
                                    proj_type="missile", color=COLOR_AMBER, radius=4.0,
                                    homing=2.2, is_enemy=True
                                ))
                        elif e.enemy_type == "boss":
                            pattern = getattr(e, 'boss_attack_pattern', 0)
                            if pattern == 0:
                                # 1. Rotating spiral cross
                                offset = getattr(e, 'boss_angle_offset', 0.0)
                                offset += 0.22
                                e.boss_angle_offset = offset
                                for k in range(4):
                                    ang = offset + k * (math.pi / 2.0)
                                    projectiles.append(Projectile(
                                        x=e.x, y=e.y, dx=math.cos(ang), dy=math.sin(ang),
                                        damage=18.0, speed=140.0, lifetime=4.5,
                                        proj_type="laser", color=(1.0, 0.2, 0.2), radius=3.5,
                                        is_enemy=True
                                    ))
                                cooldown = 0.25 # Rapid firing ticks
                                count = getattr(e, 'boss_shot_count', 0) + 1
                                e.boss_shot_count = count
                                if count >= 16:
                                    e.boss_attack_pattern = 1
                                    e.boss_shot_count = 0
                            elif pattern == 1:
                                # 2. Giant ring burst of 20 lasers
                                for k in range(20):
                                    ang = k * (2.0 * math.pi / 20.0)
                                    projectiles.append(Projectile(
                                        x=e.x, y=e.y, dx=math.cos(ang), dy=math.sin(ang),
                                        damage=15.0, speed=110.0, lifetime=5.0,
                                        proj_type="laser", color=(0.2, 0.9, 1.0), radius=3.5,
                                        is_enemy=True
                                    ))
                                cooldown = 1.6
                                e.boss_attack_pattern = 2
                            elif pattern == 2:
                                # 3. Barrage of 4 homing missiles
                                edx = player.x - e.x
                                edy = player.y - e.y
                                dist = math.sqrt(edx*edx + edy*edy)
                                if dist > 0:
                                    base_ang = math.atan2(edy, edx)
                                    for k in range(-2, 2):
                                        ang = base_ang + k * 0.2
                                        projectiles.append(Projectile(
                                            x=e.x, y=e.y, dx=math.cos(ang), dy=math.sin(ang),
                                            damage=20.0, speed=100.0, lifetime=5.5,
                                            proj_type="missile", color=(1.0, 0.5, 0.0), radius=4.5,
                                            homing=2.5, is_enemy=True
                                        ))
                                cooldown = 2.0
                                e.boss_attack_pattern = 0
                        elif e.enemy_type == "swarmer":
                            cooldown = random.uniform(1.1, 2.0)
                            vx = math.cos(e.angle)
                            vy = math.sin(e.angle)
                            projectiles.append(Projectile(
                                x=e.x, y=e.y, dx=vx, dy=vy,
                                damage=4.0, speed=180.0, lifetime=3.0,
                                proj_type="laser", color=COLOR_RED, radius=2.0,
                                is_enemy=True
                            ))
                        e.shoot_timer = cooldown
            except Exception as e:
                log_error('Enemy Update', e)
            try:
                # Update Debris
                for d in debris:
                    d.update(dt)

            except Exception as e:
                log_error('Debris Update', e)
            try:
                # Update Items
                for item in items:
                    picked_up = item.update(dt, player.x, player.y, player.magnet_radius)
                    if picked_up:
                        if item.item_type == "xp":
                            # Add XP and check for level up
                            leveled_up = player.add_xp(item.value)
                            if leveled_up:
                                game_state = STATE_LEVEL_UP
                                upgrade_options = get_upgrade_pool(player, pool_size=3)
                                selected_upgrade_idx = 0
                        elif item.item_type == "health":
                            player.health = min(player.max_health, player.health + item.value)
                        elif item.item_type == "fuel":
                            player.hyperspace_energy = min(100.0, player.hyperspace_energy + item.value)
                        elif item.item_type == "credit":
                            run_credits += item.value
                            damage_numbers.append({"x": item.x, "y": item.y, "text": f"+{item.value} CRD", "timer": 0.50, "color": COLOR_AMBER})
                        elif item.item_type == "plasma":
                            run_plasma += item.value
                            damage_numbers.append({"x": item.x, "y": item.y, "text": "+1 PLS", "timer": 0.50, "color": (0.8, 0.2, 1.0)})
                        elif item.item_type == "core":
                            run_cores += item.value
                            damage_numbers.append({"x": item.x, "y": item.y, "text": "+1 COR", "timer": 0.60, "color": (0.2, 0.9, 1.0)})
                        elif item.item_type == "magnet":
                            # Pull all active items in the sector
                            for it in items:
                                if it.active:
                                    it.magnetized = True
                                    it.speed = 360.0
                                    it.max_speed = 760.0
                                    it.acceleration = 1350.0
                        elif item.item_type == "bomb":
                            # Vaporize standard enemies and deal heavy boss damage
                            for enemy in enemies:
                                if not enemy.active:
                                    continue
                                edx = enemy.x - player.x
                                edy = enemy.y - player.y
                                edist_sq = edx*edx + edy*edy
                                if edist_sq < 650.0 * 650.0:
                                    dmg_val = 160.0 if enemy.enemy_type == "boss" else enemy.health
                                    if enemy.enemy_type == "boss":
                                        killed = enemy.take_damage(160.0)
                                    else:
                                        killed = enemy.take_damage(9999.0)
                                    damage_numbers.append({"x": enemy.x, "y": enemy.y, "text": "BOOM", "timer": 0.65, "color": enemy.color})
                                    
                                    if killed:
                                        player.kills += 1
                                        xp_val = 1
                                        if enemy.enemy_type == "chaser": xp_val = 3
                                        elif enemy.enemy_type == "stalker": xp_val = 8
                                        items.append(Item(enemy.x, enemy.y, "xp", value=xp_val))
                                    for _ in range(14):
                                        debris.append(Debris(enemy.x, enemy.y, enemy.color))
                                        
                            # Spawn screen shockwave projectile
                            p_shock = Projectile(
                                x=player.x, y=player.y,
                                dx=0, dy=0,
                                damage=0, speed=0, lifetime=0.5, pierce=9999,
                                proj_type="shockwave", color=COLOR_WHITE, radius=650.0
                            )
                            projectiles.append(p_shock)

            except Exception as e:
                log_error('Item Update', e)
            try:
                # Process pending item drops from weapons kills
                for drop in player.pending_drops:
                    items.append(Item(drop["x"], drop["y"], drop["type"], value=drop["value"]))
                player.pending_drops.clear()

            except Exception as e:
                log_error('Weapon Kill Drop Process', e)
            try:
                # --- Update DRG Objectives ---
                for obj in objective_items:
                    if not obj["active"]:
                        continue

                    # Check player contact distance
                    dx = player.x - obj["x"]
                    dy = player.y - obj["y"]
                    dist_sq = dx*dx + dy*dy

                    if obj["type"] in ("crystal", "harvest_crystal"):
                        rad_sum = player.radius + 10.0
                        if dist_sq < rad_sum * rad_sum:
                            obj["active"] = False
                            run_plasma += 1
                            if obj["type"] == "crystal":
                                objective_collected += 1
                            for _ in range(5):
                                debris.append(Debris(obj["x"], obj["y"], (0.8, 0.2, 1.0)))

                    elif obj["type"] == "egg":
                        rad_sum = player.radius + 12.0
                        if dist_sq < rad_sum * rad_sum:
                            obj["active"] = False
                            objective_collected += 1
                            run_credits += 10 # Organic eggs give credits!
                            for _ in range(8):
                                debris.append(Debris(obj["x"], obj["y"], (0.2, 1.0, 0.4)))

                    elif obj["type"] == "beacon":
                        if dist_sq < 3600.0:  # 60.0 ** 2
                            obj["progress"] = min(1.0, obj["progress"] + 0.12 * dt)

                            # Uplink defense: spawn random swarmers
                            if random.random() < 0.05:
                                sa = random.uniform(0, 2.0*math.pi)
                                sd = random.uniform(150.0, 250.0)
                                enemies.append(Enemy(obj["x"] + sd*math.cos(sa), obj["y"] + sd*math.sin(sa), "swarmer"))

                            if obj["progress"] >= 1.0:
                                obj["active"] = False
                                objective_collected += 1
                                # EMP Shockwave blast
                                p = Projectile(
                                    x=obj["x"], y=obj["y"],
                                    dx=0, dy=0,
                                    damage=50, speed=0, lifetime=0.4, pierce=9999,
                                    proj_type="shockwave", color=COLOR_BLUE, radius=200.0
                                )
                                projectiles.append(p)

                # Check objective completion
                if objective_collected >= objective_needed and not objective_completed:
                    objective_completed = True

                if objective_completed and not objective_reward_given:
                    objective_reward_given = True
                    # Large mission completion reward
                    player.add_xp(500)
                    player.health = player.max_health
                    # Position and activate the escape pod 1200px away from player
                    ang = random.uniform(0.0, math.pi * 2)
                    escape_pod["x"] = player.x + math.cos(ang) * 1200.0
                    escape_pod["y"] = player.y + math.sin(ang) * 1200.0
                    escape_pod["active"] = True

            except Exception as e:
                log_error('Objectives Update', e)
            try:
                # --- Collision Checks ---
                # 0.9. Projectiles vs Asteroids (Splitting hits)
                for p in projectiles:
                    if p.is_enemy or not p.active:
                        continue
                    for ast in asteroids:
                        if not ast["active"]:
                            continue
                        adx = ast["x"] - p.x
                        ady = ast["y"] - p.y
                        adist_sq = adx*adx + ady*ady
                        rad_sum = p.radius + ast["radius"]
                        if adist_sq < rad_sum * rad_sum:
                            # Split/destroy asteroid!
                            p.active = False
                            destroy_asteroid(ast)

                # 1. Projectiles vs Enemies
                for p in projectiles:
                    if p.is_enemy:
                        continue # Enemy bullets don't hit enemies
                        
                    if not p.active or p.proj_type in ("rail", "shockwave", "vortex"):
                        continue # Rail, shockwave and vortex deal instant/continuous damage on fire/ticks

                    for e in enemies:
                        if not e.active or e in p.hit_enemies:
                            continue

                        dx = e.x - p.x
                        dy = e.y - p.y
                        dist_sq = dx * dx + dy * dy
                        rad_sum = p.radius + e.radius
                        if dist_sq < rad_sum * rad_sum:
                            killed = e.take_damage(p.damage * player.damage_mult)
                            p.hit_enemies.add(e)

                            # Homing rocket splash explosion
                            if p.proj_type in ("missile", "meteor"):
                                splash_r = (120.0 if p.proj_type == "meteor" else 60.0) * player.proj_size_mult
                                splash_r_sq = splash_r * splash_r
                                dmg = p.damage * player.damage_mult
                                for oe in enemies:
                                    if oe == e or not oe.active:
                                        continue
                                    odx = oe.x - p.x
                                    ody = oe.y - p.y
                                    odist_sq = odx*odx + ody*ody
                                    if odist_sq < splash_r_sq:
                                        if oe.take_damage(dmg):
                                            player.kills += 1
                                            player.xp_earned(oe.score_value, oe.x, oe.y)
                                        damage_numbers.append({"x": oe.x, "y": oe.y, "text": f"{int(dmg)}", "timer": 0.55, "color": oe.color})
                                        deb_color = (1.0, 0.5, 0.0) if p.proj_type == "meteor" else oe.color
                                        for _ in range(6 if p.proj_type == "meteor" else 3):
                                            debris.append(Debris(oe.x, oe.y, deb_color))

                            if p.proj_type == "rainbow_fire":
                                p.active = False
                                for f_i in range(5):
                                    f_angle = f_i * (2.0 * math.pi / 5.0) + random.uniform(-0.1, 0.1)
                                    projectiles.append(Projectile(
                                        x=p.x, y=p.y,
                                        dx=math.cos(f_angle), dy=math.sin(f_angle),
                                        damage=p.damage * 0.5,
                                        speed=150.0,
                                        lifetime=0.5,
                                        stop_type=3, # wait, pierce=3 is correct
                                        pierce=3,
                                        proj_type="flame",
                                        color=(1.0, 0.4, 0.0),
                                        radius=8.0,
                                        owner=player
                                    ))

                            # Bouncing logic
                            bounced = False
                            if p.bounces > 0 and p.proj_type in ("laser", "missile", "rainbow", "rainbow_fire", "meteor"):
                                other_target = None
                                min_odist_sq = 999999.0 * 999999.0
                                for oe in enemies:
                                    if oe == e or not oe.active or oe in p.hit_enemies:
                                        continue
                                    odx = oe.x - p.x
                                    ody = oe.y - p.y
                                    odist_sq = odx*odx + ody*ody
                                    if odist_sq < min_odist_sq:
                                        min_odist_sq = odist_sq
                                        other_target = oe

                                if other_target:
                                    odx = other_target.x - p.x
                                    ody = other_target.y - p.y
                                    odist = math.sqrt(min_odist_sq)
                                    if odist > 0:
                                        p.dx = odx / odist
                                        p.dy = ody / odist
                                    p.bounces -= 1
                                    bounced = True

                            if not bounced:
                                p.pierce -= 1
                                if p.pierce <= 0:
                                    p.active = False
                                    if p.split_level > 0:
                                        p.split(projectiles)
                                        p.split_level = 0

                            if killed:
                                player.kills += 1
                                xp_val = 1
                                if e.enemy_type == "chaser": xp_val = 3
                                elif e.enemy_type == "stalker": xp_val = 8
                                elif e.enemy_type == "boss": xp_val = 50

                                items.append(Item(e.x, e.y, "xp", value=xp_val))

                                health_chance = 0.04
                                if e.enemy_type == "boss":
                                    health_chance = 1.0
                                if random.random() < health_chance:
                                    items.append(Item(e.x, e.y, "health", value=20))

                                p_count = 6 if e.enemy_type != "boss" else 30
                                for _ in range(p_count):
                                    debris.append(Debris(e.x, e.y, e.color))

                            if not p.active:
                                break

                # 1.5. Enemy Projectiles vs Player
                for p in projectiles:
                    if not p.is_enemy or not p.active:
                        continue
                    
                    # Dry Drone protection check
                    dry_drone_weapon = next((w for w in player.accessories if w.name == "DRONE SEC"), None)
                    if dry_drone_weapon and hasattr(dry_drone_weapon, 'drone_positions'):
                        drone_blocked = False
                        for dx, dy, _ in dry_drone_weapon.drone_positions:
                            pdx = p.x - dx
                            pdy = p.y - dy
                            pdist_sq = pdx*pdx + pdy*pdy
                            rad_sum = p.radius + 15.0
                            if pdist_sq < rad_sum * rad_sum:
                                p.active = False
                                drone_blocked = True
                                # 25% chance to trigger Necronomicon-style shockwave
                                if random.random() < 0.25:
                                    sw_dmg = dry_drone_weapon.damage * player.damage_mult
                                    sw = Projectile(
                                        x=dx, y=dy, dx=0, dy=0,
                                        damage=sw_dmg,
                                        speed=0.0,
                                        lifetime=0.5,
                                        radius=90.0 * player.proj_size_mult,
                                        proj_type="shockwave",
                                        color=(1.0, 1.0, 1.0),
                                        owner=player
                                    )
                                    projectiles.append(sw)
                                    # Deal instant damage to nearby enemies
                                    for e in enemies:
                                        if e.active:
                                            edx = e.x - dx
                                            edy = e.y - dy
                                            edist_sq = edx*edx + edy*edy
                                            rad_sum_sw = sw.radius + e.radius
                                            if edist_sq < rad_sum_sw * rad_sum_sw:
                                                if e.take_damage(sw_dmg):
                                                    player.kills += 1
                                                    player.xp_earned(e.score_value, e.x, e.y)
                                                damage_numbers.append({"x": e.x, "y": e.y, "text": f"{int(sw_dmg)}", "timer": 0.55, "color": e.color})
                                break
                        if drone_blocked:
                            continue
                            
                    pdx = player.x - p.x
                    pdy = player.y - p.y
                    pdist_sq = pdx*pdx + pdy*pdy
                    rad_sum_p = player.radius * 0.45 + p.radius
                    if pdist_sq < rad_sum_p * rad_sum_p:
                        prev_hp = player.health
                        player.take_damage(p.damage)
                        p.active = False
                        
                        # Add damage number if player lost health
                        if player.iframe_timer >= 0.48 and player.health < prev_hp:
                            damage_numbers.append({"x": player.x, "y": player.y, "text": f"-{int(p.damage)}", "timer": 0.75, "color": COLOR_RED})

                # 2. Enemies vs Player (Melee contact flat hit with iframes)
                for e in enemies:
                    if not e.active:
                        continue
                    dx = player.x - e.x
                    dy = player.y - e.y
                    dist_sq = dx * dx + dy * dy
                    rad_sum_e = player.radius * 0.45 + e.radius * 0.55
                    if dist_sq < rad_sum_e * rad_sum_e:
                        prev_hp = player.health
                        player.take_damage(e.damage)
                        
                        # Add damage number if hit was registered
                        if player.iframe_timer >= 0.48 and player.health < prev_hp:
                            damage_numbers.append({"x": player.x, "y": player.y, "text": f"-{int(e.damage)}", "timer": 0.75, "color": COLOR_RED})

                        # Push enemy back slightly so they don't lock perfectly on top
                        push_factor = 20.0
                        dist = math.sqrt(dist_sq)
                        if dist > 0:
                            e.x -= (dx / dist) * push_factor * dt
                            e.y -= (dy / dist) * push_factor * dt

                # Check Game Over
                if player.health <= 0:
                    end_run(victory=False)

            except Exception as e:
                log_error('Collision Engine', e)            # Cleanup inactive lists
            enemies = [e for e in enemies if e.active]
            projectiles = [p for p in projectiles if p.active]
            items = [i for i in items if i.active]
            debris = [d for d in debris if d.active]

        try:
            # --- DRAWING ---
            world_batch.clear()
            hud_batch.clear()
            menu_bounds_uv = (0.0, 0.0, 0.0, 0.0)

            # Build World Batch
            if game_state in (STATE_GAMEPLAY, STATE_LEVEL_UP, STATE_GAME_OVER, STATE_DEBUG, STATE_SKILL_TREE, STATE_INTRO):
                # 1. Background Grid (infinite scrolling based on Sector color theme)
                if current_sector == 2:
                    grid_color = (0.25, 0.05, 0.35) # Purple-Dim (Plasma Nebula)
                elif current_sector == 3:
                    grid_color = (0.05, 0.20, 0.35) # Blue-Dim (Stellar Abyss)
                else:
                    grid_color = COLOR_GREEN_DIM     # Green-Dim (Sandstone Belt)
                draw_grid(camera.x, camera.y, WINDOW_WIDTH, WINDOW_HEIGHT, grid_size=60.0, color=grid_color, batch=world_batch)

                # 2. Background Stars (with 3-layer parallax scrolling)
                for sx, sy, brightness, layer in stars:
                    # Determine parallax movement factor
                    if layer == 0:
                        p_factor = 0.15 # Far background
                    elif layer == 1:
                        p_factor = 0.45 # Midground
                    else:
                        p_factor = 0.85 # Foreground close

                    # Project world coordinates with parallax shift relative to camera
                    draw_x = sx + camera.x * (1.0 - p_factor)
                    draw_y = sy + camera.y * (1.0 - p_factor)

                    color = (COLOR_GREEN[0] * brightness, COLOR_GREEN[1] * brightness, COLOR_GREEN[2] * brightness)

                    if layer == 0:
                        # Far stars: tiny dot-like dashes
                        world_batch.add_line(draw_x - 0.7, draw_y, draw_x + 0.7, draw_y, color)
                    elif layer == 1:
                        # Mid stars: small horizontal notch
                        world_batch.add_line(draw_x - 1.5, draw_y, draw_x + 1.5, draw_y, color)
                        world_batch.add_line(draw_x, draw_y - 1.5, draw_x, draw_y + 1.5, color)
                    else:
                        # Close stars: larger diamond shapes to feel close to camera
                        r = 2.5
                        world_batch.add_line(draw_x - r, draw_y, draw_x, draw_y - r, color)
                        world_batch.add_line(draw_x, draw_y - r, draw_x + r, draw_y, color)
                        world_batch.add_line(draw_x + r, draw_y, draw_x, draw_y + r, color)
                        world_batch.add_line(draw_x, draw_y + r, draw_x - r, draw_y, color)

                # 2.5 Background Celestial Bodies (Deep Parallax)
                # Body 1: Giant Sun (very far, 2% scroll speed)
                sun_x = 800.0 + camera.x * 0.98
                sun_y = -600.0 + camera.y * 0.98
                # Central core
                world_batch.add_circle(sun_x, sun_y, 100.0, (1.0, 0.85, 0.2), segments=24)
                # Corona/glow
                world_batch.add_circle(sun_x, sun_y, 110.0, (1.0, 0.5, 0.0), segments=24)
                # Solar flares / rays
                for idx in range(16):
                    ray_ang = (idx / 16) * math.pi * 2 + time_accum * 0.08
                    l1 = 115.0 + 8.0 * math.sin(time_accum * 4.0 + idx)
                    l2 = 135.0 + 12.0 * math.sin(time_accum * 4.0 + idx)
                    rx1 = sun_x + math.cos(ray_ang) * l1
                    ry1 = sun_y + math.sin(ray_ang) * l1
                    rx2 = sun_x + math.cos(ray_ang) * l2
                    ry2 = sun_y + math.sin(ray_ang) * l2
                    world_batch.add_line(rx1, ry1, rx2, ry2, (1.0, 0.6, 0.1))

                # Body 2: Ringed Gas Giant (far, 5% scroll speed)
                planet_x = -700.0 + camera.x * 0.95
                planet_y = 500.0 + camera.y * 0.95
                # Planet body
                world_batch.add_circle(planet_x, planet_y, 50.0, (0.2, 0.7, 0.9), segments=16)
                # Gas giant band lines
                world_batch.add_line(planet_x - 43.0, planet_y - 15.0, planet_x + 43.0, planet_y - 15.0, (0.2, 0.5, 0.8))
                world_batch.add_line(planet_x - 49.0, planet_y, planet_x + 49.0, planet_y, (0.2, 0.5, 0.8))
                world_batch.add_line(planet_x - 43.0, planet_y + 15.0, planet_x + 43.0, planet_y + 15.0, (0.2, 0.5, 0.8))
                # Rings
                ring_pts = []
                ring_ang = math.radians(22.0)
                cos_r = math.cos(ring_ang)
                sin_r = math.sin(ring_ang)
                for idx in range(32):
                    a = (idx / 32) * math.pi * 2
                    rx = math.cos(a) * 95.0
                    ry = math.sin(a) * 22.0
                    rot_x = rx * cos_r - ry * sin_r
                    rot_y = rx * sin_r + ry * cos_r
                    ring_pts.append((planet_x + rot_x, planet_y + rot_y))
                world_batch.add_polygon(ring_pts, (0.5, 0.8, 1.0), closed=True)

                # 3. Items
                for item in items:
                    item.draw(world_batch)

                # 4. Enemies
                for enemy in enemies:
                    enemy.draw(world_batch, player.hyperspace_active)

                # 5. Projectiles
                for p in projectiles:
                    p.draw(world_batch)
                    
                # Draw combat floating text
                for d in damage_numbers:
                    world_batch.add_text(d["text"], d["x"] - len(d["text"])*3.5, d["y"] - 12, scale=0.75, color=d["color"])

                # 6. Debris
                for d in debris:
                    d.draw(world_batch)
                    
                # 6.2. Draw Asteroids (Vector Colored Polygons)
                for ast in asteroids:
                    if not ast["active"]:
                        continue
                    cos_r = math.cos(ast["rotation"])
                    sin_r = math.sin(ast["rotation"])
                    rot_pts = []
                    for px, py in ast["shape_pts"]:
                        rx = px * cos_r - py * sin_r
                        ry = px * sin_r + py * cos_r
                        rot_pts.append((ast["x"] + rx, ast["y"] + ry))
                        
                    ast_type = ast.get("type", "normal")
                    if ast_type == "gold":
                        ast_color = COLOR_AMBER
                    elif ast_type == "plasma":
                        ast_color = (0.8, 0.2, 1.0)
                    elif ast_type == "core":
                        ast_color = (0.2, 0.9, 1.0)
                    else:
                        ast_color = (0.7, 0.7, 0.7) # normal
                    world_batch.add_polygon(rot_pts, ast_color, closed=True)

                # 6.5. DRG Objectives
                for obj in objective_items:
                    if not obj["active"] and obj["type"] != "beacon":
                        continue

                    if obj["type"] in ("crystal", "harvest_crystal"):
                        # Spinning purple crystal diamond
                        ang = (time_accum * 1.5) % (math.pi * 2)
                        r = 8.0
                        pts = [
                            (obj["x"] + r * math.cos(ang), obj["y"] + r * math.sin(ang)),
                            (obj["x"] + r * 0.5 * math.cos(ang + math.pi/2), obj["y"] + r * 0.5 * math.sin(ang + math.pi/2)),
                            (obj["x"] + r * math.cos(ang + math.pi), obj["y"] + r * math.sin(ang + math.pi)),
                            (obj["x"] + r * 0.5 * math.cos(ang + 3.0*math.pi/2), obj["y"] + r * 0.5 * math.sin(ang + 3.0*math.pi/2))
                        ]
                        world_batch.add_polygon(pts, (0.8, 0.2, 1.0), closed=True)
                        world_batch.add_circle(obj["x"], obj["y"], r * 1.5, (0.4, 0.1, 0.5), segments=8)

                    elif obj["type"] == "egg":
                        # Green organic egg
                        world_batch.add_circle(obj["x"], obj["y"], 10.0, (0.2, 1.0, 0.4), segments=12)
                        world_batch.add_circle(obj["x"], obj["y"], 5.0, (0.1, 0.6, 0.2), segments=8)
                        world_batch.add_line(obj["x"] - 10.0, obj["y"], obj["x"] + 10.0, obj["y"], (0.2, 1.0, 0.4))

                    elif obj["type"] == "beacon":
                        # Blue uplink field
                        if obj["active"]:
                            pulse = 0.7 + 0.3 * math.sin(time_accum * 4.0)
                            dim_blue = (0.1 * pulse, 0.4 * pulse, 0.8 * pulse)
                            world_batch.add_circle(obj["x"], obj["y"], 60.0, dim_blue, segments=32)

                            # Antenna structure
                            world_batch.add_line(obj["x"], obj["y"] - 25.0, obj["x"], obj["y"] + 2.0, COLOR_BLUE)
                            world_batch.add_line(obj["x"] - 8.0, obj["y"] - 15.0, obj["x"] + 8.0, obj["y"] - 15.0, COLOR_BLUE)
                            world_batch.add_line(obj["x"] - 5.0, obj["y"] - 5.0, obj["x"] + 5.0, obj["y"] - 5.0, COLOR_BLUE)

                            pct = int(obj["progress"] * 100)
                            bar_w = 40.0
                            world_batch.add_line(obj["x"] - bar_w/2, obj["y"] - 38.0, obj["x"] + bar_w/2, obj["y"] - 38.0, (0.2, 0.2, 0.2))
                            world_batch.add_line(obj["x"] - bar_w/2, obj["y"] - 38.0, obj["x"] - bar_w/2 + bar_w * obj["progress"], obj["y"] - 38.0, COLOR_BLUE)
                            world_batch.add_text(f"{pct}%", obj["x"] - 12.0, obj["y"] - 52.0, scale=0.6, color=COLOR_BLUE)
                        else:
                            # Completed beacon
                            world_batch.add_circle(obj["x"], obj["y"], 60.0, (0.05, 0.3, 0.1), segments=16)
                            world_batch.add_line(obj["x"], obj["y"] - 25.0, obj["x"], obj["y"] + 2.0, (0.1, 0.6, 0.2))
                            world_batch.add_text("SECURISE", obj["x"] - 22.0, obj["y"] - 40.0, scale=0.6, color=(0.2, 1.0, 0.4))

                # 6.5 Draw Escape Pod in the world
                if escape_pod.get("active", False):
                    # Outer yellow octagon
                    world_batch.add_circle(escape_pod["x"], escape_pod["y"], 20.0, (1.0, 1.0, 0.0), segments=8)
                    # Glowing center
                    world_batch.add_circle(escape_pod["x"], escape_pod["y"], 10.0, (1.0, 0.8, 0.2), segments=8)
                    # Crossbars
                    world_batch.add_line(escape_pod["x"] - 20.0, escape_pod["y"], escape_pod["x"] + 20.0, escape_pod["y"], (1.0, 1.0, 0.0))
                    world_batch.add_line(escape_pod["x"], escape_pod["y"] - 20.0, escape_pod["x"], escape_pod["y"] + 20.0, (1.0, 1.0, 0.0))
                    # Pulsing text
                    pulse = 0.8 + 0.2 * math.sin(time_accum * 6.0)
                    world_batch.add_text("EVAC", escape_pod["x"] - 14.0, escape_pod["y"] - 35.0, scale=0.7, color=(1.0 * pulse, 1.0 * pulse, 0.0))

                # 7. Player
                if game_state == STATE_INTRO:
                    draw_3d_player(world_batch, player.x, player.y, time_accum, intro_timer)
                else:
                    player.draw(world_batch)
                    if getattr(player, 'book_of_shadows_timer', 0.0) > 0.0:
                        world_batch.add_circle(player.x, player.y, player.radius * 2.2, (1.0, 1.0, 1.0), segments=24)
                        for _ in range(3):
                            p_ang = random.uniform(0.0, math.pi * 2)
                            p_rad = player.radius * 2.2 + random.uniform(-2.0, 4.0)
                            px = player.x + p_rad * math.cos(p_ang)
                            py = player.y + p_rad * math.sin(p_ang)
                            world_batch.add_line(px, py, px + random.uniform(-1, 1), py + random.uniform(-1, 1), (0.1, 0.8, 1.0))

            # Build HUD Batch
            if game_state == STATE_MENU:
                # Main Start Screen
                hud_batch.add_rect(20 * scale_factor, 20 * scale_factor, WINDOW_WIDTH - 40 * scale_factor, WINDOW_HEIGHT - 40 * scale_factor, COLOR_GREEN)
                hud_batch.add_rect(25 * scale_factor, 25 * scale_factor, WINDOW_WIDTH - 50 * scale_factor, WINDOW_HEIGHT - 50 * scale_factor, COLOR_GREEN_DIM)

                # Title
                hud_batch.add_text("VECTOR SURVIVOR", WINDOW_WIDTH / 2 - 190 * scale_factor, WINDOW_HEIGHT / 2 - 130 * scale_factor, scale=3.0 * scale_factor, color=COLOR_GREEN)

                # Instructions
                hud_batch.add_text("COMMANDES :", WINDOW_WIDTH / 2 - 280 * scale_factor, WINDOW_HEIGHT / 2 - 30 * scale_factor, scale=1.5 * scale_factor, color=COLOR_AMBER)
                hud_batch.add_text("- ZQSD / FLECHES : DIRIGER LE VAISSEAU", WINDOW_WIDTH / 2 - 280 * scale_factor, WINDOW_HEIGHT / 2 + 10 * scale_factor, scale=1.2 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text("- LES ARMES DETECTENT ET TIRENT AUTOMATIQUEMENT", WINDOW_WIDTH / 2 - 280 * scale_factor, WINDOW_HEIGHT / 2 + 35 * scale_factor, scale=1.2 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text("- RAMASSER LES DIAMANTS BLEUS POUR AMELIORER LE SYSTEME", WINDOW_WIDTH / 2 - 280 * scale_factor, WINDOW_HEIGHT / 2 + 60 * scale_factor, scale=1.2 * scale_factor, color=COLOR_WHITE)

                # Interactive Menu choices
                choices = [
                    "COMMENCER LA MISSION",
                    "AMELIORATIONS DE LA FLOTTE (META)",
                    "QUITTER LE JEU"
                ]
                for idx, text in enumerate(choices):
                    y_pos = WINDOW_HEIGHT / 2 + (120 + idx * 30) * scale_factor
                    if main_menu_selection == idx:
                        # Draw arrowhead pointer and highlight color
                        pulse = 0.8 + 0.2 * math.sin(time_accum * 8.0)
                        col = (COLOR_AMBER[0] * pulse, COLOR_AMBER[1] * pulse, COLOR_AMBER[2] * pulse)
                        hud_batch.add_text(f"> {text}", WINDOW_WIDTH / 2 - 180 * scale_factor, y_pos, scale=1.3 * scale_factor, color=col)
                    else:
                        hud_batch.add_text(f"  {text}", WINDOW_WIDTH / 2 - 180 * scale_factor, y_pos, scale=1.2 * scale_factor, color=COLOR_WHITE)

            elif game_state == STATE_INTRO:
                # Cinematic system initialization HUD text
                pulse = 0.7 + 0.3 * math.sin(time_accum * 8.0)
                if intro_timer > 2.0:
                    text = "INITIALISATION DU GYROSCOPE 3D..."
                    color = COLOR_AMBER
                elif intro_timer > 1.0:
                    text = "SYSTEMES SPATIAUX EN LIGNE"
                    color = COLOR_BLUE
                else:
                    text = "VECTORSURVIVOR.EXE : PRET"
                    color = (0.2 * pulse, 1.0 * pulse, 0.4 * pulse)
                
                draw_centered_text(hud_batch, text, WINDOW_WIDTH / 2, WINDOW_HEIGHT - 80 * scale_factor, scale=1.3 * scale_factor, color=color)

            elif game_state in (STATE_GAMEPLAY, STATE_LEVEL_UP, STATE_DEBUG):
                # Draw standard HUD using clean retro-futuristic CRT panels
                xp_pct = min(1.0, player.xp / player.xp_needed)

                # A. Top-Left Panel: Stats & Main Objective (dynamically sized)
                tl_x = 15 * scale_factor
                tl_y = 15 * scale_factor
                tl_h = 125 * scale_factor

                obj_title = "OBJECTIF PRINCIPAL :"
                if objective_type == "crystal":
                    obj_text = f"MINER LES CRISTAUX D'ASTRAEA : {objective_collected}/{objective_needed}"
                    obj_color = (0.8, 0.2, 1.0)
                elif objective_type == "egg":
                    obj_text = f"RECUPERER LES OEUFS DE NEBULEUSE : {objective_collected}/{objective_needed}"
                    obj_color = (0.2, 1.0, 0.4)
                elif objective_type == "beacon":
                    obj_text = f"SECURISER LES LIAISONS SPATIALES : {objective_collected}/{objective_needed}"
                    obj_color = COLOR_BLUE

                # Closest objective distance calculation
                closest_obj = None
                min_obj_dist = float('inf')
                for obj in objective_items:
                    if obj["active"]:
                        odx = obj["x"] - player.x
                        ody = obj["y"] - player.y
                        odist = math.sqrt(odx*odx + ody*ody)
                        if odist < min_obj_dist:
                            min_obj_dist = odist
                            closest_obj = obj

                eta_suffix = ""
                if closest_obj and player.speed > 0:
                    dist_m = int(min_obj_dist * 0.1)
                    eta_suffix = f" ({dist_m}m)"

                if objective_completed:
                    if escape_pod.get("active", False):
                        pdx = escape_pod["x"] - player.x
                        pdy = escape_pod["y"] - player.y
                        pdist = math.sqrt(pdx*pdx + pdy*pdy)
                        dist_m = int(pdist * 0.1)
                        obj_text_full = f"CAPSULE DE SAUVETAGE ({dist_m}m)"
                        obj_color = (1.0, 1.0, 0.0)
                    else:
                        obj_text_full = "MISSION ACCOMPLIE (CAPSULE PRETE)"
                        obj_color = (0.2, 1.0, 0.4)
                else:
                    obj_text_full = obj_text + eta_suffix

                # Dynamic width matching text size
                stats_str = f"NIVEAU:{player.level}   XP:{player.xp}/{player.xp_needed}"
                res_str = f"CREDITS:{run_credits}  PLASMA:{run_plasma}  COEURS:{run_cores}"
                sec_str = "SECTEUR 3 : ABYSSE STELLAIRE"  # Reference length
                longest_len = max(len(stats_str), len(obj_title), len(obj_text_full), len(res_str), len(sec_str))
                tl_w = (longest_len * 10.4 * 0.85 + 30) * scale_factor
                tl_w = max(330 * scale_factor, tl_w)
                tl_h = 145 * scale_factor

                draw_hud_panel(hud_batch, tl_x, tl_y, tl_w, tl_h, COLOR_GREEN_DIM)

                # Level & XP text inside panel
                hud_batch.add_text(f"NIVEAU:{player.level}", tl_x + 15 * scale_factor, tl_y + 15 * scale_factor, scale=1.05 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"XP:{player.xp}/{player.xp_needed}", tl_x + 165 * scale_factor, tl_y + 15 * scale_factor, scale=1.05 * scale_factor, color=COLOR_BLUE)

                # XP bar inside panel
                bar_w = tl_w - 30 * scale_factor
                hud_batch.add_rect(tl_x + 15 * scale_factor, tl_y + 35 * scale_factor, bar_w, 8 * scale_factor, COLOR_GREEN_DIM)
                if xp_pct > 0:
                    hud_batch.add_line(tl_x + 16 * scale_factor, tl_y + 39 * scale_factor, tl_x + 16 * scale_factor + (bar_w - 2 * scale_factor) * xp_pct, tl_y + 39 * scale_factor, COLOR_BLUE)

                hud_batch.add_text(obj_title, tl_x + 15 * scale_factor, tl_y + 55 * scale_factor, scale=0.82 * scale_factor, color=COLOR_AMBER)
                hud_batch.add_text(obj_text_full, tl_x + 15 * scale_factor, tl_y + 75 * scale_factor, scale=0.85 * scale_factor, color=obj_color)

                # Resources line
                hud_batch.add_text("BUTIN :", tl_x + 15 * scale_factor, tl_y + 98 * scale_factor, scale=0.82 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"CRD:{run_credits}", tl_x + 95 * scale_factor, tl_y + 98 * scale_factor, scale=0.82 * scale_factor, color=COLOR_AMBER)
                hud_batch.add_text(f"PLS:{run_plasma}", tl_x + 175 * scale_factor, tl_y + 98 * scale_factor, scale=0.82 * scale_factor, color=(0.8, 0.2, 1.0))
                hud_batch.add_text(f"COR:{run_cores}", tl_x + 250 * scale_factor, tl_y + 98 * scale_factor, scale=0.82 * scale_factor, color=(0.2, 0.9, 1.0))

                # Sector info line
                if current_sector == 1:
                    sec_name = "SECTEUR 1 : CEINTURE DE GRES"
                    sec_color = COLOR_GREEN
                elif current_sector == 2:
                    sec_name = "SECTEUR 2 : NEBULEUSE DE PLASMA"
                    sec_color = (0.8, 0.2, 1.0)
                else:
                    sec_name = "SECTEUR 3 : ABYSSE STELLAIRE"
                    sec_color = (0.2, 0.9, 1.0)
                hud_batch.add_text(sec_name, tl_x + 15 * scale_factor, tl_y + 120 * scale_factor, scale=0.85 * scale_factor, color=sec_color)


                # B. Top-Center Panel: Survival Timer
                tc_w = 160 * scale_factor
                tc_h = 35 * scale_factor
                tc_x = WINDOW_WIDTH * 0.5 - tc_w * 0.5
                tc_y = 15 * scale_factor
                draw_hud_panel(hud_batch, tc_x, tc_y, tc_w, tc_h, COLOR_GREEN_DIM)

                mins = int(game_time // 60)
                secs = int(game_time % 60)
                hud_batch.add_text(f"TEMPS:{mins:02d}:{secs:02d}", tc_x + 15 * scale_factor, tc_y + 12 * scale_factor, scale=1.1 * scale_factor, color=COLOR_GREEN)


                # C. Right-Side Tactical Panel: Combat Stats & Mini Radar Map
                tr_w = 160 * scale_factor
                tr_h = 220 * scale_factor
                tr_x = WINDOW_WIDTH - tr_w - 15 * scale_factor
                tr_y = 15 * scale_factor
                draw_hud_panel(hud_batch, tr_x, tr_y, tr_w, tr_h, COLOR_GREEN_DIM)

                hud_batch.add_text(f"ELIMINATIONS:{player.kills}", tr_x + 15 * scale_factor, tr_y + 15 * scale_factor, scale=0.85 * scale_factor, color=COLOR_AMBER)
                hud_batch.add_text(f"ENNEMIS:{len([e for e in enemies if e.active])}", tr_x + 15 * scale_factor, tr_y + 32 * scale_factor, scale=0.85 * scale_factor, color=COLOR_RED)

                # Center of mini-radar inside the right panel
                rcx = tr_x + tr_w * 0.5
                rcy = tr_y + 130 * scale_factor
                r_rad = 55.0 * scale_factor

                hud_batch.add_circle(rcx, rcy, r_rad, COLOR_GREEN_DIM, segments=24)
                hud_batch.add_circle(rcx, rcy, r_rad * 0.5, (COLOR_GREEN_DIM[0]*0.4, COLOR_GREEN_DIM[1]*0.4, COLOR_GREEN_DIM[2]*0.4), segments=12)
                hud_batch.add_line(rcx - r_rad, rcy, rcx + r_rad, rcy, COLOR_GREEN_DIM)
                hud_batch.add_line(rcx, rcy - r_rad, rcx, rcy + r_rad, COLOR_GREEN_DIM)
                
                # Dynamic Sweep line
                sweep_a = time_accum * 2.8
                hud_batch.add_line(rcx, rcy, rcx + r_rad * math.cos(sweep_a), rcy + r_rad * math.sin(sweep_a), COLOR_GREEN)
                
                # Radar center player dot
                hud_batch.add_line(rcx - 2 * scale_factor, rcy, rcx + 2 * scale_factor, rcy, COLOR_WHITE)
                hud_batch.add_line(rcx, rcy - 2 * scale_factor, rcx, rcy + 2 * scale_factor, COLOR_WHITE)
                
                # Draw other entities (Scale: 1 radar pixel = 22 world pixels)
                rad_scale = 22.0 / scale_factor
                
                # Draw Enemies on radar
                for e in enemies:
                    if not e.active:
                        continue
                    rx = (e.x - player.x) / rad_scale
                    ry = (e.y - player.y) / rad_scale
                    if rx*rx + ry*ry < r_rad*r_rad:
                        if e.enemy_type == "boss":
                            hud_batch.add_rect(rcx + rx - 2.5 * scale_factor, rcy + ry - 2.5 * scale_factor, 5 * scale_factor, 5 * scale_factor, COLOR_WHITE)
                        else:
                            hud_batch.add_line(rcx + rx - 1 * scale_factor, rcy + ry, rcx + rx + 1 * scale_factor, rcy + ry, COLOR_RED)
                            hud_batch.add_line(rcx + rx, rcy + ry - 1 * scale_factor, rcx + rx, rcy + ry + 1 * scale_factor, COLOR_RED)
                            
                # Draw Items (Blue for XP, Magenta/Red for fuel/health/powerups)
                for it in items:
                    if not it.active:
                        continue
                    rx = (it.x - player.x) / rad_scale
                    ry = (it.y - player.y) / rad_scale
                    if rx*rx + ry*ry < r_rad*r_rad:
                        if it.item_type == "xp":
                            hud_batch.add_line(rcx + rx, rcy + ry, rcx + rx + 0.5 * scale_factor, rcy + ry, COLOR_BLUE)
                        else:
                            hud_batch.add_line(rcx + rx - 1 * scale_factor, rcy + ry, rcx + rx + 1 * scale_factor, rcy + ry, (1.0, 0.1, 0.8))
                            
                # Draw Objective goals on radar
                for obj in objective_items:
                    if not obj["active"]:
                        continue
                    rx = (obj["x"] - player.x) / rad_scale
                    ry = (obj["y"] - player.y) / rad_scale
                    if rx*rx + ry*ry < r_rad*r_rad:
                        col = (0.8, 0.2, 1.0) if obj["type"] == "crystal" else (0.2, 1.0, 0.4)
                        hud_batch.add_circle(rcx + rx, rcy + ry, 2.0 * scale_factor, col, segments=6)
                        
                # Draw Escape Pod
                if escape_pod.get("active", False):
                    rx = (escape_pod["x"] - player.x) / rad_scale
                    ry = (escape_pod["y"] - player.y) / rad_scale
                    if rx*rx + ry*ry < r_rad*r_rad:
                        hud_batch.add_circle(rcx + rx, rcy + ry, 3.0 * scale_factor, (1.0, 1.0, 0.0), segments=8)
                        
                # Draw Gravity Singularity on Radar
                if event_manager.active_event and event_manager.active_event.name == "Puits de gravite":
                    ev = event_manager.active_event
                    rx = (ev.gx - player.x) / rad_scale
                    ry = (ev.gy - player.y) / rad_scale
                    if rx*rx + ry*ry < r_rad*r_rad:
                        hud_batch.add_circle(rcx + rx, rcy + ry, 3.5 * scale_factor, (0.6, 0.1, 1.0), segments=8)


                # D. Bottom-Left Panel: Health (Coque) & Energy (Propulsion)
                bl_x = 15 * scale_factor
                bl_y = WINDOW_HEIGHT - 125 * scale_factor
                bl_w = 330 * scale_factor
                bl_h = 110 * scale_factor
                draw_hud_panel(hud_batch, bl_x, bl_y, bl_w, bl_h, COLOR_GREEN_DIM)

                # Hull Integrity (Health) Bar
                hud_batch.add_text("INTEGRITE DE LA COQUE", bl_x + 15 * scale_factor, bl_y + 12 * scale_factor, scale=0.88 * scale_factor, color=COLOR_RED)
                hud_batch.add_rect(bl_x + 15 * scale_factor, bl_y + 28 * scale_factor, 200 * scale_factor, 10 * scale_factor, COLOR_GREEN_DIM)
                health_pct = min(1.0, player.health / player.max_health)
                if health_pct > 0:
                    hud_batch.add_line(bl_x + 17 * scale_factor, bl_y + 33 * scale_factor, bl_x + 17 * scale_factor + 196 * scale_factor * health_pct, bl_y + 33 * scale_factor, COLOR_RED)
                hud_batch.add_text(f"{int(player.health)}/{int(player.max_health)}", bl_x + 225 * scale_factor, bl_y + 25 * scale_factor, scale=1.0 * scale_factor, color=COLOR_RED)

                # E.g. Active Item Gauge
                if player.active_item is not None:
                    from systems.upgrade import ACTIVE_ITEMS
                    meta = ACTIVE_ITEMS.get(player.active_item)
                    if meta:
                        lvl_mult = max(0.40, 1.0 - (player.active_item_level - 1) * 0.15)
                        max_charge = meta["cooldown"] * lvl_mult
                        charge_pct = min(1.0, player.active_charge / max_charge)
                        
                        item_label = f"{meta['name']} (NIV {player.active_item_level})"
                        hud_batch.add_text(item_label, bl_x + 15 * scale_factor, bl_y + 55 * scale_factor, scale=0.88 * scale_factor, color=(0.1, 0.8, 1.0))
                        
                        hud_batch.add_rect(bl_x + 15 * scale_factor, bl_y + 71 * scale_factor, 200 * scale_factor, 10 * scale_factor, COLOR_GREEN_DIM)
                        if charge_pct > 0:
                            bar_fill = int(196 * scale_factor * charge_pct)
                            color = (0.2, 1.0, 0.4) if charge_pct >= 1.0 else (1.0, 0.1, 0.8)
                            hud_batch.add_line(bl_x + 17 * scale_factor, bl_y + 76 * scale_factor, bl_x + 17 * scale_factor + bar_fill, bl_y + 76 * scale_factor, color)
                        
                        charge_val = f"{int(charge_pct * 100)}%" if meta["charge_type"] != "kills" else f"{int(player.active_charge)}/{int(max_charge)}"
                        hud_batch.add_text(charge_val, bl_x + 225 * scale_factor, bl_y + 68 * scale_factor, scale=1.0 * scale_factor, color=(0.1, 0.8, 1.0))
                else:
                    hud_batch.add_text("AUCUN SYSTEME ACTIF EQUIPE", bl_x + 15 * scale_factor, bl_y + 55 * scale_factor, scale=0.80 * scale_factor, color=(0.5, 0.5, 0.5))
                    hud_batch.add_rect(bl_x + 15 * scale_factor, bl_y + 71 * scale_factor, 200 * scale_factor, 10 * scale_factor, COLOR_GREEN_DIM)
                    hud_batch.add_text("0%", bl_x + 225 * scale_factor, bl_y + 68 * scale_factor, scale=1.0 * scale_factor, color=(0.5, 0.5, 0.5))


                # E. Bottom inventory panel: Weapons, Accessories & Passives
                bx = 360 * scale_factor
                by = WINDOW_HEIGHT - 125 * scale_factor
                bw = WINDOW_WIDTH - bx - 15 * scale_factor
                bh = 110 * scale_factor
                draw_hud_panel(hud_batch, bx, by, bw, bh, COLOR_GREEN_DIM)

                hud_batch.add_text("ARMEMENT", bx + 12 * scale_factor, by + 16 * scale_factor, scale=0.55 * scale_factor, color=COLOR_GREEN_DIM)
                hud_batch.add_text("PASSIFS", bx + 12 * scale_factor, by + 66 * scale_factor, scale=0.55 * scale_factor, color=COLOR_GREEN_DIM)

                SHORT_NAMES = {
                    "AUTO-LASER": "LASER",
                    "CANON ELECTROMAGNETIQUE": "RAILG.",
                    "ONDE DE CHOC": "CHOC",
                    "LANCE-FLAMMES": "FLAM.",
                    "GRENADE VORTEX": "VORTEX",
                    "LAMES SPIRALES": "LAMES",
                    "MISSILE TETE CHERCHEUSE": "MISS.",
                    "COUP DE FAUX": "FAUX",
                    "BRIMSTONE": "BRIMS.",
                    "TECH X": "TECH X",
                    "COUTEAU DE MAMAN": "COUT.",
                    "GATLING ARC-EN-CIEL": "RAINB.",
                    "LANCEUR METEORE": "METEO.",
                    "ECLAIR DE NEON": "ECLAIR",
                    "BOUCLIER ORBITAL": "BOUCL.",
                    "DRONE LASER": "D-LAS.",
                    "DRONE ROQUETTE": "D-ROQ.",
                    "TROU NOIR": "T.NOIR",
                    "BOBINE TESLA": "TESLA",
                    "DRONE DE SOIN": "D-SOIN",
                    "ROBO-BABY": "R-BABY",
                    "DRONE INFESTATEUR": "D-INF.",
                    "DRONE SEC": "D-SEC"
                }

                SHORT_PASSIVES = {
                    "THRUSTERS": "PROP.",
                    "NANO-ARMOR": "ARMOR",
                    "XP MAGNET": "AIMANT",
                    "OVERDRIVE CORE": "SURCH.",
                    "REPAIR DRONES": "REPAR.",
                    "HULL UPGRADE": "COQUE",
                    "GIANT CELLS": "G.CELL",
                    "HYPER DRIVE": "HYPER",
                    "SPLIT FIRE": "SPLIT",
                    "SMART TARGETING": "VISEE",
                    "BOUNCING MATRIX": "REBON",
                    "DRILL TIP": "FOREUR",
                    "SHRAPNEL SHELLS": "SHRAP",
                    "HEAVY DRONES": "D.LOU.",
                    "DRONE ASSEMBLY": "D.ASS.",
                    "PLASMA CORE": "PLASMA",
                    "TINY PLANET": "PLANET",
                    "LUMP OF COAL": "CHARB.",
                    "SACRED HEART": "COEUR"
                }

                # Calculate slot spacing
                slot_w = 42 * scale_factor
                gap = 8 * scale_factor
                
                # Draw weapons (primary + accessories)
                all_weapons = player.primary_weapons + player.accessories
                for idx, w in enumerate(all_weapons):
                    wx = bx + 80 * scale_factor + idx * (slot_w + gap)
                    wy = by + 6 * scale_factor
                    
                    # Box border
                    box_color = COLOR_GREEN if not getattr(w, 'is_accessory', False) else COLOR_BLUE
                    hud_batch.add_rect(wx, wy, 32 * scale_factor, 32 * scale_factor, box_color)
                    
                    # Icon inside the box
                    cx = wx + 16 * scale_factor
                    cy = wy + 16 * scale_factor
                    size_i = 10 * scale_factor
                    draw_item_icon(hud_batch, cx, cy, size_i, w.name, scale_factor)
                    
                    # Cooldown bar under the box
                    bar_y = wy + 34 * scale_factor
                    bar_w = 32 * scale_factor
                    bar_h = 3 * scale_factor
                    hud_batch.add_rect(wx, bar_y, bar_w, bar_h, COLOR_GREEN_DIM)
                    
                    # Calculate cooldown percentage
                    max_cd = w.cooldown * getattr(player, 'cooldown_mult', 1.0)
                    if max_cd > 0:
                        charge_pct = 1.0 - min(1.0, max(0.0, w.cooldown_timer) / max(0.01, max_cd))
                    else:
                        charge_pct = 1.0
                    
                    if charge_pct > 0:
                        fill_len = (bar_w - 2 * scale_factor) * charge_pct
                        color_bar = (0.2, 1.0, 0.4) if charge_pct >= 1.0 else (1.0, 0.6, 0.1)
                        hud_batch.add_line(wx + 1 * scale_factor, bar_y + 1.5 * scale_factor, wx + 1 * scale_factor + fill_len, bar_y + 1.5 * scale_factor, color_bar)
                    
                    # Short name and level underneath
                    s_name = SHORT_NAMES.get(w.name, w.name[:5])
                    text_str = f"{s_name} L.{w.level}"
                    draw_centered_text(hud_batch, text_str, wx + 16 * scale_factor, wy + 42 * scale_factor, scale=0.45 * scale_factor, color=COLOR_WHITE)

                # Draw passives
                passives_items = list(player.passives.items())
                for idx, (p_name, p_lvl) in enumerate(passives_items):
                    px = bx + 80 * scale_factor + idx * (slot_w + gap)
                    py = by + 56 * scale_factor
                    
                    # Box border
                    hud_batch.add_rect(px, py, 32 * scale_factor, 32 * scale_factor, COLOR_WHITE)
                    
                    # Icon inside the box
                    cx = px + 16 * scale_factor
                    cy = py + 16 * scale_factor
                    size_i = 10 * scale_factor
                    draw_item_icon(hud_batch, cx, cy, size_i, p_name, scale_factor)
                    
                    # Short name and level underneath
                    s_name = SHORT_PASSIVES.get(p_name, p_name[:5])
                    text_str = f"{s_name} L.{p_lvl}"
                    draw_centered_text(hud_batch, text_str, px + 16 * scale_factor, py + 36 * scale_factor, scale=0.45 * scale_factor, color=COLOR_WHITE)

                # DRG Edge indicator arrows (with ETA travel times)
                for obj in objective_items:
                    if not obj["active"] or obj["type"] == "harvest_crystal":
                        continue

                    dx = obj["x"] - camera.x
                    dy = obj["y"] - camera.y
                    dist = math.sqrt(dx*dx + dy*dy)
                    if dist > 0:
                        scale_x = (WINDOW_WIDTH * 0.5 - 32 * scale_factor) / abs(dx) if dx != 0 else float('inf')
                        scale_y = (WINDOW_HEIGHT * 0.5 - 44 * scale_factor) / abs(dy) if dy != 0 else float('inf')
                        scale = min(scale_x, scale_y)

                        if scale < 1.0: # Offscreen!
                            arrow_x = WINDOW_WIDTH * 0.5 + (dx * scale)
                            arrow_y = WINDOW_HEIGHT * 0.5 + (dy * scale)
                            # Clamp arrow_y to prevent overlapping HUD panels
                            arrow_y = max(130.0 * scale_factor, min(WINDOW_HEIGHT - 145.0 * scale_factor, arrow_y))

                            ang = math.atan2(dy, dx)
                            cos_a = math.cos(ang)
                            sin_a = math.sin(ang)

                            p1 = (arrow_x + 12.0 * scale_factor * cos_a, arrow_y + 12.0 * scale_factor * sin_a)
                            p2 = (arrow_x - 6.0 * scale_factor * cos_a - 6.0 * scale_factor * sin_a, arrow_y - 6.0 * scale_factor * sin_a + 6.0 * scale_factor * cos_a)
                            p3 = (arrow_x - 6.0 * scale_factor * cos_a + 6.0 * scale_factor * sin_a, arrow_y - 6.0 * scale_factor * sin_a - 6.0 * scale_factor * cos_a)

                            if obj["type"] == "crystal":
                                color = (0.8, 0.2, 1.0)
                            elif obj["type"] == "egg":
                                color = (0.2, 1.0, 0.4)
                            else:
                                color = COLOR_BLUE

                            hud_batch.add_polygon([p1, p2, p3], color, closed=True)
                            
                            # Draw distance in meters next to indicator
                            dist_m = int(dist * 0.1)
                            hud_batch.add_text(f"{dist_m}m", arrow_x + 10 * scale_factor, arrow_y - 5 * scale_factor, scale=0.6 * scale_factor, color=color)

                # Flashing Compass Pointer to Escape Pod
                if escape_pod.get("active", False):
                    pdx = escape_pod["x"] - camera.x
                    pdy = escape_pod["y"] - camera.y
                    pdist = math.sqrt(pdx*pdx + pdy*pdy)
                    if pdist > 0:
                        scale_x = (WINDOW_WIDTH * 0.5 - 32 * scale_factor) / abs(pdx) if pdx != 0 else float('inf')
                        scale_y = (WINDOW_HEIGHT * 0.5 - 44 * scale_factor) / abs(pdy) if pdy != 0 else float('inf')
                        scale = min(scale_x, scale_y)

                        if scale < 1.0: # Offscreen!
                            arrow_x = WINDOW_WIDTH * 0.5 + (pdx * scale)
                            arrow_y = WINDOW_HEIGHT * 0.5 + (pdy * scale)
                            # Clamp arrow_y to prevent overlapping HUD panels
                            arrow_y = max(130.0 * scale_factor, min(WINDOW_HEIGHT - 145.0 * scale_factor, arrow_y))

                            ang = math.atan2(pdy, pdx)
                            cos_a = math.cos(ang)
                            sin_a = math.sin(ang)

                            p1 = (arrow_x + 12.0 * scale_factor * cos_a, arrow_y + 12.0 * scale_factor * sin_a)
                            p2 = (arrow_x - 6.0 * scale_factor * cos_a - 6.0 * scale_factor * sin_a, arrow_y - 6.0 * scale_factor * sin_a + 6.0 * scale_factor * cos_a)
                            p3 = (arrow_x - 6.0 * scale_factor * cos_a + 6.0 * scale_factor * sin_a, arrow_y - 6.0 * scale_factor * sin_a - 6.0 * scale_factor * cos_a)

                            hud_batch.add_polygon([p1, p2, p3], (1.0, 1.0, 0.0), closed=True)
                            hud_batch.add_text("CAPSULE", arrow_x + 10 * scale_factor, arrow_y - 5 * scale_factor, scale=0.65 * scale_factor, color=(1.0, 1.0, 0.0))
                            
                            dist_m = int(pdist * 0.1)
                            hud_batch.add_text(f"{dist_m}m", arrow_x + 10 * scale_factor, arrow_y + 7 * scale_factor, scale=0.65 * scale_factor, color=(1.0, 1.0, 0.0))

                # Draw flashing Space Event Announcement warning
                if event_manager.announcement_timer > 0:
                    pulse = 0.6 + 0.4 * math.sin(time_accum * 8.0)
                    color = COLOR_RED if (event_manager.active_event and event_manager.active_event.name == "Champ d'asteroides") else COLOR_AMBER
                    c_val = (color[0]*pulse, color[1]*pulse, color[2]*pulse)
                    hud_batch.add_text(event_manager.announcement_text, WINDOW_WIDTH / 2 - len(event_manager.announcement_text) * 4.5 * scale_factor, 120 * scale_factor, scale=1.4 * scale_factor, color=c_val)

                # 5. Draw Level Up Menu if state is LEVEL_UP
                if game_state == STATE_LEVEL_UP:
                    overlay_cx = WINDOW_WIDTH // 2
                    overlay_cy = WINDOW_HEIGHT // 2

                    # Calculate dynamic box width based on longest name and description
                    max_width_needed = 0
                    for opt in upgrade_options:
                        name_w = len(opt["name"]) * 10.4 * 1.2
                        desc_w = len(opt["desc"]) * 10.4 * 0.9
                        max_width_needed = max(max_width_needed, name_w, desc_w + 50)

                    # Dynamic box size and main overlay card size
                    box_w = (max_width_needed + 40) * scale_factor
                    box_w = max(540 * scale_factor, box_w)
                    box_h = 80 * scale_factor

                    overlay_w = box_w + 60 * scale_factor
                    overlay_h = 410 * scale_factor
                    overlay_x = overlay_cx - overlay_w * 0.5
                    overlay_y = overlay_cy - 220 * scale_factor

                    # Draw semi-transparent card background (Amber)
                    draw_hud_panel(hud_batch, overlay_x, overlay_y, overlay_w, overlay_h, COLOR_AMBER, fill_color=(0.12, 0.08, 0.02))
                    if WINDOW_WIDTH > 0 and WINDOW_HEIGHT > 0:
                        menu_bounds_uv = (
                            overlay_x / WINDOW_WIDTH,
                            1.0 - (overlay_y + overlay_h) / WINDOW_HEIGHT,
                            (overlay_x + overlay_w) / WINDOW_WIDTH,
                            1.0 - overlay_y / WINDOW_HEIGHT
                        )

                    hud_batch.add_text("MODIFICATION DU SYSTEME REQUISE", overlay_cx - 230 * scale_factor, overlay_cy - 190 * scale_factor, scale=1.4 * scale_factor, color=COLOR_AMBER)

                    # Draw options
                    for idx, opt in enumerate(upgrade_options):
                        box_x = overlay_cx - box_w * 0.5
                        box_y = overlay_cy - 140 * scale_factor + idx * 100 * scale_factor

                        # Draw choice outline
                        box_color = (0.2, 1.0, 0.5) if idx == selected_upgrade_idx else (0.1, 0.45, 0.2)
                        opt_fill = (0.02, 0.08, 0.04) if idx == selected_upgrade_idx else (0.0, 0.02, 0.0)
                        draw_hud_panel(hud_batch, box_x, box_y, box_w, box_h, box_color, fill_color=opt_fill)

                        # Highlight double lines on hover/select
                        if idx == selected_upgrade_idx:
                            hud_batch.add_rect(box_x - 2 * scale_factor, box_y - 2 * scale_factor, box_w + 4 * scale_factor, box_h + 4 * scale_factor, COLOR_WHITE)
                            hud_batch.add_text(">", box_x - 25 * scale_factor, box_y + 30 * scale_factor, scale=1.8 * scale_factor, color=COLOR_WHITE)

                        # Option metadata text
                        text_color = COLOR_WHITE if idx == selected_upgrade_idx else (1.0, 0.9, 0.4)
                        
                        opt_name = opt["name"]
                        name_scale = 1.2 * scale_factor
                        name_len = len(opt_name) * 10.4 * 1.2
                        if name_len > box_w - 80 * scale_factor:
                            name_scale *= (box_w - 80 * scale_factor) / name_len
                        hud_batch.add_text(opt_name, box_x + 20 * scale_factor, box_y + 15 * scale_factor, scale=name_scale, color=text_color)

                        desc_text = opt["desc"]
                        desc_scale = 0.9 * scale_factor
                        desc_len = len(desc_text) * 10.4 * 0.9
                        if desc_len > box_w - 80 * scale_factor:
                            desc_scale *= (box_w - 80 * scale_factor) / desc_len
                        hud_batch.add_text(desc_text, box_x + 20 * scale_factor, box_y + 45 * scale_factor, scale=desc_scale, color=(0.9, 0.9, 0.9))

                        # Display quick key shortcuts
                        hud_batch.add_text(f"[{idx+1}]", box_x + box_w - 40 * scale_factor, box_y + 30 * scale_factor, scale=1.2 * scale_factor, color=box_color)

                elif game_state == STATE_DEBUG:
                    overlay_cx = WINDOW_WIDTH // 2
                    overlay_cy = WINDOW_HEIGHT // 2

                    opts = get_debug_options()
                    spacing = 22 if debug_page in (1, 2, 3) else 30

                    # Calculate dynamic box width based on longest debug name
                    max_width_needed = max(len(opt["name"]) * 10.4 * (0.9 if debug_page in (1, 2, 3) else 1.1) for opt in opts)
                    box_w = (max_width_needed + 40) * scale_factor
                    box_w = max(540 * scale_factor, box_w)

                    max_visible = 10
                    num_visible = min(len(opts), max_visible)
                    overlay_w = box_w + 60 * scale_factor
                    overlay_h = (55 + num_visible * spacing + 25) * scale_factor
                    overlay_x = overlay_cx - overlay_w * 0.5
                    overlay_y = overlay_cy - overlay_h * 0.5

                    draw_hud_panel(hud_batch, overlay_x, overlay_y, overlay_w, overlay_h, COLOR_RED, fill_color=(0.12, 0.02, 0.02))
                    if WINDOW_WIDTH > 0 and WINDOW_HEIGHT > 0:
                        menu_bounds_uv = (
                            overlay_x / WINDOW_WIDTH,
                            1.0 - (overlay_y + overlay_h) / WINDOW_HEIGHT,
                            (overlay_x + overlay_w) / WINDOW_WIDTH,
                            1.0 - overlay_y / WINDOW_HEIGHT
                        )

                    title = "CONSOLE DE DEBOGAGE // CODES DE TRICHE"
                    if debug_page == 1: title = "CONSOLE DE DEBOGAGE // ARMES PRIMAIRES"
                    elif debug_page == 2: title = "CONSOLE DE DEBOGAGE // ACCESSOIRES"
                    elif debug_page == 3: title = "CONSOLE DE DEBOGAGE // AMELIORATIONS PASSIVES"
                    hud_batch.add_text(title, overlay_cx - 230 * scale_factor, overlay_y + 20 * scale_factor, scale=1.3 * scale_factor, color=COLOR_RED)

                    # Draw visible options
                    visible_opts = opts[debug_scroll_offset : debug_scroll_offset + max_visible]
                    
                    # Draw scroll indicators
                    if debug_scroll_offset > 0:
                        hud_batch.add_text("▲", overlay_cx - 10 * scale_factor, overlay_y + 38 * scale_factor, scale=1.0 * scale_factor, color=(1.0, 0.8, 0.2))
                    if debug_scroll_offset + max_visible < len(opts):
                        hud_batch.add_text("▼", overlay_cx - 10 * scale_factor, overlay_y + (55 + num_visible * spacing + 5) * scale_factor, scale=1.0 * scale_factor, color=(1.0, 0.8, 0.2))

                    for visible_idx, opt in enumerate(visible_opts):
                        idx = debug_scroll_offset + visible_idx
                        box_x = overlay_cx - box_w * 0.5
                        box_y = overlay_y + (55 + visible_idx * spacing) * scale_factor

                        if idx == selected_debug_idx:
                            hud_batch.add_text(">", box_x - 25 * scale_factor, box_y, scale=1.0 * scale_factor, color=COLOR_WHITE)
                            opt_color = COLOR_WHITE
                        else:
                            opt_color = (1.0, 0.45, 0.45) if opt["action"] != "nop" else (1.0, 0.8, 0.2)

                        hud_batch.add_text(opt["name"], box_x + 5 * scale_factor, box_y, scale=(0.9 if debug_page in (1, 2, 3) else 1.1) * scale_factor, color=opt_color)

            elif game_state == STATE_SKILL_TREE:
                overlay_cx = WINDOW_WIDTH // 2
                overlay_cy = WINDOW_HEIGHT // 2

                w = 960 * scale_factor
                h = 680 * scale_factor
                x = overlay_cx - w * 0.5
                y = overlay_cy - h * 0.5

                # Draw large cyber card background (Green)
                draw_hud_panel(hud_batch, x, y, w, h, COLOR_GREEN, fill_color=(0.01, 0.05, 0.02))
                if WINDOW_WIDTH > 0 and WINDOW_HEIGHT > 0:
                    menu_bounds_uv = (
                        x / WINDOW_WIDTH,
                        1.0 - (y + h) / WINDOW_HEIGHT,
                        (x + w) / WINDOW_WIDTH,
                        1.0 - y / WINDOW_HEIGHT
                    )

                # Header Title
                hud_batch.add_text("ARBRE DE CONFIGURATION DU CHASSEUR", overlay_cx - 280 * scale_factor, y + 25 * scale_factor, scale=1.4 * scale_factor, color=COLOR_GREEN)
                
                # Central Vaisseau Core Box
                core_w = 200 * scale_factor
                core_h = 60 * scale_factor
                core_x = overlay_cx - core_w * 0.5
                core_y = overlay_cy - 120 * scale_factor
                draw_hud_panel(hud_batch, core_x, core_y, core_w, core_h, COLOR_WHITE, fill_color=(0.04, 0.04, 0.05))
                hud_batch.add_text("NOYAU DE CHASSE", core_x + 25 * scale_factor, core_y + 12 * scale_factor, scale=1.1 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"NIVEAU : {player.level}", core_x + 50 * scale_factor, core_y + 35 * scale_factor, scale=0.9 * scale_factor, color=COLOR_GREEN)

                # Central Active Item Box
                active_y = core_y + core_h + 15 * scale_factor
                active_w = 200 * scale_factor
                active_h = 45 * scale_factor
                active_x = overlay_cx - active_w * 0.5
                if player.active_item is not None:
                    from systems.upgrade import ACTIVE_ITEMS
                    meta = ACTIVE_ITEMS.get(player.active_item)
                    if meta:
                        draw_hud_panel(hud_batch, active_x, active_y, active_w, active_h, (0.1, 0.8, 1.0), fill_color=(0.02, 0.05, 0.08))
                        hud_batch.add_text("MODULE ACTIF", active_x + 50 * scale_factor, active_y + 8 * scale_factor, scale=0.75 * scale_factor, color=(0.1, 0.8, 1.0))
                        hud_batch.add_text(meta["name"], active_x + 10 * scale_factor, active_y + 24 * scale_factor, scale=0.65 * scale_factor, color=COLOR_WHITE)
                        hud_batch.add_text(f"NIV.{player.active_item_level}", active_x + active_w - 55 * scale_factor, active_y + 8 * scale_factor, scale=0.7 * scale_factor, color=COLOR_WHITE)
                        hud_batch.add_line(overlay_cx, core_y + core_h, overlay_cx, active_y, (0.1, 0.8, 1.0))
                else:
                    draw_hud_panel(hud_batch, active_x, active_y, active_w, active_h, COLOR_GREEN_DIM, fill_color=(0.02, 0.02, 0.02))
                    hud_batch.add_text("PAS D'ACTIF EQUIPE", active_x + 30 * scale_factor, active_y + 16 * scale_factor, scale=0.8 * scale_factor, color=COLOR_GREEN_DIM)
                    hud_batch.add_line(overlay_cx, core_y + core_h, overlay_cx, active_y, COLOR_GREEN_DIM)

                # Spacing coordinates
                y_start = overlay_cy - 210 * scale_factor
                box_w = 215 * scale_factor
                box_h = 45 * scale_factor

                # Draw Primary Weapons (Left Column)
                hud_batch.add_text("ARMES OFFENSIVES", overlay_cx - 380 * scale_factor, y_start - 30 * scale_factor, scale=1.0 * scale_factor, color=COLOR_AMBER)
                for i in range(4):
                    box_x = overlay_cx - 380 * scale_factor
                    box_y = y_start + i * 65 * scale_factor
                    if i < len(player.primary_weapons):
                        w_inst = player.primary_weapons[i]
                        draw_hud_panel(hud_batch, box_x, box_y, box_w, box_h, COLOR_AMBER, fill_color=(0.08, 0.04, 0.01))
                        hud_batch.add_text(w_inst.name, box_x + 10 * scale_factor, box_y + 10 * scale_factor, scale=0.82 * scale_factor, color=COLOR_AMBER)
                        hud_batch.add_text(f"NIV.{w_inst.level}", box_x + box_w - 55 * scale_factor, box_y + 27 * scale_factor, scale=0.8 * scale_factor, color=COLOR_WHITE)
                        # Connect to core
                        hud_batch.add_line(box_x + box_w, box_y + box_h * 0.5, core_x, core_y + core_h * 0.5, COLOR_AMBER)
                    else:
                        hud_batch.add_rect(box_x, box_y, box_w, box_h, COLOR_GREEN_DIM)
                        hud_batch.add_text("[SLOT ARME VIDE]", box_x + 35 * scale_factor, box_y + 17 * scale_factor, scale=0.8 * scale_factor, color=COLOR_GREEN_DIM)

                # Draw Accessories (Right Column)
                hud_batch.add_text("MODULES TACTIQUES", overlay_cx + 165 * scale_factor, y_start - 30 * scale_factor, scale=1.0 * scale_factor, color=COLOR_BLUE)
                for i in range(4):
                    box_x = overlay_cx + 165 * scale_factor
                    box_y = y_start + i * 65 * scale_factor
                    if i < len(player.accessories):
                        acc_inst = player.accessories[i]
                        draw_hud_panel(hud_batch, box_x, box_y, box_w, box_h, COLOR_BLUE, fill_color=(0.01, 0.04, 0.08))
                        hud_batch.add_text(acc_inst.name, box_x + 10 * scale_factor, box_y + 10 * scale_factor, scale=0.82 * scale_factor, color=COLOR_BLUE)
                        hud_batch.add_text(f"NIV.{acc_inst.level}", box_x + box_w - 55 * scale_factor, box_y + 27 * scale_factor, scale=0.8 * scale_factor, color=COLOR_WHITE)
                        # Connect to core
                        hud_batch.add_line(box_x, box_y + box_h * 0.5, core_x + core_w, core_y + core_h * 0.5, COLOR_BLUE)
                    else:
                        hud_batch.add_rect(box_x, box_y, box_w, box_h, COLOR_GREEN_DIM)
                        hud_batch.add_text("[SLOT DRONE VIDE]", box_x + 35 * scale_factor, box_y + 17 * scale_factor, scale=0.8 * scale_factor, color=COLOR_GREEN_DIM)

                # Draw Passives (Bottom Grid)
                hud_batch.add_text("NOYAU DE SYNERGIES (PASSIVE)", overlay_cx - 150 * scale_factor, overlay_cy + 95 * scale_factor, scale=1.0 * scale_factor, color=COLOR_GREEN)
                passives_list = list(player.passives.items())
                p_w = 215 * scale_factor
                p_h = 42 * scale_factor
                for k in range(6):
                    col = k % 3
                    row = k // 3
                    box_x = overlay_cx + (-330 + col * 225) * scale_factor
                    box_y = overlay_cy + (125 + row * 52) * scale_factor
                    
                    if k < len(passives_list):
                        p_name, p_lvl = passives_list[k]
                        translated_name = PASSIVE_NAMES_FR.get(p_name, p_name)
                        draw_hud_panel(hud_batch, box_x, box_y, p_w, p_h, COLOR_GREEN, fill_color=(0.01, 0.06, 0.02))
                        hud_batch.add_text(translated_name, box_x + 10 * scale_factor, box_y + 8 * scale_factor, scale=0.75 * scale_factor, color=COLOR_GREEN)
                        hud_batch.add_text(f"NIV.{p_lvl}", box_x + p_w - 55 * scale_factor, box_y + 25 * scale_factor, scale=0.75 * scale_factor, color=COLOR_WHITE)
                        
                        # Connect to core or weapon/accessory columns based on synergy type
                        # Projectile modifiers -> connect to weapons column
                        if p_name in ("GIANT CELLS", "HYPER DRIVE", "SPLIT FIRE", "SMART TARGETING", "BOUNCING MATRIX", "DRILL TIP", "SHRAPNEL SHELLS", "PLASMA CORE"):
                            hud_batch.add_line(box_x + p_w * 0.5, box_y, overlay_cx - 272.5 * scale_factor, y_start + 260 * scale_factor, COLOR_AMBER)
                        # Drone modifiers -> connect to accessories column
                        elif p_name in ("HEAVY DRONES", "DRONE ASSEMBLY"):
                            hud_batch.add_line(box_x + p_w * 0.5, box_y, overlay_cx + 272.5 * scale_factor, y_start + 260 * scale_factor, COLOR_BLUE)
                        # Base boosters -> connect to core
                        else:
                            hud_batch.add_line(box_x + p_w * 0.5, box_y, overlay_cx, core_y + core_h, COLOR_WHITE)
                    else:
                        hud_batch.add_rect(box_x, box_y, p_w, p_h, COLOR_GREEN_DIM)
                        hud_batch.add_text("[SLOT VIDE]", box_x + 55 * scale_factor, box_y + 16 * scale_factor, scale=0.8 * scale_factor, color=COLOR_GREEN_DIM)

                # Footer Legend
                hud_batch.add_text("[TAB / ECHAP] RETOUR AU COMBAT", overlay_cx - 165 * scale_factor, y + h - 35 * scale_factor, scale=1.0 * scale_factor, color=COLOR_GREEN)

            elif game_state == STATE_META_UPGRADES:
                overlay_cx = WINDOW_WIDTH // 2
                overlay_cy = WINDOW_HEIGHT // 2

                w = 960 * scale_factor
                h = 680 * scale_factor
                x = overlay_cx - w * 0.5
                y = overlay_cy - h * 0.5

                # Large tech board with yellow highlight outline
                draw_hud_panel(hud_batch, x, y, w, h, COLOR_AMBER, fill_color=(0.04, 0.03, 0.01))

                # Header Title
                hud_batch.add_text("AMELIORATIONS DE LA FLOTTE (META)", overlay_cx - 275 * scale_factor, y + 25 * scale_factor, scale=1.4 * scale_factor, color=COLOR_AMBER)

                # Show currencies at the top right
                crd_str = f"CREDITS: {save_data.get('credits', 0)}"
                pls_str = f"PLASMA: {save_data.get('plasma', 0)}"
                cor_str = f"COEURS: {save_data.get('cores', 0)}"
                
                hud_batch.add_text(crd_str, x + 50 * scale_factor, y + 75 * scale_factor, scale=1.05 * scale_factor, color=COLOR_AMBER)
                hud_batch.add_text(pls_str, x + 350 * scale_factor, y + 75 * scale_factor, scale=1.05 * scale_factor, color=(0.8, 0.2, 1.0))
                hud_batch.add_text(cor_str, x + 650 * scale_factor, y + 75 * scale_factor, scale=1.05 * scale_factor, color=(0.2, 0.9, 1.0))

                # Horizontal line separator
                hud_batch.add_line(x + 40 * scale_factor, y + 105 * scale_factor, x + w - 40 * scale_factor, y + 105 * scale_factor, COLOR_AMBER)

                # Draw Upgrades List
                keys = list(UPGRADE_METADATA.keys())
                for idx, key in enumerate(keys):
                    meta = UPGRADE_METADATA[key]
                    current_lvl = save_data["upgrades"].get(key, 0)
                    is_selected = (meta_menu_selection == idx)

                    # Row box coordinates
                    row_w = w - 100 * scale_factor
                    row_h = 70 * scale_factor
                    row_x = x + 50 * scale_factor
                    row_y = y + 125 * scale_factor + idx * 78 * scale_factor

                    # Select color based on hover selection state
                    row_color = COLOR_WHITE if is_selected else COLOR_GREEN_DIM
                    row_fill = (0.08, 0.06, 0.02) if is_selected else (0.02, 0.02, 0.02)

                    # Background row panel
                    draw_hud_panel(hud_batch, row_x, row_y, row_w, row_h, row_color, fill_color=row_fill)

                    # Upgrade Name
                    hud_batch.add_text(meta["name"], row_x + 20 * scale_factor, row_y + 12 * scale_factor, scale=1.0 * scale_factor, color=row_color)

                    # Upgrade Description
                    hud_batch.add_text(meta["desc"], row_x + 20 * scale_factor, row_y + 40 * scale_factor, scale=0.8 * scale_factor, color=(0.7, 0.7, 0.7))

                    # Level bar indicators
                    bar_str = "["
                    for l in range(10):
                        if l < current_lvl:
                            bar_str += "|"
                        else:
                            bar_str += "."
                    bar_str += f"] {current_lvl}/10"
                    
                    hud_batch.add_text(bar_str, row_x + row_w - 380 * scale_factor, row_y + 12 * scale_factor, scale=1.0 * scale_factor, color=COLOR_WHITE)

                    # Costs text
                    if current_lvl >= meta["max_lvl"]:
                        hud_batch.add_text("MAXIMUM ATTEINT", row_x + row_w - 200 * scale_factor, row_y + 28 * scale_factor, scale=1.0 * scale_factor, color=COLOR_GREEN)
                    else:
                        cost = get_upgrade_cost(key, current_lvl)
                        if cost:
                            # Verify if players have enough balance for color highlights (Green/Red)
                            c_color = COLOR_GREEN if save_data["credits"] >= cost["credits"] else COLOR_RED
                            p_color = (0.8, 0.2, 1.0) if save_data["plasma"] >= cost["plasma"] else COLOR_RED
                            o_color = (0.2, 0.9, 1.0) if save_data["cores"] >= cost["cores"] else COLOR_RED

                            hud_batch.add_text(f"{cost['credits']} CRD", row_x + row_w - 210 * scale_factor, row_y + 12 * scale_factor, scale=0.8 * scale_factor, color=c_color)
                            hud_batch.add_text(f"{cost['plasma']} PLS", row_x + row_w - 210 * scale_factor, row_y + 40 * scale_factor, scale=0.8 * scale_factor, color=p_color)
                            if cost["cores"] > 0:
                                hud_batch.add_text(f"{cost['cores']} COR", row_x + row_w - 110 * scale_factor, row_y + 26 * scale_factor, scale=0.8 * scale_factor, color=o_color)

                # Footer controls legend
                hud_batch.add_text("ZQSD / FLECHES : CHOISIR  |  ENTREE / ESPACE : ACHETER", overlay_cx - 260 * scale_factor, y + h - 55 * scale_factor, scale=0.85 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text("R : REINITIALISER LES NIVEAUX (REMBOURSE 100%)  |  ECHAP : RETOUR MENU", overlay_cx - 315 * scale_factor, y + h - 30 * scale_factor, scale=0.85 * scale_factor, color=COLOR_AMBER)

            elif game_state == STATE_SECTOR_TRANSITION:
                overlay_cx = WINDOW_WIDTH // 2
                overlay_cy = WINDOW_HEIGHT // 2

                w = 860 * scale_factor
                h = 580 * scale_factor
                x = overlay_cx - w * 0.5
                y = overlay_cy - h * 0.5

                # Large transition panel with green highlight outline
                draw_hud_panel(hud_batch, x, y, w, h, COLOR_GREEN, fill_color=(0.02, 0.08, 0.03))
                if WINDOW_WIDTH > 0 and WINDOW_HEIGHT > 0:
                    menu_bounds_uv = (
                        x / WINDOW_WIDTH,
                        1.0 - (y + h) / WINDOW_HEIGHT,
                        (x + w) / WINDOW_WIDTH,
                        1.0 - y / WINDOW_HEIGHT
                    )

                # Header Title
                hud_batch.add_text("TRANSITION DE SECTEUR REUSSIE", overlay_cx - 240 * scale_factor, y + 40 * scale_factor, scale=1.5 * scale_factor, color=COLOR_GREEN)
                hud_batch.add_text("CHARGEMENT DU DIVE SUIVANT...", overlay_cx - 165 * scale_factor, y + 80 * scale_factor, scale=1.1 * scale_factor, color=COLOR_WHITE)

                # Sector summary
                hud_batch.add_text(f"SECTEUR COMPLET : SECTEUR {current_sector}", x + 100 * scale_factor, y + 150 * scale_factor, scale=1.3 * scale_factor, color=COLOR_AMBER)
                hud_batch.add_text(f"- Niveau actuel du vaisseau : {player.level}", x + 100 * scale_factor, y + 190 * scale_factor, scale=1.1 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"- Armes equipees : {len(player.primary_weapons)}/4", x + 100 * scale_factor, y + 220 * scale_factor, scale=1.1 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"- Drones d'appui tactiques : {len(player.accessories)}/4", x + 100 * scale_factor, y + 250 * scale_factor, scale=1.1 * scale_factor, color=COLOR_WHITE)

                # Resources accumulated
                hud_batch.add_text("BUTIN SECURISE ET TRANSFERE :", x + 100 * scale_factor, y + 300 * scale_factor, scale=1.2 * scale_factor, color=COLOR_AMBER)
                hud_batch.add_text(f"  + CREDITS ASSIMILES : +{run_credits}", x + 120 * scale_factor, y + 330 * scale_factor, scale=1.05 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"  + CRISTAUX DE PLASMA : +{run_plasma}", x + 120 * scale_factor, y + 355 * scale_factor, scale=1.05 * scale_factor, color=(0.8, 0.2, 1.0))
                hud_batch.add_text(f"  + COEURS SECURISE : +{run_cores}", x + 120 * scale_factor, y + 380 * scale_factor, scale=1.05 * scale_factor, color=(0.2, 0.9, 1.0))

                # Pulse prompt
                pulse = 0.6 + 0.4 * math.sin(time_accum * 5.0)
                flash_green = (COLOR_GREEN[0] * pulse, COLOR_GREEN[1] * pulse, COLOR_GREEN[2] * pulse)
                hud_batch.add_text(f"APPUYEZ SUR ENTREE POUR EMPOSTER LE SECTEUR {current_sector + 1}", overlay_cx - 290 * scale_factor, y + h - 50 * scale_factor, scale=1.15 * scale_factor, color=flash_green)

            elif game_state == STATE_GAME_OVER:
                # Failure menu
                draw_hud_panel(hud_batch, 100 * scale_factor, 100 * scale_factor, WINDOW_WIDTH - 200 * scale_factor, WINDOW_HEIGHT - 200 * scale_factor, COLOR_RED, fill_color=(0.12, 0.02, 0.02))
                if WINDOW_WIDTH > 0 and WINDOW_HEIGHT > 0:
                    menu_bounds_uv = (
                        (100 * scale_factor) / WINDOW_WIDTH,
                        1.0 - (WINDOW_HEIGHT - 100 * scale_factor) / WINDOW_HEIGHT,
                        (WINDOW_WIDTH - 100 * scale_factor) / WINDOW_WIDTH,
                        1.0 - (100 * scale_factor) / WINDOW_HEIGHT
                    )

                hud_batch.add_text("ARRET DU SYSTEME : ELIMINE", WINDOW_WIDTH / 2 - 240 * scale_factor, 150 * scale_factor, scale=2.0 * scale_factor, color=COLOR_RED)

                # Stats
                mins = int(game_time // 60)
                secs = int(game_time % 60)
                hud_batch.add_text("RAPPORT DE DIAGNOSTIC :", 250 * scale_factor, 250 * scale_factor, scale=1.5 * scale_factor, color=COLOR_AMBER)
                hud_batch.add_text(f"- TEMPS DE SURVIE DANS LE SECTEUR : {mins:02d}:{secs:02d}", 250 * scale_factor, 300 * scale_factor, scale=1.2 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"- NAVIRES ENNEMIS MENACANTS DETRUITS : {player.kills}", 250 * scale_factor, 330 * scale_factor, scale=1.2 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"- NIVEAU ATTEINT DU MODULE CENTRAL : {player.level}", 250 * scale_factor, 360 * scale_factor, scale=1.2 * scale_factor, color=COLOR_WHITE)
                
                hud_batch.add_text("- RESSOURCES ASSIMILEES ET SAUVEGARDEES :", 250 * scale_factor, 395 * scale_factor, scale=1.2 * scale_factor, color=COLOR_AMBER)
                hud_batch.add_text(f"  + CREDITS SECURISE : +{run_credits}   (TOTAL: {save_data['credits']})", 270 * scale_factor, 420 * scale_factor, scale=1.05 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"  + CRISTAUX DE PLASMA : +{run_plasma}   (TOTAL: {save_data['plasma']})", 270 * scale_factor, 440 * scale_factor, scale=1.05 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"  + COEURS D'ASTRAEA : +{run_cores}   (TOTAL: {save_data['cores']})", 270 * scale_factor, 460 * scale_factor, scale=1.05 * scale_factor, color=COLOR_WHITE)

                # Pulse prompt
                pulse = 0.6 + 0.4 * math.sin(time_accum * 5.0)
                flash_red = (COLOR_RED[0] * pulse, COLOR_RED[1] * pulse, COLOR_RED[2] * pulse)
                hud_batch.add_text("APPUYER SUR ENTREE POUR REDEMARRER LE COEUR", WINDOW_WIDTH / 2 - 270 * scale_factor, 520 * scale_factor, scale=1.5 * scale_factor, color=flash_red)

            elif game_state == STATE_VICTORY:
                # Success screen
                draw_hud_panel(hud_batch, 100 * scale_factor, 100 * scale_factor, WINDOW_WIDTH - 200 * scale_factor, WINDOW_HEIGHT - 200 * scale_factor, COLOR_GREEN, fill_color=(0.025, 0.12, 0.04))
                if WINDOW_WIDTH > 0 and WINDOW_HEIGHT > 0:
                    menu_bounds_uv = (
                        (100 * scale_factor) / WINDOW_WIDTH,
                        1.0 - (WINDOW_HEIGHT - 100 * scale_factor) / WINDOW_HEIGHT,
                        (WINDOW_WIDTH - 100 * scale_factor) / WINDOW_WIDTH,
                        1.0 - (100 * scale_factor) / WINDOW_HEIGHT
                    )

                hud_batch.add_text("TRANSMISSION REUSSIE : VICTOIRE !", WINDOW_WIDTH / 2 - 270 * scale_factor, 150 * scale_factor, scale=2.0 * scale_factor, color=COLOR_GREEN)

                # Stats
                mins = int(game_time // 60)
                secs = int(game_time % 60)
                hud_batch.add_text("RAPPORT DE FIN DE MISSION :", 250 * scale_factor, 250 * scale_factor, scale=1.5 * scale_factor, color=COLOR_AMBER)
                hud_batch.add_text(f"- TEMPS ENREGISTRE : {mins:02d}:{secs:02d}", 250 * scale_factor, 300 * scale_factor, scale=1.2 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"- MENACES ENNEMIES ELIMINEES : {player.kills}", 250 * scale_factor, 330 * scale_factor, scale=1.2 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"- NIVEAU FINAL DU VAISSEAU : {player.level}", 250 * scale_factor, 360 * scale_factor, scale=1.2 * scale_factor, color=COLOR_WHITE)
                
                hud_batch.add_text("- BUTIN DE MISSION SECURISE (BONUS COMPRIS) :", 250 * scale_factor, 395 * scale_factor, scale=1.2 * scale_factor, color=COLOR_AMBER)
                hud_batch.add_text(f"  + CREDITS SECURISE : +{run_credits} (Dont +150 Bonus)  (TOTAL: {save_data['credits']})", 270 * scale_factor, 420 * scale_factor, scale=1.05 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"  + CRISTAUX DE PLASMA : +{run_plasma}  (TOTAL: {save_data['plasma']})", 270 * scale_factor, 440 * scale_factor, scale=1.05 * scale_factor, color=COLOR_WHITE)
                hud_batch.add_text(f"  + COEURS D'ASTRAEA : +{run_cores} (Dont +2 Bonus)  (TOTAL: {save_data['cores']})", 270 * scale_factor, 460 * scale_factor, scale=1.05 * scale_factor, color=COLOR_WHITE)

                # Pulse prompt
                pulse = 0.6 + 0.4 * math.sin(time_accum * 5.0)
                flash_green = (COLOR_GREEN[0] * pulse, COLOR_GREEN[1] * pulse, COLOR_GREEN[2] * pulse)
                hud_batch.add_text("APPUYER SUR ENTREE POUR LE MENU PRINCIPAL", WINDOW_WIDTH / 2 - 270 * scale_factor, 520 * scale_factor, scale=1.3 * scale_factor, color=flash_green)


        except Exception as e:
            log_error('Vector Batch Builder', e)
        try:
            # --- ModernGL Rendering Steps ---

            # Pass 1: Render scene (world vectors + HUD vectors) into offscreen FBO
            fbo.use()
            ctx.clear(0.0, 0.0, 0.0, 1.0) # Start with black background

            # Configure line shader program uniforms
            line_prog['u_resolution'].value = (float(WINDOW_WIDTH), float(WINDOW_HEIGHT))
            line_prog['u_angle'].value = camera_rotation_angle
            line_prog['u_zoom'].value = current_zoom

            # A. Draw World Batch
            if game_state not in (STATE_MENU, STATE_LEVEL_UP, STATE_SKILL_TREE, STATE_GAME_OVER, STATE_VICTORY, STATE_META_UPGRADES, STATE_SECTOR_TRANSITION):
                if world_batch.get_vertex_count() > 0:
                    vdata = np.array(world_batch.vertices, dtype='f4')
                    # Clip if data somehow overflows VBO limit
                    vcount = world_batch.get_vertex_count()
                    if vcount > max_vertices:
                        vcount = max_vertices
                        vdata = vdata[:max_vertices * 5]

                    line_vbo.write(vdata.tobytes())
                    line_prog['u_camera'].value = (camera.x, camera.y)
                    line_prog['u_is_hud'].value = False
                    line_vao.render(moderngl.LINES, vertices=vcount)

            # B. HUD batch is no longer drawn in Pass 1 (to FBO) to avoid text distortion/blur.

            # Pass 2: Render full screen quad to main window, applying neon blur, glow, scanlines & vignette
            ctx.screen.use()
            ctx.clear(0.0, 0.0, 0.0, 1.0)

            fbo_texture.use(0)
            post_prog['u_texture'].value = 0
            post_prog['u_time'].value = time_accum
            post_prog['u_resolution'].value = (float(WINDOW_WIDTH), float(WINDOW_HEIGHT))
            
            # Calculate screen space coordinate for black holes/vortices (for gravitational lens distortion)
            blackhole_ndc = (0.0, 0.0)
            blackhole_r = 0.0
            active_bhs = [pr for pr in projectiles if pr.active and pr.proj_type in ("vortex", "blackhole")]
            if active_bhs:
                bh = active_bhs[0]
                diff_x = bh.x - camera.x
                diff_y = bh.y - camera.y
                cos_a = math.cos(camera_rotation_angle)
                sin_a = math.sin(camera_rotation_angle)
                rx = diff_x * cos_a - diff_y * sin_a
                ry = diff_x * sin_a + diff_y * cos_a
                # Normalize to screen NDC [-1, 1]
                if WINDOW_WIDTH > 0 and WINDOW_HEIGHT > 0:
                    ndc_x = (rx * current_zoom) / (WINDOW_WIDTH * 0.5)
                    ndc_y = -(ry * current_zoom) / (WINDOW_HEIGHT * 0.5)
                    # Map to UV coordinates [0, 1]
                    blackhole_ndc = (ndc_x * 0.5 + 0.5, ndc_y * 0.5 + 0.5)
                    blackhole_r = (bh.radius * current_zoom) / (WINDOW_WIDTH * 0.5)

            # Waving CRT background distortion for menus
            wave_val = 1.0 if game_state in (STATE_LEVEL_UP, STATE_DEBUG, STATE_SKILL_TREE, STATE_GAME_OVER, STATE_META_UPGRADES, STATE_SECTOR_TRANSITION) else 0.0

            post_prog['u_glitch'].value = min(0.35, glitch_timer * 0.7)
            post_prog['u_blackhole_pos'].value = blackhole_ndc
            post_prog['u_blackhole_radius'].value = blackhole_r
            post_prog['u_wave_intensity'].value = wave_val
            post_prog['u_menu_bounds'].value = menu_bounds_uv

            quad_vao.render(moderngl.TRIANGLES)

            # Pass 3: Draw HUD batch directly to screen to keep text 100% sharp and readable
            if hud_batch.get_vertex_count() > 0:
                vdata = np.array(hud_batch.vertices, dtype='f4')
                vcount = hud_batch.get_vertex_count()
                if vcount > max_vertices:
                    vcount = max_vertices
                    vdata = vdata[:max_vertices * 5]

                line_vbo.write(vdata.tobytes())
                line_prog['u_is_hud'].value = True
                line_vao.render(moderngl.LINES, vertices=vcount)

        except Exception as e:
            log_error('ModernGL GPU Pass', e)
        # Flip screen buffer
        pygame.display.flip()

if __name__ == '__main__':
    main()
