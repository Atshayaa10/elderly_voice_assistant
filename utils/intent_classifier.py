# utils/intent_classifier.py

from utils import emergency_alert  # Import the emergency alert module

# Classify the intent based on input text
def classify(text):
    text = text.lower()
    if any(keyword in text for keyword in ["help", "emergency", "save me", "danger", "i need help"]):
        return "emergency"
    elif "reminder" in text:
        return "reminder"
    elif "hello" in text or "hi" in text or "hey" in text:
        return "greeting"
    else:
        return "unknown"

# Handle the intent and return a suitable response
def handle_intent(intent, text):
    if intent == "emergency":
        try:
            emergency_alert.send_emergency_alert()  # Trigger call + SMS
            return "Emergency alert has been sent. Help is on the way!"
        except Exception as e:
            return f"Failed to send emergency alert: {str(e)}"

    elif intent == "reminder":
        return "What reminder should I set?"

    elif intent == "greeting":
        return "Hello! How can I help you today?"

    else:
        return "Sorry, I didn't understand that."
