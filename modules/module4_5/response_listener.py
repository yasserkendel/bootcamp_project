import imaplib
import email
import json

def fetch_emails():
    print("📥 [LISTENER] Connecting to Gmail to fetch supplier replies...")
    
    # Connection details
    IMAP_SERVER = "imap.gmail.com"
    EMAIL_USER = "procurement.solutions259@gmail.com"
    EMAIL_PASS = "qtsmysakmrnjbvyk"

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Search for all emails
        status, messages = mail.search(None, 'ALL')
        email_ids = messages[0].split()
        
        responses = []

        # Only grab the last 5-10 emails to keep it fast for the demo
        for i in email_ids[-10:]:
            res, msg_data = mail.fetch(i, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    sender = msg.get("From")
                    subject = msg.get("Subject")
                    
                    # Extract the body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                    else:
                        body = msg.get_payload(decode=True).decode()

                    responses.append({
                        "sender": sender,
                        "subject": subject,
                        "content": body
                    })

        # ✅ UPDATED PATH: Save into the data sub-folder
        with open('data/supplier_responses.json', 'w') as f:
            json.dump(responses, f, indent=4)
        
        print(f"✅ [SUCCESS] Fetched {len(responses)} messages and saved to data/supplier_responses.json")
        mail.close()
        mail.logout()

    except Exception as e:
        print(f"❌ Listener Error: {e}")

if __name__ == "__main__":
    fetch_emails()