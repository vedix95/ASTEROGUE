# scripts/generate_synergies_pdf.py
import os
import math
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle, Group

class NumberedCanvas(canvas.Canvas):
    """
    Custom canvas that performs two-pass rendering to dynamically compute
    the total page count, and draws custom headers and footers on all pages
    except the cover page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Draw beautiful border on Cover Page
            self.saveState()
            self.setStrokeColor(colors.HexColor('#10B981')) # Emerald green
            self.setLineWidth(2)
            self.rect(20, 20, 572, 752)
            
            # Inner double border
            self.setStrokeColor(colors.HexColor('#1E293B'))
            self.setLineWidth(0.5)
            self.rect(25, 25, 562, 742)
            self.restoreState()
            return
            
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor('#64748B')) # Slate gray
        
        # Draw Header
        self.drawString(40, 755, "ASTEROGUE — GUIDE TECHNIQUE DE SYNERGIES & D'OPTIMISATION")
        self.setStrokeColor(colors.HexColor('#E2E8F0'))
        self.setLineWidth(0.5)
        self.line(40, 747, 572, 747)
        
        # Draw Footer
        page_text = f"Page {self._pageNumber} sur {page_count}"
        self.drawRightString(572, 30, page_text)
        self.drawString(40, 30, "CLASSIFICATION : TACTIQUE // DÉFENSE STELLAIRE DE HAUT NIVEAU")
        self.line(40, 40, 572, 40)
        self.restoreState()

def create_skill_tree_drawing():
    """
    Creates a visual flowchart representing the skill tree branches
    using ReportLab graphics.
    """
    d = Drawing(532, 160)
    
    # Background card
    d.add(Rect(0, 0, 532, 160, fillColor=colors.HexColor('#F8FAFC'), strokeColor=colors.HexColor('#E2E8F0'), strokeWidth=1, rx=5, ry=5))
    
    # Root Node: Player Ship
    d.add(Rect(216, 115, 100, 30, fillColor=colors.HexColor('#0F172A'), strokeColor=colors.HexColor('#10B981'), strokeWidth=1.5, rx=3, ry=3))
    d.add(String(266, 126, "VAISSEAU (Noyau)", fontName="Helvetica-Bold", fontSize=8, textAnchor="middle", fillColor=colors.white))
    
    # Three Branches Nodes
    # 1. Offensive Branch
    d.add(Rect(20, 20, 140, 45, fillColor=colors.HexColor('#1E293B'), strokeColor=colors.HexColor('#F43F5E'), strokeWidth=1, rx=3, ry=3))
    d.add(String(90, 46, "BRANCHE OFFENSIVE", fontName="Helvetica-Bold", fontSize=8, textAnchor="middle", fillColor=colors.HexColor('#F43F5E')))
    d.add(String(90, 34, "8 Armes (Max Lvl 8)", fontName="Helvetica", fontSize=7, textAnchor="middle", fillColor=colors.HexColor('#94A3B8')))
    d.add(String(90, 24, "Projectiles, Rail, Grenades", fontName="Helvetica-Oblique", fontSize=6, textAnchor="middle", fillColor=colors.HexColor('#64748B')))
    
    # 2. Tactical Branch (Drones)
    d.add(Rect(196, 20, 140, 45, fillColor=colors.HexColor('#1E293B'), strokeColor=colors.HexColor('#3B82F6'), strokeWidth=1, rx=3, ry=3))
    d.add(String(266, 46, "BRANCHE TACTIQUE", fontName="Helvetica-Bold", fontSize=8, textAnchor="middle", fillColor=colors.HexColor('#3B82F6')))
    d.add(String(266, 34, "6 Drones (Max Lvl 8)", fontName="Helvetica", fontSize=7, textAnchor="middle", fillColor=colors.HexColor('#94A3B8')))
    d.add(String(266, 24, "Bouclier, Laser, Roquettes", fontName="Helvetica-Oblique", fontSize=6, textAnchor="middle", fillColor=colors.HexColor('#64748B')))

    # 3. Synergy Branch (Passives)
    d.add(Rect(372, 20, 140, 45, fillColor=colors.HexColor('#1E293B'), strokeColor=colors.HexColor('#10B981'), strokeWidth=1, rx=3, ry=3))
    d.add(String(442, 46, "BRANCHE SYNERGIQUE", fontName="Helvetica-Bold", fontSize=8, textAnchor="middle", fillColor=colors.HexColor('#10B981')))
    d.add(String(442, 34, "16 Passifs (Max Lvl 5)", fontName="Helvetica", fontSize=7, textAnchor="middle", fillColor=colors.HexColor('#94A3B8')))
    d.add(String(442, 24, "Stats & Projectile Modifiers", fontName="Helvetica-Oblique", fontSize=6, textAnchor="middle", fillColor=colors.HexColor('#64748B')))

    # Connection Lines
    # Root to Center Fork
    d.add(Line(266, 115, 266, 90, strokeColor=colors.HexColor('#CBD5E1'), strokeWidth=1.5))
    # Horizontal bar
    d.add(Line(90, 90, 442, 90, strokeColor=colors.HexColor('#CBD5E1'), strokeWidth=1.5))
    # Dropdowns to branches
    d.add(Line(90, 90, 90, 65, strokeColor=colors.HexColor('#CBD5E1'), strokeWidth=1.5))
    d.add(Line(266, 90, 266, 65, strokeColor=colors.HexColor('#CBD5E1'), strokeWidth=1.5))
    d.add(Line(442, 90, 442, 65, strokeColor=colors.HexColor('#CBD5E1'), strokeWidth=1.5))
    
    return d

def build_pdf():
    pdf_filename = "Asterogue_Guide_Synergies.pdf"
    
    # Setup document
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=70,  # High margin to prevent overlapping with headers
        bottomMargin=60 # Prevent overlapping with footers
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor('#0F172A') # Slate 900 (deep navy)
    c_secondary = colors.HexColor('#1E293B') # Slate 800 (navy)
    c_accent = colors.HexColor('#10B981') # Emerald green (cyber vector vibe)
    c_text = colors.HexColor('#334155') # Slate 700
    c_muted = colors.HexColor('#64748B') # Slate 500
    c_card_bg = colors.HexColor('#F8FAFC') # Slate 50
    c_border = colors.HexColor('#E2E8F0') # Slate 200
    
    # Text Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=c_primary,
        alignment=1, # Center
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=c_muted,
        alignment=1,
        spaceAfter=40
    )
    
    h1_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=10,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'SubsectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=c_secondary,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=c_text,
        spaceAfter=8
    )

    italic_style = ParagraphStyle(
        'ItalicTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=c_muted,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=body_style,
        leftIndent=15,
        bulletIndent=5,
        spaceAfter=4
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=c_text
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=c_primary
    )

    table_cell_accent = ParagraphStyle(
        'TableCellAccent',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor('#059669') # Dark Emerald
    )

    story = []
    
    # ==========================================
    # PAGE 1: PAGE DE GARDE
    # ==========================================
    story.append(Spacer(1, 140))
    
    # Decorative Header line
    cover_line_d = Drawing(532, 10)
    cover_line_d.add(Rect(0, 4, 532, 4, fillColor=c_accent, strokeColor=None))
    story.append(cover_line_d)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("ASTEROGUE", title_style))
    story.append(Paragraph("MANUEL TACTIQUE DES SYNERGIES & DE L'ARBRE DE COMPÉTENCES", subtitle_style))
    
    story.append(Spacer(1, 15))
    story.append(cover_line_d)
    story.append(Spacer(1, 80))
    
    # Center Card details
    cover_details = [
        [Paragraph("Classification :", table_cell_bold), Paragraph("CONFIDENTIEL // DÉFENSE SECTEUR ASTRÉ", table_cell_style)],
        [Paragraph("Auteur :", table_cell_bold), Paragraph("Assistant Tactique Antigravity v3.5", table_cell_style)],
        [Paragraph("Objet :", table_cell_bold), Paragraph("Optimisation mathématique des builds de combat", table_cell_style)],
        [Paragraph("Version du Jeu :", table_cell_bold), Paragraph("Asterogue v1.0 - Édition Vectorielle", table_cell_style)]
    ]
    details_table = Table(cover_details, colWidths=[2.0*inch, 3.0*inch])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_card_bg),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    
    story.append(details_table)
    story.append(PageBreak())

    # ==========================================
    # PAGE 2: STRUCTURATION DU CHROME-PONT
    # ==========================================
    story.append(Paragraph("1. Structuration du Chrome-Pont & Slots d'Équipement", h1_style))
    story.append(Paragraph(
        "Dans <i>Asterogue</i>, la coque du chasseur dispose de connecteurs d'interface matériels "
        "limités. Pour optimiser un build de combat, le pilote doit composer avec les contraintes "
        "systémiques suivantes :",
        body_style
    ))
    
    story.append(Paragraph("<b>• Slots Offensifs (Armes Principales) : Maximum 4</b>", bullet_style))
    story.append(Paragraph(
        "Le pilote peut installer jusqu'à 4 systèmes d'armes principaux en parallèle. À chaque montée de niveau, "
        "si un nouvel emplacement est disponible, le système d'upgrade propose d'installer une nouvelle arme "
        "(parmi 8 possibles). Installer une nouvelle arme remplace l'arme précédente si les slots sont pleins, "
        "mais conserve son niveau d'amélioration. Chaque arme évolue jusqu'au niveau 8.",
        body_style
    ))
    
    story.append(Paragraph("<b>• Slots Tactiques (Accessoires de Drones) : Maximum 4</b>", bullet_style))
    story.append(Paragraph(
        "Les accessoires sont des unités orbitales autonomes qui patrouillent autour du navire (drones d'assaut, boucliers "
        "de défense, bobines Tesla, etc.). Le pilote peut en équiper jusqu'à 4 simultanément (parmi 6 possibles). "
        "Comme les armes, ils évoluent jusqu'au niveau 8.",
        body_style
    ))
    
    story.append(Paragraph("<b>• Slots Synergétiques (Modules Passifs) : Maximum 6</b>", bullet_style))
    story.append(Paragraph(
        "Les modules passifs (16 au total) sont des modifications logicielles et matérielles du noyau. Ils sont "
        "divisés en deux catégories : les <i>Stat Boosters</i> (vitesse, blindage fixe, aimant, régénération, santé) "
        "et les <i>Tear Modifiers</i> (attrapant directement la physique des projectiles : taille, division, rebond, perforation, "
        "guidage). Les passifs peuvent être améliorés jusqu'au niveau 5.",
        body_style
    ))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph("Mécanique d'Apparition du Pool d'Upgrade", h2_style))
    story.append(Paragraph(
        "À chaque gain de niveau, le jeu génère un pool aléatoire de 3 choix d'upgrades. Le pool combine "
        "les déverrouillages d'armes, les améliorations d'armes existantes, et les modules passifs. "
        "Pour favoriser la spécialisation, le jeu limite l'apparition de déverrouillages d'armes/accessoires à "
        "<b>un seul par pool maximum</b> (avec 45% de chance). Si le joueur a déjà maximisé toutes ses armes et passifs, "
        "une option de secours unique apparaît : <i>Réparation Initialisée</i> (+30 PV à la coque). Une planification "
        "stricte des choix d'upgrades est donc indispensable pour ne pas diluer la puissance offensive.",
        body_style
    ))
    
    story.append(PageBreak())

    # ==========================================
    # PAGE 3: L'ARBRE DE COMPÉTENCES CONCEPTUEL
    # ==========================================
    story.append(Paragraph("2. L'Arbre de Compétences Conceptuel", h1_style))
    story.append(Paragraph(
        "Bien que les choix soient présentés dynamiquement au joueur, ils s'organisent selon "
        "trois branches interconnectées. Ce diagramme structure la hiérarchie de l'équipement :",
        body_style
    ))
    story.append(Spacer(1, 10))
    
    # Add drawing
    story.append(create_skill_tree_drawing())
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("Branches de l'Arbre & Potentiels d'Optimisation", h2_style))
    story.append(Paragraph(
        "Chaque branche interagit directement avec les autres à travers le processeur du joueur. "
        "Par exemple, un projectile tiré par une arme de la <b>Branche Offensive</b> héritera instantanément de tous "
        "les modificateurs appliqués par la <b>Branche Synergique</b> (perforation, taille, division). "
        "De la même manière, les drones de la <b>Branche Tactique</b> sont affectés par les modificateurs de vitesse "
        "et de taille de projectiles de la branche synergique, augmentant le rayon de leur orbite et la zone "
        "d'action de leurs tirs.",
        body_style
    ))
    
    story.append(Paragraph(
        "Optimiser son build consiste à choisir des passifs de la Branche Synergique qui démultiplient "
        "de manière multiplicative (et non additive) l'efficacité des tirs des branches Offensive et Tactique. "
        "Le chapitre suivant détaille précisément ces interactions.",
        body_style
    ))
    
    story.append(PageBreak())

    # ==========================================
    # PAGE 4: MATRICE DES SYNERGIES D'ARMES (OFFENSIVE)
    # ==========================================
    story.append(Paragraph("3. Matrice des Synergies : Armes Principales", h1_style))
    story.append(Paragraph(
        "Ce tableau liste les 8 armes offensives de l'arbre et identifie les passifs qui optimisent "
        "radicalement leurs performances physiques et de dégâts.",
        body_style
    ))
    story.append(Spacer(1, 5))

    # Weapons table data
    weapons_matrix = [
        ("AUTO-LASER", "TIR DIVISE, VISEE INTELLIGENTE, OBUS SHRAPNEL, MATRICE REBONDISSANTE",
         "La visée intelligente corrige l'imprécision du Tir Divisé. Les shrapnels créés à l'impact rebondissent sur les bords de l'écran, saturant la zone."),
        
        ("CANON ELECTROMAGNETIQUE", "TIR DIVISE, HYPER-PROPULSION, FOREUSE DE BLINDAGE, COEUR PLASMA",
         "Tire plusieurs rayons transperçant tout l'écran. La taille accrue (Cœur Plasma) élargit le rayon d'impact. L'Hyper-propulsion augmente la portée effective (la longueur du laser dépendant de la vitesse de projectile)."),
         
        ("ONDE DE CHOC", "CELLULES GEANTES, COEUR PLASMA, NOYAU DE SURCHARGE, HYPER-PROPULSION",
         "Le rayon de l'onde de choc s'étend avec la taille de projectile (jusqu'à +125% avec les passifs cumulés). L'Hyper-propulsion augmente la force de recul (push) appliquée aux ennemis de 20%."),
         
        ("LANCE-FLAMMES", "CELLULES GEANTES, FOREUSE DE BLINDAGE, COEUR PLASMA, TIR DIVISE",
         "Crée un immense cône de flammes persistant qui traverse tous les ennemis (Foreuse de blindage). Le Tir Divisé ajoute des jets de flamme sans altérer le flux continu."),
         
        ("GRENADE VORTEX", "CELLULES GEANTES, OBUS SHRAPNEL, MATRICE REBONDISSANTE, COEUR PLASMA",
         "Les bombes gravitationnelles ont un rayon d'attraction géant et se divisent en lasers à leur explosion (Shrapnel). Les lasers générés héritent du rebond."),
         
        ("LAMES SPIRALES", "CELLULES GEANTES, MATRICE REBONDISSANTE, HYPER-PROPULSION, COEUR PLASMA",
         "Les scies s'étendent beaucoup plus loin et plus vite (Hyper-propulsion). Au lieu de disparaître en bout de course, elles rebondissent sur les bords d'écran."),
         
        ("MISSILE TETE CHERCHEUSE", "TIR DIVISE, OBUS SHRAPNEL, CELLULES GEANTES, NOYAU DE SURCHARGE",
         "Déclenche une pluie de roquettes lourdes autoguidées. À l'impact, chaque roquette explose (dégâts de zone accrus) et se sépare en mini-roquettes (Shrapnel)."),
         
        ("COUP DE FAUX", "CELLULES GEANTES, NOYAU DE SURCHARGE, HYPER-PROPULSION, COEUR PLASMA",
         "Augmente considérablement la portée de la faux en arc de cercle en face du vaisseau, formant une barrière de recul impénétrable idéale pour les builds défensifs.")
    ]

    w_table_data = [[
        Paragraph("Arme Principale", table_header_style),
        Paragraph("Passifs Recommandés (Synergies Fortes)", table_header_style),
        Paragraph("Analyse Mécanique de l'Optimisation", table_header_style)
    ]]

    for name, passives, desc in weapons_matrix:
        w_table_data.append([
            Paragraph(name, table_cell_bold),
            Paragraph(passives, table_cell_accent),
            Paragraph(desc, table_cell_style)
        ])

    w_table = Table(w_table_data, colWidths=[1.3*inch, 1.9*inch, 4.2*inch])
    w_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_card_bg])
    ]))

    story.append(w_table)
    story.append(PageBreak())

    # ==========================================
    # PAGE 5: MATRICE DES SYNERGIES D'ACCESSOIRES (DRONES)
    # ==========================================
    story.append(Paragraph("4. Matrice des Synergies : Accessoires (Drones)", h1_style))
    story.append(Paragraph(
        "Ce tableau présente les synergies pour les 6 accessoires de drones. Les drones sont "
        "particulièrement sensibles aux passifs dédiés et à la physique générale des projectiles.",
        body_style
    ))
    story.append(Spacer(1, 5))

    accessories_matrix = [
        ("BOUCLIER ORBITAL", "DRONES LOURDS, ASSEMBLAGE DE DRONES, HYPER-PROPULSION, CELLULES GEANTES",
         "L'Assemblage augmente le nombre de boucliers (+1). Les Drones Lourds augmentent leur vitesse orbitale de +30%, créant un mur protecteur quasi-continu. Le rayon d'orbite grandit avec l'Hyper-propulsion."),
         
        ("DRONE LASER", "DRONES LOURDS, ASSEMBLAGE DE DRONES, HYPER-PROPULSION, VISEE INTELLIGENTE",
         "Génère une escouade de drones légers à cadence ultra-rapide. Les tirs de drones profitent du guidage de la visée intelligente."),
         
        ("DRONE ROQUETTE", "DRONES LOURDS, ASSEMBLAGE DE DRONES, CELLULES GEANTES, OBUS SHRAPNEL",
         "Multiplie le nombre de roquettes à fragmentation. Le rayon d'explosion augmente avec la taille cumulée des projectiles (+45% avec Cœur Plasma)."),
         
        ("TROU NOIR", "DRONES LOURDS, HYPER-PROPULSION, CELLULES GEANTES, COEUR PLASMA",
         "La vitesse orbitale du trou noir s'accroît, nettoyant une large couronne autour du vaisseau. Son champ d'attraction gravitationnelle double de volume."),
         
        ("BOBINE TESLA", "ASSEMBLAGE DE DRONES, HYPER-PROPULSION, NOYAU DE SURCHARGE",
         "La vitesse d'attaque augmente de +22% par niveau d'Assemblage. La portée des arcs électriques et leur propagation sautent plus loin grâce à la vitesse de projectile."),
         
        ("DRONE DE SOIN", "ASSEMBLAGE DE DRONES, DRONES LOURDS, AMELIORATION DE LA COQUE",
         "Accélère le rythme de soin de coque de 18% par niveau d'Assemblage. Les drones orbitent plus vite pour collecter les orbes d'XP sans danger.")
    ]

    a_table_data = [[
        Paragraph("Accessoire (Drone)", table_header_style),
        Paragraph("Passifs Recommandés (Synergies Fortes)", table_header_style),
        Paragraph("Analyse Mécanique de l'Optimisation", table_header_style)
    ]]

    for name, passives, desc in accessories_matrix:
        a_table_data.append([
            Paragraph(name, table_cell_bold),
            Paragraph(passives, table_cell_accent),
            Paragraph(desc, table_cell_style)
        ])

    a_table = Table(a_table_data, colWidths=[1.3*inch, 1.9*inch, 4.2*inch])
    a_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_card_bg])
    ]))

    story.append(a_table)
    story.append(PageBreak())

    # ==========================================
    # PAGE 6: ARCHÉTYPES DE BUILDS ULTIMES
    # ==========================================
    story.append(Paragraph("5. Les 4 Archétypes de Builds Ultimes (Configurations)", h1_style))
    story.append(Paragraph(
        "Voici les 4 combinaisons de fin de partie (Endgame) testées et optimisées pour "
        "maximiser la puissance offensive ou assurer la survie face aux swarms de niveau 10+.",
        body_style
    ))
    story.append(Spacer(1, 5))

    # Build 1
    story.append(Paragraph("Configuration A : Le Suzerain des Drones (Flotte Spatiale)", h2_style))
    story.append(Paragraph(
        "<b>Arme :</b> AUTO-LASER & MISSILE TETE CHERCHEUSE | <b>Accessoires :</b> DRONE LASER, DRONE ROQUETTE, BOUCLIER ORBITAL, DRONE DE SOIN<br/>"
        "<b>Passifs :</b> DRONES LOURDS, ASSEMBLAGE DE DRONES, COEUR PLASMA, PROPULSEURS, AMELIORATION COQUE, NOYAU DE SURCHARGE<br/>"
        "<i>Description :</i> Ce build maximise la puissance orbitale. La synergie d'Assemblage réduit le cooldown des drones de -90% (cap maximum) et "
        "ajoute +5 drones par accessoire. Combiné à Drones Lourds, les boucliers orbitaux forment une barrière impénétrable tandis que les drones laser "
        "et roquette pulvérisent la carte à une vitesse frénétique. Cœur Plasma réduit aussi le temps de recharge global.",
        body_style
    ))
    story.append(Spacer(1, 5))

    # Build 2
    story.append(Paragraph("Configuration B : L'Artillerie Tempête (Nettoyage d'Écran)", h2_style))
    story.append(Paragraph(
        "<b>Arme :</b> GRENADE VORTEX & LAMES SPIRALES | <b>Accessoires :</b> TROU NOIR, BOBINE TESLA, BOUCLIER ORBITAL, DRONE ROQUETTE<br/>"
        "<b>Passifs :</b> TIR DIVISE, MATRICE REBONDISSANTE, OBUS SHRAPNEL, FOREUSE DE BLINDAGE, CELLULES GEANTES, COEUR PLASMA<br/>"
        "<i>Description :</i> Conçu pour saturer l'écran de projectiles. Les Grenades Vortex et Lames Spirales rebondissent et traversent tous les ennemis. "
        "À chaque impact, les projectiles se divisent (Shrapnel) en créant une réaction en chaîne de micro-lasers et micro-lames rebondissants. "
        "Le Trou Noir regroupe les ennemis au centre de cette tempête balistique.",
        body_style
    ))
    story.append(Spacer(1, 5))

    # Build 3
    story.append(Paragraph("Configuration C : L'Éclair Agile (Skirmisher Vitesse)", h2_style))
    story.append(Paragraph(
        "<b>Arme :</b> CANON ELECTROMAGNETIQUE (Railgun) & LANCE-FLAMMES | <b>Accessoires :</b> BOBINE TESLA, DRONE LASER, TROU NOIR, DRONE ROQUETTE<br/>"
        "<b>Passifs :</b> HYPER-PROPULSION, VISEE INTELLIGENTE, PROPULSEURS, ATTRACTEUR XP, COEUR PLASMA, NOYAU DE SURCHARGE<br/>"
        "<i>Description :</i> Un build basé sur le 'Hit & Run'. Le pilote se déplace à +50% de vitesse (Propulseurs). La réduction de cooldown d'Hyper-propulsion "
        "et de Cœur Plasma cumulée permet au Canon Électromagnétique de tirer de longs faisceaux continus autoguidés (Visée Intelligente) à une fréquence folle, "
        "permettant de balayer les boss en restant à distance.",
        body_style
    ))
    story.append(Spacer(1, 5))

    # Build 4
    story.append(Paragraph("Configuration D : Le Bastion Insubmersible (Tank Absolu)", h2_style))
    story.append(Paragraph(
        "<b>Arme :</b> ONDE DE CHOC & COUP DE FAUX | <b>Accessoires :</b> BOUCLIER ORBITAL, DRONE DE SOIN, TROU NOIR, DRONE LASER<br/>"
        "<b>Passifs :</b> NANO-BLINDAGE, DRONES DE REPARATION, AMELIORATION COQUE, CELLULES GEANTES, COEUR PLASMA, NOYAU DE SURCHARGE<br/>"
        "<i>Description :</i> Build de survie extrême. Nano-Blindage réduit tous les dégâts de 10 points. Les Drones de Réparation régénèrent 5.0 PV/sec, "
        "couplés à un bonus de +100 PV Max (Amélioration Coque). L'Onde de Choc et le Coup de Faux géants (Cellules Géantes) repoussent continuellement "
        "les ennemis hors du rayon de contact de la coque, rendant le vaisseau invulnérable.",
        body_style
    ))

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF Successfully generated at: {pdf_filename}")

if __name__ == "__main__":
    build_pdf()
