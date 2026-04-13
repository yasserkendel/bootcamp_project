"""
Module 9 – Catalogue multi-format (PDF, HTML, Excel, JSON, XML)
- Pays forcé à "Algérie" pour tous les fournisseurs
- Couleurs sombres et professionnelles
- Affiche tous les fournisseurs avec email et TCO individuel
"""

import os
import json
import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from jinja2 import Environment, FileSystemLoader

# ----------------------------------------------------------------------
# DONNÉES MOCK (si state['suppliers'] absent)
# ----------------------------------------------------------------------
MOCK_SPECS = {
    "diametre_nominal": "DN100",
    "pression_nominale": "40 bar",
    "materiau": {
        "corps": "Fonte GS 400-15",
        "disque": "Inox 316L",
        "siège": "PTFE",
        "tige": "Inox 316",
        "joint": "EPDM"
    },
    "longueur_face_a_face": "229 mm",
    "norme": "EN 558"
}

MOCK_SUPPLIERS = [
    {"nom_fournisseur": "Aciers Algérie SA", "prix_unitaire": 11250, "email": "contact@aciersalgerie.dz", "delai": "15 jours"},
    {"nom_fournisseur": "EuroValve GmbH", "prix_unitaire": 10500, "email": "sales@eurovalve.de", "delai": "30 jours"},
    {"nom_fournisseur": "Tunisie Acier", "prix_unitaire": 10800, "email": "info@tunisieacier.tn", "delai": "20 jours"}
]

# ----------------------------------------------------------------------
# 1. PDF – couleurs sombres, pays forcé "Algérie"
# ----------------------------------------------------------------------
def generate_catalogue_pdf(specs, suppliers_with_tco, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    
    # Couleurs sombres
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18,
                                 textColor=colors.HexColor('#1a252c'), alignment=1, spaceAfter=12)
    heading2 = ParagraphStyle('Heading2', parent=styles['Heading2'], fontSize=14,
                              textColor=colors.HexColor('#2c3e50'), spaceBefore=12, spaceAfter=6)
    normal = styles['Normal']

    story = []

    # Page de garde
    story.append(Paragraph("Catalogue Produit", title_style))
    story.append(Spacer(1, 10*mm))
    matiere = specs.get('materiau', {})
    if isinstance(matiere, dict):
        matiere_str = matiere.get('corps', 'N/A')
    else:
        matiere_str = str(matiere)
    story.append(Paragraph(f"Référence : {specs.get('diametre_nominal', 'N/A')} - {matiere_str}", normal))
    story.append(Paragraph(f"Date : {datetime.datetime.now().strftime('%d/%m/%Y')}", normal))
    story.append(Spacer(1, 20*mm))

    # Spécifications techniques
    story.append(Paragraph("1. Spécifications techniques", heading2))
    flat_specs = {}
    for k, v in specs.items():
        if isinstance(v, dict):
            for subk, subv in v.items():
                flat_specs[f"{k} - {subk}"] = subv
        else:
            flat_specs[k] = v
    spec_data = [[k.capitalize(), str(v)] for k, v in flat_specs.items()]
    spec_table = Table(spec_data, colWidths=[60*mm, 100*mm])
    spec_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#ecf0f1')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(spec_table)
    story.append(Spacer(1, 10*mm))

    # Fournisseurs (pays forcé "Algérie")
    story.append(Paragraph("2. Fournisseurs sélectionnés et TCO", heading2))
    sup_data = [["Fournisseur", "Pays", "Email", "Prix unitaire (DZD)", "Délai", "TCO total (DZD)"]]
    for s in suppliers_with_tco[:5]:
        sup_data.append([
            s.get('nom_fournisseur', ''),
            "Algérie",                                                          # STATIQUE
            s.get('email', ''),
            f"{s.get('prix_unitaire', 0):,.0f}",
            s.get('delai', ''),
            f"{s.get('tco_total', 0):,.0f}"
        ])
    sup_table = Table(sup_data, repeatRows=1)
    sup_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#34495e')),   # en-tête bleu nuit
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    story.append(sup_table)
    story.append(Spacer(1, 10*mm))

    doc.build(story)
    return output_path

