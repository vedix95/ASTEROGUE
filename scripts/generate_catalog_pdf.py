# scripts/generate_catalog_pdf.py
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
            # Draw beautiful border on Cover Page (Industrial Amber/Orange)
            self.saveState()
            self.setStrokeColor(colors.HexColor('#D97706')) # Amber
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
        self.drawString(40, 755, "VECTOR SURVIVOR — CATALOGUE D'ARMEMENT & STRATÉGIE TACTIQUE")
        self.setStrokeColor(colors.HexColor('#E2E8F0'))
        self.setLineWidth(0.5)
        self.line(40, 747, 572, 747)
        
        # Draw Footer
        page_text = f"Page {self._pageNumber} sur {page_count}"
        self.drawRightString(572, 30, page_text)
        self.drawString(40, 30, "CLASSIFICATION : CONFIDENTIEL // SECTEUR PROFOND DE LA FLOTTE")
        self.line(40, 40, 572, 40)
        self.restoreState()

def build_pdf():
    pdf_filename = "Vector_Survivor_Catalog_FR.pdf"
    
    # Setup document (letter size is 612 x 792 pt, margins of 41 pt leave 530 pt width)
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        rightMargin=41,
        leftMargin=41,
        topMargin=55,
        bottomMargin=55
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
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#475569'),
        alignment=1,
        spaceAfter=40
    )
    
    h1_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=18,
        spaceAfter=8,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'SubsectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#D97706'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
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
        fontSize=8.5,
        leading=10.5,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor('#334155')
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor('#0F172A')
    )

    story = []
    
    # ==========================================
    # PAGE 1: COUVERTURE
    # ==========================================
    story.append(Spacer(1, 120))
    story.append(Paragraph("VECTOR SURVIVOR", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("CATALOGUE TACTIQUE COMPLET DES SYSTÈMES ET DES ENTITÉS", subtitle_style))
    story.append(Spacer(1, 60))
    
    # Draw a simple decorative border layout in tables for the cover sheet
    cover_table_data = [
        [Paragraph("<b>SYSTÈMES :</b> 14 Armes Principales | 9 Drones Tactiques | 19 Modificateurs Passifs", subtitle_style)],
        [Paragraph("<b>ÉVOLUTION :</b> 6 Améliorations de Flotte Permanente (Méta-Shop)", subtitle_style)],
        [Paragraph("<b>EXPLORATION :</b> 4 Types d'Astéroïdes Récoltables | 3 Objectifs DRG", subtitle_style)]
    ]
    cover_table = Table(cover_table_data, colWidths=[500])
    cover_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#E2E8F0'))
    ]))
    story.append(cover_table)
    
    story.append(Spacer(1, 100))
    story.append(Paragraph("<b>AUTEUR :</b> Antigravity AI Subsystem Manager", caption_style))
    story.append(Paragraph("<b>CLASSIFICATION :</b> Renseignement de Flotte Stellaire // Deep Rock Survivor Style", caption_style))
    story.append(PageBreak())

    # ==========================================
    # PAGE 2: ENTITÉS, ENNEMIS ET RÉCOLTE
    # ==========================================
    story.append(Paragraph("1. Classification des Secteurs, des Entités & de la Récolte", h1_style))
    story.append(Paragraph(
        "Les opérations minières s'effectuent dans des secteurs spatiaux hautement hostiles. Le pilote doit naviguer "
        "entre l'élimination des menaces biologiques, l'extraction de minerais précieux et la progression à travers les couches géologiques.",
        body_style
    ))
    
    story.append(Paragraph("1.1 Progression des Secteurs (Dives Stellaires)", h2_style))
    story.append(Paragraph(
        "Une mission standard se compose d'une plongée ('dive') à travers <b>3 Secteurs distincts</b> de difficulté croissante. "
        "Le pilote conserve son niveau, ses armes et son butin accumulé en entrant dans la capsule d'évacuation :<br/>"
        "• <b>Secteur 1 : Ceinture de Grès (Vert)</b> : Secteur d'entrée, faible densité d'ennemis, gisements d'Or et de minerai brut, multiplicateur de PV ennemis x1.0.<br/>"
        "• <b>Secteur 2 : Nébuleuse de Plasma (Violet)</b> : Milieu hostile, introduction des préfixes de monstres (Solar, Quantum, Spectral), gisements de Plasma requis pour les upgrades, multiplicateur de PV x1.3.<br/>"
        "• <b>Secteur 3 : Abysse Stellaire (Cyan/Bleu)</b> : Zone d'élite, densité maximale, filons de Noyaux matriciels rares. Le Dreadnought Boss final apparaît à 2 minutes de jeu. Multiplicateur de PV x1.6.",
        body_style
    ))

    story.append(Paragraph("1.2 Le Chasseur Vector & Astéroïdes Récoltables", h2_style))
    story.append(Paragraph(
        "<b>Le Joueur</b> pilote un chasseur Vector équipé d'armes à visée automatique. Il dispose d'un aimant à débris et "
        "d'un blindage contre les impacts.<br/>"
        "<b>Le Système de Récolte</b> permet d'extraire des ressources des astéroïdes statiques dispersés dans le secteur. "
        "Le pilote effectue l'extraction soit en tirant dessus, soit en entrant en collision directe (forage). "
        "Entrer en contact avec un astéroïde active les foreuses de coque, ce qui ralentit la vitesse du vaisseau de 65% "
        "mais extrait rapidement les composants internes de l'astéroïde.",
        body_style
    ))

    # Asteroids table (Width = 530 pt)
    asteroid_headers = [
        Paragraph("Gisement d'Astéroïde", table_header_style),
        Paragraph("Couleur Vectorielle", table_header_style),
        Paragraph("Ressource Extraite", table_header_style),
        Paragraph("Utilité / Évolution", table_header_style)
    ]
    asteroid_rows = [
        [
            Paragraph("Astéroïde Standard", table_cell_bold),
            Paragraph("Gris / Blanc", table_cell_style),
            Paragraph("Cristaux d'XP (35%) / Crédits (10%)", table_cell_style),
            Paragraph("Progression de niveau en cours de run", table_cell_style)
        ],
        [
            Paragraph("Filon d'Or Stellaire", table_cell_bold),
            Paragraph("Jaune / Ambre", table_cell_style),
            Paragraph("Pépites de Crédits de Flotte", table_cell_style),
            Paragraph("Achat d'améliorations permanentes (Méta-Shop)", table_cell_style)
        ],
        [
            Paragraph("Filon de Plasma", table_cell_bold),
            Paragraph("Violet / Magenta", table_cell_style),
            Paragraph("Cristaux de Plasma", table_cell_style),
            Paragraph("Composant requis pour les évolutions avancées", table_cell_style)
        ],
        [
            Paragraph("Filon de Noyau Cosmique", table_cell_bold),
            Paragraph("Cyan Néon (Rare)", table_cell_style),
            Paragraph("Noyaux de Matrice (Astraea)", table_cell_style),
            Paragraph("Matériau d'élite requis pour les paliers d'évolution 4+", table_cell_style)
        ]
    ]
    
    ast_table_data = [asteroid_headers] + asteroid_rows
    ast_table = Table(ast_table_data, colWidths=[120, 100, 140, 170])
    ast_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(ast_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1.2 Menaces Biologiques & Préfixes Modificateurs", h2_style))
    story.append(Paragraph(
        "Les extraterrestres défendent férocement leurs secteurs. Ils apparaissent en vagues et possèdent "
        "des variantes de statistiques signalées par leur couleur et un préfixe tactique :",
        body_style
    ))

    # Enemies Table (Width = 530 pt)
    enemy_headers = [
        Paragraph("Préfixe de Menace", table_header_style),
        Paragraph("Couleur Vector", table_header_style),
        Paragraph("Modificateurs de Statistiques", table_header_style),
        Paragraph("Comportement / Renseignement", table_header_style)
    ]
    enemy_rows = [
        [Paragraph("Swarmer / Chaser / Stalker", table_cell_bold), Paragraph("Vert / Rouge", table_cell_style), Paragraph("Statistiques de Base", table_cell_style), Paragraph("Unités de mêlée standards cherchant le contact.", table_cell_style)],
        [Paragraph("Void", table_cell_bold), Paragraph("Violet", table_cell_style), Paragraph("Vie +35%, Vitesse -15%", table_cell_style), Paragraph("Blindage lourd résistant.", table_cell_style)],
        [Paragraph("Solar", table_cell_bold), Paragraph("Ambre", table_cell_style), Paragraph("Vitesse +20%, Dégâts +20%", table_cell_style), Paragraph("Thermique, rapide et agressif.", table_cell_style)],
        [Paragraph("Quantum", table_cell_bold), Paragraph("Cyan", table_cell_style), Paragraph("Taille -20%, Vitesse +35%, Vie -20%", table_cell_style), Paragraph("Difficile à viser, planeur instable.", table_cell_style)],
        [Paragraph("Spectral", table_cell_bold), Paragraph("Bleu Pâle", table_cell_style), Paragraph("Vie -25%, Vitesse +15%", table_cell_style), Paragraph("Semi-matériel, passe à travers les obstacles.", table_cell_style)],
        [Paragraph("Magnetic", table_cell_bold), Paragraph("Vert Néon", table_cell_style), Paragraph("Dégâts +30%", table_cell_style), Paragraph("Perturbe les boucliers à l'impact.", table_cell_style)],
        [Paragraph("Plasma", table_cell_bold), Paragraph("Rouge Foncé", table_cell_style), Paragraph("Dégâts +45%, Vie -10%", table_cell_style), Paragraph("Tire des munitions de plasma lourd.", table_cell_style)],
        [Paragraph("Nova", table_cell_bold), Paragraph("Blanc", table_cell_style), Paragraph("Taille +25%, Vie +25%", table_cell_style), Paragraph("Gros noyau instable explosant à la mort.", table_cell_style)],
        [Paragraph("Glitch", table_cell_bold), Paragraph("Magenta", table_cell_style), Paragraph("Vitesse +20%, Dégâts +20%", table_cell_style), Paragraph("Mouvement saccadé et téléportations brèves.", table_cell_style)],
        [Paragraph("Abyssal", table_cell_bold), Paragraph("Violet Sombre", table_cell_style), Paragraph("Vie +50%, Vitesse -20%, Taille +20%", table_cell_style), Paragraph("Léviathan géant très résistant.", table_cell_style)],
        [Paragraph("Boss (Dreadnought)", table_cell_bold), Paragraph("Rouge Scintillant", table_cell_style), Paragraph("Vie massive, tirs lourds", table_cell_style), Paragraph("Apparaît en fin de run. Débloque la capsule d'extraction.", table_cell_style)]
    ]
    
    en_table_data = [enemy_headers] + enemy_rows
    en_table = Table(en_table_data, colWidths=[110, 80, 150, 190])
    en_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(en_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("1.2.1 Évolutions Visuelles & Morphologiques du Chasseur (Style Isaac)", h2_style))
    story.append(Paragraph(
        "Afin de fournir un retour visuel direct sur la puissance accumulée, le chasseur Vector subit des transformations "
        "physiques en temps réel basées sur ses modules passifs et ses armes :<br/>"
        "• <b>Croissance Physique</b> : Le chasseur grandit de 2% à chaque niveau atteint (facteur d'échelle global).<br/>"
        "• <b>Tuyère de Poussée Centrale</b> : S'active si le passif <i>Propulseurs</i> ou la Vitesse Méta est supérieure à 0. Ajoute une tuyère centrale projetant une longue flamme thermique.<br/>"
        "• <b>Plaques d'Armure Nano-Blindées</b> : S'ajoutent sur les flancs du vaisseau si le passif <i>Nano-Blindage</i> est équipé.<br/>"
        "• <b>Halo de Cœur Sacré</b> : Un emblème doré de croix lumineuse apparaît au centre de l'appareil si le passif <i>Cœur Sacré</i> est actif.<br/>"
        "• <b>Croix Médicales d'Ailes</b> : Des symboles verts d'assistance s'affichent sur les bouts d'ailes si le passif <i>Drones de Réparation</i> est actif.<br/>"
        "• <b>Lame de combat frontale</b> : Une dague d'énergie rouge s'installe au nez du vaisseau si l'arme active <i>Couteau de Maman</i> est possédée.<br/>"
        "• <b>Canons de Gatling Arc-en-ciel</b> : Les canons d'ailes s'allongent et projettent une coloration néon cyclique.<br/>"
        "• <b>Thématique des Ailes par Secteur</b> : Les panneaux intérieurs des ailes se colorent dynamiquement selon le secteur actuel (Cyan au Secteur 1, Plasma/Violet au Secteur 2, Or/Ambre au Secteur 3).",
        body_style
    ))
    story.append(PageBreak())

    # ==========================================
    # PAGE 3: OBJETS COLLECTIBLES ET MONNAIES
    # ==========================================
    story.append(Paragraph("1.3 Inventaire des Objets Collectibles & Monnaies", h1_style))
    story.append(Paragraph(
        "Les objets flottants dans l'espace sont attirés par le rayon magnétique du joueur. Il existe deux types d'objets : "
        "les consommables de combat (utiles uniquement pendant le run) et les monnaies persistantes de la flotte.",
        body_style
    ))

    # Collectibles Table (Width = 530 pt)
    coll_headers = [
        Paragraph("Nom du Collectible", table_header_style),
        Paragraph("Type d'Objet", table_header_style),
        Paragraph("Effet / Mécanique de Collecte", table_header_style),
        Paragraph("Persistance", table_header_style)
    ]
    coll_rows = [
        [Paragraph("Diamant d'XP", table_cell_bold), Paragraph("Combat", table_cell_style), Paragraph("Octroie des points d'expérience pour monter de niveau.", table_cell_style), Paragraph("Perdu en fin de run", table_cell_style)],
        [Paragraph("Kit de Coque (PV)", table_cell_bold), Paragraph("Combat", table_cell_style), Paragraph("Restaure une partie de la santé du vaisseau.", table_cell_style), Paragraph("Perdu en fin de run", table_cell_style)],
        [Paragraph("Hypersaut Fuel", table_cell_bold), Paragraph("Combat", table_cell_style), Paragraph("Charge l'énergie d'activation de la propulsion active.", table_cell_style), Paragraph("Perdu en fin de run", table_cell_style)],
        [Paragraph("Aimant Stellaire", table_cell_bold), Paragraph("Combat", table_cell_style), Paragraph("Attire instantanément tous les objets du secteur vers le joueur.", table_cell_style), Paragraph("Perdu en fin de run", table_cell_style)],
        [Paragraph("Bombe à Fusion", table_cell_bold), Paragraph("Combat", table_cell_style), Paragraph("Déclenche une onde de choc thermique détruisant les ennemis.", table_cell_style), Paragraph("Perdu en fin de run", table_cell_style)],
        [Paragraph("Crédits de Flotte", table_cell_bold), Paragraph("Monnaie Méta", table_cell_style), Paragraph("Monnaie standard pour acheter des upgrades dans le Méta-Shop.", table_cell_style), Paragraph("Conservé & Cumulé", table_cell_style)],
        [Paragraph("Cristaux de Plasma", table_cell_bold), Paragraph("Monnaie Méta", table_cell_style), Paragraph("Composant minéral requis pour l'évolution technologique.", table_cell_style), Paragraph("Conservé & Cumulé", table_cell_style)],
        [Paragraph("Noyau de Matrice (Core)", table_cell_bold), Paragraph("Monnaie Méta", table_cell_style), Paragraph("Composant d'élite requis pour les paliers d'upgrades avancés.", table_cell_style), Paragraph("Conservé & Cumulé", table_cell_style)]
    ]
    
    coll_table_data = [coll_headers] + coll_rows
    coll_table = Table(coll_table_data, colWidths=[110, 80, 240, 100])
    coll_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(coll_table)
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("1.4 Opérations & Objectifs tactiques (Deep Rock Style)", h2_style))
    story.append(Paragraph(
        "Chaque mission assigne aléatoirement l'un des trois objectifs principaux dans le secteur :<br/>"
        "1. <b>Minage de Cristaux</b> : Extraire 35 cristaux d'Astraea violets répartis dans la zone.<br/>"
        "2. <b>Récupération d'Œufs de Nébuleuse</b> : Extraire 5 œufs organiques gardés par des essaims agressifs.<br/>"
        "3. <b>Contrôle de Balises</b> : Activer 3 balises de communication en restant dans leur zone. "
        "Une fois la liaison complétée à 100%, la balise émet une impulsion IEM détruisant les ennemis proches.<br/>"
        "<i>Succès d'Objectif : Répare intégralement la coque du chasseur et octroie +500 XP. Débloque le point d'extraction final.</i>",
        body_style
    ))
    story.append(PageBreak())

    # ==========================================
    # PAGE 4: ARME COMPLÈTE (14 ARMES)
    # ==========================================
    story.append(Paragraph("2. Arsenal Principal : Armes Offensives", h1_style))
    story.append(Paragraph(
        "Le Chasseur Vector peut équiper jusqu'à 4 armes offensives simultanément. Elles tirent de manière autonome "
        "sur les cibles situées dans leur portée de détection.",
        body_style
    ))
    
    # 14 weapons comparative table (Width = 530 pt)
    wp_headers = [
        Paragraph("Nom de l'Arme", table_header_style),
        Paragraph("Mécanique & Type de Tir", table_header_style),
        Paragraph("Dmg (N1)", table_header_style),
        Paragraph("Dmg (N8)", table_header_style),
        Paragraph("CD (N1)", table_header_style),
        Paragraph("CD (N8)", table_header_style),
        Paragraph("Note Tactique & Synergies", table_header_style)
    ]
    
    wp_rows = [
        [Paragraph("AUTO-LASER", table_cell_bold), Paragraph("Lasers rapides sur la cible la plus proche.", table_cell_style), Paragraph("10", table_cell_style), Paragraph("45", table_cell_style), Paragraph("0.45s", table_cell_style), Paragraph("0.25s", table_cell_style), Paragraph("Excellent avec Multishot & Homing.", table_cell_style)],
        [Paragraph("RAILGUN", table_cell_bold), Paragraph("Faisceau perforant instantané orienté.", table_cell_style), Paragraph("35", table_cell_style), Paragraph("180", table_cell_style), Paragraph("1.2s", table_cell_style), Paragraph("0.8s", table_cell_style), Paragraph("Tir en ligne droite dévastateur.", table_cell_style)],
        [Paragraph("ONDE DE CHOC", table_cell_bold), Paragraph("Champs de force à fort recul radial.", table_cell_style), Paragraph("20", table_cell_style), Paragraph("95", table_cell_style), Paragraph("2.2s", table_cell_style), Paragraph("1.5s", table_cell_style), Paragraph("Défense de foule à courte portée.", table_cell_style)],
        [Paragraph("LANCE-FLAMMES", table_cell_bold), Paragraph("Jet de feu continu en cône frontal.", table_cell_style), Paragraph("5", table_cell_style), Paragraph("20", table_cell_style), Paragraph("0.1s", table_cell_style), Paragraph("0.06s", table_cell_style), Paragraph("DPS de zone extrême, tirs perçants.", table_cell_style)],
        [Paragraph("GRENADE VORTEX", table_cell_bold), Paragraph("Lobe des bombes attirant les ennemis.", table_cell_style), Paragraph("35", table_cell_style), Paragraph("150", table_cell_style), Paragraph("2.4s", table_cell_style), Paragraph("1.5s", table_cell_style), Paragraph("Regroupe les cibles avant explosion.", table_cell_style)],
        [Paragraph("LAMES SPIRALES", table_cell_bold), Paragraph("Scies tourbillonnant vers l'extérieur.", table_cell_style), Paragraph("15", table_cell_style), Paragraph("60", table_cell_style), Paragraph("1.6s", table_cell_style), Paragraph("0.8s", table_cell_style), Paragraph("Bonne couverture périphérique.", table_cell_style)],
        [Paragraph("SEEKER MISSILE", table_cell_bold), Paragraph("Missiles autoguidés à effet d'explosion.", table_cell_style), Paragraph("28", table_cell_style), Paragraph("100", table_cell_style), Paragraph("1.5s", table_cell_style), Paragraph("0.9s", table_cell_style), Paragraph("Synergise avec taille et explosion.", table_cell_style)],
        [Paragraph("COUP DE FAUX", table_cell_bold), Paragraph("Large faucheuse d'énergie à fort recul.", table_cell_style), Paragraph("45", table_cell_style), Paragraph("200", table_cell_style), Paragraph("1.5s", table_cell_style), Paragraph("0.9s", table_cell_style), Paragraph("Dégage les menaces frontales.", table_cell_style)],
        [Paragraph("BRIMSTONE", table_cell_bold), Paragraph("Rayon de sang chargé continu.", table_cell_style), Paragraph("60/s", table_cell_style), Paragraph("280/s", table_cell_style), Paragraph("3.0s", table_cell_style), Paragraph("1.8s", table_cell_style), Paragraph("DPS de cible unique inégalable.", table_cell_style)],
        [Paragraph("TECH X", table_cell_bold), Paragraph("Tire un anneau laser expansif perforant.", table_cell_style), Paragraph("25", table_cell_style), Paragraph("115", table_cell_style), Paragraph("2.0s", table_cell_style), Paragraph("1.1s", table_cell_style), Paragraph("Nettoie des lignes entières de monstres.", table_cell_style)],
        [Paragraph("COUTEAU MAMAN", table_cell_bold), Paragraph("Couteau orbital poignardant.", table_cell_style), Paragraph("40", table_cell_style), Paragraph("190", table_cell_style), Paragraph("1.0s", table_cell_style), Paragraph("0.5s", table_cell_style), Paragraph("Défense rapprochée perforante.", table_cell_style)],
        [Paragraph("GATLING ARC-EN", table_cell_bold), Paragraph("Tir ultra-rapide multicolore.", table_cell_style), Paragraph("8", table_cell_style), Paragraph("36", table_cell_style), Paragraph("0.08s", table_cell_style), Paragraph("0.04s", table_cell_style), Paragraph("Cadence frénétique.", table_cell_style)],
        [Paragraph("METEORE", table_cell_bold), Paragraph("Lobe des météores créant du feu au sol.", table_cell_style), Paragraph("50", table_cell_style), Paragraph("240", table_cell_style), Paragraph("3.0s", table_cell_style), Paragraph("1.6s", table_cell_style), Paragraph("Dégâts résiduels de zone élevés.", table_cell_style)],
        [Paragraph("ECLAIR NEON", table_cell_bold), Paragraph("Arcs électriques sautant de cible en cible.", table_cell_style), Paragraph("18", table_cell_style), Paragraph("85", table_cell_style), Paragraph("1.4s", table_cell_style), Paragraph("0.7s", table_cell_style), Paragraph("Idéal contre les petits essaims.", table_cell_style)]
    ]
    
    wp_table_data = [wp_headers] + wp_rows
    wp_table = Table(wp_table_data, colWidths=[90, 140, 40, 40, 40, 40, 140])
    wp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(wp_table)
    story.append(PageBreak())

    # ==========================================
    # PAGE 5: DRONES TACTIQUES (9 DRONES)
    # ==========================================
    story.append(Paragraph("3. Modules Tactiques : Drones Orbitaux", h1_style))
    story.append(Paragraph(
        "Les modules tactiques gravitent autour du vaisseau principal, fournissant des fonctions automatiques "
        "de couverture défensive, de soutien laser ou de régénération médicale.",
        body_style
    ))
    
    # 9 accessories table (Width = 530 pt)
    acc_headers = [
        Paragraph("Nom du Drone", table_header_style),
        Paragraph("Mécanique Opérationnelle", table_header_style),
        Paragraph("Dmg (N1)", table_header_style),
        Paragraph("Dmg (N8)", table_header_style),
        Paragraph("Stat 1 (N1)", table_header_style),
        Paragraph("Stat 2 (N8)", table_header_style),
        Paragraph("Rôle Tactique Majeur", table_header_style)
    ]
    
    acc_rows = [
        [Paragraph("BOUCLIER ORBITAL", table_cell_bold), Paragraph("Génère des barrières orbitales.", table_cell_style), Paragraph("12", table_cell_style), Paragraph("42", table_cell_style), Paragraph("1 bouclier", table_cell_style), Paragraph("6 boucliers", table_cell_style), Paragraph("Protection anti-projectile.", table_cell_style)],
        [Paragraph("DRONE LASER", table_cell_bold), Paragraph("Tire des lasers précis sur les cibles.", table_cell_style), Paragraph("8", table_cell_style), Paragraph("40", table_cell_style), Paragraph("CD: 1.2s", table_cell_style), Paragraph("CD: 0.45s", table_cell_style), Paragraph("Soutien monocible fiable.", table_cell_style)],
        [Paragraph("DRONE ROQUETTE", table_cell_bold), Paragraph("Tire des mini-missiles autoguidés.", table_cell_style), Paragraph("20", table_cell_style), Paragraph("95", table_cell_style), Paragraph("CD: 2.2s", table_cell_style), Paragraph("CD: 1.1s", table_cell_style), Paragraph("Contrôle de zone explosif.", table_cell_style)],
        [Paragraph("TROU NOIR", table_cell_bold), Paragraph("Orbite en générant des puits gravitationnels.", table_cell_style), Paragraph("10/t", table_cell_style), Paragraph("48/t", table_cell_style), Paragraph("Zone: 130px", table_cell_style), Paragraph("Zone: 240px", table_cell_style), Paragraph("Regroupement de masse.", table_cell_style)],
        [Paragraph("BOBINE TESLA", table_cell_bold), Paragraph("Projette des éclairs en chaîne.", table_cell_style), Paragraph("25", table_cell_style), Paragraph("110", table_cell_style), Paragraph("3 rebonds", table_cell_style), Paragraph("8 rebonds", table_cell_style), Paragraph("Destruction d'essaims rapide.", table_cell_style)],
        [Paragraph("DRONE DE SOIN", table_cell_bold), Paragraph("Restaure les PV de coque périodiquement.", table_cell_style), Paragraph("0", table_cell_style), Paragraph("0", table_cell_style), Paragraph("5 HP (5s)", table_cell_style), Paragraph("40 HP (2.4s)", table_cell_style), Paragraph("Survie prolongée en combat.", table_cell_style)],
        [Paragraph("ROBO-BABY", table_cell_bold), Paragraph("Tire des lasers légers de soutien.", table_cell_style), Paragraph("7", table_cell_style), Paragraph("34", table_cell_style), Paragraph("CD: 1.0s", table_cell_style), Paragraph("CD: 0.5s", table_cell_style), Paragraph("DPS régulier d'appoint.", table_cell_style)],
        [Paragraph("DRONE INFESTATEUR", table_cell_bold), Paragraph("Génère des mouches de combat.", table_cell_style), Paragraph("6/m", table_cell_style), Paragraph("28/m", table_cell_style), Paragraph("CD: 3.0s", table_cell_style), Paragraph("CD: 1.2s", table_cell_style), Paragraph("Harcèlement de cibles distantes.", table_cell_style)],
        [Paragraph("DRONE SEC", table_cell_bold), Paragraph("Drone défensif lourd à projectiles.", table_cell_style), Paragraph("15", table_cell_style), Paragraph("70", table_cell_style), Paragraph("CD: 1.5s", table_cell_style), Paragraph("CD: 0.7s", table_cell_style), Paragraph("Dégâts et recul de proximité.", table_cell_style)]
    ]
    
    acc_table_data = [acc_headers] + acc_rows
    acc_table = Table(acc_table_data, colWidths=[95, 145, 45, 45, 55, 55, 90])
    acc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(acc_table)
    story.append(PageBreak())

    # ==========================================
    # PAGE 6: AMÉLIORATIONS PASSIVES (19 PASSIVES)
    # ==========================================
    story.append(Paragraph("4. Système de Synergies : Améliorations Passives", h1_style))
    story.append(Paragraph(
        "Le vaisseau possède 6 slots de modules passifs. Ces composants modifient soit les statistiques de base du vaisseau, "
        "soit altèrent la physique globale des projectiles (système de synergies de type The Binding of Isaac).",
        body_style
    ))
    
    # 19 passives table (Width = 530 pt)
    pass_headers = [
        Paragraph("Module Passif", table_header_style),
        Paragraph("Type d'Upgrade", table_header_style),
        Paragraph("Mécanique & Impact de la Synergie", table_header_style)
    ]
    
    pass_rows = [
        [Paragraph("PROPULSEURS (THRUSTERS)", table_cell_bold), Paragraph("Statistique Vaisseau", table_cell_style), Paragraph("+10% vitesse de déplacement par niveau (Max Lvl 5 / +50%).", table_cell_style)],
        [Paragraph("NANO-BLINDAGE (NANO-ARMOR)", table_cell_bold), Paragraph("Statistique Vaisseau", table_cell_style), Paragraph("+2 de réduction de dégâts fixe sur chaque coup (Max Lvl 5 / +10).", table_cell_style)],
        [Paragraph("ATTRACTEUR D'XP (XP MAGNET)", table_cell_bold), Paragraph("Statistique Vaisseau", table_cell_style), Paragraph("+25% rayon magnétique d'attraction des objets (Max Lvl 5 / +125%).", table_cell_style)],
        [Paragraph("NOYAU SURCHARGE (OVERDRIVE)", table_cell_bold), Paragraph("Statistique Vaisseau", table_cell_style), Paragraph("+15% multiplicateur de dégâts sur toutes les armes (Max Lvl 5 / +75%).", table_cell_style)],
        [Paragraph("DRONES REPARATION (REPAIR)", table_cell_bold), Paragraph("Statistique Vaisseau", table_cell_style), Paragraph("Régénère passivement +1.0 PV par seconde (Max Lvl 5 / +5.0 PV/s).", table_cell_style)],
        [Paragraph("BLINDAGE COQUE (HULL UPGRADE)", table_cell_bold), Paragraph("Statistique Vaisseau", table_cell_style), Paragraph("+20 PV Max de coque et soigne instantanément +20 PV par niveau.", table_cell_style)],
        [Paragraph("CELLULES GEANTES (GIANT CELLS)", table_cell_bold), Paragraph("Modificateur de Projectile", table_cell_style), Paragraph("+20% taille des projectiles et +10% dégâts par niveau.", table_cell_style)],
        [Paragraph("HYPER-PROPULSION (HYPER DRIVE)", table_cell_bold), Paragraph("Modificateur de Projectile", table_cell_style), Paragraph("+20% vitesse de tir et -10% temps de rechargement global par niveau.", table_cell_style)],
        [Paragraph("TIR DIVISE (SPLIT FIRE)", table_cell_bold), Paragraph("Modificateur de Projectile", table_cell_style), Paragraph("Ajoute +1 projectile tiré par salve, mais réduit les dégâts de -12%.", table_cell_style)],
        [Paragraph("VISEE INTELLIGENTE (SMART TARGET)", table_cell_bold), Paragraph("Modificateur de Projectile", table_cell_style), Paragraph("Les tirs se dirigent activement vers les cibles (homing +1.5/niveau).", table_cell_style)],
        [Paragraph("MATRICE REBOND (BOUNCING)", table_cell_bold), Paragraph("Modificateur de Projectile", table_cell_style), Paragraph("Les projectiles rebondissent sur les bords de l'écran (+1 rebond/niveau).", table_cell_style)],
        [Paragraph("FOREUSE BLINDAGE (DRILL TIP)", table_cell_bold), Paragraph("Modificateur de Projectile", table_cell_style), Paragraph("Les projectiles transpercent +1 cible supplémentaire par niveau.", table_cell_style)],
        [Paragraph("OBUS SHRAPNEL (SHRAPNEL)", table_cell_bold), Paragraph("Modificateur de Projectile", table_cell_style), Paragraph("Les balles se séparent en 2 shrapnels perpendiculaires à l'impact.", table_cell_style)],
        [Paragraph("DRONES LOURDS (HEAVY DRONES)", table_cell_bold), Paragraph("Synergie Drones", table_cell_style), Paragraph("Vitesse d'orbite des drones +30% & dégâts des drones +15% par niveau.", table_cell_style)],
        [Paragraph("ASSEMBLAGE DRONES (ASSEMBLY)", table_cell_bold), Paragraph("Synergie Drones", table_cell_style), Paragraph("Rechargement des drones -18% & projectiles de drone +1 par niveau.", table_cell_style)],
        [Paragraph("COEUR PLASMA (PLASMA CORE)", table_cell_bold), Paragraph("Modificateur Mixte", table_cell_style), Paragraph("Taille des projectiles +25% & rechargement des armes -12% par niveau.", table_cell_style)],
        [Paragraph("PLANETE MINUSCULE (TINY PLANET)", table_cell_bold), Paragraph("Modificateur Trajectoire", table_cell_style), Paragraph("Les projectiles orbitent en spirale autour du vaisseau.", table_cell_style)],
        [Paragraph("CHARBON ACTIF (LUMP OF COAL)", table_cell_bold), Paragraph("Modificateur Trajectoire", table_cell_style), Paragraph("Les projectiles grossissent et gagnent +45% dégâts par seconde de vol.", table_cell_style)],
        [Paragraph("COEUR SACRE (SACRED HEART)", table_cell_bold), Paragraph("Modificateur Divin", table_cell_style), Paragraph("+50% dégâts massifs, projectiles autoguidés, vitesse du vaisseau -20%.", table_cell_style)]
    ]
    
    pass_table_data = [pass_headers] + pass_rows
    pass_table = Table(pass_table_data, colWidths=[130, 110, 290])
    pass_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(pass_table)
    story.append(PageBreak())

    # ==========================================
    # PAGE 7: ÉVOLUTION PERMANENTE (MÉTA-SHOP)
    # ==========================================
    story.append(Paragraph("5. Évolution Permanente : Améliorations de Flotte (Méta)", h1_style))
    story.append(Paragraph(
        "Au retour de chaque mission, qu'elle soit couronnée de succès ou interrompue par l'ennemi, les "
        "ressources minières sécurisées (Crédits, Plasma, Noyaux) sont transférées dans le coffre persistant. "
        "Elles permettent d'appliquer des optimisations durables sur la flotte de chasseurs.",
        body_style
    ))
    
    story.append(Paragraph("5.1 Liste des Optimisations Stériles Disponibles", h2_style))
    story.append(Paragraph(
        "Le Méta-Shop propose exactement 6 modules d'évolutions permanentes, chacun améliorant un attribut majeur "
        "du vaisseau et cumulable jusqu'au niveau 10 :",
        body_style
    ))

    # Meta Upgrades list
    meta_headers = [
        Paragraph("Amélioration Permanente", table_header_style),
        Paragraph("Effet / Description Technique", table_header_style),
        Paragraph("Progression Totale (Niveau 10)", table_header_style)
    ]
    meta_rows = [
        [Paragraph("BLINDAGE DE LA COQUE (Hull)", table_cell_bold), Paragraph("Augmente les points de structure max de base du chasseur.", table_cell_style), Paragraph("+10% PV Max de base par niveau (+100% au niv. 10)", table_cell_style)],
        [Paragraph("MOTEURS SURCHARGES (Engine)", table_cell_bold), Paragraph("Renforce la vitesse de poussée directionnelle du vaisseau.", table_cell_style), Paragraph("+5% vitesse de déplacement par niveau (+50% au niv. 10)", table_cell_style)],
        [Paragraph("NOYAU DE PUISSANCE (Damage)", table_cell_bold), Paragraph("Surcharge le flux de dégâts de l'armement principal.", table_cell_style), Paragraph("+5% de dégâts sur toutes les armes par niveau (+50% au niv. 10)", table_cell_style)],
        [Paragraph("RECEPTEUR FLUX-MAGNETIQUE (Magnet)", table_cell_bold), Paragraph("Élargit le champ d'attraction gravitaire des débris spatiaux.", table_cell_style), Paragraph("+15% rayon d'attraction des collectibles par niveau (+150% au niv. 10)", table_cell_style)],
        [Paragraph("SCANNER DE FLUX XP (Scanner)", table_cell_bold), Paragraph("Optimise l'assimilation des données pour monter de niveau en vol.", table_cell_style), Paragraph("+8% d'XP gagnée par diamant collecté par niveau (+80% au niv. 10)", table_cell_style)],
        [Paragraph("LASER DE FORAGE RAPIDE (Mining)", table_cell_bold), Paragraph("Accélère la vitesse de concassage et de forage des astéroïdes.", table_cell_style), Paragraph("+25% de vitesse de forage d'astéroïdes par contact par niveau (+250% au niv. 10)", table_cell_style)]
    ]
    
    meta_table_data = [meta_headers] + meta_rows
    meta_table = Table(meta_table_data, colWidths=[150, 210, 170])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    story.append(meta_table)
    
    story.append(Spacer(1, 15))
    story.append(Paragraph("5.2 Structure de Coûts & Formule de Respec", h2_style))
    story.append(Paragraph(
        "<b>Progression des coûts</b> : Les prix augmentent de façon quadratique pour les Crédits "
        "et de façon progressive pour le Plasma et les Noyaux de Matrice. Les premiers niveaux requièrent uniquement des Crédits, "
        "puis l'évolution demande du Plasma (dès le niveau 1) et des Noyaux de Matrice (dès le niveau 3).<br/>"
        "<i>Formule de coût : Crédits = 100 + Niveau * 150 + Niveau² * 75 | Plasma = 3 + Niveau * 5 + Niveau² * 1.5 | Noyaux = Niveau - 2 (si Lvl >= 3)</i>.<br/>"
        "<b>Système de Recyclage (Respec)</b> : Pour garantir une flexibilité tactique, le pilote peut appuyer sur <b>[R]</b> "
        "à tout moment sur l'écran d'améliorations pour réinitialiser tous ses upgrades de flotte au niveau 0, "
        "remboursant intégralement (100% de remboursement) tous les Crédits, Plasma et Noyaux de Matrice investis.",
        body_style
    ))
    
    # Build Document using NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF Successfully generated at: {pdf_filename}")

if __name__ == "__main__":
    build_pdf()
