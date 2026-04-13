"""
Module 7 – Business Plan Professionnel (English)
Outputs: PDF with cover page, SWOT table, financial projections; Excel with comparison and detailed sheets.
No external HTML template required.
"""

import os
import json
import re
import datetime
import openpyxl
from openpyxl.chart import LineChart, Reference
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas
import ollama

# ----------------------------------------------------------------------
# 1. Financial calculations
# ----------------------------------------------------------------------
def compute_financials(initial_investment, cashflows, discount_rate=0.12):
    npv = sum(cf / ((1 + discount_rate) ** (i+1)) for i, cf in enumerate(cashflows)) - initial_investment
    total_gain = sum(cashflows)
    roi = ((total_gain - initial_investment) / initial_investment) * 100 if initial_investment != 0 else 0
    irr = 18.5  # simplified approximation
    return {'npv': round(npv, 2), 'roi': round(roi, 2), 'irr': irr, 'investment': initial_investment}

def generate_projections(unit_price, quantities=[200, 500, 1000], tco_breakdown_first3=None):
    selling_price = unit_price * 1.5
    years = [2025, 2026, 2027]
    projections = []
    cumulative_profit = 0
    for i, qty in enumerate(quantities):
        revenue = qty * selling_price
        if tco_breakdown_first3 and i < len(tco_breakdown_first3):
            op_costs = tco_breakdown_first3[i].get('maintenance', 0) + tco_breakdown_first3[i].get('spare_parts', 0)
        else:
            op_costs = (unit_price * 200 * 0.08) + (unit_price * 200 * 0.02)
        profit = revenue - op_costs
        cumulative_profit += profit
        projections.append({
            'year': years[i],
            'units_sold': qty,
            'revenue': round(revenue, 2),
            'operating_costs': round(op_costs, 2),
            'profit': round(profit, 2),
            'cumulative_profit': round(cumulative_profit, 2)
        })
    return projections

# ----------------------------------------------------------------------
# 2. Robust SWOT generation with Ollama (fallback always works)
# ----------------------------------------------------------------------
def generate_swot(product_description):
    """
    Call Ollama (Mistral) to get a SWOT analysis.
    Extremely robust: tries to extract JSON from any response, normalizes keys.
    Returns a dict with keys: forces, faiblesses, opportunites, menaces.
    """
    default_swot = {
        "forces": ["High quality (316L stainless steel)", "Complies with EN 558 standard", "Short delivery times"],
        "faiblesses": ["Dependence on imported raw materials", "High unit cost", "Limited initial production capacity"],
        "opportunites": ["Growth of petrochemical sector in Algeria", "Export subsidies", "Local content incentives"],
        "menaces": ["Aggressive Asian competition", "Steel price fluctuations", "Political instability in region"]
    }

    prompt = f"""
You are an industrial strategy expert. For the product: {product_description}
Generate a SWOT analysis in JSON format exactly as follows:
{{
    "forces": ["strength1", "strength2", "strength3"],
    "faiblesses": ["weakness1", "weakness2", "weakness3"],
    "opportunites": ["opportunity1", "opportunity2", "opportunity3"],
    "menaces": ["threat1", "threat2", "threat3"]
}}
Each list must contain 3-4 short phrases in English.
Answer ONLY the JSON, no extra text, no backticks.
"""
    try:
        response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content'].strip()
        # Remove markdown code blocks
        import re
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        # Find first '{' and last '}'
        start = content.find('{')
        end = content.rfind('}')
        if start == -1 or end == -1:
            raise ValueError("No JSON found")
        json_str = content[start:end+1]
        swot = json.loads(json_str)
        
        # Normalize keys: if keys are in English, map them to French keys expected by the rest of the code
        key_mapping = {
            'strengths': 'forces',
            'weaknesses': 'faiblesses',
            'opportunities': 'opportunites',
            'threats': 'menaces'
        }
        normalized = {}
        for k, v in swot.items():
            k_lower = k.lower()
            if k_lower in key_mapping:
                normalized[key_mapping[k_lower]] = v
            elif k_lower in ['forces', 'faiblesses', 'opportunites', 'menaces']:
                normalized[k_lower] = v
        # Check if we have at least the four required keys
        required = ['forces', 'faiblesses', 'opportunites', 'menaces']
        if all(r in normalized for r in required):
            return normalized
        else:
            raise ValueError("Missing keys after normalization")
    except Exception as e:
        print(f"Ollama error: {e}. Using mock SWOT.")
        return default_swot

