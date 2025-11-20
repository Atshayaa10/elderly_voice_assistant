# utils/emergency_alert.py
"""
Emergency Alert Module using Twilio
-----------------------------------
Sends an emergency SMS and optionally places a voice call
to the configured contact using Twilio API.
Supports live Google Maps location links.
"""

import os
import logging
import time
from typing import Dict, Any, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_twilio_client() -> Optional[Client]:
    """
    Initialize and return a Twilio Client if environment is configured.
    Raises EnvironmentError if configuration is missing.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        raise EnvironmentError(
            "❌ Missing Twilio credentials. "
            "Please set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in your environment."
        )
    return Client(account_sid, auth_token)


def send_emergency_alert(
    message_text: str = "🚨 Emergency! The user needs help.",
    location_url: Optional[str] = None,
    send_sms: bool = True,
    make_call: bool = True,
    retries: int = 2
) -> Dict[str, Any]:
    """
    Sends an emergency SMS and/or places a call to the configured contact.

    Args:
        message_text (str): Message content for SMS and call TTS.
        location_url (str): Optional Google Maps link to include in SMS.
        send_sms (bool): Whether to send SMS alert (default: True).
        make_call (bool): Whether to place a voice call (default: True).
        retries (int): Number of retry attempts for transient failures.

    Returns:
        dict: Results of operations { "sms": status, "call": status }.
    """
    results = {"sms": None, "call": None}

    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
    emergency_contact = os.getenv("EMERGENCY_CONTACT")

    if not twilio_number or not emergency_contact:
        raise EnvironmentError(
            "❌ Missing Twilio config. "
            "Please set TWILIO_PHONE_NUMBER and EMERGENCY_CONTACT in your environment."
        )

    client = get_twilio_client()

    # Append location link to message if provided
    sms_message = message_text
    if location_url:
        sms_message += f"\n📍 Location: {location_url}"

    # --- Send SMS ---
    if send_sms:
        for attempt in range(1, retries + 2):
            try:
                logger.info("🔔 Sending Emergency SMS (Attempt %s)...", attempt)
                message = client.messages.create(
                    body=sms_message,
                    from_=twilio_number,
                    to=emergency_contact
                )
                results["sms"] = f"✅ SMS sent (SID: {message.sid})"
                logger.info("✅ SMS sent successfully.")
                break
            except TwilioRestException as e:
                logger.error("❌ SMS failed: %s", str(e))
                if attempt <= retries:
                    time.sleep(2)
                else:
                    results["sms"] = f"❌ SMS failed: {str(e)}"

    # --- Place Call ---
    if make_call:
        for attempt in range(1, retries + 2):
            try:
                logger.info("📞 Placing Emergency Call (Attempt %s)...", attempt)
                # For voice, only read the text; URL not read aloud
                call = client.calls.create(
                    twiml=f'<Response><Say>{message_text}</Say></Response>',
                    from_=twilio_number,
                    to=emergency_contact
                )
                results["call"] = f"✅ Call placed (SID: {call.sid})"
                logger.info("✅ Call placed successfully.")
                break
            except TwilioRestException as e:
                logger.error("❌ Call failed: %s", str(e))
                if attempt <= retries:
                    time.sleep(2)
                else:
                    results["call"] = f"❌ Call failed: {str(e)}"

    return results


# --- Optional Standalone Run ---
if __name__ == "__main__":
    sample_text = "🚨 Emergency detected! User requires assistance."
    sample_location = "https://www.google.com/maps?q=12.9716,77.5946"
    output = send_emergency_alert(message_text=sample_text, location_url=sample_location)
    logger.info("Final Results: %s", output)
