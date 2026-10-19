#!/usr/bin/env python3
# devkit_editor.py

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import cairo
import json
import os
import math
import random

# Default fallback templates if files are missing
DEFAULT_TEMPLATES = {
    "swarmer": {
        "base_hp": 10.0, "base_speed": 135.0, "base_damage": 8.0,
        "base_score": 10, "base_radius": 21.0, "color": [0.1, 0.9, 0.1],
        "suffixes": ["Swarmer", "Scout", "Scarab", "Glider"],
        "is_spaceship": False, "enemy_class_suffix": None,
        "weapon_type": None, "modifiers": {}
    },
    "chaser": {
        "base_hp": 25.0, "base_speed": 95.0, "base_damage": 14.0,
        "base_score": 25, "base_radius": 28.0, "color": [1.0, 0.75, 0.0],
        "suffixes": ["Chaser", "Reaver", "Charger", "Seeker"],
        "is_spaceship": False, "enemy_class_suffix": None,
        "weapon_type": None, "modifiers": {}
    },
    "stalker": {
        "base_hp": 55.0, "base_speed": 65.0, "base_damage": 22.0,
        "base_score": 60, "base_radius": 38.0, "color": [1.0, 0.2, 0.2],
        "suffixes": ["Stalker", "Devourer", "Sentinel", "Goliath"],
        "is_spaceship": False, "enemy_class_suffix": None,
        "weapon_type": None, "modifiers": {}
    },
    "boss": {
        "base_hp": 380.0, "base_speed": 48.0, "base_damage": 45.0,
        "base_score": 500, "base_radius": 62.0, "color": [1.0, 1.0, 1.0],
        "suffixes": [], "is_spaceship": False, "enemy_class_suffix": "Boss",
        "weapon_type": None, "modifiers": {}
    },
    "light_fighter": {
        "base_hp": 16.0, "base_speed": 120.0, "base_damage": 9.0,
        "base_score": 15, "base_radius": 18.0, "color": [0.3, 0.6, 1.0],
        "suffixes": [], "is_spaceship": True, "enemy_class_suffix": "Fighter",
        "weapon_type": "laser", "modifiers": {"spread": 1}, "name": "Chasseur Leger"
    }
}

DEFAULT_SHAPES = {
    "player": {
        "fuselage": {
            "type": "polygon",
            "points": [[16.0, 0.0], [5.0, 4.0], [-10.0, 4.0], [-6.0, 0.0], [-10.0, -4.0], [5.0, -4.0]],
            "color": "COLOR_WHITE"
        }
    },
    "enemies": {
        "Fighter": [
            {"type": "polygon", "points": [[1.0, 0.0], [-0.6, -0.7], [-0.3, 0.0], [-0.6, 0.7]], "color": "enemy_color"}
        ]
    }
}

TEMPLATE_TO_SHAPE = {
    "swarmer": "Swarmer",
    "chaser": "Chaser",
    "stalker": "Stalker",
    "boss": "Boss",
    "light_fighter": "Fighter",
    "interceptor": "Interceptor",
    "bomber": "Bomber",
    "frigate": "Frigate",
    "corvette": "Corvette",
    "cruiser": "Cruiser",
    "destroyer": "Destroyer",
    "dreadnought": "Dreadnought",
    "recon": "Recon",
    "carrier": "Carrier"
}


class DevkitEditorWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Vector Survivor Devkit & CAD Editor")
        self.set_default_size(1050, 780)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Files config paths
        self.config_path = os.path.join("data", "enemy_config.json")
        self.shapes_path = os.path.join("data", "shapes.json")
        
        # App internal database
        self.config_data = {}
        self.shapes_data = {}
        self.load_data_files()
        
        # Selection states
        self.current_active_key = None
        self.active_shape_key = "Fighter"
        self.active_component_idx = 0
        self.dragged_vertex = None
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.active_projectiles = []
        self.proj_spawn_timer = 0.0
        
        # Grid parameters
        self.canvas_w = 450
        self.canvas_h = 320
        
        # Build UI layout
        self.build_ui()
        
        # Populate vertical entity list
        self.populate_entities_list()
        
        # Continuous animation loop setup
        self.anim_time = 0.0
        self.active_weapon_key = None
        GLib.timeout_add(16, self.on_animation_tick)
        
    def load_data_files(self):
        # Stats templates
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
            except Exception as e:
                print(f"Error loading enemy_config.json: {e}")
                self.config_data = {"templates": DEFAULT_TEMPLATES}
        else:
            self.config_data = {"templates": DEFAULT_TEMPLATES}
            
        # Shapes drawing
        if os.path.exists(self.shapes_path):
            try:
                with open(self.shapes_path, "r", encoding="utf-8") as f:
                    self.shapes_data = json.load(f)
            except Exception as e:
                print(f"Error loading shapes.json: {e}")
                self.shapes_data = DEFAULT_SHAPES
        else:
            self.shapes_data = DEFAULT_SHAPES
            
    def save_data_files(self):
        # Save active stat gui changes first
        if self.current_active_key and self.current_active_key != "player":
            self.save_gui_to_template(self.current_active_key)
            
        # Verify data folder exists
        os.makedirs("data", exist_ok=True)
        
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            with open(self.shapes_path, "w", encoding="utf-8") as f:
                json.dump(self.shapes_data, f, indent=2, ensure_ascii=False)
            self.show_info_dialog("Enregistrement réussi !", "Toutes les modifications géométriques et statistiques ont été écrites avec succès.")
        except Exception as e:
            self.show_error_dialog("Erreur d'enregistrement", f"Impossible d'écrire les fichiers : {e}")

    def show_info_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_error_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)
        
        # --- TOP HEADER BAR ---
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        top_bar.set_border_width(6)
        main_box.pack_start(top_bar, False, False, 0)
        
        lbl_title = Gtk.Label(label="Éditeur de Vaisseaux & Entités")
        lbl_title.set_markup("<b><span size='large'>Vector Survivor Devkit</span></b>")
        top_bar.pack_start(lbl_title, False, False, 10)
        
        btn_save = Gtk.Button(label="💾 Enregistrer")
        btn_save.connect("clicked", lambda w: self.save_data_files())
        top_bar.pack_end(btn_save, False, False, 5)
        
        btn_reload = Gtk.Button(label="🔄 Recharger")
        btn_reload.connect("clicked", lambda w: self.reload_configs())
        top_bar.pack_end(btn_reload, False, False, 5)
        
        # --- MAIN PANED DIVISION ---
        h_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        h_paned.set_position(240)
        main_box.pack_start(h_paned, True, True, 0)
        
        # 1. LEFT PANEL: VERTICAL LIST OF ENEMIES & PLAYER
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        left_box.set_border_width(6)
        
        left_title = Gtk.Label(label="Entités & Ennemis")
        left_title.set_markup("<b>Entités &amp; Ennemis</b>")
        left_box.pack_start(left_title, False, False, 5)
        
        left_scroll = Gtk.ScrolledWindow()
        left_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        left_scroll.set_min_content_width(260)
        left_scroll.set_min_content_height(600)
        left_box.pack_start(left_scroll, True, True, 0)
        
        self.listbox_entities = Gtk.ListBox()
        self.listbox_entities.connect("row-selected", self.on_entity_row_selected)
        left_scroll.add(self.listbox_entities)
        
        btn_create_ship = Gtk.Button(label="✨ Créer Nouveau Vaisseau")
        btn_create_ship.connect("clicked", self.on_create_new_ship)
        left_box.pack_start(btn_create_ship, False, False, 5)
        
        h_paned.pack1(left_box, resize=False, shrink=False)
        
        # 2. RIGHT PANEL: SPLIT INTO TOP (CAD) AND BOTTOM (STATS)
        v_paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        v_paned.set_position(360)
        h_paned.pack2(v_paned, resize=True, shrink=False)
        
        # 2A. TOP PANE: POLYGON/SHAPES CAD EDITOR
        top_cad_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        top_cad_box.set_border_width(6)
        
        # Left side: Drawing canvas
        canvas_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(450, 320)
        self.drawing_area.connect("draw", self.on_draw_canvas)
        self.drawing_area.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.POINTER_MOTION_MASK
        )
        self.drawing_area.connect("button-press-event", self.on_canvas_button_press)
        self.drawing_area.connect("button-release-event", self.on_canvas_button_release)
        self.drawing_area.connect("motion-notify-event", self.on_canvas_motion_notify)
        canvas_container.pack_start(self.drawing_area, True, True, 0)
        
        lbl_help = Gtk.Label(label="Clic Gauche : Placer/Déplacer point | Clic Droit : Retirer dernier point | Drag : Bouger point")
        lbl_help.set_markup("<span size='small' color='#666666'>Clic Gauche : Placer/Déplacer point | Clic Droit : Retirer point | Drag : Bouger point</span>")
        canvas_container.pack_start(lbl_help, False, False, 2)
        top_cad_box.pack_start(canvas_container, True, True, 0)
        
        # Right side: Component controls
        cad_controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        cad_controls_box.set_size_request(220, -1)
        cad_controls_box.pack_start(Gtk.Label(label="Composants du dessin :"), False, False, 2)
        
        cad_scroll = Gtk.ScrolledWindow()
        cad_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        cad_scroll.set_size_request(-1, 140)
        self.listbox_components = Gtk.ListBox()
        self.listbox_components.connect("row-selected", self.on_component_row_selected)
        cad_scroll.add(self.listbox_components)
        cad_controls_box.pack_start(cad_scroll, True, True, 0)
        
        # Type & Color of selected component
        comp_grid = Gtk.Grid()
        comp_grid.set_column_spacing(5)
        comp_grid.set_row_spacing(5)
        comp_grid.attach(Gtk.Label(label="Type:"), 0, 0, 1, 1)
        self.combo_comp_type = Gtk.ComboBoxText()
        self.combo_comp_type.append_text("polygon")
        self.combo_comp_type.append_text("line")
        self.combo_comp_type.append_text("circle")
        self.combo_comp_type.connect("changed", self.on_comp_type_changed)
        comp_grid.attach(self.combo_comp_type, 1, 0, 1, 1)
        
        comp_grid.attach(Gtk.Label(label="Couleur:"), 0, 1, 1, 1)
        self.combo_comp_color = Gtk.ComboBoxText()
        self.combo_comp_color.append_text("enemy_color")
        self.combo_comp_color.append_text("COLOR_WHITE")
        self.combo_comp_color.append_text("COLOR_RED")
        self.combo_comp_color.append_text("COLOR_GREEN")
        self.combo_comp_color.append_text("COLOR_AMBER")
        self.combo_comp_color.connect("changed", self.on_comp_color_changed)
        comp_grid.attach(self.combo_comp_color, 1, 1, 1, 1)
        cad_controls_box.pack_start(comp_grid, False, False, 2)
        
        # Control buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        btn_add = Gtk.Button(label="+ Ajouter")
        btn_add.connect("clicked", self.on_add_component)
        btn_box.pack_start(btn_add, True, True, 0)
        btn_del = Gtk.Button(label="- Retirer")
        btn_del.connect("clicked", self.on_delete_component)
        btn_box.pack_start(btn_del, True, True, 0)
        btn_clear = Gtk.Button(label="Vider")
        btn_clear.connect("clicked", self.on_clear_points)
        btn_box.pack_start(btn_clear, True, True, 0)
        cad_controls_box.pack_start(btn_box, False, False, 2)
        
        top_cad_box.pack_start(cad_controls_box, False, False, 0)
        v_paned.pack1(top_cad_box, resize=True, shrink=False)
        
        # 2B. BOTTOM PANE: STATS/CHARACTERISTICS EDITOR FORM
        stats_frame = Gtk.Frame(label="Caractéristiques de l'Entité")
        stats_frame.set_shadow_type(Gtk.ShadowType.IN)
        stats_scroll = Gtk.ScrolledWindow()
        stats_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        stats_frame.add(stats_scroll)
        
        self.stats_grid = Gtk.Grid()
        self.stats_grid.set_column_spacing(15)
        self.stats_grid.set_row_spacing(10)
        self.stats_grid.set_border_width(10)
        stats_scroll.add(self.stats_grid)
        
        # Build Stats Form Widgets
        self.build_stats_form()
        
        v_paned.pack2(stats_frame, resize=False, shrink=False)

    def build_stats_form(self):
        # HP Entry
        lbl_hp = Gtk.Label(label="Points de vie de base (base_hp) :")
        self.stats_grid.attach(lbl_hp, 0, 0, 1, 1)
        self.spin_hp = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=10, lower=1, upper=10000, step_increment=1, page_increment=10, page_size=0), climb_rate=1.0, digits=1)
        self.stats_grid.attach(self.spin_hp, 1, 0, 1, 1)
        
        # Speed Entry
        lbl_speed = Gtk.Label(label="Vitesse max de vol (base_speed) :")
        self.stats_grid.attach(lbl_speed, 0, 1, 1, 1)
        self.spin_speed = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=100, lower=10, upper=2000, step_increment=5, page_increment=50, page_size=0), climb_rate=2.0, digits=1)
        self.stats_grid.attach(self.spin_speed, 1, 1, 1, 1)
        
        # Damage Entry
        lbl_dmg = Gtk.Label(label="Dégâts de contact (base_damage) :")
        self.stats_grid.attach(lbl_dmg, 2, 0, 1, 1)
        self.spin_dmg = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=5, lower=1, upper=1000, step_increment=1, page_increment=10, page_size=0), climb_rate=1.0, digits=1)
        self.stats_grid.attach(self.spin_dmg, 3, 0, 1, 1)
        
        # Score Entry
        lbl_score = Gtk.Label(label="Score attribué (base_score) :")
        self.stats_grid.attach(lbl_score, 2, 1, 1, 1)
        self.spin_score = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=10, lower=0, upper=50000, step_increment=5, page_increment=50, page_size=0), climb_rate=5.0, digits=0)
        self.stats_grid.attach(self.spin_score, 3, 1, 1, 1)
        
        # Radius Entry
        lbl_rad = Gtk.Label(label="Rayon Hitbox en pixels (base_radius) :")
        self.stats_grid.attach(lbl_rad, 0, 2, 1, 1)
        self.spin_radius = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=20, lower=5, upper=300, step_increment=1, page_increment=10, page_size=0), climb_rate=1.0, digits=1)
        self.stats_grid.attach(self.spin_radius, 1, 2, 1, 1)
        
        # Weapon Combo
        lbl_weapon = Gtk.Label(label="Arme par défaut :")
        self.stats_grid.attach(lbl_weapon, 2, 2, 1, 1)
        self.combo_weapon = Gtk.ComboBoxText()
        for w in ["None", "laser", "missile", "vortex", "blade", "flame", "lightning", "meteor", "carrier_spawner"]:
            self.combo_weapon.append_text(w)
        self.stats_grid.attach(self.combo_weapon, 3, 2, 1, 1)
        
        # Color Sliders
        lbl_color = Gtk.Label(label="Couleur de base (RGB) :")
        self.stats_grid.attach(lbl_color, 0, 3, 1, 1)
        
        color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.spin_r = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=0.5, lower=0.0, upper=1.0, step_increment=0.05, page_increment=0.1, page_size=0), climb_rate=0.05, digits=2)
        self.spin_g = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=0.5, lower=0.0, upper=1.0, step_increment=0.05, page_increment=0.1, page_size=0), climb_rate=0.05, digits=2)
        self.spin_b = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=0.5, lower=0.0, upper=1.0, step_increment=0.05, page_increment=0.1, page_size=0), climb_rate=0.05, digits=2)
        color_box.pack_start(Gtk.Label(label="R:"), False, False, 0)
        color_box.pack_start(self.spin_r, False, False, 0)
        color_box.pack_start(Gtk.Label(label="G:"), False, False, 0)
        color_box.pack_start(self.spin_g, False, False, 0)
        color_box.pack_start(Gtk.Label(label="B:"), False, False, 0)
        color_box.pack_start(self.spin_b, False, False, 0)
        self.stats_grid.attach(color_box, 1, 3, 3, 1)
        
        # Custom French Name Entry
        lbl_name = Gtk.Label(label="Nom Français :")
        self.stats_grid.attach(lbl_name, 0, 4, 1, 1)
        self.entry_name = Gtk.Entry()
        self.stats_grid.attach(self.entry_name, 1, 4, 1, 1)
        
        # Suffix List Entry
        lbl_suffixes = Gtk.Label(label="Suffixes aléatoires :")
        self.stats_grid.attach(lbl_suffixes, 2, 4, 1, 1)
        self.entry_suffixes = Gtk.Entry()
        self.stats_grid.attach(self.entry_suffixes, 3, 4, 1, 1)
        
        # Structured weapon modifiers
        lbl_mods_title = Gtk.Label(label="Modificateurs d'Armes :")
        lbl_mods_title.set_markup("<b>Modificateurs d'Armes :</b>")
        self.stats_grid.attach(lbl_mods_title, 0, 5, 1, 1)
        
        mods_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.stats_grid.attach(mods_box, 1, 5, 3, 1)
        
        # 1. Spread (tirs)
        mods_box.pack_start(Gtk.Label(label="Multi-Tirs:"), False, False, 0)
        self.spin_mod_spread = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=1, lower=1, upper=10, step_increment=1, page_increment=1, page_size=0), climb_rate=1.0, digits=0)
        mods_box.pack_start(self.spin_mod_spread, False, False, 0)
        
        # 2. Homing (tête chercheuse)
        self.chk_mod_homing = Gtk.CheckButton(label="Tête Chercheuse")
        self.chk_mod_homing.connect("toggled", self.on_homing_chk_toggled)
        mods_box.pack_start(self.chk_mod_homing, False, False, 0)
        self.spin_mod_homing = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=1.0, lower=0.5, upper=10.0, step_increment=0.5, page_increment=1.0, page_size=0), climb_rate=0.5, digits=1)
        self.spin_mod_homing.set_sensitive(False)
        mods_box.pack_start(self.spin_mod_homing, False, False, 0)
        
        # 3. Bounce (rebonds)
        mods_box.pack_start(Gtk.Label(label="Rebonds:"), False, False, 0)
        self.spin_mod_bounce = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=0, lower=0, upper=10, step_increment=1, page_increment=1, page_size=0), climb_rate=1.0, digits=0)
        mods_box.pack_start(self.spin_mod_bounce, False, False, 0)
        
        # 4. Pierce (transpercement)
        mods_box.pack_start(Gtk.Label(label="Pénétration:"), False, False, 0)
        self.spin_mod_pierce = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=0, lower=0, upper=10, step_increment=1, page_increment=1, page_size=0), climb_rate=1.0, digits=0)
        mods_box.pack_start(self.spin_mod_pierce, False, False, 0)
        
        # 5. Tiny Planet (orbite)
        self.chk_mod_orbit = Gtk.CheckButton(label="Orbite")
        mods_box.pack_start(self.chk_mod_orbit, False, False, 0)
        
        # 6. Thickness (épaisseur)
        mods_box.pack_start(Gtk.Label(label="Épaisseur:"), False, False, 0)
        self.spin_mod_thick = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=1, lower=1, upper=10, step_increment=1, page_increment=1, page_size=0), climb_rate=1.0, digits=0)
        mods_box.pack_start(self.spin_mod_thick, False, False, 0)
        
        # 7. Size (taille)
        mods_box.pack_start(Gtk.Label(label="Taille:"), False, False, 0)
        self.spin_mod_size = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=1.0, lower=0.5, upper=10.0, step_increment=0.1, page_increment=0.5, page_size=0), climb_rate=0.1, digits=1)
        mods_box.pack_start(self.spin_mod_size, False, False, 0)
        
        # 8. Speed (vitesse)
        mods_box.pack_start(Gtk.Label(label="Vitesse:"), False, False, 0)
        self.spin_mod_speed_mult = Gtk.SpinButton(adjustment=Gtk.Adjustment(value=1.0, lower=0.2, upper=10.0, step_increment=0.1, page_increment=0.5, page_size=0), climb_rate=0.1, digits=1)
        mods_box.pack_start(self.spin_mod_speed_mult, False, False, 0)

        # Collect widgets that only apply to ships (weapons ignore these)
        self.non_weapon_widgets = [
            self.spin_hp, self.spin_speed, self.spin_dmg, self.spin_score,
            self.spin_radius, self.spin_r, self.spin_g, self.spin_b,
            self.entry_name, self.entry_suffixes
        ]

    # --- ENTITIES LIST INJECTION ---
    def populate_entities_list(self):
        # Clear list box first
        for child in self.listbox_entities.get_children():
            self.listbox_entities.remove(child)

        # 1. Player ship at the very top
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_border_width(8)
        lbl = Gtk.Label(label="🚀 Joueur (vaisseau)")
        box.pack_start(lbl, True, True, 5)
        row.key = "player"
        row.is_weapon = False
        row.add(box)
        self.listbox_entities.add(row)
        
        # 2. Enemies templates
        templates = self.config_data.get("templates", {})
        for key in sorted(templates.keys()):
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.set_border_width(8)
            name_fr = templates[key].get("name", key.capitalize())
            lbl = Gtk.Label(label=f"👾 {key} ({name_fr})")
            box.pack_start(lbl, True, True, 5)
            row.key = key
            row.is_weapon = False
            row.add(box)
            self.listbox_entities.add(row)

        # 3. Weapons preview animations at the bottom
        weapons_list = [
            ("laser", "Laser à Impulsion"),
            ("missile", "Missile Guidé"),
            ("vortex", "Vortex Gravitationnel"),
            ("blade", "Bouclier de Lames"),
            ("flame", "Lance-Flammes"),
            ("lightning", "Éclair de Chaîne"),
            ("meteor", "Pluie de Météores"),
            ("carrier_spawner", "Porte-Nefs Spawner")
        ]
        for w_key, w_name in weapons_list:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            box.set_border_width(8)
            lbl = Gtk.Label(label=f"⚔️ Arme: {w_name}")
            box.pack_start(lbl, True, True, 5)
            row.key = f"weapon_{w_key}"
            row.is_weapon = True
            row.add(box)
            self.listbox_entities.add(row)
            
        self.listbox_entities.show_all()
        # Default select Player
        self.listbox_entities.select_row(self.listbox_entities.get_row_at_index(0))

    def on_create_new_ship(self, btn):
        dialog = Gtk.Dialog(title="Créer un Nouveau Vaisseau", parent=self, flags=0)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        
        box = dialog.get_content_area()
        box.set_spacing(10)
        box.set_border_width(12)
        
        lbl = Gtk.Label(label="Identifiant unique (ex: heavy_destroyer) :")
        box.pack_start(lbl, False, False, 0)
        
        entry = Gtk.Entry()
        box.pack_start(entry, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            new_key = entry.get_text().strip().lower()
            if not new_key:
                self.show_error_dialog("Erreur", "L'identifiant ne peut pas être vide.")
            elif new_key in self.config_data.get("templates", {}) or new_key == "player":
                self.show_error_dialog("Erreur", f"L'identifiant '{new_key}' existe déjà.")
            else:
                # Add default stats template
                self.config_data["templates"][new_key] = {
                    "base_hp": 30.0,
                    "base_speed": 100.0,
                    "base_damage": 12.0,
                    "base_score": 50,
                    "base_radius": 24.0,
                    "color": [1.0, 1.0, 1.0],
                    "suffixes": [],
                    "is_spaceship": True,
                    "enemy_class_suffix": new_key.capitalize(),
                    "weapon_type": "laser",
                    "modifiers": {},
                    "name": new_key.capitalize()
                }
                
                # Add default geometry
                shape_key = new_key.capitalize()
                if "enemies" not in self.shapes_data:
                    self.shapes_data["enemies"] = {}
                
                if shape_key not in self.shapes_data["enemies"]:
                    self.shapes_data["enemies"][shape_key] = [
                        {"type": "polygon", "points": [[1.0, 0.0], [-0.7, -0.6], [-0.3, 0.0], [-0.7, 0.6]], "color": "enemy_color"}
                    ]
                
                # Register mapping in translation dictionary
                TEMPLATE_TO_SHAPE[new_key] = shape_key
                
                # Refresh UI vertical list
                self.populate_entities_list()
                
                # Auto-select the newly created row
                for child in self.listbox_entities.get_children():
                    if getattr(child, "key", None) == new_key:
                        self.listbox_entities.select_row(child)
                        break
                        
        dialog.destroy()

    def on_entity_row_selected(self, listbox, row):
        if not row:
            return
            
        # Save previous stats from form
        if self.current_active_key and not self.current_active_key.startswith("weapon_") and self.current_active_key != "player":
            self.save_gui_to_template(self.current_active_key)
            
        key = row.key
        self.current_active_key = key
        
        # Reset current animation particles
        self.active_projectiles = []
        self.proj_spawn_timer = 0.0
        
        if getattr(row, "is_weapon", False):
            # Selection of weapon
            self.active_weapon_key = key
            self.active_shape_key = None
            
            # Disable ship stats, but leave weapon modifications active!
            for w in self.non_weapon_widgets:
                w.set_sensitive(False)
            self.combo_weapon.set_sensitive(True)
            self.spin_mod_spread.set_sensitive(True)
            self.chk_mod_homing.set_sensitive(True)
            self.spin_mod_bounce.set_sensitive(True)
            self.spin_mod_pierce.set_sensitive(True)
            self.chk_mod_orbit.set_sensitive(True)
            self.spin_mod_thick.set_sensitive(True)
            self.spin_mod_size.set_sensitive(True)
            self.spin_mod_speed_mult.set_sensitive(True)
            
            self.listbox_components.set_sensitive(False)
            self.combo_comp_type.set_sensitive(False)
            self.combo_comp_color.set_sensitive(False)
            
            # Show descriptive label
            self.load_weapon_dummy_stats(key)
            self.drawing_area.queue_draw()
        else:
            # Selection of ship / template
            self.active_weapon_key = None
            self.listbox_components.set_sensitive(True)
            self.combo_comp_type.set_sensitive(True)
            self.combo_comp_color.set_sensitive(True)
            
            # Re-enable all fields
            for w in self.non_weapon_widgets:
                w.set_sensitive(True)
            self.combo_weapon.set_sensitive(True)
            self.spin_mod_spread.set_sensitive(True)
            self.chk_mod_homing.set_sensitive(True)
            self.spin_mod_bounce.set_sensitive(True)
            self.spin_mod_pierce.set_sensitive(True)
            self.chk_mod_orbit.set_sensitive(True)
            self.spin_mod_thick.set_sensitive(True)
            self.spin_mod_size.set_sensitive(True)
            self.spin_mod_speed_mult.set_sensitive(True)
            
            if key == "player":
                for w in self.non_weapon_widgets:
                    w.set_sensitive(False)
                self.combo_weapon.set_sensitive(False)
                self.spin_mod_spread.set_sensitive(False)
                self.chk_mod_homing.set_sensitive(False)
                self.spin_mod_bounce.set_sensitive(False)
                self.spin_mod_pierce.set_sensitive(False)
                self.chk_mod_orbit.set_sensitive(False)
                self.spin_mod_thick.set_sensitive(False)
                self.spin_mod_size.set_sensitive(False)
                self.spin_mod_speed_mult.set_sensitive(False)
                
                self.load_player_dummy_stats()
                self.select_shape_key("player")
            else:
                self.load_template_to_gui(key)
                # Match template to vector shape key
                shape_key = TEMPLATE_TO_SHAPE.get(key, "Boss")
                self.select_shape_key(shape_key)

    def load_player_dummy_stats(self):
        self.spin_hp.set_value(100.0)
        self.spin_speed.set_value(200.0)
        self.spin_dmg.set_value(0.0)
        self.spin_score.set_value(0)
        self.spin_radius.set_value(20.0)
        self.spin_r.set_value(1.0)
        self.spin_g.set_value(1.0)
        self.spin_b.set_value(1.0)
        self.combo_weapon.set_active(0)
        self.entry_name.set_text("Vaisseau du Joueur")
        self.entry_suffixes.set_text("N/A")
        
        # Reset modifiers
        self.spin_mod_spread.set_value(1)
        self.chk_mod_homing.set_active(False)
        self.spin_mod_homing.set_value(1.0)
        self.spin_mod_homing.set_sensitive(False)
        self.spin_mod_bounce.set_value(0)
        self.spin_mod_pierce.set_value(0)
        self.chk_mod_orbit.set_active(False)
        self.spin_mod_thick.set_value(1)
        self.spin_mod_size.set_value(1.0)
        self.spin_mod_speed_mult.set_value(1.0)

    def load_template_to_gui(self, key):
        templates = self.config_data.get("templates", {})
        if key not in templates:
            return
        t = templates[key]
        self.spin_hp.set_value(t.get("base_hp", 10.0))
        self.spin_speed.set_value(t.get("base_speed", 100.0))
        self.spin_dmg.set_value(t.get("base_damage", 5.0))
        self.spin_score.set_value(t.get("base_score", 10))
        self.spin_radius.set_value(t.get("base_radius", 20.0))
        
        col = t.get("color", [1.0, 1.0, 1.0])
        self.spin_r.set_value(col[0] if len(col) > 0 else 1.0)
        self.spin_g.set_value(col[1] if len(col) > 1 else 1.0)
        self.spin_b.set_value(col[2] if len(col) > 2 else 1.0)
        
        w_type = t.get("weapon_type")
        if w_type is None:
            self.combo_weapon.set_active(0)
        else:
            for idx, text in enumerate(["None", "laser", "missile", "vortex", "blade", "flame", "lightning", "meteor", "carrier_spawner"]):
                if text == w_type:
                    self.combo_weapon.set_active(idx)
                    break
                    
        self.entry_name.set_text(t.get("name", ""))
        self.entry_suffixes.set_text(", ".join(t.get("suffixes", [])))
        
        # Load structured modifiers
        mods = t.get("modifiers", {})
        self.spin_mod_spread.set_value(mods.get("spread", 1))
        
        has_homing = "homing" in mods
        self.chk_mod_homing.set_active(has_homing)
        self.spin_mod_homing.set_value(mods.get("homing", 1.0))
        self.spin_mod_homing.set_sensitive(has_homing)
        
        self.spin_mod_bounce.set_value(mods.get("bounce", 0))
        self.spin_mod_pierce.set_value(mods.get("pierce", 0))
        self.chk_mod_orbit.set_active(mods.get("tiny_planet", False))
        self.spin_mod_thick.set_value(mods.get("thickness", 1))
        self.spin_mod_size.set_value(mods.get("size", 1.0))
        self.spin_mod_speed_mult.set_value(mods.get("speed_mult", 1.0))
        
    def save_gui_to_template(self, key):
        if not key or key == "player":
            return
        templates = self.config_data.get("templates", {})
        if key not in templates:
            templates[key] = {}
            
        t = templates[key]
        t["base_hp"] = self.spin_hp.get_value()
        t["base_speed"] = self.spin_speed.get_value()
        t["base_damage"] = self.spin_dmg.get_value()
        t["base_score"] = int(self.spin_score.get_value())
        t["base_radius"] = self.spin_radius.get_value()
        t["color"] = [
            round(self.spin_r.get_value(), 2),
            round(self.spin_g.get_value(), 2),
            round(self.spin_b.get_value(), 2)
        ]
        
        w_text = self.combo_weapon.get_active_text()
        t["weapon_type"] = None if w_text == "None" else w_text
        
        name = self.entry_name.get_text().strip()
        if name:
            t["name"] = name
        elif "name" in t:
            del t["name"]
            
        suf_text = self.entry_suffixes.get_text()
        t["suffixes"] = [s.strip() for s in suf_text.split(",") if s.strip()]
        
        # Save structured modifiers
        mods = {}
        spread_val = int(self.spin_mod_spread.get_value())
        if spread_val > 1:
            mods["spread"] = spread_val
            
        if self.chk_mod_homing.get_active():
            mods["homing"] = round(self.spin_mod_homing.get_value(), 1)
            
        bounce_val = int(self.spin_mod_bounce.get_value())
        if bounce_val > 0:
            mods["bounce"] = bounce_val
            
        offset_val = int(self.spin_mod_pierce.get_value())
        if offset_val > 0:
            mods["pierce"] = offset_val
            
        if self.chk_mod_orbit.get_active():
            mods["tiny_planet"] = True
            
        thick_val = int(self.spin_mod_thick.get_value())
        if thick_val > 1:
            mods["thickness"] = thick_val
            
        size_val = round(self.spin_mod_size.get_value(), 1)
        if size_val != 1.0:
            mods["size"] = size_val
            
        speed_val = round(self.spin_mod_speed_mult.get_value(), 1)
        if speed_val != 1.0:
            mods["speed_mult"] = speed_val
            
        t["modifiers"] = mods

    def on_homing_chk_toggled(self, chk):
        self.spin_mod_homing.set_sensitive(chk.get_active())

    # --- SHAPES UTILS ---
    def select_shape_key(self, key):
        self.active_shape_key = key
        self.active_component_idx = 0
        self.update_components_list()
        self.drawing_area.queue_draw()
        
    def get_shape_components(self, key):
        if key == "player":
            return list(self.shapes_data.get("player", {}).items())
        else:
            enemy_list = self.shapes_data.get("enemies", {}).get(key, [])
            return [(f"Element {i}", c) for i, c in enumerate(enemy_list)]
            
    def set_shape_components(self, key, components):
        if key == "player":
            self.shapes_data["player"] = {}
            for name, comp in components:
                self.shapes_data["player"][name] = comp
        else:
            if "enemies" not in self.shapes_data:
                self.shapes_data["enemies"] = {}
            self.shapes_data["enemies"][key] = [comp for name, comp in components]

    def update_components_list(self):
        # Clear listbox
        for child in self.listbox_components.get_children():
            self.listbox_components.remove(child)
            
        components = self.get_shape_components(self.active_shape_key)
        for i, (name, comp) in enumerate(components):
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            row.add(box)
            lbl_name = Gtk.Label(label=f"[{comp.get('type', 'poly')}] {name}")
            box.pack_start(lbl_name, True, True, 5)
            self.listbox_components.add(row)
            
        self.listbox_components.show_all()
        
        # Select active component
        if len(components) > 0:
            if self.active_component_idx >= len(components):
                self.active_component_idx = len(components) - 1
            row = self.listbox_components.get_row_at_index(self.active_component_idx)
            if row:
                self.listbox_components.select_row(row)
                
            comp = components[self.active_component_idx][1]
            ctype = comp.get("type", "polygon")
            for idx, text in enumerate(["polygon", "line", "circle"]):
                if text == ctype:
                    self.combo_comp_type.set_active(idx)
                    break
            ccol = comp.get("color", "enemy_color")
            if isinstance(ccol, list):
                ccol = "COLOR_WHITE"
            for idx, text in enumerate(["enemy_color", "COLOR_WHITE", "COLOR_RED", "COLOR_GREEN", "COLOR_AMBER"]):
                if text == ccol:
                    self.combo_comp_color.set_active(idx)
                    break

    def on_component_row_selected(self, listbox, row):
        if row:
            self.active_component_idx = row.get_index()
            components = self.get_shape_components(self.active_shape_key)
            if 0 <= self.active_component_idx < len(components):
                comp = components[self.active_component_idx][1]
                ctype = comp.get("type", "polygon")
                for idx, text in enumerate(["polygon", "line", "circle"]):
                    if text == ctype:
                        self.combo_comp_type.set_active(idx)
                        break
                ccol = comp.get("color", "enemy_color")
                if isinstance(ccol, list):
                    ccol = "COLOR_WHITE"
                for idx, text in enumerate(["enemy_color", "COLOR_WHITE", "COLOR_RED", "COLOR_GREEN", "COLOR_AMBER"]):
                    if text == ccol:
                        self.combo_comp_color.set_active(idx)
                        break
            self.drawing_area.queue_draw()

    def on_comp_type_changed(self, combo):
        components = self.get_shape_components(self.active_shape_key)
        if 0 <= self.active_component_idx < len(components):
            comp = components[self.active_component_idx][1]
            new_type = combo.get_active_text()
            if new_type and comp.get("type") != new_type:
                comp["type"] = new_type
                if new_type == "polygon":
                    comp["points"] = []
                    if "p1" in comp: del comp["p1"]
                    if "p2" in comp: del comp["p2"]
                    if "center" in comp: del comp["center"]
                elif new_type == "line":
                    comp["p1"] = [0.0, 0.0]
                    comp["p2"] = [0.0, 0.0]
                    if "points" in comp: del comp["points"]
                    if "center" in comp: del comp["center"]
                elif new_type == "circle":
                    comp["center"] = [0.0, 0.0]
                    comp["radius"] = 0.5
                    if "points" in comp: del comp["points"]
                    if "p1" in comp: del comp["p1"]
                    if "p2" in comp: del comp["p2"]
                    
                self.set_shape_components(self.active_shape_key, components)
                self.drawing_area.queue_draw()
                self.update_components_list()

    def on_comp_color_changed(self, combo):
        components = self.get_shape_components(self.active_shape_key)
        if 0 <= self.active_component_idx < len(components):
            comp = components[self.active_component_idx][1]
            new_color = combo.get_active_text()
            if new_color:
                if new_color == "COLOR_WHITE":
                    comp["color"] = [1.0, 1.0, 1.0]
                elif new_color == "COLOR_RED":
                    comp["color"] = [1.0, 0.2, 0.2]
                elif new_color == "COLOR_GREEN":
                    comp["color"] = [0.1, 0.9, 0.1]
                elif new_color == "COLOR_AMBER":
                    comp["color"] = [1.0, 0.75, 0.0]
                else:
                    comp["color"] = "enemy_color"
                self.set_shape_components(self.active_shape_key, components)
                self.drawing_area.queue_draw()

    def on_add_component(self, btn):
        components = self.get_shape_components(self.active_shape_key)
        if self.active_shape_key == "player":
            comp_name = f"wing_panel_{len(components)}"
            new_comp = {"type": "polygon", "points": [], "color": "COLOR_WHITE"}
            components.append((comp_name, new_comp))
        else:
            new_comp = {"type": "polygon", "points": [], "color": "enemy_color"}
            components.append((f"Element {len(components)}", new_comp))
            
        self.set_shape_components(self.active_shape_key, components)
        self.active_component_idx = len(components) - 1
        self.update_components_list()
        self.drawing_area.queue_draw()
        
    def on_delete_component(self, btn):
        components = self.get_shape_components(self.active_shape_key)
        if 0 <= self.active_component_idx < len(components):
            components.pop(self.active_component_idx)
            self.set_shape_components(self.active_shape_key, components)
            self.active_component_idx = max(0, self.active_component_idx - 1)
            self.update_components_list()
            self.drawing_area.queue_draw()
            
    def on_clear_points(self, btn):
        components = self.get_shape_components(self.active_shape_key)
        if 0 <= self.active_component_idx < len(components):
            comp = components[self.active_component_idx][1]
            ctype = comp.get("type", "polygon")
            if ctype == "polygon":
                comp["points"] = []
            elif ctype == "line":
                comp["p1"] = [0.0, 0.0]
                comp["p2"] = [0.0, 0.0]
            elif ctype == "circle":
                comp["center"] = [0.0, 0.0]
                comp["radius"] = 0.1
            self.set_shape_components(self.active_shape_key, components)
            self.drawing_area.queue_draw()

    def reload_configs(self):
        self.load_data_files()
        self.populate_entities_list()
        self.show_info_dialog("Rechargé !", "Tous les fichiers de données ont été actualisés.")

    def on_draw_canvas(self, widget, cr):
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        self.canvas_w = width
        self.canvas_h = height
        
        cx = width / 2
        cy = height / 2
        
        # Draw Weapon Preview if selected
        if self.active_weapon_key:
            self.draw_weapon_animation(cr, cx, cy, width, height)
            return
            
        scale_factor = 8.0 if self.active_shape_key == "player" else 110.0
        
        # Dark Space Background ONLY for Drawing Canvas
        cr.set_source_rgb(0.06, 0.06, 0.09)
        cr.paint()
        
        # Grid lines
        cr.set_source_rgba(0.0, 1.0, 0.8, 0.15)
        cr.set_line_width(0.5)
        grid_step = 20
        for x in range(0, width, grid_step):
            cr.move_to(x, 0)
            cr.line_to(x, height)
            cr.stroke()
        for y in range(0, height, grid_step):
            cr.move_to(0, y)
            cr.line_to(width, y)
            cr.stroke()
            
        # Hitbox guides
        cr.set_source_rgba(1.0, 0.1, 0.1, 0.25)
        cr.set_line_width(1.0)
        cr.set_dash([4.0, 4.0])
        cr.arc(cx, cy, scale_factor, 0, 2 * math.pi)
        cr.stroke()
        cr.set_dash([])
        
        # Center Axes
        cr.set_source_rgba(0.0, 1.0, 0.8, 0.5)
        cr.set_line_width(1.0)
        cr.move_to(cx, 0)
        cr.line_to(cx, height)
        cr.stroke()
        cr.move_to(0, cy)
        cr.line_to(width, cy)
        cr.stroke()
        
        # Draw vector components
        components = self.get_shape_components(self.active_shape_key)
        for idx, (name, comp) in enumerate(components):
            ctype = comp.get("type", "polygon")
            color_val = comp.get("color", "enemy_color")
            
            if color_val == "enemy_color":
                r_c, g_c, b_c = (0.0, 1.0, 0.8) # default preview cyan
            elif isinstance(color_val, list):
                r_c, g_c, b_c = color_val
            else:
                r_c, g_c, b_c = (1.0, 1.0, 1.0)
                
            cr.set_source_rgb(r_c, g_c, b_c)
            cr.set_line_width(2.0 if idx == self.active_component_idx else 1.0)
            
            if ctype == "polygon":
                pts = comp.get("points", [])
                if pts:
                    cr.move_to(cx + pts[0][0] * scale_factor, cy + pts[0][1] * scale_factor)
                    for p in pts[1:]:
                        cr.line_to(cx + p[0] * scale_factor, cy + p[1] * scale_factor)
                    cr.close_path()
                    
                    cr.set_source_rgba(r_c, g_c, b_c, 0.2 if idx == self.active_component_idx else 0.05)
                    cr.fill_preserve()
                    cr.set_source_rgb(r_c, g_c, b_c)
                    cr.stroke()
            elif ctype == "line":
                p1 = comp.get("p1")
                p2 = comp.get("p2")
                if p1 and p2:
                    cr.move_to(cx + p1[0] * scale_factor, cy + p1[1] * scale_factor)
                    cr.line_to(cx + p2[0] * scale_factor, cy + p2[1] * scale_factor)
                    cr.stroke()
            elif ctype == "circle":
                center = comp.get("center", [0.0, 0.0])
                radius = comp.get("radius", 0.2)
                cr.arc(cx + center[0] * scale_factor, cy + center[1] * scale_factor, radius * scale_factor, 0, 2 * math.pi)
                cr.set_source_rgba(r_c, g_c, b_c, 0.1)
                cr.fill_preserve()
                cr.set_source_rgb(r_c, g_c, b_c)
                cr.stroke()
                
        # Draw point handles
        for idx, (name, comp) in enumerate(components):
            is_active = (idx == self.active_component_idx)
            ctype = comp.get("type", "polygon")
            
            pts_handles = []
            if ctype == "polygon":
                pts_handles = comp.get("points", [])
            elif ctype == "line":
                if "p1" in comp: pts_handles.append(comp["p1"])
                if "p2" in comp: pts_handles.append(comp["p2"])
            elif ctype == "circle":
                if "center" in comp: pts_handles.append(comp["center"])
                
            for p_idx, p in enumerate(pts_handles):
                px = cx + p[0] * scale_factor
                py = cy + p[1] * scale_factor
                
                if is_active:
                    cr.set_source_rgb(1.0, 0.65, 0.0) # Amber
                    handle_size = 5.0
                else:
                    cr.set_source_rgb(0.5, 0.5, 0.6) # Gray-Blue
                    handle_size = 3.5
                    
                cr.arc(px, py, handle_size, 0, 2 * math.pi)
                cr.fill()
                cr.set_source_rgb(1.0, 1.0, 1.0)
                cr.set_line_width(1.0)
                cr.arc(px, py, handle_size, 0, 2 * math.pi)
                cr.stroke()

    # --- MOUSE LOGIC ---
    def get_vertex_under_mouse(self, mx, my):
        cx = self.canvas_w / 2
        cy = self.canvas_h / 2
        scale_factor = 8.0 if self.active_shape_key == "player" else 110.0
        
        components = self.get_shape_components(self.active_shape_key)
        for comp_idx, (name, comp) in enumerate(components):
            ctype = comp.get("type", "polygon")
            
            if ctype == "polygon":
                pts = comp.get("points", [])
                for pt_idx, p in enumerate(pts):
                    px = cx + p[0] * scale_factor
                    py = cy + p[1] * scale_factor
                    if math.hypot(mx - px, my - py) < 9.0:
                        return comp_idx, "points", pt_idx
            elif ctype == "line":
                for key in ["p1", "p2"]:
                    if key in comp:
                        p = comp[key]
                        px = cx + p[0] * scale_factor
                        py = cy + p[1] * scale_factor
                        if math.hypot(mx - px, my - py) < 9.0:
                            return comp_idx, key, None
            elif ctype == "circle":
                if "center" in comp:
                    p = comp["center"]
                    px = cx + p[0] * scale_factor
                    py = cy + p[1] * scale_factor
                    if math.hypot(mx - px, my - py) < 9.0:
                        return comp_idx, "center", None
        return None

    def on_canvas_button_press(self, widget, event):
        if event.button == 1:
            target = self.get_vertex_under_mouse(event.x, event.y)
            if target:
                comp_idx, key, pt_idx = target
                self.dragged_vertex = (comp_idx, key, pt_idx)
                self.active_component_idx = comp_idx
                self.update_components_list()
            else:
                # Add point to active component
                cx = self.canvas_w / 2
                cy = self.canvas_h / 2
                scale_factor = 8.0 if self.active_shape_key == "player" else 110.0
                
                local_x = round((event.x - cx) / scale_factor, 3)
                local_y = round((event.y - cy) / scale_factor, 3)
                
                components = self.get_shape_components(self.active_shape_key)
                if components and 0 <= self.active_component_idx < len(components):
                    comp = components[self.active_component_idx][1]
                    ctype = comp.get("type", "polygon")
                    
                    if ctype == "polygon":
                        if "points" not in comp:
                            comp["points"] = []
                        comp["points"].append([local_x, local_y])
                    elif ctype == "line":
                        if "p1" not in comp or comp["p1"] == [0.0, 0.0]:
                            comp["p1"] = [local_x, local_y]
                        else:
                            comp["p2"] = [local_x, local_y]
                    elif ctype == "circle":
                        comp["center"] = [local_x, local_y]
                        
                    self.set_shape_components(self.active_shape_key, components)
                    self.drawing_area.queue_draw()
                    
        elif event.button == 3: # Right Click: pop last point
            components = self.get_shape_components(self.active_shape_key)
            if components and 0 <= self.active_component_idx < len(components):
                comp = components[self.active_component_idx][1]
                ctype = comp.get("type", "polygon")
                if ctype == "polygon" and comp.get("points"):
                    comp["points"].pop()
                elif ctype == "line":
                    comp["p2"] = [0.0, 0.0]
                elif ctype == "circle":
                    comp["center"] = [0.0, 0.0]
                self.set_shape_components(self.active_shape_key, components)
                self.drawing_area.queue_draw()
        return True

    def on_canvas_button_release(self, widget, event):
        if event.button == 1:
            self.dragged_vertex = None
        return True

    def on_canvas_motion_notify(self, widget, event):
        self.mouse_x = event.x
        self.mouse_y = event.y
        
        if self.dragged_vertex and self.active_shape_key:
            comp_idx, key, pt_idx = self.dragged_vertex
            cx = self.canvas_w / 2
            cy = self.canvas_h / 2
            scale_factor = 8.0 if self.active_shape_key == "player" else 110.0
            
            local_x = round((event.x - cx) / scale_factor, 3)
            local_y = round((event.y - cy) / scale_factor, 3)
            
            components = self.get_shape_components(self.active_shape_key)
            comp = components[comp_idx][1]
            
            if key == "points":
                comp["points"][pt_idx] = [local_x, local_y]
            elif key in ["p1", "p2", "center"]:
                comp[key] = [local_x, local_y]
                
            self.set_shape_components(self.active_shape_key, components)
            self.drawing_area.queue_draw()
        return True

    def on_animation_tick(self):
        self.anim_time += 0.016
        if self.active_weapon_key:
            self.update_editor_projectiles(0.016)
        self.drawing_area.queue_draw()
        return True

    def load_weapon_dummy_stats(self, key):
        self.spin_hp.set_value(0.0)
        self.spin_speed.set_value(0.0)
        self.spin_dmg.set_value(0.0)
        self.spin_score.set_value(0)
        self.spin_radius.set_value(0.0)
        self.spin_r.set_value(0.0)
        self.spin_g.set_value(0.0)
        self.spin_b.set_value(0.0)
        
        w_type = key.replace("weapon_", "")
        for idx, text in enumerate(["None", "laser", "missile", "vortex", "blade", "flame", "lightning", "meteor", "carrier_spawner"]):
            if text == w_type:
                self.combo_weapon.set_active(idx)
                break
                
        self.entry_name.set_text(f"Animation de l'arme : {w_type.capitalize()}")
        self.entry_suffixes.set_text("Visualisation")

    def update_editor_projectiles(self, dt):
        cx = self.canvas_w / 2
        cy = self.canvas_h / 2
        
        w_type = self.combo_weapon.get_active_text()
        if not w_type or w_type == "None":
            self.active_projectiles = []
            return
            
        spread = int(self.spin_mod_spread.get_value())
        has_homing = self.chk_mod_homing.get_active()
        homing_force = self.spin_mod_homing.get_value()
        bounces = int(self.spin_mod_bounce.get_value())
        tiny_planet = self.chk_mod_orbit.get_active()
        thickness = int(self.spin_mod_thick.get_value())
        size = self.spin_mod_size.get_value()
        speed_mult = self.spin_mod_speed_mult.get_value()
        
        # Spawn new particles periodically
        self.proj_spawn_timer -= dt
        if self.proj_spawn_timer <= 0.0:
            if w_type == "flame":
                self.proj_spawn_timer = 0.06
            elif w_type == "laser":
                self.proj_spawn_timer = 0.22
            elif w_type == "missile":
                self.proj_spawn_timer = 0.45
            elif w_type == "lightning":
                self.proj_spawn_timer = 0.25
            elif w_type == "meteor":
                self.proj_spawn_timer = 0.35
            else: # carrier_spawner / vortex / blade
                self.proj_spawn_timer = 0.30
                
            dx = self.mouse_x - cx
            dy = self.mouse_y - cy
            base_angle = math.atan2(dy, dx)
            
            count = spread
            for i in range(count):
                if count > 1:
                    angle_offset = (i - (count - 1) / 2.0) * 0.22
                else:
                    angle_offset = 0.0
                proj_angle = base_angle + angle_offset
                
                speed = 280.0
                if w_type == "flame":
                    speed = 180.0
                elif w_type == "meteor":
                    speed = 220.0
                    
                # Apply speed modifier multiplier
                speed *= speed_mult
                vx = math.cos(proj_angle) * speed
                vy = math.sin(proj_angle) * speed
                
                px, py = cx, cy
                if tiny_planet:
                    orbit_r = 90.0
                    px = cx + math.cos(self.anim_time * 3 + i * (2*math.pi/count)) * orbit_r
                    py = cy + math.sin(self.anim_time * 3 + i * (2*math.pi/count)) * orbit_r
                    tang_ang = self.anim_time * 3 + i * (2*math.pi/count) + math.pi/2
                    vx = math.cos(tang_ang) * speed * 0.7
                    vy = math.sin(tang_ang) * speed * 0.7
                    
                self.active_projectiles.append({
                    "x": px, "y": py,
                    "vx": vx, "vy": vy,
                    "life": 1.4 if w_type == "flame" else 2.5,
                    "bounces": bounces,
                    "type": w_type,
                    "thickness": thickness,
                    "size": size,
                    "orbit_angle": self.anim_time * 3 + i * (2*math.pi/count) if tiny_planet else 0.0
                })
                
        alive_projectiles = []
        for p in self.active_projectiles:
            p["life"] -= dt
            if p["life"] <= 0.0:
                continue
                
            if has_homing and not tiny_planet:
                dx = self.mouse_x - p["x"]
                dy = self.mouse_y - p["y"]
                dist = math.hypot(dx, dy)
                if dist > 5.0:
                    tx = (dx / dist) * 280.0
                    ty = (dy / dist) * 280.0
                    steer_rate = homing_force * 3.5 * dt
                    p["vx"] += (tx - p["vx"]) * steer_rate
                    p["vy"] += (ty - p["vy"]) * steer_rate
                    
            if tiny_planet:
                p["orbit_angle"] += 3.0 * dt
                orbit_r = 90.0
                p["x"] = cx + math.cos(p["orbit_angle"]) * orbit_r
                p["y"] = cy + math.sin(p["orbit_angle"]) * orbit_r
            else:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                
            if p["bounces"] > 0 and not tiny_planet:
                b_trig = False
                if p["x"] < 0 or p["x"] > self.canvas_w:
                    p["vx"] = -p["vx"]
                    p["x"] = max(0, min(self.canvas_w, p["x"]))
                    b_trig = True
                if p["y"] < 0 or p["y"] > self.canvas_h:
                    p["vy"] = -p["vy"]
                    p["y"] = max(0, min(self.canvas_h, p["y"]))
                    b_trig = True
                if b_trig:
                    p["bounces"] -= 1
                    
            if 0 <= p["x"] <= self.canvas_w and 0 <= p["y"] <= self.canvas_h:
                alive_projectiles.append(p)
            elif p["bounces"] > 0:
                alive_projectiles.append(p)
                
        self.active_projectiles = alive_projectiles

    def draw_weapon_animation(self, cr, cx, cy, width, height):
        # Grid lines
        cr.set_source_rgba(0.0, 1.0, 0.8, 0.15)
        cr.set_line_width(0.5)
        grid_step = 20
        for x in range(0, width, grid_step):
            cr.move_to(x, 0)
            cr.line_to(x, height)
            cr.stroke()
        for y in range(0, height, grid_step):
            cr.move_to(0, y)
            cr.line_to(width, y)
            cr.stroke()
            
        w_type = self.combo_weapon.get_active_text()
        if not w_type or w_type == "None":
            return
            
        has_homing = self.chk_mod_homing.get_active()
        
        # Center nozzle
        cr.set_source_rgb(0.6, 0.6, 0.7)
        cr.arc(cx, cy, 14, 0, 2*math.pi)
        cr.fill()
        
        # Draw target cursor if homing is active
        if has_homing:
            cr.set_source_rgba(1.0, 0.1, 0.1, 0.5)
            cr.set_line_width(1.5)
            cr.arc(self.mouse_x, self.mouse_y, 8, 0, 2*math.pi)
            cr.stroke()
            cr.move_to(self.mouse_x - 12, self.mouse_y)
            cr.line_to(self.mouse_x + 12, self.mouse_y)
            cr.stroke()
            cr.move_to(self.mouse_x, self.mouse_y - 12)
            cr.line_to(self.mouse_x, self.mouse_y + 12)
            cr.stroke()
            
        # Draw active projectiles simulation
        for p in self.active_projectiles:
            px, py = p["x"], p["y"]
            ptype = p["type"]
            t = int(p.get("thickness", 1))
            size = p.get("size", 1.0)
            
            if ptype == "laser":
                v_len = math.hypot(p["vx"], p["vy"])
                ux = (p["vx"] / v_len) if v_len > 0 else 1.0
                uy = (p["vy"] / v_len) if v_len > 0 else 0.0
                px_dir = -uy
                py_dir = ux
                
                length = 22 * size
                if t <= 1:
                    cr.set_source_rgb(0.1, 0.9, 1.0)
                    cr.set_line_width(4)
                    cr.move_to(px - ux * length, py - uy * length)
                    cr.line_to(px, py)
                    cr.stroke()
                else:
                    step = 0.8
                    cr.set_source_rgb(0.1, 0.9, 1.0)
                    cr.set_line_width(2.5)
                    for k in range(t):
                        offset = k - (t - 1) / 2.0
                        ox = px_dir * offset * step
                        oy = py_dir * offset * step
                        cr.move_to((px + ox) - ux * length, (py + oy) - uy * length)
                        cr.line_to(px + ox, py + oy)
                        cr.stroke()
            elif ptype == "missile":
                v_len = math.hypot(p["vx"], p["vy"])
                if v_len > 0:
                    cos_t = p["vx"] / v_len
                    sin_t = p["vy"] / v_len
                else:
                    cos_t, sin_t = 1.0, 0.0
                    
                cr.set_source_rgb(1.0, 0.45, 0.1)
                cr.set_line_width(1.5)
                # scale missile points by size
                r_pts = [(12 * size, 0), (-8 * size, -5 * size), (-5 * size, 0), (-8 * size, 5 * size)]
                cr.move_to(px + r_pts[0][0]*cos_t - r_pts[0][1]*sin_t, py + r_pts[0][0]*sin_t + r_pts[0][1]*cos_t)
                for px_o, py_o in r_pts[1:]:
                    cr.line_to(px + px_o*cos_t - py_o*sin_t, py + px_o*sin_t + py_o*cos_t)
                cr.close_path()
                cr.stroke()
                
                # tail flame particle
                cr.set_source_rgb(1.0, 0.8, 0.0)
                cr.arc(px - 10 * size * cos_t, py - 10 * size * sin_t, 3 * size, 0, 2*math.pi)
                cr.fill()
                
            elif ptype == "vortex":
                cr.set_source_rgb(0.8, 0.2, 1.0)
                cr.set_line_width(1.5)
                cr.arc(px, py, (10 + 4*math.sin(self.anim_time*15)) * size, 0, 2*math.pi)
                cr.stroke()
                
            elif ptype == "blade":
                b_ang = self.anim_time * 8
                b_cos = math.cos(b_ang)
                b_sin = math.sin(b_ang)
                
                cr.set_source_rgb(1.0, 0.8, 0.0)
                cr.set_line_width(1.5)
                # scale blade points by size
                b_pts = [(12 * size, 0), (-6 * size, -4 * size), (-3 * size, 0), (-6 * size, 4 * size)]
                cr.move_to(px + b_pts[0][0]*b_cos - b_pts[0][1]*b_sin, py + b_pts[0][0]*b_sin + b_pts[0][1]*b_cos)
                for px_o, py_o in b_pts[1:]:
                    cr.line_to(px + px_o*b_cos - py_o*b_sin, py + px_o*b_sin + py_o*b_cos)
                cr.close_path()
                cr.stroke()
                
            elif ptype == "flame":
                t_fade = p["life"] / 1.4
                alpha = max(0.0, t_fade)
                cr.set_source_rgba(1.0, max(0.0, t_fade - 0.25), 0.0, alpha)
                cr.arc(px, py, (1.4 - t_fade) * 22 * size, 0, 2*math.pi)
                cr.fill()
                
            elif ptype == "lightning":
                # Jagged lightning simulation supporting thickness offsets
                cr.set_source_rgb(0.3, 0.8, 1.0)
                cr.set_line_width(1.5)
                
                # build a random lightning path segments first
                steps = 5
                pts = [(cx, cy)]
                random.seed(int(p["life"] * 100))
                for step in range(steps):
                    t_f = (step + 1) / steps
                    target_x = cx + (px - cx) * t_f
                    target_y = cy + (py - cy) * t_f
                    if step < steps - 1:
                        lx = target_x + random.uniform(-15, 15)
                        ly = target_y + random.uniform(-15, 15)
                    else:
                        lx, ly = px, py
                    pts.append((lx, ly))
                    
                if t <= 1:
                    cr.move_to(cx, cy)
                    for lx, ly in pts[1:]:
                        cr.line_to(lx, ly)
                    cr.stroke()
                else:
                    # Draw parallel lightning lines
                    step_val = 0.8
                    dist = math.hypot(px - cx, py - cy)
                    if dist > 0:
                        px_dir = -(py - cy) / dist
                        py_dir = (px - cx) / dist
                        for k in range(t):
                            offset = k - (t - 1) / 2.0
                            ox = px_dir * offset * step_val
                            oy = py_dir * offset * step_val
                            cr.move_to(cx + ox, cy + oy)
                            for lx, ly in pts[1:]:
                                cr.line_to(lx + ox, ly + oy)
                            cr.stroke()
                
            elif ptype == "meteor":
                cr.set_source_rgb(0.7, 0.35, 0.25)
                cr.set_line_width(2.0)
                cr.arc(px, py, 14 * size, 0, 2*math.pi)
                cr.stroke()
                
                cr.set_source_rgb(1.0, 0.3, 0.0)
                cr.arc(px - 8 * size, py - 8 * size, 4 * size, 0, 2*math.pi)
                cr.fill()
                
            elif ptype == "carrier_spawner":
                cr.set_source_rgb(1.0, 0.0, 0.5)
                cr.set_line_width(1.2)
                cr.arc(px, py, 6 * size, 0, 2*math.pi)
                cr.stroke()


if __name__ == "__main__":
    win = DevkitEditorWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
