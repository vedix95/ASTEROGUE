# entities/shapes.py
import math
import random
import time
import json
import os
from config import COLOR_WHITE, COLOR_AMBER, COLOR_GREEN, COLOR_RED

# Load shapes data from JSON
SHAPES_DATA = {}
json_shapes_path = os.path.join("data", "shapes.json")
if os.path.exists(json_shapes_path):
    try:
        with open(json_shapes_path, "r", encoding="utf-8") as f:
            SHAPES_DATA = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load {json_shapes_path}: {e}")

def draw_player_ship(batch, player, scale_factor=1.0):
    scale = (1.0 + (player.level - 1) * 0.02) * scale_factor
    cos_a = math.cos(player.angle)
    sin_a = math.sin(player.angle)

    def draw_poly(pts, color, closed=True):
        rot_pts = []
        for px, py in pts:
            s_px = px * scale
            s_py = py * scale
            rx = s_px * cos_a - s_py * sin_a
            ry = s_px * sin_a + s_py * cos_a
            rot_pts.append((player.x + rx, player.y + ry))
        batch.add_polygon(rot_pts, color, closed=closed)

    def draw_line(p1, p2, color):
        s_p1 = (p1[0] * scale, p1[1] * scale)
        s_p2 = (p2[0] * scale, p2[1] * scale)
        rx1 = s_p1[0] * cos_a - s_p1[1] * sin_a
        ry1 = s_p1[0] * sin_a + s_p1[1] * cos_a
        rx2 = s_p2[0] * cos_a - s_p2[1] * sin_a
        ry2 = s_p2[0] * sin_a + s_p2[1] * cos_a
        batch.add_line(player.x + rx1, player.y + ry1, player.x + rx2, player.y + ry2, color)

    # Draw Hyperspace motion trails (ghost silhouettes)
    if player.hyperspace_active:
        for i, (tx, ty, tang) in enumerate(player.trail_history):
            alpha = 0.05 + (i / len(player.trail_history)) * 0.40
            color = (0.1 * alpha, 0.8 * alpha, 1.0 * alpha)
            cos_t = math.cos(tang)
            sin_t = math.sin(tang)
            
            g_pts = [(14.0, 0.0), (-10.0, -10.0), (-6.0, 0.0), (-10.0, 10.0)]
            rot_g = []
            for px, py in g_pts:
                s_px = px * scale
                s_py = py * scale
                rx = s_px * cos_t - s_py * sin_t
                ry = s_px * sin_t + s_py * cos_t
                rot_g.append((tx + rx, ty + ry))
            batch.add_polygon(rot_g, color, closed=True)

    # Read base meshes from JSON
    p_shapes = SHAPES_DATA.get("player", {})
    
    # Wing panel color based on Sector theme
    c_sec = getattr(player, 'current_sector', 1)
    if c_sec == 2:
        panel_color = (0.8, 0.2, 1.0) # Purple/Plasma Nebula
    elif c_sec == 3:
        panel_color = (0.2, 0.9, 1.0) # Neon Cyan/Stellar Abyss
    else:
        panel_color = (0.1, 0.8, 1.0) # Classic Blue/Green

    # 1. Main Fuselage
    if "fuselage" in p_shapes:
        draw_poly(p_shapes["fuselage"]["points"], COLOR_WHITE)
    else:
        draw_poly([(16.0, 0.0), (5.0, 4.0), (-10.0, 4.0), (-6.0, 0.0), (-10.0, -4.0), (5.0, -4.0)], COLOR_WHITE)

    # 2. Left Wing & Panel
    if "left_wing" in p_shapes:
        draw_poly(p_shapes["left_wing"]["points"], COLOR_WHITE)
    if "left_panel" in p_shapes:
        draw_poly(p_shapes["left_panel"]["points"], panel_color)

    # 3. Right Wing & Panel
    if "right_wing" in p_shapes:
        draw_poly(p_shapes["right_wing"]["points"], COLOR_WHITE)
    if "right_panel" in p_shapes:
        draw_poly(p_shapes["right_panel"]["points"], panel_color)

    # 4. Wing Gun Barrels
    has_rainbow_gatling = any(w.name == "GATLING ARC-EN-CIEL" for w in player.weapons)
    if has_rainbow_gatling:
        cycle_t = time.time() * 5.0
        r = 0.5 + 0.5 * math.sin(cycle_t)
        g = 0.5 + 0.5 * math.sin(cycle_t + 2.0)
        b = 0.5 + 0.5 * math.sin(cycle_t + 4.0)
        gun_color = (r, g, b)
        draw_line((-12.0, -15.0), (6.0, -15.0), gun_color)
        draw_line((-12.0, 15.0), (6.0, 15.0), gun_color)
    else:
        draw_line((-12.0, -15.0), (-3.0, -15.0), (0.1, 0.8, 1.0))
        draw_line((-12.0, 15.0), (-3.0, 15.0), (0.1, 0.8, 1.0))

    # 5. Cockpit Canopy
    if "canopy" in p_shapes:
        draw_poly(p_shapes["canopy"]["points"], tuple(p_shapes["canopy"]["color"]))
    else:
        draw_poly([(8.0, 0.0), (2.0, 2.5), (-2.0, 0.0), (2.0, -2.5)], (0.2, 0.8, 1.0))

    # 6. Engine Exhaust nozzles
    draw_line((-10.0, -3.0), (-10.0, -1.0), COLOR_WHITE)
    draw_line((-10.0, 1.0), (-10.0, 3.0), COLOR_WHITE)

    # 7. Engine Flames
    if player.is_moving:
        flame_len = 12.0 + random.uniform(0.0, 9.0)
        draw_poly([(-10.0, -3.0), (-10.0 - flame_len, -2.0), (-10.0, -1.0)], COLOR_AMBER, closed=True)
        draw_poly([(-10.0, 1.0), (-10.0 - flame_len, 2.0), (-10.0, 3.0)], COLOR_AMBER, closed=True)

    # A. Central heavy thruster
    has_thruster = (player.passives.get("THRUSTERS", 0) > 0) or (getattr(player, 'meta_engine_level', 0) > 0)
    if has_thruster:
        draw_line((-10.0, -1.0), (-10.0, 1.0), COLOR_WHITE)
        if player.is_moving:
            c_flame_len = 15.0 + random.uniform(0.0, 12.0)
            draw_poly([(-10.0, -1.0), (-10.0 - c_flame_len, 0.0), (-10.0, 1.0)], (1.0, 0.4, 0.0), closed=True)

    # B. Additional Nano-Armor Plating
    has_armor = player.passives.get("NANO-ARMOR", 0) > 0
    if has_armor:
        draw_poly([(2.0, -8.0), (-5.0, -8.0), (-8.0, -4.0), (-2.0, -4.0)], (0.75, 0.75, 0.75), closed=True)
        draw_poly([(2.0, 8.0), (-5.0, 8.0), (-8.0, 4.0), (-2.0, 4.0)], (0.75, 0.75, 0.75), closed=True)

    # C. Sacred Heart Halo
    has_sacred = player.passives.get("COEUR SACRE", 0) > 0
    if has_sacred:
        draw_line((0.0, -6.0), (0.0, 6.0), (1.0, 0.9, 0.0))
        draw_line((-3.0, 0.0), (3.0, 0.0), (1.0, 0.9, 0.0))

    # D. Repair / Health Crosses on wings
    has_repair = player.passives.get("REPAIR DRONES", 0) > 0
    if has_repair:
        draw_line((-12.0, -17.0), (-12.0, -13.0), (0.1, 1.0, 0.2))
        draw_line((-14.0, -15.0), (-10.0, -15.0), (0.1, 1.0, 0.2))
        draw_line((-12.0, 13.0), (-12.0, 17.0), (0.1, 1.0, 0.2))
        draw_line((-14.0, 15.0), (-10.0, 15.0), (0.1, 1.0, 0.2))

    # E. Mom's Knife Combat Blade
    has_knife = any(w.name == "COUTEAU DE MAMAN" for w in player.weapons)
    if has_knife:
        draw_poly([(16.0, 0.0), (28.0, 0.0), (16.0, 2.0)], (0.9, 0.1, 0.2), closed=True)
        draw_poly([(16.0, 0.0), (28.0, 0.0), (16.0, -2.0)], (0.9, 0.1, 0.2), closed=True)

    # Draw magnetic range loop
    batch.add_circle(player.x, player.y, player.magnet_radius, (0.02, 0.15, 0.03), segments=24)


