import requests

def get_algerian_market_data():
    """
    Module 4: Sourcing Market Intelligence
    Fetches the most recent VALID (non-null) inflation data for Algeria.
    """
    # World Bank API for Algerian Inflation (Consumer Price Index)
    url = "https://api.worldbank.org/v2/country/DZ/indicator/FP.CPI.TOTL.ZG?format=json"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        # The data is in the second element of the list: data[1]
        records = data[1]
        
        # --- THE CLEAN UP LOGIC ---
        # We loop through the years (starting from the most recent)
        for record in records:
            if record['value'] is not None:
                year = record['date']
                value = record['value']
                print(f"--- 🌍 [MODULE 4] Sourcing Market Intelligence ---")
                print(f"✅ Success: Using data from year {year} ({round(value, 2)}%)")
                return value
                
        return 4.5  # Emergency fallback if all years are null
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return 4.0  # Safe fallback for negotiation logic