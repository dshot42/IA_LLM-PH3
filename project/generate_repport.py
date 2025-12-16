from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from datetime import datetime
from flask import send_file,abort
from config import Config
import os
import os.path as op

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
        story.append(Paragraph(content.replace("\n", "<br/>"), styles["Normal"]))
        story.append(Spacer(1, 16))

    doc.build(story)

def repportLLM(result_llm,anomalies):
    sections = [
        ("Résultat Anomalie constaté : ",anomalies),
        ("Résultat IA", result_llm)
    ]

    datenow = datetime.now().strftime("%Y%m%d_%H%M%S")
    generate_pdf_report(
        filename= op.join(Config.rapport_llm_export,  f"rapport_llm_{datenow}.pdf"),
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

