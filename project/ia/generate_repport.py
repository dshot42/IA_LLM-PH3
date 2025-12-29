from decimal import Decimal
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from datetime import date, datetime
from flask import send_file,abort
from config import Config
import os
import os.path as op
from pathlib import Path
import re
from reportlab.lib.enums import TA_LEFT,TA_CENTER


dark_line = colors.Color(
    11/255,
    15/255,
    23/255,
    alpha=0.85
)

def download_report(repport_name):
    file_path = op.join(Config.rapport_llm_export,repport_name)  # chemin réel du fichier
    if not os.path.exists(file_path):
        abort(404, description="Fichier introuvable")

    return send_file(
        file_path,
        as_attachment=True,
        download_name=repport_name,
        mimetype="application/pdf"
    )

############### PARSE LLM RESULT -> version debug -> texte brut avec prompt  ################# 


def content_to_text(content) -> str:
    """
    Convertit n'importe quel contenu en texte affichable PDF
    (dict, list, datetime, None, etc.)
    """
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, (datetime, date)):
        return content.isoformat()

    if isinstance(content, Decimal):
        return str(float(content))

    if isinstance(content, dict):
        lines = []
        for k, v in content.items():
            lines.append(f"{k} : {v}")
        return "\n".join(lines)

    if isinstance(content, list):
        return "\n".join(str(v) for v in content)

    return str(content)

def generate_pdf_report_debug(filename, title, sections):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story = []

    # Titre
    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    # Date
    story.append(Paragraph(
        f"Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 20))

    # Sections
    for section_title, content in sections:
        story.append(Paragraph(f"<b>{section_title}</b>", styles["Heading2"]))
        story.append(Spacer(1, 8))
        text = content_to_text(content)
        story.append(
            Paragraph(
                text.replace("\n", "<br/>"),
                styles["Normal"]
            )
        )
        story.append(Spacer(1, 16))

    try:
        doc.build(story)
    except Exception as e:
        print("[PDF][TRS] build failed:", e)
        raise

def repportLLM_debug(result_llm, anomalies, prompt):
    
    sections = [
        ("Résultat Anomalie constaté : ",anomalies),
        ("Prompt : ", prompt),
        ("#####################", ""),
        ("Résultat IA", result_llm)
    ]

    folder = Path(
        Config.rapport_llm_export,
        datetime.now().strftime("%Y%m%d"),
        "anomaly",
        "debug"
    )

    folder.mkdir(parents=True, exist_ok=True)
    filename = op.join(
        folder,
        f"rapport_llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )
    generate_pdf_report_debug(
        filename = filename,
        title="Rapport de Supervision IA - ",
        sections=sections
    )
    return filename
    


############### PARSE LLM RESULT -> version clean  ################# 

def build_styles():
    styles = getSampleStyleSheet()

    # =========================
    # TITLE (override)
    # =========================
    title = styles["Title"]
    title.fontSize = 18
    title.leading = 22
    title.fontName = "Helvetica-Bold"
    title.textColor = colors.white
    title.backColor = dark_line
    title.alignment = TA_CENTER
    title.spaceBefore = 16
    title.spaceAfter = 10
    title.leftIndent = 6
    title.rightIndent = 6
    title.borderPadding = (6, 20, 6, 20)

    # =========================
    # SECTION TITLE
    # =========================
    if "SectionTitle" not in styles:
        styles.add(ParagraphStyle(name="SectionTitle"))

    section = styles["SectionTitle"]

    section.fontSize = 13
    section.leading = 16
    section.fontName = "Helvetica-Bold"

    # 🎯 TEXTE
    section.textColor = colors.black
    section.backColor = None 

    # 🎯 ESPACEMENTS
    section.spaceBefore = 16
    section.spaceAfter = 8
    section.leftIndent = 0
    section.rightIndent = 0

    # 🎯 SOULIGNEMENT PROPRE (bordure basse)
    section.borderBottomWidth = 1.2
    section.borderBottomColor = dark_line
    section.borderPadding = (0, 0, 4, 0) 

    # =========================
    # BODY
    # =========================
    if "Body" not in styles:
        styles.add(ParagraphStyle(name="Body"))

    body = styles["Body"]
    body.fontSize = 10.5
    body.leading = 14
    body.spaceAfter = 6
    body.alignment = TA_LEFT

    # =========================
    # META
    # =========================
    if "Meta" not in styles:
        styles.add(ParagraphStyle(name="Meta"))

    meta = styles["Meta"]
    meta.fontSize = 9
    meta.leading = 12
    meta.textColor = colors.HexColor("#555555")

    return styles


def split_llm_sections(text: str):
    """
    Découpe un texte LLM en sections lisibles.
    Tolère :
    - titres finissant par :
    - TITRES EN MAJUSCULES
    - séparateurs =====
    - fallback si aucune section détectée
    """

    sections = {}
    current_title = None
    buffer = []

    lines = text.splitlines()

    def flush():
        nonlocal buffer, current_title
        if current_title and buffer:
            sections[current_title] = "\n".join(buffer).strip()
        buffer = []

    for raw in lines:
        line = raw.strip()

        # ===== TITRE TYPE "====="
        if re.match(r"^=+$", line):
            continue

        # TITRE EXPLICITE "Titre :"
        if line.endswith(":") and len(line) < 80:
            flush()
            current_title = line[:-1].strip()
            continue

        # TITRE EN MAJUSCULES
        if (
            len(line) > 5
            and len(line) < 80
            and line.isupper()
            and not line.endswith(".")
        ):
            flush()
            current_title = line.strip()
            continue

        buffer.append(line)

    flush()

    # 🔒 FALLBACK ABSOLU
    if not sections:
        return {"Analyse": text.strip()}

    return sections


def generate_pdf_report(filename, anomaly_meta, llm_result):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = build_styles()
    story = []

    # =========================
    # PAGE DE GARDE
    # =========================
    story.append(Paragraph(
        "Rapport d’Analyse d’Anomalie de Production",
        styles["Title"]
    ))
    story.append(Spacer(1, 20))

    for k, v in anomaly_meta.items():
        story.append(Paragraph(f"<b>{k}</b> : {v}", styles["Meta"]))

    story.append(Spacer(1, 30))

    # =========================
    # CONTENU LLM STRUCTURÉ
    # =========================
    llm_sections = split_llm_sections(llm_result)

    for title, content in llm_sections.items():
        story.append(Paragraph(title, styles["SectionTitle"]))
        for paragraph in content.split("\n\n"):
            story.append(
                Paragraph(
                    paragraph.replace("\n", "<br/>"),
                    styles["Body"]
                )
            )

    try:
        doc.build(story)
    except Exception as e:
        print("[PDF][TRS] build failed:", e)
        raise
    
    
def repportLLM(result_llm, anomaly, prompt):
    
    repportLLM_debug(result_llm, anomaly, prompt)
    
    
    folder = Path(
        Config.rapport_llm_export,
        datetime.now().strftime("%Y%m%d"),
        "anomaly"
    )
    folder.mkdir(parents=True, exist_ok=True)

    filename = folder / f"rapport_anomalie_{anomaly['id']}.pdf"

    anomaly_meta = {
        "Machine": anomaly["machine"],
        "Step": anomaly["stepId"],
        "Pièce": anomaly["partId"],
        "Cycle": anomaly["cycle"],
        "Sévérité": anomaly["severity"],
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    generate_pdf_report(
        filename=str(filename),
        anomaly_meta=anomaly_meta,
        llm_result=result_llm
    )

    return str(filename)

