from decimal import Decimal
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,HRFlowable
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from datetime import date, datetime
from flask import send_file, abort
from pathlib import Path
import os
import os.path as op
import re
from config import Config

# ======================================================
# CONSTANTS
# ======================================================

dark_line = colors.Color(11/255, 15/255, 23/255, alpha=0.85)

# ======================================================
# DEBUG UTIL
# ======================================================

def content_to_text(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (datetime, date)):
        return content.isoformat()
    if isinstance(content, Decimal):
        return str(float(content))
    if isinstance(content, dict):
        return "\n".join(f"{k} : {v}" for k, v in content.items())
    if isinstance(content, list):
        return "\n".join(str(v) for v in content)
    return str(content)


    
def render_recurrence_analysis(story, styles, r):
    if not r:
        return

    story.append(PageBreak())

    story.append(Paragraph(
        "ANALYSE DE RÉCURRENCE TEMPORELLE",
        styles["SectionTitle"]
    ))

    text = f"""
    <b>Fenêtre d’analyse</b> : {r['windowDays']} jours<br/>
    <i>Période temporelle utilisée pour analyser la répétition des anomalies similaires.</i><br/><br/>

    <b>Occurrences observées</b> : {r['totalOccurrences']}<br/>
    <i>Nombre total d’anomalies similaires détectées sur la période analysée.</i><br/><br/>

    <b>Intervalle moyen entre occurrences</b> : {r['meanIntervalS']:.2f} s<br/>
    <i>Temps moyen séparant deux anomalies successives. Un intervalle court indique une récurrence élevée.</i><br/><br/>

    <b>Écart-type de l’intervalle</b> : {r['stdDevIntervalS']:.2f} s<br/>
    <i>Mesure de la variabilité des intervalles. Une valeur faible indique une répétition régulière.</i><br/><br/>

    <b>Overrun moyen</b> : {r['meanOverrunS']:.2f} s<br/>
    <i>Écart moyen entre la durée réelle et la durée nominale lors des anomalies.</i><br/><br/>

    <b>Écart-type de l’overrun</b> : {r['stdDevOverrunS']:.2f} s<br/>
    <i>Variabilité de l’impact temporel des anomalies sur le cycle de production.</i><br/><br/>

    <b>Fréquence des anomalies en hausse</b> : {"OUI" if r['frequencyIncreasing'] else "NON"}<br/>
    <i>Indique si les anomalies surviennent de plus en plus fréquemment au fil du temps.</i><br/><br/>

    <b>Impact temporel en hausse</b> : {"OUI" if r['overrunIncreasing'] else "NON"}<br/>
    <i>Indique si l’impact des anomalies sur la durée du cycle tend à s’aggraver.</i><br/><br/>

    <b>Conclusion de tendance globale</b> : 
    <b>{r['trendConclusion']}</b><br/>
    <i>Synthèse de l’évolution temporelle combinant fréquence et impact.</i>
    """

    story.append(Paragraph(text, styles["Body"]))


# ======================================================
# STYLES
# ======================================================
def SectionTitle(text: str,styles):
    return [
        Paragraph(text, styles["SectionTitle"]),
        HRFlowable(
            width="100%",
            thickness=1.1,
            color=dark_line,
            spaceBefore=2,
            spaceAfter=10
        )
    ]
    
def build_styles():
    styles = getSampleStyleSheet()

    styles["Title"].fontSize = 18
    styles["Title"].leading = 22
    styles["Title"].fontName = "Helvetica-Bold"
    styles["Title"].textColor = colors.white
    styles["Title"].backColor = dark_line
    styles["Title"].alignment = TA_CENTER
    styles["Title"].borderPadding = 12

    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=13.5,
        leading=17,
        textColor=colors.black,
        spaceBefore=18,
        spaceAfter=4,
    ))


    styles.add(ParagraphStyle(
        name="Body",
        fontSize=10.5,
        leading=14,
        alignment=TA_LEFT
    ))

    styles.add(ParagraphStyle(
        name="BlockBox",
        fontSize=10,
        leading=14,
        backColor=colors.HexColor("#F5F7FA"),
        borderColor=colors.grey,
        borderWidth=1.5,
        borderPadding=10,
        spaceBefore=12,
        spaceAfter=16
    ))

    return styles

# ======================================================
# LLM PARSER
# ======================================================

def split_llm_sections(text: str):
    sections = {}
    current_title = None
    buffer = []

    def flush():
        nonlocal buffer, current_title
        if current_title and buffer:
            sections[current_title] = "\n".join(buffer).strip()
        buffer = []

    for raw in text.splitlines():
        line = raw.strip()

        if re.match(r"^=+$", line):
            continue

        if line.endswith(":") and len(line) < 80:
            flush()
            current_title = line[:-1].strip()
            continue

        if line.isupper() and 5 < len(line) < 80:
            flush()
            current_title = line
            continue

        buffer.append(line)

    flush()
    return sections or {"Analyse": text.strip()}

# ======================================================
# RENDER BLOCKS
# ======================================================