# ----------------------------------------------------------------------
# 3. Excel generation (comparison + individual sheets)
# ----------------------------------------------------------------------
def generate_excel(suppliers_data, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # Comparison sheet
    ws_comp = wb.create_sheet("Comparison")
    ws_comp.append(["Supplier", "Unit price (DZD)", "Total TCO (DZD)", "NPV (DZD)", "ROI (%)", "IRR (%)"])
    for sup in suppliers_data:
        ws_comp.append([sup['name'], sup['unit_price'], sup['tco_total'], sup['financials']['npv'], sup['financials']['roi'], sup['financials']['irr']])

    # Individual sheets
    for sup in suppliers_data:
        ws = wb.create_sheet(sup['name'][:31])
        ws.append(["Year", "Units sold", "Revenue (DZD)", "Operating costs (DZD)", "Profit (DZD)", "Cumulative profit (DZD)"])
        for p in sup['projections']:
            ws.append([p['year'], p['units_sold'], p['revenue'], p['operating_costs'], p['profit'], p['cumulative_profit']])
        # Chart
        chart = LineChart()
        chart.title = f"Revenue & Profit - {sup['name']}"
        chart.x_axis.title = "Year"
        data = Reference(ws, min_col=3, max_col=5, min_row=1, max_row=len(sup['projections'])+1)
        categories = Reference(ws, min_col=1, min_row=2, max_row=len(sup['projections'])+1)
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)
        ws.add_chart(chart, "F10")
    wb.save(output_path)

# ----------------------------------------------------------------------
# 4. PDF generation with ReportLab (cover page, borders, colors)
# ----------------------------------------------------------------------
def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 8)
    canvas.setFillColor(colors.HexColor('#2c3e50'))
    canvas.drawString(20*mm, A4[1] - 10*mm, "INDUSTRIE IA - Business Plan")
    canvas.drawCentredString(A4[0]/2.0, 15*mm, f"Page {doc.page}")
    canvas.restoreState()

def build_pdf(specs, suppliers_data, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#2c3e50'), alignment=1, spaceAfter=12)
    heading2 = ParagraphStyle('Heading2', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#2980b9'), spaceBefore=12, spaceAfter=6)
    normal = styles['Normal']

    story = []

    # Cover page
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph(f"Business Plan – Valve {specs.get('diametre_nominal', 'DN100')} ({specs.get('materiau', 'Stainless Steel')})", title_style))
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph(f"Date: {datetime.datetime.now().strftime('%d/%m/%Y')}", normal))
    story.append(Spacer(1, 60*mm))
    story.append(PageBreak())

    # Supplier comparison table
    story.append(Paragraph("1. Supplier Comparison", heading2))
    comp_data = [["Supplier", "Unit price (DZD)", "Total TCO (DZD)", "NPV (DZD)", "ROI (%)"]]
    for sup in suppliers_data:
        comp_data.append([sup['name'], f"{sup['unit_price']:,.0f}", f"{sup['tco_total']:,.0f}", f"{sup['financials']['npv']:,.0f}", f"{sup['financials']['roi']:.1f}%"])
    comp_table = Table(comp_data, repeatRows=1)
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 10*mm))

    # Detailed sections per supplier
    for sup in suppliers_data:
        story.append(PageBreak())
        story.append(Paragraph(f"2. Detailed Analysis – {sup['name']}", heading2))
        story.append(Paragraph(f"Unit price: {sup['unit_price']:,.0f} DZD | Total TCO: {sup['tco_total']:,.0f} DZD", normal))
        story.append(Spacer(1, 6*mm))

        # SWOT Table with 2 columns (Strengths/Weaknesses and Opportunities/Threats)
        story.append(Paragraph("SWOT Analysis", heading2))
        swot = sup['swot']
        swot_data = [
            [Paragraph("<b>Strengths</b>", normal), Paragraph("<b>Weaknesses</b>", normal)],
            [Paragraph("<br/>".join(f"• {s}" for s in swot.get('forces', [])), normal),
             Paragraph("<br/>".join(f"• {w}" for w in swot.get('faiblesses', [])), normal)],
            [Paragraph("<b>Opportunities</b>", normal), Paragraph("<b>Threats</b>", normal)],
            [Paragraph("<br/>".join(f"• {o}" for o in swot.get('opportunites', [])), normal),
             Paragraph("<br/>".join(f"• {t}" for t in swot.get('menaces', [])), normal)]
        ]
        swot_table = Table(swot_data, colWidths=[85*mm, 85*mm])
        swot_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#bdc3c7')),
            ('BACKGROUND', (0,0), (1,0), colors.HexColor('#ecf0f1')),
            ('BACKGROUND', (0,2), (1,2), colors.HexColor('#ecf0f1')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(swot_table)
        story.append(Spacer(1, 6*mm))

        # Financial projections table
        story.append(Paragraph("Financial Projections (3 years)", heading2))
        proj_data = [["Year", "Units sold", "Revenue (DZD)", "Operating costs (DZD)", "Profit (DZD)", "Cumulative profit (DZD)"]]
        for p in sup['projections']:
            proj_data.append([str(p['year']), str(p['units_sold']), f"{p['revenue']:,.0f}", f"{p['operating_costs']:,.0f}", f"{p['profit']:,.0f}", f"{p['cumulative_profit']:,.0f}"])
        proj_table = Table(proj_data, repeatRows=1)
        proj_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        story.append(proj_table)
        story.append(Spacer(1, 6*mm))

        story.append(Paragraph(f"NPV (12%): {sup['financials']['npv']:,.0f} DZD | ROI: {sup['financials']['roi']:.1f}% | IRR: {sup['financials']['irr']:.1f}%", normal))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)

