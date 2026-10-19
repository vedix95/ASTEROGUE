# scripts/generate_pdf.py
import os
import math
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def build_pdf():
    pdf_filename = "Vector_Survivor_Catalog.pdf"
    
    # Setup document
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=colors.HexColor('#0F172A'),
        alignment=1, # Center
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=40
    )
    
    h1_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'SubsectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )

    caption_style = ParagraphStyle(
        'CaptionStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#64748B'),
        alignment=1,
        spaceAfter=15
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#334155')
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#0F172A')
    )

    story = []
    
    # Path to generated images (located in artifact folder)
    img_dir = "/home/vedix/.gemini/antigravity-cli/brain/0fdb01d2-fc9b-4732-af0e-054d52b5857e"
    laser_img_path = os.path.join(img_dir, "weapon_laser_blaster_1783678270621.jpg")
    rail_img_path = os.path.join(img_dir, "weapon_piercing_rail_1783678285570.jpg")
    missile_img_path = os.path.join(img_dir, "weapon_seeker_missile_1783678296670.jpg")
    boss_img_path = os.path.join(img_dir, "boss_dreadnought_1783678311405.jpg")

    # ==========================================
    # PAGE 1: COVER
    # ==========================================
    story.append(Spacer(1, 100))
    story.append(Paragraph("VECTOR SURVIVOR", title_style))
    story.append(Paragraph("SYSTEM UPGRADES & TACTICAL CATALOG", subtitle_style))
    story.append(Spacer(1, 20))
    
    # Add Cover Art (Dreadnought)
    if os.path.exists(boss_img_path):
        story.append(Image(boss_img_path, width=3.5*inch, height=3.5*inch))
        story.append(Paragraph("Tactical Scan: Class-V Star Destroyer Boss", caption_style))
    
    story.append(Spacer(1, 40))
    story.append(Paragraph("Author: Antigravity AI Subsystem Manager", caption_style))
    story.append(Paragraph("Classification: Top Secret // Deep Space Sector 4", caption_style))
    story.append(PageBreak())

    # ==========================================
    # PAGE 2: PRIMARY WEAPONS
    # ==========================================
    story.append(Paragraph("1. Primary Weapons", h1_style))
    story.append(Paragraph(
        "Primary weapons represent the central offense capability of the ship. Only exactly 1 primary weapon can be active at a time. "
        "Unlocking a new primary weapon replaces the old one but carries over its level. All damage scales with player's damage multipliers.",
        body_style
    ))
    story.append(Spacer(1, 10))

    # Laser Weapon Description & Image Inline
    weapons_data = [
        ("AUTO-LASER", "Fires fast green energy bolts at the closest enemy targets.", 
         "10", "45", "0.8s", "0.4s", "Power Rating: 7/10\nSynergy: High (multishot + homing)"),
        ("PIERCING RAIL", "Fires a devastating, instantaneous piercing beam in moving/facing direction.", 
         "35", "180", "2.2s", "1.2s", "Power Rating: 9/10\nSynergy: Med (multishot cone)"),
        ("SHOCKWAVE", "Creates expanding force fields that push back and damage all nearby threats.", 
         "20", "95", "4.0s", "2.0s", "Power Rating: 8/10\nSynergy: High (size modifier)"),
        ("FLAME THROWER", "Fires a continuous, rapid-firing cone of short-range fire particles.", 
         "5", "20", "0.1s", "0.06s", "Power Rating: 8.5/10\nSynergy: High (size + pierce)"),
        ("VORTEX GRENADE", "Lobs gravitational bombs that pull enemies in before detonating and splitting.", 
         "35", "150", "2.4s", "1.5s", "Power Rating: 9.5/10\nSynergy: Extreme (size + splits)"),
        ("SPIRAL BLADES", "Launches sawblades that spiral outwards from the ship, shredding all targets.", 
         "15", "60", "1.6s", "0.8s", "Power Rating: 9/10\nSynergy: High (bounces + size)"),
        ("SEEKER MISSILE", "Fires rockets that actively steer towards enemies and explode on contact.", 
         "28", "100", "1.5s", "0.9s", "Power Rating: 9.5/10\nSynergy: Extreme (homing + splash)"),
        ("SCYTHE SLASH", "Swings a massive energy scythe in front of the ship, dealing massive knockback.", 
         "45", "200", "1.5s", "0.9s", "Power Rating: 8.5/10\nSynergy: Med (size + speed)")
    ]

    # Build Weapons Table
    table_data = [[
        Paragraph("Weapon Name", table_header_style),
        Paragraph("Description", table_header_style),
        Paragraph("Dmg (Lvl 1)", table_header_style),
        Paragraph("Dmg (Lvl 8)", table_header_style),
        Paragraph("CD (Lvl 1)", table_header_style),
        Paragraph("CD (Lvl 8)", table_header_style),
        Paragraph("Tactical Notes", table_header_style)
    ]]

    for name, desc, d1, d8, c1, c8, notes in weapons_data:
        table_data.append([
            Paragraph(name, table_cell_bold),
            Paragraph(desc, table_cell_style),
            Paragraph(d1, table_cell_style),
            Paragraph(d8, table_cell_style),
            Paragraph(c1, table_cell_style),
            Paragraph(c8, table_cell_style),
            Paragraph(notes.replace('\n', '<br/>'), table_cell_style)
        ])

    weapons_table = Table(table_data, colWidths=[1.1*inch, 1.8*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.6*inch, 1.7*inch])
    weapons_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))

    story.append(weapons_table)
    story.append(Spacer(1, 20))

    # Add weapon showcase side-by-side
    showcase = []
    if os.path.exists(laser_img_path):
        showcase.append(Image(laser_img_path, width=1.8*inch, height=1.8*inch))
    if os.path.exists(rail_img_path):
        showcase.append(Image(rail_img_path, width=1.8*inch, height=1.8*inch))
    if os.path.exists(missile_img_path):
        showcase.append(Image(missile_img_path, width=1.8*inch, height=1.8*inch))

    if showcase:
        # Wrap images in a layout table
        img_table = Table([showcase], colWidths=[2.2*inch]*len(showcase))
        img_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
        ]))
        story.append(img_table)
        story.append(Paragraph("Visual Scans: Auto-Laser, Piercing Rail, and Seeker Missile", caption_style))

    story.append(PageBreak())

    # ==========================================
    # PAGE 3: ACCESSORIES
    # ==========================================
    story.append(Paragraph("2. Orbiting Accessories (Drones)", h1_style))
    story.append(Paragraph(
        "Accessories are autonomous orbital sub-modules that orbit the ship. The player can equip up to 4 accessories at the same time. "
        "They fire or defend automatically and their radius scales with projectile speed and size modifiers.",
        body_style
    ))
    story.append(Spacer(1, 10))

    accessories_data = [
        ("ORBIT SHIELD", "Creates orbiting shield nodes that block threats and deal continuous damage.", 
         "12 / node", "42 / node", "1 node", "6 nodes", "DPS Shield barrier"),
        ("LASER DRONE", "A small tactical drone shooting lasers at nearby targets.", 
         "8", "40", "1.2s", "0.45s", "Reliable single-target support"),
        ("ROCKET DRONE", "Fires miniature homing missiles that explode with splash damage.", 
         "20", "95", "2.2s", "1.1s", "High damage area control"),
        ("BLACK HOLE", "Orbits player, creating gravitational fields that pull and damage enemies.", 
         "10 / tick", "48 / tick", "130px", "240px", "Excellent crowd control"),
        ("LIGHTNING COIL", "Periodically fires chain-lightning zapping and jumping between enemies.", 
         "25", "110", "3 jumps", "8 jumps", "Clears large crowds instantly"),
        ("HEAL DRONE", "Heals player hull integrity periodically and provides flat passive regen boost.", 
         "5 HP", "40 HP", "5.0s", "2.4s", "Vital for long-term survival")
    ]

    acc_table_data = [[
        Paragraph("Accessory Name", table_header_style),
        Paragraph("Description", table_header_style),
        Paragraph("Dmg (Lvl 1)", table_header_style),
        Paragraph("Dmg (Lvl 8)", table_header_style),
        Paragraph("Stat 1 (L1)", table_header_style),
        Paragraph("Stat 2 (L8)", table_header_style),
        Paragraph("Uplink Utility", table_header_style)
    ]]

    for name, desc, d1, d8, s1, s8, utility in accessories_data:
        acc_table_data.append([
            Paragraph(name, table_cell_bold),
            Paragraph(desc, table_cell_style),
            Paragraph(d1, table_cell_style),
            Paragraph(d8, table_cell_style),
            Paragraph(s1, table_cell_style),
            Paragraph(s8, table_cell_style),
            Paragraph(utility, table_cell_style)
        ])

    acc_table = Table(acc_table_data, colWidths=[1.2*inch, 1.8*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.8*inch, 1.0*inch])
    acc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))

    story.append(acc_table)
    story.append(Spacer(1, 25))

    # ==========================================
    # PASSIVES & ISSAC SYNERGIES
    # ==========================================
    story.append(Paragraph("3. Passive Items & Projectile Synergies", h1_style))
    story.append(Paragraph(
        "Passives are system upgrades that alter stats or projectile physics. Up to 6 passives can be equipped. "
        "Isaac-style passives completely change projectile behaviors, generating powerful combo synergies.",
        body_style
    ))
    story.append(Spacer(1, 10))

    passives_data = [
        ("THRUSTERS", "Stat Booster", "Increases ship movement speed by +10% per level (Max Lvl 5 / +50%)."),
        ("NANO-ARMOR", "Stat Booster", "Grants +2 flat damage reduction on hull hit per level (Max Lvl 5 / +10)."),
        ("XP MAGNET", "Stat Booster", "Increases experience pickup magnetic range by +25% per level (Max Lvl 5 / +125%)."),
        ("OVERDRIVE CORE", "Stat Booster", "Increases all weapon damage output by +15% per level (Max Lvl 5 / +75%)."),
        ("REPAIR DRONES", "Stat Booster", "Passively regenerates +1.0 HP per second per level (Max Lvl 5 / +5.0 HP/s)."),
        ("HULL UPGRADE", "Stat Booster", "Increases max health limit by +20 and heals +20 HP per level (Max Lvl 5 / +100 HP)."),
        ("GIANT CELLS", "Tear Modifier", "Increases projectile size by +20% and damage by +10% per level. Synergizes with all weapons."),
        ("HYPER DRIVE", "Tear Modifier", "Increases projectile speed by +20% and decreases reload cooldowns by -10% per level."),
        ("SPLIT FIRE", "Tear Modifier", "Adds +1 extra projectile shot per level, but slightly decreases individual bullet damage by -12%."),
        ("SMART TARGETING", "Tear Modifier", "Bends laser and missile trajectories towards active targets. Homing strength grows by +1.5 per level."),
        ("BOUNCING MATRIX", "Tear Modifier", "Projectiles bounce off the camera/viewport edges rather than expiring (+1 bounce per level)."),
        ("DRILL TIP", "Tear Modifier", "Projectiles gain piercing and cut through +1 additional enemy target per level."),
        ("SHRAPNEL SHELLS", "Tear Modifier", "Projectiles split into two smaller perpendicular shrapnels upon collision or expiration.")
    ]

    pass_table_data = [[
        Paragraph("Passive System", table_header_style),
        Paragraph("Upgrade Type", table_header_style),
        Paragraph("Upgrade Mechanics & Synergy Impact", table_header_style)
    ]]

    for name, utype, mech in passives_data:
        pass_table_data.append([
            Paragraph(name, table_cell_bold),
            Paragraph(utype, table_cell_style),
            Paragraph(mech, table_cell_style)
        ])

    pass_table = Table(pass_table_data, colWidths=[1.5*inch, 1.2*inch, 4.3*inch])
    pass_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))

    story.append(pass_table)
    story.append(PageBreak())

    # ==========================================
    # PAGE 4: ENEMIES, BOSSES & DRG MISSIONS
    # ==========================================
    story.append(Paragraph("4. Procedural Threats, Bosses & Operations", h1_style))
    story.append(Paragraph(
        "Space sectors are heavily guarded by hostile alien vector ships. Enemies scale in difficulty based on waves and wave multipliers. "
        "Deep Rock Galactic-style objectives must be secured to successfully extract from the sector.",
        body_style
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Enemy Prefix Modifiers (Stat variations)", h2_style))
    
    enemies_info = [
        ("Void", "Purple", "health +35%, speed -15%", "Sturdy armor shields"),
        ("Solar", "Amber", "speed +20%, damage +20%", "High thermal output"),
        ("Quantum", "Cyan", "radius -20%, speed +35%, health -20%", "Evasive subatomic gliders"),
        ("Spectral", "Faint Blue", "health -25%, speed +15%", "Semi-corporeal phantoms"),
        ("Magnetic", "Neon Green", "damage +30%", "Disrupts shielding"),
        ("Plasma", "Deep Red", "damage +45%, health -10%", "Fires superheated energy"),
        ("Nova", "White", "radius +25%, health +25%", "Large exploding cores"),
        ("Glitch", "Magenta", "speed +20%, damage +20%", "Erratic phasing movements"),
        ("Abyssal", "Dark Violet", "health +50%, speed -20%, radius +20%", "Colossal deep space leviathans")
    ]

    enemy_table_data = [[
        Paragraph("Prefix Class", table_header_style),
        Paragraph("Vector Color", table_header_style),
        Paragraph("Stat Modifier Details", table_header_style),
        Paragraph("Threat Assessment", table_header_style)
    ]]

    for prefix, color, stats, assessment in enemies_info:
        enemy_table_data.append([
            Paragraph(prefix, table_cell_bold),
            Paragraph(color, table_cell_style),
            Paragraph(stats, table_cell_style),
            Paragraph(assessment, table_cell_style)
        ])

    enemy_table = Table(enemy_table_data, colWidths=[1.2*inch, 1.2*inch, 2.4*inch, 2.2*inch])
    enemy_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(enemy_table)
    story.append(Spacer(1, 15))

    story.append(Paragraph("Deep Rock Galactic-style Objectives", h2_style))
    story.append(Paragraph(
        "Each mission draws a primary objective in the sector space: <br/>"
        "1. <b>Mine Astraea Crystals</b>: Locate and harvest 35 purple space crystals. <br/>"
        "2. <b>Recover Nebula Eggs</b>: Collect 5 organic green pods guarded by heavy alien squads. <br/>"
        "3. <b>Secure Space Uplinks</b>: Stand inside 3 beacons and defend the zone until 100%. "
        "Securing a beacon fires an EMP Shockwave that disintegrates nearby enemies. <br/>"
        "<i>Reward: Completing the objective awards +500 XP and fully repairs the ship hull structure.</i>",
        body_style
    ))
    
    # Build Document
    doc.build(story)
    print(f"PDF Successfully generated at: {pdf_filename}")

if __name__ == "__main__":
    build_pdf()