def render_anomaly_block(story, styles, ctx):
    lines = [
        f"<b>Machine</b> : {ctx['machineCode']} – {ctx.get('machineName','')}",
        f"<b>Étape</b> : {ctx['stepCode']} – {ctx.get('stepName','')}",
        f"<b>Date détection</b> : {ctx['detectedAt']}",
        f"<b>Pièce concernée</b> : {ctx.get('partId', 'N/A')}",
        f"<b>Sévérité</b> : <font color='red'><b>{ctx['severity']}</b></font>",
        f"<b>Score anomalie</b> : {ctx['anomalyScore']}",
        f"<b>Durée nominale</b> : {ctx['nominalDurationS']} s",
        f"<b>Durée réelle</b> : {ctx['realDurationS']} s",
        f"<b>Dépassement</b> : {ctx['overrunS']} s",
        f"<b>Erreur PLC</b> : {'OUI' if ctx['hasPlcError'] else 'NON'}"
    ]

    if ctx.get("triggeredRules"):
        lines.append("<b>Règles déclenchées :</b>")
        for r in ctx["triggeredRules"]:
            lines.append(f"- {r.get('ruleCode')} : {r.get('message')}")

    story.append(Paragraph("<br/>".join(lines), styles["BlockBox"]))



def render_workflow(story, styles, cycle_trace):
    story.append(Spacer(1, 20))
    story.append(Paragraph("WORKFLOW DU CYCLE", styles["SectionTitle"]))
    story.append(Spacer(1, 20))
    
    if not cycle_trace:
        story.append(Paragraph("Aucun workflow disponible.", styles["Body"]))
        return

    current_machine = None
    step_buffer = []

    def flush_machine_block(machine, steps, with_arrow_down=True):
        if not machine or not steps:
            return

        content = f"""
        <b>{machine}</b><br/>
        {" → ".join(steps)}
        """

        story.append(
            Paragraph(content, styles["BlockBox"])
        )


        if with_arrow_down:
            story.append(Paragraph("↓", styles["Body"]))

        story.append(Spacer(1, 6))

    for s in cycle_trace:
        machine = s.get("machineCode")
        step = s.get("stepCode")

        if not machine or not step:
            continue

        label = step
        if s.get("anomalyDetected"):
            label = f"<font color='red'><b>{label}</b></font>"

        # changement de machine
        if current_machine and machine != current_machine:
            flush_machine_block(current_machine, step_buffer, with_arrow_down=True)
            step_buffer = []

        current_machine = machine
        step_buffer.append(label)

    # dernier bloc sans flèche ↓
    flush_machine_block(current_machine, step_buffer, with_arrow_down=False)



# ======================================================
# 🔥 TABLE DES ANOMALIES SIMILAIRES (PlcAnomalyDto)
# ======================================================

def render_similar_anomalies_table(story, styles, anomalies):

    story.append(PageBreak())

    story.append(Paragraph(
        "HISTORIQUE DES ANOMALIES SIMILAIRES",
        styles["SectionTitle"]
    ))

    story.append(Spacer(1, 20))

    if not anomalies:
        story.append(
            "Aucune Anomalies similaire detecté sur les 7 derniers jours "
        )
        return
    
    data = [["Date PLC", "Étape", "Nom étape","Anomalie type"]]

    for a in anomalies:
        data.append([
            a.get("plcEventTs"),
            a.get("productionStepCode"),
            a.get("productionStepName"),
            a.get("ruleReason")
        ])
        

    table = Table(data, colWidths=[4*cm,3*cm, 4*cm, 7*cm])
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

    story.append(table)
    
    

def render_llm_analysis(story, styles, llm_text):
    if not llm_text:
        return

    story.append(PageBreak())
    
    sections = split_llm_sections(llm_text)

    story.append(Paragraph("ANALYSE IA (LLM)", styles["Title"]))

    for title, content in sections.items():
        story.append(Paragraph(title, styles["SectionTitle"]))
        story.append(Paragraph(content.replace("\n", "<br/>"), styles["Body"]))

# ======================================================
# MAIN PIPELINE
# ======================================================

def generate_pdf_report(filename, anomaly, llm_result):
    ctx = anomaly["anomalyContext"]

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

    story.append(Paragraph(
        "Rapport d’Analyse d’Anomalie de Production",
        styles["Title"]
    ))
    story.append(Spacer(1, 20))

    render_anomaly_block(story, styles, ctx)
    render_workflow(story, styles, ctx["cycleTrace"])
    render_recurrence_analysis(story, styles, ctx.get("reccurenceAnomalyAnalyseDto"))
    render_similar_anomalies_table(
        story, styles, ctx.get("allSimilarAnomalies", [])
    )
    render_llm_analysis(story, styles, llm_result)

    doc.build(story)

# ======================================================
# ENTRY POINT
# ======================================================

def repportLLM(result_llm, anomaly, prompt):
    folder = Path(
        Config.rapport_llm_export,
        datetime.now().strftime("%Y%m%d"),
        "anomaly"
    )
    folder.mkdir(parents=True, exist_ok=True)

    filename = folder / f"rapport_anomalie_{anomaly['id']}.pdf"
    generate_pdf_report(str(filename), anomaly, result_llm)
    return str(filename)

def download_report(repport_name):
    file_path = op.join(Config.rapport_llm_export, repport_name)
    if not os.path.exists(file_path):
        abort(404, description="Fichier introuvable")

    return send_file(
        file_path,
        as_attachment=True,
        download_name=repport_name,
        mimetype="application/pdf"
    )
