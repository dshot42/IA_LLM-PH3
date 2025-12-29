from decimal import Decimal
from typing import List
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
from ia.generate_repport import build_styles


dark_line = colors.Color(
    11/255,
    15/255,
    23/255,
    alpha=0.85
)

############### TRS #############

def repportLLM_TRS(
    result_llm: str,
    trs: dict,
    impact: List[dict],
    dateStart,
    dateEnd,
    prompt: str
):
    # Debug
    repportLLM_TRS_debug(result_llm, trs, impact, dateStart, dateEnd, prompt)

    folder = Path(
        Config.rapport_llm_export,
        datetime.now().strftime("%Y%m%d"),
        "trs"
    )
    folder.mkdir(parents=True, exist_ok=True)

    filename = folder / f"rapport_trs_{datetime.now().strftime('%H%M%S')}.pdf"

    # =========================
    # MÉTA TRS
    # =========================
    trs_meta = {
        "Période analysée": f"{dateStart} → {dateEnd}",

        "TRS global (Performance × Qualité)": {
            "valeur": round(trs["trs"], 4),
            "definition": "Correspond à la performance multipliée par la qualité"
        },

        "Performance de production": {
            "valeur": round(trs["performance"], 4),
            "definition": "Correspond au rendement machine : Temps nominal / Temps réel"
        },

        "Qualité": {
            "valeur": round(trs["quality"], 4),
            "definition": "Correspond au ratio pièces bonnes / pièces totales"
        },

        "Étapes analysées": trs["totalSteps"],

        "Étapes bonnes": {
            "valeur": trs["goodSteps"],
            "definition": "Nombre d’étapes exécutées conformément au workflow nominal"
        },

        "Étapes mauvaises": {
            "valeur": trs["badSteps"],
            "definition": "Nombre d’étapes présentant un écart ou une anomalie"
        },

        "Temps nominal cumulé (s)": {
            "valeur": round(trs["totalTheoreticalTimeS"], 2),
            "definition": "Somme des durées nominales attendues pour les étapes analysées"
        },

        "Temps réel cumulé (s)": {
            "valeur": round(trs["totalRealTimeS"], 2),
            "definition": "Somme des durées réellement observées pour les étapes analysées"
        },

        "Date génération": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


    impact_table = [
        {
            "Machine": l["machineCode"],
            "Step": l["stepCode"],
            "Occurrences": l["occurrences"],
            "Sur-durée totale (s)": round(l["totalOverrunS"], 2),
            "Impact TRS (%)": round(l["impactPercentTRS"], 2),
            "Score danger": round(l["dangerScore"], 3),
            "Renforcement": "OUI" if l["reinforcing"] else "NON"
        }
        for l in impact.values()
    ]

    generate_pdf_report_TRS(
        filename=str(filename),
        trs_meta=trs_meta,
        impact_table=impact_table,
        llm_result=result_llm
    )

    return str(filename)



######### GENERATE TRS REPPORT #########

def _escape_paragraph(text: str) -> str:
    if text is None:
        return ""
    # Échappement minimal pour ReportLab Paragraph (XML-ish)
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))

def _truncate(text: str, max_chars: int = 1800) -> str:
    if text is None:
        return ""
    t = str(text)
    return t if len(t) <= max_chars else t[:max_chars] + "\n...[TRONQUÉ]..."

def _kv_table(data: dict, col_widths=(6*cm, 10*cm)):
    """
    Affiche un dict key/value en table propre.
    """
    rows = [[Paragraph(f"<b>{_escape_paragraph(k)}</b>", getSampleStyleSheet()["BodyText"]),
             Paragraph(_escape_paragraph(v), getSampleStyleSheet()["BodyText"])]
            for k, v in data.items()]

    table = Table(rows, colWidths=list(col_widths), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, dark_line),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table

def _impact_table(impact_table: list):
    """
    Table structurée impacts.
    impact_table: List[dict] avec clés Machine, Step, Occurrences, Sur-durée..., etc.
    """
    headers = ["Machine", "Step", "Occurrences", "Overrun(s)", "Impact TRS(%)", "Danger", "Renforcement"]
    data = [headers]

    for l in impact_table:
        data.append([
            str(l.get("Machine", "")),
            str(l.get("Step", "")),
            str(l.get("Occurrences", "")),
            str(l.get("Sur-durée totale (s)", "")),
            str(l.get("Impact TRS (%)", "")),
            str(l.get("Score danger", "")),
            str(l.get("Renforcement", "")),
        ])

    table = Table(
        data,
        colWidths=[2.0*cm, 2.2*cm, 1.2*cm, 2.2*cm, 2.4*cm, 1.8*cm, 1.6*cm],
        hAlign="LEFT"
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),

        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return table