# ----------------------------------------------------------------------
# 2. HTML – couleurs sombres, pays statique
# ----------------------------------------------------------------------
def generate_catalogue_html(specs, suppliers_with_tco, output_path):
    template_dir = 'templates'
    os.makedirs(template_dir, exist_ok=True)
    template_path = os.path.join(template_dir, 'catalogue.html')

    default_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Catalogue produit</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 2cm; background-color: #f5f7fa; }
        h1 { color: #1a252c; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }
        h2 { color: #2c3e50; margin-top: 30px; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 25px; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        th, td { border: 1px solid #bdc3c7; padding: 10px; text-align: left; }
        th { background-color: #34495e; color: white; font-weight: bold; }
        .spec-table td:first-child { background-color: #ecf0f1; font-weight: bold; }
        footer { font-size: 10px; text-align: center; margin-top: 40px; color: #7f8c8d; }
    </style>
</head>
<body>
    <h1>Catalogue produit</h1>
    <p>Référence : {{ specs.diametre_nominal }} - {% if specs.materiau is mapping %}{{ specs.materiau.corps }}{% else %}{{ specs.materiau }}{% endif %}</p>
    <p>Date : {{ date }}</p>
    
    <h2>Spécifications techniques</h2>
    <table class="spec-table">
        {% for key, value in specs.items() %}
            {% if value is mapping %}
                {% for subkey, subvalue in value.items() %}
                <tr>
                    <th>{{ key }} - {{ subkey }}</th>
                    <td>{{ subvalue }}</td>
                </tr>
                {% endfor %}
            {% else %}
            <tr>
                <th>{{ key }}</th>
                <td>{{ value }}</td>
            </tr>
            {% endif %}
        {% endfor %}
    </table>
    
    <h2>Fournisseurs et TCO</h2>
    <table>
        <tr>
            <th>Nom</th><th>Pays</th><th>Email</th><th>Prix unitaire (DZD)</th><th>Délai</th><th>TCO total (DZD)</th>
        </tr>
        {% for s in suppliers %}
        <tr>
            <td>{{ s.nom_fournisseur }}</td>
            <td>Algérie</td>                <!-- STATIQUE -->
            <td>{{ s.email }}</td>
            <td>{{ s.prix_unitaire }}</td>
            <td>{{ s.delai }}</td>
            <td>{{ s.tco_total }}</td>
        </tr>
        {% endfor %}
    </table>
    <footer>Document généré automatiquement par INDUSTRIE IA</footer>
</body>
</html>"""
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(default_template)

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('catalogue.html')
    html_content = template.render(
        specs=specs,
        suppliers=suppliers_with_tco,
        date=datetime.datetime.now().strftime("%d/%m/%Y")
    )
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    return output_path

# ----------------------------------------------------------------------
# 3. Excel – pays statique "Algérie"
# ----------------------------------------------------------------------
def generate_catalogue_excel(specs, suppliers_with_tco, output_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Catalogue"

    # Titre
    ws.merge_cells('A1:F1')
    ws['A1'] = "Catalogue produit"
    ws['A1'].font = Font(size=16, bold=True)
    ws['A1'].alignment = Alignment(horizontal='center')

    # Spécifications
    row = 3
    ws.cell(row=row, column=1, value="Spécifications").font = Font(bold=True)
    row += 1
    for k, v in specs.items():
        if isinstance(v, dict):
            for subk, subv in v.items():
                ws.cell(row=row, column=1, value=f"{k} - {subk}")
                ws.cell(row=row, column=2, value=str(subv))
                row += 1
        else:
            ws.cell(row=row, column=1, value=k.capitalize())
            ws.cell(row=row, column=2, value=str(v))
            row += 1
    row += 1

    # Fournisseurs (pays forcé)
    ws.cell(row=row, column=1, value="Fournisseurs et TCO").font = Font(bold=True)
    row += 1
    headers = ["Nom", "Pays", "Email", "Prix unitaire (DZD)", "Délai", "TCO total (DZD)"]
    for col, h in enumerate(headers, 1):
        ws.cell(row=row, column=col, value=h).font = Font(bold=True)
    row += 1
    for s in suppliers_with_tco[:5]:
        ws.cell(row=row, column=1, value=s.get('nom_fournisseur', ''))
        ws.cell(row=row, column=2, value="Algérie")          # STATIQUE
        ws.cell(row=row, column=3, value=s.get('email', ''))
        ws.cell(row=row, column=4, value=s.get('prix_unitaire', 0))
        ws.cell(row=row, column=5, value=s.get('delai', ''))
        ws.cell(row=row, column=6, value=s.get('tco_total', 0))
        row += 1

    # Ajuster largeur colonnes
    for col in ws.columns:
        max_len = 0
        col_letter = None
        for cell in col:
            if col_letter is None and hasattr(cell, 'column_letter'):
                col_letter = cell.column_letter
            try:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            except:
                pass
        if col_letter:
            ws.column_dimensions[col_letter].width = min(max_len + 2, 30)

    wb.save(output_path)
    return output_path

# ----------------------------------------------------------------------
# 4. JSON – pays statique "Algérie"
# ----------------------------------------------------------------------
def generate_catalogue_json(specs, suppliers_with_tco, output_path):
    # On recrée la liste des fournisseurs avec pays forcé
    suppliers_fixed = []
    for s in suppliers_with_tco:
        suppliers_fixed.append({
            "nom": s.get('nom_fournisseur'),
            "pays": "Algérie",
            "email": s.get('email'),
            "prix_unitaire": s.get('prix_unitaire'),
            "delai": s.get('delai'),
            "tco_total": s.get('tco_total')
        })
    data = {
        "product": specs,
        "suppliers": suppliers_fixed,
        "generated_at": datetime.datetime.now().isoformat()
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return output_path

# ----------------------------------------------------------------------
# 5. XML – pays statique "Algérie"
# ----------------------------------------------------------------------
def generate_catalogue_xml(specs, suppliers_with_tco, output_path):
    root = ET.Element("catalogue")
    ET.SubElement(root, "generated_at").text = datetime.datetime.now().isoformat()

    product = ET.SubElement(root, "product")
    for k, v in specs.items():
        if isinstance(v, dict):
            sub_elem = ET.SubElement(product, k)
            for subk, subv in v.items():
                ET.SubElement(sub_elem, subk).text = str(subv)
        else:
            ET.SubElement(product, k).text = str(v)

    suppliers_elem = ET.SubElement(root, "suppliers")
    for s in suppliers_with_tco[:5]:
        sup = ET.SubElement(suppliers_elem, "supplier")
        ET.SubElement(sup, "name").text = s.get('nom_fournisseur', '')
        ET.SubElement(sup, "country").text = "Algérie"               # STATIQUE
        ET.SubElement(sup, "email").text = s.get('email', '')
        ET.SubElement(sup, "unit_price").text = str(s.get('prix_unitaire', 0))
        ET.SubElement(sup, "lead_time").text = s.get('delai', '')
        ET.SubElement(sup, "tco_total").text = str(s.get('tco_total', 0))

    xml_str = ET.tostring(root, encoding='utf-8')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    return output_path

# ----------------------------------------------------------------------
# 6. Fonction principale
# ----------------------------------------------------------------------
def run_module_9(state):
    specs = state.get('specs', MOCK_SPECS)
    suppliers = state.get('suppliers', MOCK_SUPPLIERS)

    # Récupérer les TCO par fournisseur depuis state['all_tco'] (produit par module 6)
    all_tco = state.get('all_tco', [])
    tco_map = {}
    if all_tco:
        for item in all_tco:
            sup_info = item.get('supplier_info', {})
            tco_res = item.get('tco_result', {})
            nom = sup_info.get('nom_fournisseur')
            if nom:
                tco_map[nom] = tco_res.get('total_tco', 0)
    else:
        # Générer des TCO mock
        for s in suppliers:
            unit_price = s.get('prix_unitaire', 10000)
            tco_map[s.get('nom_fournisseur')] = round(unit_price * 200 * 2.2, 2)

    # Construire la liste des fournisseurs avec leur TCO
    suppliers_with_tco = []
    for s in suppliers:
        suppliers_with_tco.append({
            'nom_fournisseur': s.get('nom_fournisseur'),
            'email': s.get('email', ''),
            'prix_unitaire': s.get('prix_unitaire'),
            'delai': s.get('delai'),
            'tco_total': tco_map.get(s.get('nom_fournisseur'), 0)
        })

    os.makedirs('outputs', exist_ok=True)

    pdf_path = generate_catalogue_pdf(specs, suppliers_with_tco, 'outputs/catalogue.pdf')
    html_path = generate_catalogue_html(specs, suppliers_with_tco, 'outputs/catalogue.html')
    excel_path = generate_catalogue_excel(specs, suppliers_with_tco, 'outputs/catalogue.xlsx')
    json_path = generate_catalogue_json(specs, suppliers_with_tco, 'outputs/catalogue.json')
    xml_path = generate_catalogue_xml(specs, suppliers_with_tco, 'outputs/catalogue.xml')

    state['catalogue_files'] = [pdf_path, html_path, excel_path, json_path, xml_path]
    return state

# ----------------------------------------------------------------------
# 7. Test indépendant
# ----------------------------------------------------------------------
if __name__ == "__main__":
    test_state = {}
    result = run_module_9(test_state)
    print("Catalogue généré :")
    for f in result['catalogue_files']:
        print(f"  - {f}")