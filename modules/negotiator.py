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
            # Login using your App Password
            smtp.login("procurement.solutions259@gmail.com", "qtsmysakmrnjbvyk")
            smtp.send_message(msg)
            return True
    except Exception as e:
        print(f"❌ Mail Error for {recipient_email}: {e}")
        return False

def run_integrated_system():
    print("🚀 [PHASE 1] SOURCING VIA WIKIDATA...")
    real_companies = search_algerian_suppliers()
    
    print("\n📈 [PHASE 2] MARKET INTELLIGENCE...")
    inflation = get_algerian_market_data()
    
    # Corrected Parenthesis here: len(real_companies)
    suppliers = [
        {"name": real_companies[0] if len(real_companies) > 0 else "Algeria Valve", "email": "yasserkend8@gmail.com", "contact": "Mr. Yasser"},
        {"name": real_companies[1] if len(real_companies) > 1 else "Sarl Hydro-Tech", "email": "ramykhelfaoui@gmail.com", "contact": "Mr. Ramy"},
        {"name": real_companies[2] if len(real_companies) > 2 else "Industrie DZ", "email": "kholoudakbi@gmail.com", "contact": "Mme. Kholoud"},
        {"name": "Mediterranean Tech", "email": "maysabendou@gmail.com", "contact": "Mme Maysa"},
        {"name": "Industrial Parts Algiers", "email": "khelfaatr@gmail.com", "contact": "Mr. Amine"}
    ]

    print("\n🤖 [PHASE 3] AUTONOMOUS NEGOTIATION...")
    for s in suppliers:
        print(f"Drafting for {s['name']}...")
        
        prompt = (
            f"You are Khelfaoui Ramy from Algeria Industrie Solutions. "
            f"Write a formal email to {s['contact']} at {s['name']}. "
            f"We need 500 High Pressure Valves. Mention that the current Algerian inflation is {round(inflation, 2)}%. "
            f"Request a competitive unit price in DZD. Sign off professionally."
        )

        try:
            response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
            body = response['message']['content']
            
            success = send_real_email(s['email'], f"Sourcing Request: {s['name']}", body)
            if success:
                print(f"✅ Email successfully sent to {s['name']}")
        except Exception as e:
            print(f"❌ Error during AI generation/sending: {e}")

    with open('contacted_suppliers.json', 'w') as f:
        json.dump(suppliers, f, indent=4)
    print("\n🏁 [FINISH] All initial emails dispatched.")

if __name__ == "__main__":
    run_integrated_system()