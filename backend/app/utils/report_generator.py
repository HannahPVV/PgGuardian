from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import Flowable
from datetime import datetime


# ── Paleta de colores ──────────────────────────────────────────────────────────
DARK_BG    = colors.HexColor("#0F172A")
ACCENT     = colors.HexColor("#6366F1")
ACCENT2    = colors.HexColor("#10B981")
WARNING    = colors.HexColor("#F59E0B")
CARD_BG    = colors.HexColor("#F8FAFC")
BORDER     = colors.HexColor("#E2E8F0")
TEXT_DARK  = colors.HexColor("#1E293B")
TEXT_MID   = colors.HexColor("#475569")
TEXT_LIGHT = colors.HexColor("#94A3B8")
WHITE      = colors.white


# ── Línea decorativa ──────────────────────────────────────────────────────────
class ColorBar(Flowable):
    def __init__(self, width, height, color):
        Flowable.__init__(self)
        self.bar_width  = width
        self.bar_height = height
        self.color      = color

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.bar_width, self.bar_height, fill=1, stroke=0)


# ── Estilos de texto ──────────────────────────────────────────────────────────
def make_styles():
    return {
        "hero_title": ParagraphStyle("hero_title", fontName="Helvetica-Bold", fontSize=22, textColor=WHITE, spaceAfter=4, alignment=TA_CENTER, leading=28),
        "hero_sub":   ParagraphStyle("hero_sub",   fontName="Helvetica",      fontSize=10, textColor=colors.HexColor("#CBD5E1"), alignment=TA_CENTER),
        "section_label": ParagraphStyle("section_label", fontName="Helvetica-Bold", fontSize=8, textColor=TEXT_LIGHT, spaceAfter=6, leading=10),
        "card_code":  ParagraphStyle("card_code",  fontName="Helvetica-Bold", fontSize=8,  textColor=WARNING),
        "card_title": ParagraphStyle("card_title", fontName="Helvetica-Bold", fontSize=12, textColor=TEXT_DARK, leading=16, spaceAfter=6),
        "label":      ParagraphStyle("label",      fontName="Helvetica-Bold", fontSize=8,  textColor=ACCENT,  spaceBefore=6, spaceAfter=2),
        "body":       ParagraphStyle("body",       fontName="Helvetica",      fontSize=9,  textColor=TEXT_MID, leading=13),
        "fix_label":  ParagraphStyle("fix_label",  fontName="Helvetica-Bold", fontSize=8,  textColor=ACCENT2, spaceBefore=6, spaceAfter=2),
        "fix_body":   ParagraphStyle("fix_body",   fontName="Helvetica-Oblique", fontSize=9, textColor=colors.HexColor("#0F766E"), leading=13),
        "footer":     ParagraphStyle("footer",     fontName="Helvetica",      fontSize=7,  textColor=TEXT_LIGHT, alignment=TA_CENTER),
    }


# ── Encabezado hero ───────────────────────────────────────────────────────────
def build_header(styles, page_width):
    fecha = datetime.now().strftime("%d/%m/%Y  %H:%M")
    data = [
        [Paragraph("🛡  PgGuardian", styles["hero_title"])],
        [Paragraph("Resumen Ejecutivo de Auditoría", styles["hero_title"])],
        [Paragraph(f"Generado el {fecha}", styles["hero_sub"])],
    ]
    tbl = Table(data, colWidths=[page_width])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), DARK_BG),
        ("TOPPADDING",    (0, 0), (-1, 0),  24),
        ("BOTTOMPADDING", (0,-1), (-1,-1),  20),
        ("LEFTPADDING",   (0, 0), (-1,-1),  0),
        ("RIGHTPADDING",  (0, 0), (-1,-1),  0),
    ]))
    return tbl


# ── Tarjeta de hallazgo ───────────────────────────────────────────────────────
def build_card(issue, styles, page_width):
    code  = str(issue.get("problem_code") or "INF")
    title = str(issue.get("title")        or "Hallazgo")
    desc  = str(issue.get("description")  or "Sin detalles")
    table = str(issue.get("table_name")   or "Global / Config")
    fix   = str(issue.get("fix_sql")      or "Revisión manual")

    inner_w = page_width - 24

    content = [
        Paragraph(f'<font color="#{WARNING.hexval()[2:]}"><b>[{code}]</b></font>', styles["card_code"]),
        Paragraph(title, styles["card_title"]),
        HRFlowable(width=inner_w, thickness=1, color=BORDER, spaceAfter=4),
        Paragraph("▸ HALLAZGO",          styles["label"]),
        Paragraph(desc,                   styles["body"]),
        Paragraph("▸ OBJETO AFECTADO",   styles["label"]),
        Paragraph(table,                  styles["body"]),
        Paragraph("▸ RECOMENDACIÓN",     styles["fix_label"]),
        Paragraph(fix,                    styles["fix_body"]),
    ]

    cell_table = Table([[content]], colWidths=[inner_w])
    cell_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), CARD_BG),
        ("BOX",           (0,0), (-1,-1), 1, BORDER),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))

    accent_bar = Table([[""]], colWidths=[4])
    accent_bar.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), ACCENT),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))

    card = Table([[accent_bar, cell_table]], colWidths=[4, page_width - 4])
    card.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return KeepTogether([card, Spacer(1, 10)])


# ── Clase principal ───────────────────────────────────────────────────────────
class ReportGenerator:
    def __init__(self, issues):
        self.issues = issues

    def create_pdf(self, filename="reporte_auditoria.pdf"):
        doc = SimpleDocTemplate(
            filename,
            pagesize=letter,
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.6 * inch,
        )
        page_w = letter[0] - 1.2 * inch
        styles = make_styles()
        story  = []

        story.append(build_header(styles, page_w))
        story.append(Spacer(1, 18))
        story.append(Paragraph(f"HALLAZGOS DETECTADOS  ·  {len(self.issues)} ÍTEM(S)", styles["section_label"]))
        story.append(ColorBar(page_w, 2, ACCENT))
        story.append(Spacer(1, 12))

        for issue in self.issues:
            try:
                story.append(build_card(issue, styles, page_w))
            except Exception as e:
                print(f"Error en hallazgo: {e}")

        story.append(Spacer(1, 14))
        story.append(HRFlowable(width=page_w, thickness=0.5, color=BORDER))
        story.append(Spacer(1, 6))
        story.append(Paragraph("PgGuardian Audit Report  ·  Documento confidencial  ·  Generado automáticamente", styles["footer"]))

        doc.build(story)
        return filename