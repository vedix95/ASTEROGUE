# systems/upgrade.py
import random
from config import PLAYER_START_MAGNET

# Import all weapons and accessories
from systems.weapon import (
    LaserWeapon, Railgun, RadialShockwave, FlameThrower, VortexGrenade, SpiralBlades, SeekerMissile, ScytheSlash,
    DroneShield, LaserDrone, RocketDrone, BlackHoleOrbital, LightningCoil, HealDrone,
    BrimstoneWeapon, TechXRingWeapon, MomsKnifeWeapon, RoboBabyDrone, FlyDrone, DryDrone,
    RainbowGatling, MeteorLauncher, NeonThunderbolt
)

PRIMARY_WEAPONS = {
    "AUTO-LASER": LaserWeapon,
    "CANON ELECTROMAGNETIQUE": Railgun,
    "ONDE DE CHOC": RadialShockwave,
    "LANCE-FLAMMES": FlameThrower,
    "GRENADE VORTEX": VortexGrenade,
    "LAMES SPIRALES": SpiralBlades,
    "MISSILE TETE CHERCHEUSE": SeekerMissile,
    "COUP DE FAUX": ScytheSlash,
    "BRIMSTONE": BrimstoneWeapon,
    "TECH X": TechXRingWeapon,
    "COUTEAU DE MAMAN": MomsKnifeWeapon,
    "GATLING ARC-EN-CIEL": RainbowGatling,
    "LANCEUR METEORE": MeteorLauncher,
    "ECLAIR DE NEON": NeonThunderbolt
}

ACCESSORIES = {
    "BOUCLIER ORBITAL": DroneShield,
    "DRONE LASER": LaserDrone,
    "DRONE ROQUETTE": RocketDrone,
    "TROU NOIR": BlackHoleOrbital,
    "BOBINE TESLA": LightningCoil,
    "DRONE DE SOIN": HealDrone,
    "ROBO-BABY": RoboBabyDrone,
    "DRONE INFESTATEUR": FlyDrone,
    "DRONE SEC": DryDrone
}

ALL_UPGRADE_WEAPONS = {**PRIMARY_WEAPONS, **ACCESSORIES}

ACTIVE_ITEMS = {
    "HYPERSAUT": {
        "name": "PROPULSION HYPERSPATIALE",
        "desc": "ACTIVE : Fonce en avant et devient invulnerable pendant 2s. recharge: 15s.",
        "cooldown": 15.0,
        "charge_type": "time"
    },
    "D6": {
        "name": "D6 (DES DU DESTIN)",
        "desc": "ACTIVE : Relance le pool de choix d'upgrade lors d'un level-up. 1 charge/niveau.",
        "cooldown": 1.0,
        "charge_type": "level"
    },
    "NECRONOMICON": {
        "name": "LE NECRONOMICON",
        "desc": "ACTIVE : Inflige 120 degats a tous les ennemis a l'ecran. recharge: 30 elimin.",
        "cooldown": 30.0,
        "charge_type": "kills"
    },
    "LIVRE DES OMBRES": {
        "name": "LIVRE DES OMBRES",
        "desc": "ACTIVE : Barriere d'invulnerabilite complete pendant 5s. recharge: 40s.",
        "cooldown": 40.0,
        "charge_type": "time"
    }
}

PASSIVE_DESCRIPTIONS = {
    # Base passives
    "THRUSTERS": "PROPULSEURS : +10% vitesse de deplacement.",
    "NANO-ARMOR": "NANO-BLINDAGE : +2 reduction de degats fixe.",
    "XP MAGNET": "ATTRACTEUR D'XP : +25% portee de collecte.",
    "OVERDRIVE CORE": "NOYAU DE SURCHARGE : +15% multiplicateur de degats.",
    "REPAIR DRONES": "DRONES DE REPARATION : Regenere 1.0 PV par seconde.",
    "HULL UPGRADE": "AMELIORATION COQUE : +20 PV max & soigne 20 PV.",
    
    # Isaac-style tear modifiers
    "GIANT CELLS": "CELLULES GEANTES : +20% taille des projectiles, +10% degats.",
    "HYPER DRIVE": "HYPER-PROPULSION : +20% vitesse de projectile, -10% temps de recharge.",
    "SPLIT FIRE": "TIR DIVISE : +1 projectile tire, -12% degats.",
    "SMART TARGETING": "VISEE INTELLIGENTE : Les projectiles se dirigent vers les cibles proches.",
    "BOUNCING MATRIX": "MATRICE REBONDISSANTE : Les projectiles rebondissent sur les bords de l'ecran.",
    "DRILL TIP": "FOREUSE DE BLINDAGE : Les projectiles transpercent +1 cible supplementaire.",
    "SHRAPNEL SHELLS": "OBUS SHRAPNEL : Les projectiles se divisent en deux a l'impact.",
    "HEAVY DRONES": "DRONES LOURDS : Vitesse d'orbite des drones +30% & Degats des drones +15%.",
    "DRONE ASSEMBLY": "ASSEMBLAGE DE DRONES : Temps de recharge des drones -18% & Projectiles des drones +1.",
    "PLASMA CORE": "COEUR PLASMA : Taille des projectiles +25% & Temps de recharge des armes -12%.",
    "TINY PLANET": "PLANETE MINUSCULE : Les projectiles gravitent en spirale autour du vaisseau.",
    "LUMP OF COAL": "CHARBON ACTIF : Les projectiles grossissent et infligent +45% degats/sec de vol.",
    "SACRED HEART": "COEUR SACRE : +50% degats, projectiles plus gros/autoguides, vitesse -20%."
}