def generate_pdf_report_TRS(filename, trs_meta, impact_table, llm_result, dateStart=None, dateEnd=None, prompt=None):
    """
    ✅ Rapport TRS principal (non-debug)
    - Ajoute période + prompt + TRS détails + impacts détaillés + analyse LLM
    - NOTE: pour garder ton fonctionnement, dateStart/dateEnd/prompt sont optionnels.
      Si tu veux les afficher, passe-les depuis repportLLM_TRS (recommandé).
    """

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = build_styles()
    story = []

    # =========================
    # TITRE
    # =========================
    story.append(Paragraph("Rapport d’Analyse TRS — Supervision Industrielle", styles["Title"]))
    story.append(Spacer(1, 10))

    # =========================
    # PÉRIODE + DATE GÉNÉRATION
    # =========================
    period_line = trs_meta.get("Période analysée", None)
    if dateStart is not None and dateEnd is not None:
        period_line = f"{dateStart} → {dateEnd}"
    if period_line:
        story.append(Paragraph(f"<b>Période analysée</b> : {_escape_paragraph(period_line)}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Date génération</b> : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["BodyText"]))
    story.append(Spacer(1, 14))

    # =========================
    # TRS GLOBAL (DÉTAILS)
    # =========================
    story.append(Paragraph("Synthèse TRS", styles["Heading2"] if "Heading2" in styles else styles["Heading2"]))
    story.append(Spacer(1, 6))
    # table key/value lisible
    story.append(_kv_table(trs_meta))
    story.append(Spacer(1, 16))

    # =========================
    # PROMPT UTILISÉ (EXTRAIT)
    # =========================
    if prompt:
        story.append(Paragraph("Prompt utilisé (extrait)", styles["Heading2"] if "Heading2" in styles else styles["Heading2"]))
        story.append(Spacer(1, 6))
        story.append(Paragraph(_escape_paragraph(_truncate(prompt, 2200)).replace("\n", "<br/>"), styles["BodyText"]))
        story.append(Spacer(1, 16))

    # =========================
    # IMPACTS (TABLE DÉTAILLÉE)
    # =========================
    story.append(Paragraph("Impacts TRS par Step / Machine", styles["Heading2"] if "Heading2" in styles else styles["Heading2"]))
    story.append(Spacer(1, 8))

    if impact_table and isinstance(impact_table, list):
        story.append(_impact_table(impact_table))
    else:
        story.append(Paragraph("Aucun impact disponible.", styles["BodyText"]))

    story.append(Spacer(1, 18))

    # =========================
    # ANALYSE LLM
    # =========================
    
    story.append(PageBreak())

    story.append(Paragraph("Analyse IA", styles["Title"]))
    story.append(Spacer(1, 8))

    llm_sections = split_llm_sections(llm_result) if "split_llm_sections" in globals() else {"Résultat": llm_result}

    for title, content in llm_sections.items():
        story.append(Paragraph(_escape_paragraph(title), styles["Heading3"] if "Heading3" in styles else styles["Heading2"]))
        story.append(Spacer(1, 6))
        safe = _escape_paragraph(content)
        for paragraph in safe.split("\n\n"):
            story.append(Paragraph(paragraph.replace("\n", "<br/>"), styles["BodyText"]))
            story.append(Spacer(1, 6))

    try:
        doc.build(story)
    except Exception as e:
        print("[PDF][TRS] build failed:", e)
        raise


def repportLLM_TRS_debug(result, trs, impact, dateStart, dateEnd, prompt):

    sections = [
        ("Impacts TRS agrégés", impact),
        ("Date début", dateStart),
        ("Date fin", dateEnd),
        ("Prompt LLM", prompt),
        ("TRS Global", trs),
        ("Résultat IA", result)
    ]

    folder = Path(
        Config.rapport_llm_export,
        datetime.now().strftime("%Y%m%d"),
        "trs",
        "debug"
    )
    folder.mkdir(parents=True, exist_ok=True)

    filename = op.join(
        folder,
        f"rapport_llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    generate_pdf_report_TRS_debug(
        filename=filename,
        title=f"Rapport TRS DEBUG — {dateStart} → {dateEnd}",
        sections=sections
    )

    return filename


def _trs_debug_content_to_text(content):
    """
    Conversion robuste vers texte lisible debug
    """
    if content is None:
        return "∅"

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        return "\n".join(f"{k} : {v}" for k, v in content.items())

    if isinstance(content, list):
        if not content:
            return "(liste vide)"
        lines = []
        for i, item in enumerate(content, 1):
            lines.append(f"[{i}] {_trs_debug_content_to_text(item)}")
        return "\n".join(lines)

    return str(content)


def generate_pdf_report_TRS_debug(filename, title, sections):
    """
    Rapport DEBUG TRS
    - sections : List[(title, content)]
    - content peut être str | dict | list
    """

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()
    story = []

    # =========================
    # TITRE
    # =========================
    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        f"Généré le : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        styles["Normal"]
    ))
    story.append(Spacer(1, 20))

    # =========================
    # SECTIONS DEBUG
    # =========================
    for section_title, content in sections:
        story.append(Paragraph(f"<b>{section_title}</b>", styles["Heading2"]))
        story.append(Spacer(1, 8))

        text = _trs_debug_content_to_text(content)

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