def draw_enemy_ship(batch, enemy, hyperspace_active=False):
    cos_a = math.cos(enemy.angle)
    sin_a = math.sin(enemy.angle)

    if hyperspace_active:
        back_x = enemy.x - cos_a * (enemy.radius * 1.5)
        back_y = enemy.y - sin_a * (enemy.radius * 1.5)
        r, g, b = enemy.color
        fade_color = (r * 0.4, g * 0.4, b * 0.4)
        batch.add_line(enemy.x, enemy.y, back_x, back_y, fade_color)

    suffix = enemy.enemy_class_suffix
    r = enemy.radius

    def draw_local_poly(pts, color):
        rot = []
        for px, py in pts:
            rx = px * cos_a - py * sin_a
            ry = px * sin_a + py * cos_a
            rot.append((enemy.x + rx, enemy.y + ry))
        batch.add_polygon(rot, color, closed=True)

    def draw_local_line(p1, p2, color):
        rx1 = p1[0] * cos_a - p1[1] * sin_a
        ry1 = p1[0] * sin_a + p1[1] * cos_a
        rx2 = p2[0] * cos_a - p2[1] * sin_a
        ry2 = p2[0] * sin_a + p2[1] * cos_a
        batch.add_line(enemy.x + rx1, enemy.y + ry1, enemy.x + rx2, enemy.y + ry2, color)

    # Base shapes lookup in JSON configuration
    e_shapes = SHAPES_DATA.get("enemies", {})

    # Normalise suffix classes
    match_suffix = suffix
    if suffix not in e_shapes:
        if suffix in ("Swarmer", "Scout", "Scarab", "Glider"):
            match_suffix = "Swarmer"
        elif suffix in ("Chaser", "Reaver", "Charger", "Seeker"):
            match_suffix = "Chaser"
        elif suffix in ("Stalker", "Devourer", "Sentinel", "Goliath"):
            match_suffix = "Stalker"
        else:
            match_suffix = "Boss"

    # Draw shapes from data file
    commands = e_shapes.get(match_suffix, [])
    for cmd in commands:
        ctype = cmd.get("type")
        color_val = cmd.get("color")
        if color_val == "enemy_color":
            draw_color = enemy.color
        elif isinstance(color_val, list):
            draw_color = tuple(color_val)
        else:
            draw_color = enemy.color

        if ctype == "polygon":
            pts = [[px * r, py * r] for px, py in cmd["points"]]
            draw_local_poly(pts, draw_color)
        elif ctype == "line":
            p1 = [cmd["p1"][0] * r, cmd["p1"][1] * r]
            p2 = [cmd["p2"][0] * r, cmd["p2"][1] * r]
            draw_local_line(p1, p2, draw_color)
        elif ctype == "circle":
            cx = cmd["center"][0] * r
            cy = cmd["center"][1] * r
            cr = cmd["radius"] * r
            rcx = cx * cos_a - cy * sin_a
            rcy = cx * sin_a + cy * cos_a
            batch.add_circle(enemy.x + rcx, enemy.y + rcy, cr, draw_color, segments=cmd.get("segments", 12))

    # Procedural tentacles for Stalker squids
    if match_suffix == "Stalker":
        phase = enemy.rotation * 1.6
        tentacles = [
            [-0.25, 0.0, -0.6, 0.1, -1.1, 0.0],
            [-0.35, -0.2, -0.75, -0.38, -1.25, -0.3],
            [-0.35, 0.2, -0.75, 0.38, -1.25, 0.3]
        ]
        for t in tentacles:
            w1 = math.sin(phase) * 0.1
            w2 = math.cos(phase) * 0.15
            
            p0 = (t[0] * r, t[1] * r)
            p1 = (t[2] * r, (t[3] + w1) * r)
            p2 = (t[4] * r, (t[5] + w2) * r)
            
            rx0 = p0[0]*cos_a - p0[1]*sin_a
            ry0 = p0[0]*sin_a + p0[1]*cos_a
            rx1 = p1[0]*cos_a - p1[1]*sin_a
            ry1 = p1[0]*sin_a + p1[1]*cos_a
            rx2 = p2[0]*cos_a - p2[1]*sin_a
            ry2 = p2[0]*sin_a + p2[1]*cos_a
            
            batch.add_line(enemy.x + rx0, enemy.y + ry0, enemy.x + rx1, enemy.y + ry1, enemy.color)
            batch.add_line(enemy.x + rx1, enemy.y + ry1, enemy.x + rx2, enemy.y + ry2, enemy.color)

    # Procedural walking legs for Boss queens
    elif match_suffix == "Boss":
        spider_offsets = [0.25, 0.0, -0.3, -0.7]
        for off in spider_offsets:
            # Left leg joint
            draw_local_line((off * r, -0.7 * r), ((off - 0.35) * r, -1.45 * r), enemy.color)
            # Right leg joint
            draw_local_line((off * r, 0.7 * r), ((off - 0.35) * r, 1.45 * r), enemy.color)

    # Health Bar rendering (only when damaged)
    if enemy.enemy_type == "boss":
        health_pct = max(0.0, enemy.health / enemy.max_health)
        bar_y = enemy.y - enemy.radius - 15.0
        bar_half_w = 55.0
        batch.add_line(enemy.x - bar_half_w, bar_y, enemy.x + bar_half_w, bar_y, COLOR_RED)
        batch.add_line(enemy.x - bar_half_w, bar_y, enemy.x - bar_half_w + (bar_half_w * 2.0 * health_pct), bar_y, COLOR_WHITE)
        batch.add_text(enemy.name, enemy.x - len(enemy.name) * 3.5, bar_y - 12.0, scale=0.8, color=enemy.color)
    elif enemy.health < enemy.max_health:
        health_pct = max(0.0, enemy.health / enemy.max_health)
        bar_y = enemy.y - enemy.radius - 8.0
        bar_half_w = enemy.radius * 0.7
        batch.add_line(enemy.x - bar_half_w, bar_y, enemy.x + bar_half_w, bar_y, COLOR_RED)
        batch.add_line(enemy.x - bar_half_w, bar_y, enemy.x - bar_half_w + (bar_half_w * 2.0 * health_pct), bar_y, COLOR_WHITE)
