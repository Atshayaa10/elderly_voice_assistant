# app.py — SINGLE FILE, CLOUD-SAFE
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
from twilio.rest import Client
from yt_dlp import YoutubeDL

# ======================= BASIC SETUP =======================
load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, format="%(message)s")

app = Flask(__name__)
CORS(app)

os.makedirs("static", exist_ok=True)
OUTPUT_AUDIO = "static/output.wav"

# Detect Render environment
IS_RENDER = os.getenv("RENDER") == "true"

# ======================= CONFIG =======================
ALERT_COOLDOWN = 15

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
VERIFIED_NUMBER = os.getenv("VERIFIED_NUMBER")
VOICE_MP3_URL = os.getenv("VOICE_MP3_URL")

print("🔑 ENV LOADED")
print("🚀 Running on Render:", IS_RENDER)

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
# IMPORTANT: Disable pyttsx3 on Render to avoid crash
engine = None
if not IS_RENDER:
    import pyttsx3
    engine = pyttsx3.init()
    print("🔊 pyttsx3 enabled (local)")
else:
    print("🔇 pyttsx3 disabled on Render")

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

    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text).strip()
    now = datetime.now()

    if "good morning" in text:
        return "Good morning. I hope you have a peaceful day."
    if "good afternoon" in text:
        return "Good afternoon. I am here to help you."
    if "good evening" in text:
        return "Good evening. I am with you."
    if "good night" in text:
        return "Good night. Sleep well and stay safe."

    if any(p in text for p in ["time now", "what is the time", "current time"]):
        return f"The time is {now.strftime('%I:%M %p')}."

    if any(p in text for p in ["day today", "what day"]):
        return f"Today is {now.strftime('%A')}."

    if "date" in text:
        return f"Today's date is {now.strftime('%d %B %Y')}."

    if "who are you" in text or "your name" in text:
        return "I am your Elderly Voice Assistant, always here to help you."

    if any(p in text for ["medicine", "tablet", "pill"]):
        return "Please remember to take your medicines on time."

    return random.choice([
        "I am listening.",
        "Please tell me how I can help you.",
        "You can say emergency if you need help.",
        "I am here with you."
    ])

# ======================= YOUTUBE =======================
def get_youtube_video(query):
    try:
        ydl_opts = {
            "quiet": True,
            "default_search": "ytsearch1",
            "noplaylist": True
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            video = info["entries"][0]
            video_id = video.get("id")
            return video_id, f"https://www.youtube.com/watch?v={video_id}"
    except Exception as e:
        print("[❌ YOUTUBE ERROR]", e)
        return None, None

# ======================= ROUTES =======================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/voice_input", methods=["POST"])
def voice_input():
    data = request.json or {}
    text = (data.get("text") or "").strip()

    print("[🗣️ USER SAID]", text)

    if is_emergency(text):
        send_emergency_alert(text)
        return jsonify({"status": "🚨 Emergency alert sent!"})

    if text.lower().startswith("play "):
        query = text[5:]
        _, youtube_url = get_youtube_video(query)
        if youtube_url:
            return jsonify({
                "status": f"🎵 Playing {query}",
                "youtube_url": youtube_url
            })

    reply = generate_ai_reply(text)

    # 🔊 Generate audio ONLY if not Render
    if engine:
        engine.save_to_file(reply, OUTPUT_AUDIO)
        engine.runAndWait()

    return jsonify({
        "status": reply,
        "reply_audio": None if IS_RENDER else OUTPUT_AUDIO
    })

# ======================= MAIN =======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