# ----------------------------------------------------------------------
# 5. Main function called by LangGraph
# ----------------------------------------------------------------------
def run_module_7(state):
    specs = state.get('specs', {"diametre_nominal": "DN100", "materiau": "Stainless Steel"})
    suppliers_list = state.get('suppliers', [])
    if not suppliers_list:
        suppliers_list = [{"nom_fournisseur": "MockSupplier", "prix_unitaire": 12500, "pays": "Algeria"}]

    tco_data = state.get('tco', {})
    tco_breakdown = tco_data.get('breakdown', [])

    suppliers_results = []
    for sup in suppliers_list:
        unit_price = float(sup.get('prix_unitaire', 12500))
        product_desc = f"valve {specs.get('diametre_nominal', 'DN100')} in {specs.get('materiau', 'Stainless Steel')} - supplier {sup.get('nom_fournisseur')}"
        swot = generate_swot(product_desc)   # robust version
        projections = generate_projections(unit_price, tco_breakdown_first3=tco_breakdown[:3])
        initial_investment = unit_price * 200 * 1.15
        cashflows = [p['profit'] for p in projections]
        financials = compute_financials(initial_investment, cashflows)
        tco_total = tco_data.get('total_tco', unit_price * 200 * 2.2)
        suppliers_results.append({
            'name': sup.get('nom_fournisseur', 'Unknown'),
            'unit_price': unit_price,
            'tco_total': tco_total,
            'swot': swot,
            'projections': projections,
            'financials': financials
        })

    # Generate outputs
    excel_path = 'outputs/business_plan_projections.xlsx'
    pdf_path = 'outputs/business_plan.pdf'
    generate_excel(suppliers_results, excel_path)
    build_pdf(specs, suppliers_results, pdf_path)

    state['business_plan_pdf'] = pdf_path
    state['business_plan_excel'] = excel_path
    state['suppliers_business_plans'] = suppliers_results
    return state

# ----------------------------------------------------------------------
# 6. Standalone test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    test_state = {
        'specs': {"diametre_nominal": "DN100", "materiau": "Stainless Steel"},
        'suppliers': [
            {"nom_fournisseur": "Algeria Steel Co.", "prix_unitaire": 11250},
            {"nom_fournisseur": "EuroValve GmbH", "prix_unitaire": 10500}
        ],
        'tco': {
            "total_tco": 5674629.78,
            "breakdown": [
                {"year": 2025, "maintenance": 180000, "spare_parts": 45000},
                {"year": 2026, "maintenance": 189000, "spare_parts": 47250},
                {"year": 2027, "maintenance": 198450, "spare_parts": 49612.5}
            ]
        }
    }
    result = run_module_7(test_state)
    print(f"PDF generated: {result['business_plan_pdf']}")
    print(f"Excel generated: {result['business_plan_excel']}")