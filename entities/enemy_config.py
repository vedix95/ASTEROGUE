# entities/enemy_config.py
import json
import os
from config import COLOR_GREEN, COLOR_AMBER, COLOR_RED, COLOR_WHITE

# Fallbacks in case JSON is missing or corrupt
PREFIXES_STD = [
    "Void", "Quantum", "Solar", "Glitch", "Plasma", "Nova", "Stellar",
    "Abyssal", "Dark", "Chrono", "Cosmic", "Nebula", "Spectral", "Magnetic"
]

PREFIX_TRANSLATIONS = {
    "Void": "du Neant", "Quantum": "Quantique", "Solar": "Solaire",
    "Glitch": "Buggue", "Plasma": "de Plasma", "Nova": "Nova",
    "Stellar": "Stellaire", "Abyssal": "Abyssal", "Dark": "Sombre",
    "Chrono": "Temporel", "Cosmic": "Cosmique", "Nebula": "Nebulaire",
    "Spectral": "Spectral", "Magnetic": "Magnetique"
}

SUFFIX_TRANSLATIONS = {
    "Swarmer": "Essaim", "Scout": "Eclaireur", "Scarab": "Scarabee",
    "Glider": "Planeur", "Chaser": "Chasseur", "Reaver": "Ravageur",
    "Charger": "Chargeur", "Seeker": "Chercheur", "Stalker": "Traqueur",
    "Devourer": "Devoreur", "Sentinel": "Sentinelle", "Goliath": "Goliath"
}

ENEMY_TEMPLATES = {
    "swarmer": {
        "base_hp": 10.0, "base_speed": 135.0, "base_damage": 8.0,
        "base_score": 10, "base_radius": 21.0, "color": COLOR_GREEN,
        "suffixes": ["Swarmer", "Scout", "Scarab", "Glider"],
        "is_spaceship": False, "enemy_class_suffix": None,
        "weapon_type": None, "modifiers": {}
    },
    "chaser": {
        "base_hp": 25.0, "base_speed": 95.0, "base_damage": 14.0,
        "base_score": 25, "base_radius": 28.0, "color": COLOR_AMBER,
        "suffixes": ["Chaser", "Reaver", "Charger", "Seeker"],
        "is_spaceship": False, "enemy_class_suffix": None,
        "weapon_type": None, "modifiers": {}
    },
    "stalker": {
        "base_hp": 55.0, "base_speed": 65.0, "base_damage": 22.0,
        "base_score": 60, "base_radius": 38.0, "color": COLOR_RED,
        "suffixes": ["Stalker", "Devourer", "Sentinel", "Goliath"],
        "is_spaceship": False, "enemy_class_suffix": None,
        "weapon_type": None, "modifiers": {}
    },
    "boss": {
        "base_hp": 380.0, "base_speed": 48.0, "base_damage": 45.0,
        "base_score": 500, "base_radius": 62.0, "color": COLOR_WHITE,
        "suffixes": [], "is_spaceship": False, "enemy_class_suffix": "Boss",
        "weapon_type": None, "modifiers": {}
    },
    "light_fighter": {
        "base_hp": 16.0, "base_speed": 120.0, "base_damage": 9.0,
        "base_score": 15, "base_radius": 18.0, "color": (0.3, 0.6, 1.0),
        "suffixes": [], "is_spaceship": True, "enemy_class_suffix": "Fighter",
        "weapon_type": "laser", "modifiers": {"spread": 1}, "name": "Chasseur Leger"
    },
    "interceptor": {
        "base_hp": 13.0, "base_speed": 155.0, "base_damage": 7.0,
        "base_score": 20, "base_radius": 15.0, "color": (0.0, 1.0, 0.8),
        "suffixes": [], "is_spaceship": True, "enemy_class_suffix": "Interceptor",
        "weapon_type": "laser", "modifiers": {"spread": 2, "homing": 1.0}, "name": "Intercepteur"
    },
    "bomber": {
        "base_hp": 38.0, "base_speed": 75.0, "base_damage": 18.0,
        "base_score": 30, "base_radius": 26.0, "color": (1.0, 0.4, 0.0),
        "suffixes": [], "is_spaceship": True, "enemy_class_suffix": "Bomber",
        "weapon_type": "missile", "modifiers": {"bounce": 1}, "name": "Bombardier"
    },
    "frigate": {
        "base_hp": 55.0, "base_speed": 85.0, "base_damage": 15.0,
        "base_score": 45, "base_radius": 30.0, "color": (0.8, 0.2, 1.0),
        "suffixes": [], "is_spaceship": True, "enemy_class_suffix": "Frigate",
        "weapon_type": "vortex", "modifiers": {"pierce": 2}, "name": "Fregate"
    },
    "corvette": {
        "base_hp": 32.0, "base_speed": 110.0, "base_damage": 10.0,
        "base_score": 35, "base_radius": 22.0, "color": (1.0, 0.8, 0.0),
        "suffixes": [], "is_spaceship": True, "enemy_class_suffix": "Corvette",
        "weapon_type": "blade", "modifiers": {"tiny_planet": True}, "name": "Corvette"
    },
    "cruiser": {
        "base_hp": 85.0, "base_speed": 70.0, "base_damage": 22.0,
        "base_score": 75, "base_radius": 34.0, "color": (1.0, 0.2, 0.2),
        "suffixes": [], "is_spaceship": True, "enemy_class_suffix": "Cruiser",
        "weapon_type": "flame", "modifiers": {"pierce": 3, "spread": 3}, "name": "Croiseur"
    },
    "destroyer": {
        "base_hp": 115.0, "base_speed": 60.0, "base_damage": 25.0,
        "base_score": 100, "base_radius": 38.0, "color": (0.2, 0.5, 1.0),
        "suffixes": [], "is_spaceship": True, "enemy_class_suffix": "Destroyer",
        "weapon_type": "lightning", "modifiers": {"homing": 2.0}, "name": "Destroyer"
    },
    "dreadnought": {
        "base_hp": 190.0, "base_speed": 45.0, "base_damage": 35.0,
        "base_score": 180, "base_radius": 46.0, "color": (0.6, 0.6, 0.6),
        "suffixes": [], "is_spaceship": True, "enemy_class_suffix": "Dreadnought",
        "weapon_type": "meteor", "modifiers": {"bounce": 2, "homing": 1.2}, "name": "Dreadnought"
    },
    "recon": {
        "base_hp": 22.0, "base_speed": 135.0, "base_damage": 12.0,
        "base_score": 25, "base_radius": 18.0, "color": (0.1, 0.9, 0.1),
        "suffixes": [], "is_spaceship": True, "enemy_class_suffix": "Recon",
        "weapon_type": "missile", "modifiers": {"homing": 3.0, "bounce": 1}, "name": "Recon"
    },
    "carrier": {
        "base_hp": 260.0, "base_speed": 38.0, "base_damage": 30.0,
        "base_score": 250, "base_radius": 50.0, "color": (1.0, 0.0, 0.5),
        "suffixes": [], "is_spaceship": True, "enemy_class_suffix": "Carrier",
        "weapon_type": "carrier_spawner", "modifiers": {"spread": 4}, "name": "Porte-Nefs"
    }
}