PASSIVE_NAMES_FR = {
    "THRUSTERS": "PROPULSEURS",
    "NANO-ARMOR": "NANO-BLINDAGE",
    "XP MAGNET": "ATTRACTEUR D'XP",
    "OVERDRIVE CORE": "NOYAU DE SURCHARGE",
    "REPAIR DRONES": "DRONES DE REPARATION",
    "HULL UPGRADE": "AMELIORATION DE LA COQUE",
    "GIANT CELLS": "CELLULES GEANTES",
    "HYPER DRIVE": "HYPER-PROPULSION",
    "SPLIT FIRE": "TIR DIVISE",
    "SMART TARGETING": "VISEE INTELLIGENTE",
    "BOUNCING MATRIX": "MATRICE REBONDISSANTE",
    "DRILL TIP": "FOREUSE DE BLINDAGE",
    "SHRAPNEL SHELLS": "OBUS SHRAPNEL",
    "HEAVY DRONES": "DRONES LOURDS",
    "DRONE ASSEMBLY": "ASSEMBLAGE DE DRONES",
    "PLASMA CORE": "COEUR PLASMA",
    "TINY PLANET": "PLANETE MINUSCULE",
    "LUMP OF COAL": "CHARBON ACTIF",
    "SACRED HEART": "COEUR SACRE"
}

