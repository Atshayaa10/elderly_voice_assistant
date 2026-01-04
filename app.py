# ======================= app.py =======================
# Elderly Voice Assistant – Rule Based + Emergency + YouTube Play
# Cloud-safe (Render compatible)

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

# ======================= TEXT TO SPEECH (LOCAL ONLY) =======================
engine = None
if not IS_RENDER:
    import pyttsx3
    engine = pyttsx3.init()

# ======================= EMERGENCY KEYWORDS =======================
EMERGENCY_WORDS = [
    "help", "emergency", "save me", "danger", "rescue",
    "accident", "hospital", "ambulance",
    "உதவி", "உதவி வேணும்", "அவசரம்", "காப்பாத்து",
    "udavi", "udhavi", "kapathu", "kaapathu"
]

_last_alert = 0

def is_emergency(text):
    return any(word in text.lower() for word in EMERGENCY_WORDS)

# ======================= SEND EMERGENCY ALERT =======================
def send_emergency_alert(msg, location=None):
    global _last_alert

    if not TWILIO_AVAILABLE:
        return

    if time.time() - _last_alert < ALERT_COOLDOWN:
        return

    body = f"🚨 Emergency Alert 🚨\n{msg}"
    if location:
        body += f"\n📍 Location: {location}"

    client.messages.create(
        body=body,
        from_=TWILIO_NUMBER,
        to=VERIFIED_NUMBER
    )

    if VOICE_MP3_URL:
        client.calls.create(
            from_=TWILIO_NUMBER,
            to=VERIFIED_NUMBER,
            twiml=f"<Response><Play>{VOICE_MP3_URL}</Play></Response>"
        )

    _last_alert = time.time()

# ======================= RULE BASED CHAT =======================
def generate_reply(text):
    text = re.sub(r"[^\w\s]", "", text.lower())
    now = datetime.now()

    if "good morning" in text:
        return "Good morning. I hope you are feeling well."
    if "good evening" in text:
        return "Good evening. I am here with you."
    if "time" in text:
        return f"The time is {now.strftime('%I:%M %p')}."
    if "day" in text:
        return f"Today is {now.strftime('%A')}."
    if "date" in text:
        return f"Today's date is {now.strftime('%d %B %Y')}."
    if "medicine" in text or "tablet" in text or "pill" in text:
        return "Please remember to take your medicine on time."

    return random.choice([
        "I am listening.",
        "Please tell me how I can help you.",
        "I am here with you."
    ])

# ======================= YOUTUBE FETCH =======================
def get_youtube_url(query):
    try:
        ydl_opts = {
            "quiet": True,
            "default_search": "ytsearch1",
            "noplaylist": True
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            video_id = info["entries"][0]["id"]
            return f"https://www.youtube.com/watch?v={video_id}"
    except:
        return None

# ======================= ROUTES =======================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/voice_input", methods=["POST"])
def voice_input():
    try:
        data = request.json or {}
        text = (data.get("text") or "").strip()
        location = data.get("location")

        # 🔥 PLAY COMMAND — MUST BE FIRST
        if text.lower().startswith("play "):
            query = text[5:]
            youtube_url = get_youtube_url(query)
            if youtube_url:
                return jsonify({
                    "status": f"🎵 Playing {query}",
                    "youtube_url": youtube_url
                })

        # 🚨 EMERGENCY
        if is_emergency(text):
            send_emergency_alert(text, location)
            return jsonify({
                "status": "🚨 Emergency alert sent. Help is on the way."
            })

        # 💬 RULE BASED RESPONSE
        reply = generate_reply(text)

        if engine:
            engine.save_to_file(reply, OUTPUT_AUDIO)
            engine.runAndWait()

        return jsonify({
            "status": reply,
            "reply_audio": None if IS_RENDER else OUTPUT_AUDIO
        })

    except Exception as e:
        print("BACKEND ERROR:", e)
        return jsonify({"status": "Backend error"}), 500

# ======================= MAIN =======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