# Attempt to load from JSON
json_path = os.path.join("data", "enemy_config.json")
if os.path.exists(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            js_data = json.load(f)
            if "prefixes_std" in js_data:
                PREFIXES_STD = js_data["prefixes_std"]
            if "prefix_translations" in js_data:
                PREFIX_TRANSLATIONS = js_data["prefix_translations"]
            if "suffix_translations" in js_data:
                SUFFIX_TRANSLATIONS = js_data["suffix_translations"]
            if "templates" in js_data:
                for k, v in js_data["templates"].items():
                    # Convert color list to tuple
                    if "color" in v:
                        v["color"] = tuple(v["color"])
                    ENEMY_TEMPLATES[k] = v
    except Exception as e:
        print(f"Warning: Failed to load {json_path}, using default configs. Error: {e}")

def apply_prefix_modifiers(prefix, color, hp, speed, damage, radius):
    """Applies prefix modifiers to stats and color."""
    if prefix == "Void":
        return (0.6, 0.1, 1.0), hp * 1.35, speed * 0.85, damage, radius
    elif prefix == "Solar":
        return (1.0, 0.65, 0.0), hp, speed * 1.2, damage * 1.2, radius
    elif prefix == "Quantum":
        return (0.1, 0.8, 1.0), hp * 0.80, speed * 1.35, damage, radius * 0.80
    elif prefix == "Spectral":
        return (0.75, 0.75, 1.0), hp * 0.75, speed * 1.15, damage, radius
    elif prefix == "Magnetic":
        return (0.2, 1.0, 0.4), hp, speed, damage * 1.3, radius
    elif prefix == "Plasma":
        return (1.0, 0.3, 0.1), hp * 0.90, speed, damage * 1.45, radius
    elif prefix == "Nova":
        return (1.0, 1.0, 1.0), hp * 1.25, speed, damage, radius * 1.25
    elif prefix == "Glitch":
        return (1.0, 0.1, 0.8), hp, speed * 1.2, damage * 1.2, radius
    elif prefix == "Chrono":
        return (0.9, 0.9, 0.1), hp, speed * 1.25, damage, radius
    elif prefix == "Abyssal":
        return (0.35, 0.05, 0.7), hp * 1.5, speed * 0.8, damage, radius * 1.2
    return color, hp, speed, damage, radius
