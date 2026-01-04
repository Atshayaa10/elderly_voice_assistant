# app.py — SINGLE FILE, WINDOWS-SAFE
# Elderly Voice Assistant (Rule-Based, Voice-Based Emergency)

import os
import time
import random
import logging
import re
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from waitress import serve
from twilio.rest import Client
from yt_dlp import YoutubeDL
import pyttsx3

# ======================= BASIC SETUP =======================
load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, format="%(message)s")

app = Flask(__name__)
CORS(app)

os.makedirs("static", exist_ok=True)
OUTPUT_AUDIO = "static/output.wav"

# ======================= CONFIG =======================
ALERT_COOLDOWN = 15

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
VERIFIED_NUMBER = os.getenv("VERIFIED_NUMBER")
VOICE_MP3_URL = os.getenv("VOICE_MP3_URL")

print("🔑 ENV LOADED")

# ======================= TWILIO =======================
TWILIO_AVAILABLE = all([
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_NUMBER,
    VERIFIED_NUMBER
])

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_AVAILABLE else None
if TWILIO_AVAILABLE:
    print("🔔 Twilio client initialized")

# ======================= TEXT TO SPEECH =======================
engine = pyttsx3.init()

# ======================= EMERGENCY KEYWORDS =======================
EMERGENCY_WORDS = [
    "help", "emergency", "save me", "danger", "rescue",
    "accident", "hospital", "ambulance",
    "உதவி", "உதவி வேணும்", "அவசரம்", "காப்பாத்து",
    "udavi", "udhavi", "kapathu", "kaapathu"
]

_last_alert = 0
latest_location_url = None

# ======================= EMERGENCY CHECK =======================
def is_emergency(text):
    if not text:
        return False
    return any(word in text.lower() for word in EMERGENCY_WORDS)

# ======================= SEND ALERT =======================
def send_emergency_alert(msg, location=None):
    global _last_alert
    if not TWILIO_AVAILABLE:
        return
    if time.time() - _last_alert < ALERT_COOLDOWN:
        return

    body = f"🚨 Emergency Alert 🚨\n{msg}"
    if location:
        body += f"\n📍 {location}"

    client.messages.create(body=body, from_=TWILIO_NUMBER, to=VERIFIED_NUMBER)
    client.calls.create(
        from_=TWILIO_NUMBER,
        to=VERIFIED_NUMBER,
        twiml=f"<Response><Play>{VOICE_MP3_URL}</Play></Response>"
    )

    _last_alert = time.time()
    print("[✅ EMERGENCY ALERT SENT]")

# ======================= RULE-BASED CHAT =======================
def generate_ai_reply(text):
    if not text:
        return "I am here with you."

    # Normalize text
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = text.strip()

    now = datetime.now()

    # 🌅 GREETINGS
    if "good morning" in text:
        return "Good morning. I hope you have a peaceful day."
    if "good afternoon" in text:
        return "Good afternoon. I am here to help you."
    if "good evening" in text:
        return "Good evening. I am with you."
    if "good night" in text:
        return "Good night. Sleep well and stay safe."

    # 🕒 TIME / DAY / DATE
    if any(p in text for p in [
        "time now", "what is the time", "tell me time", "current time"
    ]):
        return f"The time is {now.strftime('%I:%M %p')}."

    if any(p in text for p in [
        "day today", "what day", "today is which day"
    ]):
        return f"Today is {now.strftime('%A')}."

    if "date" in text:
        return f"Today's date is {now.strftime('%d %B %Y')}."

    # 🤖 ABOUT ASSISTANT
    if "who are you" in text or "your name" in text:
        return "I am your Elderly Voice Assistant, always here to help you."

    if "what do you do" in text:
        return "I help you during emergencies and assist you with daily needs."

    # 💊 MEDICINE (FIXED & ROBUST)
    if any(p in text for p in [
        "medicine", "tablet", "pill",
        "forgot my medicine", "missed my medicine",
        "didnt take my medicine", "medicine reminder",
        "pill reminder"
    ]):
        return "It is important to take your medicines on time. Would you like me to remind you?"

    # 🆘 EMOTIONAL SUPPORT
    if any(p in text for p in ["scared", "afraid", "fear"]):
        return "Do not worry. You are not alone."

    if "alone" in text:
        return "I am here with you. You are safe."

    if any(p in text for p in ["stay with me", "talk to me"]):
        return "I am listening. Please talk to me."

    # 🧠 ORIENTATION
    if any(p in text for p in ["where am i", "my location"]):
        return "You are in a safe place. If you need help, say emergency."

    if "am i safe" in text:
        return "Yes, you are safe. I am here to help."

    # 😌 CALMING
    if any(p in text for p in ["relax", "calm", "anxious", "tension"]):
        return "Take a deep breath. Everything will be okay."

    # 🙏 POLITE
    if "thank" in text:
        return "You are welcome. I am happy to help you."

    if "bye" in text or "goodbye" in text:
        return "Goodbye. I am always here if you need me."

    # 🔄 DEFAULT
    return random.choice([
        "I am listening.",
        "Please tell me how I can help you.",
        "You can say emergency if you need help.",
        "I am here with you."
    ])


# ======================= YOUTUBE (FIXED yt_dlp) =======================
def get_youtube_video(query):
    try:
        ydl_opts = {
            "quiet": True,
            "format": "bestaudio/best",
            "default_search": "ytsearch1",
            "noplaylist": True
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)

            # ytsearch returns entries
            if "entries" in info and len(info["entries"]) > 0:
                video = info["entries"][0]
            else:
                video = info

            video_id = video.get("id")
            if not video_id:
                return None, None

            print("[🎵 YOUTUBE VIDEO ID]", video_id)
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"

            return video_id, youtube_url
    except Exception as e:
        print("[❌ YOUTUBE ERROR]", e)
        return None, None

# ======================= ROUTES =======================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/voice_input", methods=["POST"])
def voice_input():
    global latest_location_url

    data = request.json or {}
    text = (data.get("text") or "").strip()
    location = data.get("location")

    print("[🗣️ USER SAID]", text)

    # 🚨 Emergency
    if is_emergency(text):
        send_emergency_alert(text, latest_location_url)
        return jsonify({"status": "🚨 Emergency alert sent!"})

    # 🎵 PLAY COMMAND (FIXED)
    if text.lower().startswith("play "):
        query = text[5:]
        video_id, youtube_url = get_youtube_video(query)

        if video_id:
            return jsonify({
                "status": f"🎵 Playing {query}",
                "video_id": video_id,
                "youtube_url": youtube_url
            })
        else:
            return jsonify({
                "status": "Sorry, I could not find that song."
            })

    # 🤖 Normal reply
    reply = generate_ai_reply(text)
    engine.save_to_file(reply, OUTPUT_AUDIO)
    engine.runAndWait()

    return jsonify({
        "status": reply,
        "reply_audio": OUTPUT_AUDIO
    })

# ======================= MAIN =======================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
