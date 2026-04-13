import ollama
import json
import re
from negotiator import send_real_email 

# Configuration - You can change this or pull it from your specs module
BASE_PRICE_MARKET = 16000 

def clean_json_string(raw_string):
    """Extracts the JSON block from the AI's response."""
    match = re.search(r'\{.*\}', raw_string, re.DOTALL)
    if match:
        return match.group(0)
    return raw_string

def parse_and_negotiate():
    print("🧠 [AI AGENT] Starting Semantic Analysis of Supplier Emails...")
    
    try:
        # ✅ UPDATED PATH: Looking inside the data folder
        with open('data/supplier_responses.json', 'r') as f:
            replies = json.load(f)
    except FileNotFoundError:
        print("❌ Error: 'data/supplier_responses.json' not found. Run the listener first.")
        return

    final_table = []

    for reply in replies:
        content = reply['content']
        email_addr = reply['sender']

        # THE DYNAMIC PROMPT: Integrated with your BASE_PRICE_MARKET and logic branches
        prompt = (
            f"[SYSTEM: SENIOR PROCUREMENT ANALYST MODE]\n"
            f"Analyze this supplier email: '{content}'\n\n"
            "STRICT RULE for supplier_name:\n"
            "- 'Algeria Industrie Solutions' is OUR company. DO NOT use it as the supplier name.\n"
            "- Look for the supplier name in the 'From' field or the sender's specific signature.\n"
            "- If unsure, extract the name from the email address (e.g., 'Ramy Khelfaoui').\n\n"
            f"CONTEXT:\n"
            f"- Our reference base price is {BASE_PRICE_MARKET} DZD.\n\n"
            f"STRICT LOGIC RULES:\n"
            f"1. REJECTION CHECK: If the supplier is out of stock, refuses to quote, or says they are 'unable' or 'sorry', you MUST set status to 'REJECTED' and unit_price to 0.\n"
            f"2. PERCENTAGE DISCOUNT: If they offer a % (e.g. 10%), calculate: {BASE_PRICE_MARKET} - ({BASE_PRICE_MARKET} * the pourcentage).\n"
            f"3. FLAT DISCOUNT: If they offer a fixed amount off (e.g. 1000 DZD), calculate: {BASE_PRICE_MARKET} - 1000.\n"
            f"4. DIRECT PRICE: If they state a specific new price (e.g. '14500 DZD'), use that exactly.\n"
            f"5. VAGUE/CHAT: If they don't provide any numbers or specific answers, set status to 'INCOMPLETE'.\n"
            f"6. VALID QUOTE: If a price is successfully calculated or found, set status to 'READY'.\n\n"
            f"7. STRICT CALCULATION: You must use the EXACT percentage mentioned in the email. Do not round. If the email says 12%, you must calculate 16000 * 0.12 and subtract it.\n"
            f"Return ONLY a raw JSON object with this exact structure:\n"
            f"{{\"supplier_name\": \"Name\", \"unit_price\": 0, \"status\": \"READY/INCOMPLETE/REJECTED\", \"analysis\": \"Brief math or reason\"}}"
        )

        try:
            response = ollama.chat(model='mistral', messages=[{'role': 'user', 'content': prompt}])
            raw_output = response['message']['content']
            
            # Clean and parse the AI response
            json_data = clean_json_string(raw_output)
            data = json.loads(json_data)
            
            status = data.get('status', 'INCOMPLETE')
            
            if status == 'READY':
                print(f"✅ [SUCCESS] {email_addr} -> Extracted Price: {data['unit_price']} DZD")
                # Add to the table for the TCO person
                final_table.append({
                    "supplier": data.get('supplier_name', email_addr),
                    "unit_price": data['unit_price'],
                    "email": email_addr
                })

            elif status == 'INCOMPLETE':
                print(f"⚠️ [VAGUE] {email_addr} was unclear. Sending Follow-up...")
                msg = "We appreciate the details! However, we need a specific unit price to finalize our TCO comparison. Could you provide a figure?"
                send_real_email(email_addr, "Clarification Needed - AIS Procurement", msg)

            elif status == 'REJECTED':
                print(f"🚫 [REJECTED] {email_addr} declined. Sending closure.")
                msg = "Thank you for your response. We will keep your information in our records for future opportunities."
                send_real_email(email_addr, "Procurement Update - AIS", msg)

        except Exception as e:
            print(f"❌ Failed to parse response from {email_addr}: {e}")

    # ✅ UPDATED PATH: Saving final table into the data folder
    with open('data/final_offers_table.json', 'w') as f:
        json.dump(final_table, f, indent=4)
    
    print(f"\n🏁 [SYSTEM] Analysis complete. {len(final_table)} offers ready for TCO.")

if __name__ == "__main__":
    parse_and_negotiate()