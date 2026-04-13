import ollama
import json
import smtplib
from email.message import EmailMessage
from sourcing_engine import search_algerian_suppliers
from market_analyst import get_algerian_market_data

def send_real_email(recipient_email, subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['To'] = recipient_email
    msg['From'] = "procurement.solutions259@gmail.com"

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login("procurement.solutions259@gmail.com", "qtsmysakmrnjbvyk")
            smtp.send_message(msg)
            return True
    except Exception as e:
        print(f"❌ Mail Error for {recipient_email}: {e}")
        return False

def run_integrated_system():
    # --- ✅ NEW: READ SPECS FROM DATA FOLDER ---
    try:
        with open('data/extracted_specs.json', 'r') as f:
            specs = json.load(f)
            item_name = specs.get("item", "High Pressure Valves")
            quantity = specs.get("quantity", "500")
    except FileNotFoundError:
        print("⚠️ extracted_specs.json not found in data/. Using defaults.")
        item_name = "High Pressure Valves"
        quantity = "500"

    print("🚀 [PHASE 1] SOURCING VIA WIKIDATA...")
    real_companies = search_algerian_suppliers()
    
    print("\n📈 [PHASE 2] MARKET INTELLIGENCE...")
    inflation = get_algerian_market_data()
    
    suppliers = [
        {
            "name": real_companies[1] if len(real_companies) > 1 else "Sarl Hydro-Tech", 
            "email": "ramykhelfaoui@gmail.com", 
            "contact": "Mr. Ramy"
        },
        {
            "name": real_companies[2] if len(real_companies) > 2 else "Industrie DZ", 
            "email": "kholoudakbi@gmail.com", 
            "contact": "Mme. Kholoud"
        } 
    ]

    print("\n🤖 [PHASE 3] AUTONOMOUS NEGOTIATION...")
    for s in suppliers:
        print(f"Drafting for {s['name']}...")
        
        # ✅ PROMPT UPDATED TO USE DATA FROM JSON
        prompt = (
            f"You are Khelfaoui Ramy from Algeria Industrie Solutions. "
            f"Write a formal email to {s['contact']} at {s['name']}. "
            f"We need {quantity} {item_name}. Mention that the current Algerian inflation is {round(inflation, 2)}%. "
            f"Request a competitive unit price in DZD. Sign off professionally."
            f"STRICTLY FORBIDDEN: Do not use any placeholders. Use 'Khelfaoui Ramy' and 'Algeria Industrie Solutions'."
        )

        try:
            response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
            body = response['message']['content']
            
            success = send_real_email(s['email'], f"Sourcing Request: {s['name']}", body)
            if success:
                print(f"✅ Email successfully sent to {s['name']}")
        except Exception as e:
            print(f"❌ Error during AI generation/sending: {e}")

    # ✅ SAVES TO DATA FOLDER
    with open('data/contacted_suppliers.json', 'w') as f:
        json.dump(suppliers, f, indent=4)
        
    print("\n🏁 [FINISH] All initial emails dispatched.")

if __name__ == "__main__":
    run_integrated_system()