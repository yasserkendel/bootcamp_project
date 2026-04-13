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
        with open('supplier_responses.json', 'r') as f:
            replies = json.load(f)
    except FileNotFoundError:
        print("❌ Error: 'supplier_responses.json' not found. Run the listener first.")
        return

    final_table = []

    for reply in replies:
        content = reply['content']
        email_addr = reply['sender']

        # THE DYNAMIC PROMPT: We tell the AI the current market base price
        prompt = (
            f"You are a Senior Procurement Analyst. Analyze this supplier email: '{content}'\n\n"
            f"CONTEXT:\n"
            f"- Our reference base price is {BASE_PRICE_MARKET} DZD.\n"
            f"- We need a specific unit price to send to our TCO calculator.\n\n"
            f"LOGIC RULES:\n"
            f"1. If they offer a percentage discount (e.g. 10%), calculate: {BASE_PRICE_MARKET} minus that percentage.\n"
            f"2. If they offer a flat discount (e.g. 1000 DZD off), calculate: {BASE_PRICE_MARKET} - the number they offered e.g 1000.\n"
            f"3. If they give a specific price (e.g. '14500 DZD'), use that number.\n"
            f"4. If they are vague/just chatting, set status to 'INCOMPLETE'.\n"
            f"5. If they refuse to discount or reject us, set status to 'REJECTED'.\n"
            f"6. Otherwise, set status to 'READY'.\n\n"
            f"Return ONLY a JSON object:\n"
            f"{{\"supplier_name\": \"\", \"unit_price\": 0, \"status\": \"READY/INCOMPLETE/REJECTED\", \"analysis\": \"Brief reason why\"}}"
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

    # Save the clean data for the TCO module
    with open('final_offers_table.json', 'w') as f:
        json.dump(final_table, f, indent=4)
    
    print(f"\n🏁 [SYSTEM] Analysis complete. {len(final_table)} offers ready for TCO.")

if __name__ == "__main__":
    parse_and_negotiate()