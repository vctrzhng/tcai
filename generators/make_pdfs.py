# -*- coding: utf-8 -*-
"""
make_pdfs.py  --  (re)generate the PDF mock contracts and export the DOCX
content for make_docx.js.

Run from anywhere:  python generators/make_pdfs.py
Then:               node generators/make_docx.js
Requires: pip install reportlab

NOTE: The 6 mock contracts are already committed in mock_contracts/. You only
need to run the generators if you want to change or add contracts (edit
contract_content.py and ground_truth.json together).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # for contract_content

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from contract_content import CONTRACTS

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
OUT = os.path.join(REPO_ROOT, "mock_contracts")
os.makedirs(OUT, exist_ok=True)

styles = getSampleStyleSheet()
title_style = ParagraphStyle("ctitle", parent=styles["Title"], fontName="Times-Bold",
                             fontSize=15, alignment=TA_CENTER, spaceAfter=18)
heading_style = ParagraphStyle("cheading", parent=styles["Heading2"], fontName="Times-Bold",
                               fontSize=11, spaceBefore=12, spaceAfter=6)
body_style = ParagraphStyle("cbody", parent=styles["Normal"], fontName="Times-Roman",
                            fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=6)

PDF_KEYS = ["01_northwind_msa_CLEAN", "02_acme_msa_MODERATE",
            "04_initech_services_MESSY", "06_stark_equipment_MODERATE"]
DOCX_KEYS = ["03_globex_saas_MODERATE", "05_umbrella_supply_MESSY"]

for key in PDF_KEYS:
    c = CONTRACTS[key]
    path = os.path.join(OUT, key + ".pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, topMargin=1*inch, bottomMargin=1*inch,
                            leftMargin=1*inch, rightMargin=1*inch, title=c["title"])
    story = [Paragraph(c["title"], title_style), Spacer(1, 6)]
    for heading, body in c["sections"]:
        if heading:
            story.append(Paragraph(heading, heading_style))
        story.append(Paragraph(body, body_style))
    doc.build(story)
    print("wrote", path)

# export DOCX content for the node script
docx_payload = {k: CONTRACTS[k] for k in DOCX_KEYS}
with open(os.path.join(HERE, "docx_content.json"), "w", encoding="utf-8") as f:
    json.dump(docx_payload, f, ensure_ascii=False)
print("wrote", os.path.join(HERE, "docx_content.json"), "(now run: node generators/make_docx.js)")
