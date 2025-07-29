from twilio.rest import Client
import os

# --- Twilio Credentials ---
# ✅ Option 1: Directly in code (Not recommended for production)
account_sid = 'ACed12602f2b19cbad148318aa7f3643f0'
auth_token = '88b58549a5cdce68430e92632104e207'
twilio_number = '+18455830282'
emergency_contact = '+919345559652'

# ✅ Option 2: From environment variables (RECOMMENDED)
# account_sid = os.getenv("TWILIO_ACCOUNT_SID")
# auth_token = os.getenv("TWILIO_AUTH_TOKEN")
# twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
# emergency_contact = os.getenv("EMERGENCY_CONTACT")

# --- Initialize Twilio Client ---
client = Client(account_sid, auth_token)

def send_emergency_alert():
    try:
        print("🔔 Sending Emergency SMS...")
        message = client.messages.create(
            body="🚨 Emergency! The user needs help.",
            from_=twilio_number,
            to=emergency_contact
        )
        print("✅ SMS sent:", message.sid)

        print("📞 Making Emergency Call...")
        call = client.calls.create(
            twiml='<Response><Say>Emergency! The user needs immediate help. Please respond quickly.</Say></Response>',
            from_=twilio_number,
            to=emergency_contact
        )
        print("✅ Call placed:", call.sid)

    except Exception as e:
        print("❌ Error in sending alert:", e)

# --- Optional Standalone Run ---
if __name__ == "__main__":
    send_emergency_alert()
