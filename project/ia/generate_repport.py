from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from datetime import date, datetime
from flask import send_file,abort
from config import Config
import os
import os.path as op
from pathlib import Path


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

def generate_pdf_report(filename, title, sections):
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

    doc.build(story)

def repportLLM(result_llm,anomalies, prompt):
    print(result_llm)
    
    sections = [
        ("Résultat Anomalie constaté : ",anomalies),
        ("Prompt : ", prompt),
        ("#####################", ""),
        ("Résultat IA", result_llm)
    ]

    folder = Path(
        Config.rapport_llm_export,
        datetime.now().strftime("%Y%m%d")
    )

    folder.mkdir(parents=True, exist_ok=True)
    generate_pdf_report(
        filename = op.join(
            folder,
            f"rapport_llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        ),
        title="Rapport de Supervision IA - ",
        sections=sections
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

