import os
import json
import requests
import openpyxl
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Font, Alignment

def get_inflation_algeria(years=10):
    url = "https://api.worldbank.org/v2/country/DZ/indicator/FP.CPI.TOTL.ZG?format=json"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        records = data[1]
        inflation = []
        for r in records:
            if r['value'] is not None:
                inflation.append(float(r['value']))
        if len(inflation) > years:
            inflation = inflation[-years:]
        elif len(inflation) < years:
            last = inflation[-1] if inflation else 5.0
            inflation.extend([last] * (years - len(inflation)))
        return inflation
    except Exception:
        return [5.0] * years

def compute_tco_for_supplier(unit_price, quantity=200, years=10, inflation_rates=None):
    if inflation_rates is None:
        inflation_rates = [0.0] * years
    purchase = unit_price * quantity
    installation = purchase * 0.15
    total = purchase + installation
    maint_base = purchase * 0.08
    spare_base = purchase * 0.02
    breakdown = []
    cumul_inflation = 1.0
    for y in range(1, years + 1):
        if y <= len(inflation_rates):
            cumul_inflation *= (1 + inflation_rates[y-1] / 100)
        maint = maint_base * cumul_inflation
        spare = spare_base * cumul_inflation
        total += maint + spare
        breakdown.append({
            'year': 2025 + y - 1,
            'maintenance': round(maint, 2),
            'spare_parts': round(spare, 2),
            'cumulative_tco': round(total, 2)
        })
    return {
        'total_tco': round(total, 2),
        'purchase': round(purchase, 2),
        'installation': round(installation, 2),
        'breakdown': breakdown
    }

def create_supplier_sheet(wb, supplier_info, tco_result, inflation_rates, quantity):
    sheet_name = supplier_info.get('nom_fournisseur', 'Fournisseur')[:31]
    ws = wb.create_sheet(title=sheet_name)
    ws.append(["Année", "Maintenance (DZD)", "Pièces (DZD)", "TCO cumulé (DZD)"])
    for yd in tco_result['breakdown']:
        ws.append([yd['year'], yd['maintenance'], yd['spare_parts'], yd['cumulative_tco']])
    last_row = ws.max_row + 1
    ws.cell(row=last_row, column=1, value="TOTAL TCO")
    ws.cell(row=last_row, column=4, value=tco_result['total_tco']).font = Font(bold=True)
    chart = BarChart()
    chart.title = f"TCO cumulé - {supplier_info.get('nom_fournisseur')}"
    chart.x_axis.title = "Année"
    chart.y_axis.title = "DZD"
    data = Reference(ws, min_col=4, max_col=4, min_row=1, max_row=len(tco_result['breakdown'])+1)
    categories = Reference(ws, min_col=1, min_row=2, max_row=len(tco_result['breakdown'])+1)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(categories)
    ws.add_chart(chart, "E5")
    ws_params = wb.create_sheet(title=f"Params_{sheet_name[:20]}")
    ws_params.append(["Paramètre", "Valeur"])
    ws_params.append(["Fournisseur", supplier_info.get('nom_fournisseur')])
    ws_params.append(["Pays", "Algérie"])
    ws_params.append(["Email", supplier_info.get('email', '')])   # AJOUT
    ws_params.append(["Prix unitaire (DZD)", supplier_info.get('prix_unitaire')])
    ws_params.append(["Quantité", quantity])
    ws_params.append(["Coût d'achat total (DZD)", tco_result['purchase']])
    ws_params.append(["Coût installation (15%)", tco_result['installation']])
    ws_params.append(["Taux inflation (%)", ", ".join(map(str, inflation_rates))])

def create_summary_sheet(wb, suppliers_results, quantity):
    ws = wb.create_sheet(title="Comparatif TCO", index=0)
    ws.append(["Fournisseur", "Pays", "Email", "Prix unitaire (DZD)", "TCO total (DZD)", "Coût achat (DZD)", "Installation (DZD)"])
    for sup in suppliers_results:
        sup_info = sup['supplier_info']
        ws.append([
            sup_info.get('nom_fournisseur'),
            "Algérie",
            sup_info.get('email', ''),   # AJOUT
            sup_info.get('prix_unitaire'),
            sup['tco_result']['total_tco'],
            sup['tco_result']['purchase'],
            sup['tco_result']['installation']
        ])
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_len:
                    max_len = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[col_letter].width = min(max_len + 2, 30)

def generate_global_json(suppliers_results, inflation_rates, quantity, output_path='outputs/tco_data.json'):
    data = {
        "quantity": quantity,
        "inflation_rates": inflation_rates,
        "suppliers": []
    }
    for sup in suppliers_results:
        sup_info = sup['supplier_info']
        data["suppliers"].append({
            "nom": sup_info.get('nom_fournisseur'),
            "pays": "Algérie",
            "email": sup_info.get('email', ''),   # AJOUT
            "prix_unitaire": sup_info.get('prix_unitaire'),
            "total_tco": sup['tco_result']['total_tco'],
            "purchase": sup['tco_result']['purchase'],
            "installation": sup['tco_result']['installation'],
            "breakdown": sup['tco_result']['breakdown']
        })
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return output_path

def run_module_6(state):
    suppliers = state.get('suppliers', [])
    if not suppliers:
        suppliers = [{
            "nom_fournisseur": "MockFournisseur",
            "pays": "Algérie",
            "email": "contact@mock.com",   # AJOUT mock
            "prix_unitaire": 12500
        }]
    quantity = 200
    inflation_rates = get_inflation_algeria(10)
    suppliers_results = []
    for sup in suppliers:
        unit_price = float(sup.get('prix_unitaire', 12500))
        tco_result = compute_tco_for_supplier(unit_price, quantity, 10, inflation_rates)
        suppliers_results.append({
            'supplier_info': sup,
            'tco_result': tco_result
        })
    excel_path = 'outputs/tco_report.xlsx'
    os.makedirs('outputs', exist_ok=True)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    create_summary_sheet(wb, suppliers_results, quantity)
    for res in suppliers_results:
        create_supplier_sheet(wb, res['supplier_info'], res['tco_result'], inflation_rates, quantity)
    wb.save(excel_path)
    json_path = generate_global_json(suppliers_results, inflation_rates, quantity, 'outputs/tco_data.json')
    state['tco'] = suppliers_results[0]['tco_result'] if suppliers_results else None
    state['tco_excel_path'] = excel_path
    state['tco_json_path'] = json_path
    state['all_tco'] = suppliers_results
    return state

if __name__ == "__main__":
    test_state = {
        'suppliers': [
            {"nom_fournisseur": "Aciers Algérie SA", "pays": "Algérie", "email": "contact@aciersalgerie.dz", "prix_unitaire": 11250},
            {"nom_fournisseur": "EuroValve GmbH", "pays": "Allemagne", "email": "sales@eurovalve.de", "prix_unitaire": 10500},
            {"nom_fournisseur": "Tunisie Acier", "pays": "Tunisie", "email": "info@tunisieacier.tn", "prix_unitaire": 10800}
        ]
    }
    result = run_module_6(test_state)
    print(f"Excel généré : {result['tco_excel_path']}")
    print(f"JSON généré : {result['tco_json_path']}")
    for sup in result['all_tco']:
        print(f"  {sup['supplier_info']['nom_fournisseur']} : {sup['tco_result']['total_tco']} DZD")