from modules.module_6_tco import run_module_6
from modules.module_7_business_plan import run_module_7
from modules.module_9_catalogue import run_module_9

def main():
    state = {}
    print("=== Module 6 ===")
    state = run_module_6(state)
    print("TCO Excel:", state.get('tco_excel_path'))
    print("=== Module 7 ===")
    state = run_module_7(state)
    print("Business Plan PDF:", state.get('business_plan_pdf'))
    print("=== Module 9 ===")
    state = run_module_9(state)
    print("Catalogue fichiers:", state.get('catalogue_files'))

if __name__ == "__main__":
    main()