def get_available_upgrades(player):
    options = []

    # Active Item unlocks/upgrades
    if player.active_item is None:
        for key, meta in ACTIVE_ITEMS.items():
            options.append({
                "id": f"unlock_active_{key}",
                "name": f"MODULE ACTIF : {meta['name']}",
                "desc": meta["desc"],
                "type": "active_unlock",
                "target": key
            })
    else:
        if player.active_item_level < 5:
            meta = ACTIVE_ITEMS[player.active_item]
            options.append({
                "id": f"upgrade_active_{player.active_item}",
                "name": f"AMELIORATION ACTIF : {meta['name']} (Niv {player.active_item_level + 1})",
                "desc": f"Reduit le temps de recharge / conditions de charge de 15%.",
                "type": "active_upgrade",
                "target": player.active_item
            })

    # 1. Primary weapon unlocks
    current_pri_names = [w.name for w in player.primary_weapons]
    if len(player.primary_weapons) < 4:
        for name in PRIMARY_WEAPONS:
            if name not in current_pri_names:
                options.append({
                    "id": f"unlock_weapon_{name}",
                    "name": f"DEVERROUILLAGE : {name}",
                    "desc": f"Equiper le systeme d'arme {name}.",
                    "type": "weapon_unlock",
                    "target": name
                })
            
    # Accessories Unlock: If player has fewer than 4 accessories, they can unlock new ones
    current_acc_names = [a.name for a in player.accessories]
    if len(player.accessories) < 4:
        for name in ACCESSORIES:
            if name not in current_acc_names:
                options.append({
                    "id": f"unlock_weapon_{name}",
                    "name": f"DEVERROUILLAGE ACC : {name}",
                    "desc": f"Equiper le drone accessoire {name}.",
                    "type": "weapon_unlock",
                    "target": name
                })

    # Upgrade active primary weapon and accessories
    for weapon in player.weapons:
        if weapon.level < weapon.max_level:
            options.append({
                "id": f"upgrade_weapon_{weapon.name}",
                "name": f"AMELIORATION : {weapon.name} (Niv {weapon.level + 1})",
                "desc": f"Augmenter les statistiques et l'efficacite de {weapon.name}.",
                "type": "weapon_upgrade",
                "target": weapon.name
            })
            
        # Upgrade weapon-specific modifiers up to 10
        if not hasattr(weapon, "modifiers"):
            weapon.modifiers = {
                "spread": 0, "homing": 0.0, "bounce": 0, "pierce": 0,
                "thickness": 0, "size": 0.0, "speed": 0.0
            }
        for mod_key in ["spread", "homing", "bounce", "pierce", "thickness", "size", "speed"]:
            current_val = weapon.modifiers.get(mod_key, 0)
            if current_val < 10:
                mod_names_fr = {
                    "spread": "Multi-Tirs",
                    "homing": "Tete Chercheuse",
                    "bounce": "Rebonds",
                    "pierce": "Penetration",
                    "thickness": "Epaisseur",
                    "size": "Taille",
                    "speed": "Vitesse"
                }
                mod_desc_fr = {
                    "spread": "+1 projectile simultane en eventail.",
                    "homing": "Les projectiles se dirigent plus fort vers les cibles.",
                    "bounce": "+1 rebond sur les bords de l'ecran.",
                    "pierce": "+1 penetration de cible supplementaire.",
                    "thickness": "Faisceau plus epais et doublement des traces.",
                    "size": "+15% de taille physique et zone de collision.",
                    "speed": "+15% de vitesse de deplacement des tirs."
                }
                options.append({
                    "id": f"mod_upgrade_{weapon.name}_{mod_key}",
                    "name": f"EVOLUTION {weapon.name} : {mod_names_fr[mod_key]} (Niv {int(current_val) + 1})",
                    "desc": mod_desc_fr[mod_key],
                    "type": "weapon_modifier_upgrade",
                    "target": (weapon.name, mod_key)
                })

    # 2. Passive upgrades
    # Limit passives to 6 slots
    if len(player.passives) < 6:
        for name in PASSIVE_DESCRIPTIONS:
            if name not in player.passives:
                options.append({
                    "id": f"unlock_passive_{name}",
                    "name": f"DEVERROUILLAGE : {PASSIVE_NAMES_FR.get(name, name)}",
                    "desc": PASSIVE_DESCRIPTIONS[name],
                    "type": "passive_unlock",
                    "target": name
                })

    # Upgrade existing passives
    for name, lvl in player.passives.items():
        if lvl < 5:
            options.append({
                "id": f"upgrade_passive_{name}",
                "name": f"AMELIORATION : {PASSIVE_NAMES_FR.get(name, name)} (Niv {lvl + 1})",
                "desc": PASSIVE_DESCRIPTIONS[name],
                "type": "passive_upgrade",
                "target": name
            })

    return options

def get_upgrade_pool(player, pool_size=3):
    options = get_available_upgrades(player)
    if not options:
        return [{
            "id": "heal_fallback",
            "name": "REPARATION INITIALISEE",
            "desc": "Restaure 30 PV a la coque.",
            "type": "heal",
            "target": "heal"
        }]
        
    # Separate upgrades and unlocks
    upgrades = [o for o in options if o["type"] in ("weapon_upgrade", "passive_upgrade", "passive_unlock")]
    unlocks = [o for o in options if o["type"] == "weapon_unlock"]
    
    random.shuffle(upgrades)
    random.shuffle(unlocks)
    
    pool = []
    # Limit to at most 1 weapon/accessory unlock in the choice pool to favor upgrades!
    if unlocks and random.random() < 0.45:
        pool.append(unlocks[0])
        
    for u in upgrades:
        if len(pool) < pool_size:
            pool.append(u)
            
    if len(pool) < pool_size:
        for unl in unlocks:
            if unl not in pool and len(pool) < pool_size:
                pool.append(unl)
                
    return pool

def apply_upgrade(player, upgrade):
    utype = upgrade["type"]
    target = upgrade["target"]

    if utype == "weapon_unlock":
        if target in PRIMARY_WEAPONS:
            # Accumulate: unlock and add to primary_weapons starting at level 1
            player.primary_weapons.append(PRIMARY_WEAPONS[target]())
        elif target in ACCESSORIES:
            player.accessories.append(ACCESSORIES[target]())
            
    elif utype == "weapon_upgrade":
        for w in player.weapons:
            if w.name == target:
                w.level_up()
                break
                
    elif utype == "weapon_modifier_upgrade":
        w_name, mod_key = target
        for w in player.weapons:
            if w.name == w_name:
                if not hasattr(w, "modifiers"):
                    w.modifiers = {
                        "spread": 0, "homing": 0.0, "bounce": 0, "pierce": 0,
                        "thickness": 0, "size": 0.0, "speed": 0.0
                    }
                w.modifiers[mod_key] = w.modifiers.get(mod_key, 0) + 1
                break
                
    elif utype == "passive_unlock":
        player.passives[target] = 1
        
    elif utype == "passive_upgrade":
        player.passives[target] += 1
        
    elif utype == "active_unlock":
        player.active_item = target
        player.active_item_level = 1
        player.active_charge = 0.0
        if target in ("HYPERSAUT", "LIVRE DES OMBRES"):
            lvl_mult = max(0.40, 1.0 - (player.active_item_level - 1) * 0.15)
            player.active_charge = ACTIVE_ITEMS[target]["cooldown"] * lvl_mult
            
    elif utype == "active_upgrade":
        player.active_item_level += 1
        
    elif utype == "heal":
        player.health = min(player.max_health, player.health + 30.0)
        return

    # Recalculate player stats based on passives and meta upgrades
    meta_engine = getattr(player, 'meta_engine_level', 0)
    player.speed_mult = (1.0 + 0.05 * meta_engine) + player.passives.get("THRUSTERS", 0) * 0.10
    
    player.armor = player.passives.get("NANO-ARMOR", 0) * 2.0
    
    meta_magnet = getattr(player, 'meta_magnet_level', 0)
    player.magnet_radius = PLAYER_START_MAGNET * ((1.0 + 0.15 * meta_magnet) + player.passives.get("XP MAGNET", 0) * 0.25)
    
    # Damage Multiplier (incorporates Overdrive, Giant Cells, Split Fire, Plasma Core, and Sacred Heart AND meta upgrades!)
    meta_damage = getattr(player, 'meta_damage_level', 0)
    base_dmg_mult = (1.0 + 0.05 * meta_damage) + player.passives.get("OVERDRIVE CORE", 0) * 0.15
    giant_cells_dmg = player.passives.get("GIANT CELLS", 0) * 0.10
    split_fire_reduction = player.passives.get("SPLIT FIRE", 0) * -0.12
    plasma_core_dmg = player.passives.get("PLASMA CORE", 0) * 0.10
    sacred_heart_dmg = player.passives.get("SACRED HEART", 0) * 0.50
    player.damage_mult = max(0.1, base_dmg_mult + giant_cells_dmg + split_fire_reduction + plasma_core_dmg + sacred_heart_dmg)
    
    # Hull Upgrade (Health cap AND meta upgrades!)
    old_max = player.max_health
    meta_hull = getattr(player, 'meta_hull_level', 0)
    player.max_health = 100.0 * (1.0 + 0.10 * meta_hull) + player.passives.get("HULL UPGRADE", 0) * 20.0
    if player.max_health > old_max:
        player.health += (player.max_health - old_max)
        
    player.health_regen = player.passives.get("REPAIR DRONES", 0) * 1.0
    
    meta_scanner = getattr(player, 'meta_scanner_level', 0)
    player.xp_mult = 1.0 + 0.08 * meta_scanner

    # Apply Isaac synergy stats
    player.proj_size_mult = 1.0 + player.passives.get("GIANT CELLS", 0) * 0.20 + player.passives.get("PLASMA CORE", 0) * 0.25 + player.passives.get("SACRED HEART", 0) * 0.40
    player.proj_speed_mult = (1.0 + player.passives.get("HYPER DRIVE", 0) * 0.20) * (1.0 - player.passives.get("SACRED HEART", 0) * 0.20)
    player.cooldown_mult = max(0.15, 1.0 - player.passives.get("HYPER DRIVE", 0) * 0.10 - player.passives.get("PLASMA CORE", 0) * 0.12)
    
    player.proj_count_mod = player.passives.get("SPLIT FIRE", 0)
    player.proj_homing = player.passives.get("SMART TARGETING", 0) * 1.5 + player.passives.get("SACRED HEART", 0) * 3.0
    player.proj_bounce = player.passives.get("BOUNCING MATRIX", 0)
    player.proj_pierce_mod = player.passives.get("DRILL TIP", 0)
    player.proj_split = player.passives.get("SHRAPNEL SHELLS", 0)
