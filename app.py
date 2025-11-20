# app.py – Elderly Voice Assistant (Flask + Twilio + HuggingFace + YouTube + ML Emergency Detection + Real-time Background Mic Monitor)

import os
import random
import threading
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import numpy as np

# Twilio
from twilio.rest import Client

# ML
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

# TTS
import pyttsx3
from yt_dlp import YoutubeDL

# Sounddevice
SD_AVAILABLE = False
try:
    import sounddevice as sd
    SD_AVAILABLE = True
except Exception:
    pass

# ----------------- Flask Setup -----------------
app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = 'audio'
OUTPUT_AUDIO = os.path.join('static', 'output.wav')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static', exist_ok=True)

# ----------------- Logging Setup -----------------
logging.basicConfig(level=logging.INFO, format="%(message)s")

# ----------------- Environment -----------------
load_dotenv(override=True)
HF_TOKEN = os.getenv("HF_TOKEN")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER") or os.getenv("TWILIO_PHONE_NUMBER")
VERIFIED_NUMBER = os.getenv("VERIFIED_NUMBER") or os.getenv("EMERGENCY_CONTACT")
VOICE_MP3_URL = os.getenv("VOICE_MP3_URL")

FALL_ALERT_COOLDOWN = int(os.getenv("FALL_ALERT_COOLDOWN", "60"))
LOUD_AMPLITUDE_THRESHOLD = float(os.getenv("LOUD_AMPLITUDE_THRESHOLD", "0.25"))
MIC_SAMPLE_RATE = 16000
MIC_DEVICE_ID = int(os.getenv("MIC_DEVICE_ID", "1"))
ALERT_COOLDOWN = 15

# ----------------- Mask Helper -----------------
def mask(s):
    if not s:
        return None
    s = str(s)
    if len(s) <= 8:
        return "****"
    return s[:4] + "..." + s[-4:]

print("🔑 ENV LOADED:")
print(" TWILIO_ACCOUNT_SID:", mask(TWILIO_ACCOUNT_SID))
print(" TWILIO_NUMBER:", TWILIO_NUMBER)
print(" VERIFIED_NUMBER:", VERIFIED_NUMBER)
print(" VOICE_MP3_URL set:", bool(VOICE_MP3_URL))
print(" HF_TOKEN set:", bool(HF_TOKEN))
print(" TRANSFORMERS_AVAILABLE:", TRANSFORMERS_AVAILABLE)
print(" SD_AVAILABLE:", SD_AVAILABLE)

# ----------------- Twilio Setup -----------------
TWILIO_AVAILABLE = all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_NUMBER, VERIFIED_NUMBER])
client = None
if TWILIO_AVAILABLE:
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("🔔 Twilio client initialized.")
    except Exception as e:
        print("[❌ TWILIO INIT ERROR]", e)
        client = None
        TWILIO_AVAILABLE = False
else:
    print("[⚠️ TWILIO NOT AVAILABLE] Missing Twilio env variables.")

# ----------------- Hugging Face Chatbot -----------------
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/blenderbot-400M-distill"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}

# ----------------- Globals -----------------
latest_location_url = None
latest_location_lock = threading.Lock()
_alert_last_time = 0

# ----------------- ML Emergency Detection -----------------
MODEL_NAME = "xlm-roberta-base"
tokenizer = None
model = None
model_ready = False

def load_ml_model_background():
    global tokenizer, model, model_ready
    if not TRANSFORMERS_AVAILABLE:
        print("[ℹ️ TRANSFORMERS NOT INSTALLED] ML disabled.")
        return
    try:
        print(f"[⏳ LOADING ML MODEL: {MODEL_NAME}]")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)
        model.eval()
        model_ready = True
        print("[✅ ML MODEL LOADED]")
    except Exception as e:
        print("[❌ ML LOAD FAILED]", e)

threading.Thread(target=load_ml_model_background, daemon=True).start()

# ----------------- Emergency Keywords -----------------
FALLBACK_EMERGENCY_KEYWORDS = [
    "help", "emergency", "urgent", "rescue", "danger", "save me", "i need help",
    "fell", "i fell", "fall detected", "accident",
    "உதவி", "அவசரம்", "உதவி வேண்டும்", "நான் விழுந்துவிட்டேன்", "விழுந்தேன்",
    "udhavi", "udhavi venum", "vizhundhen", "vizhundhu"
]

def ml_emergency_check(text: str, threshold: float = 0.6) -> bool:
    if not text:
        return False
    txt = text.lower()
    for kw in FALLBACK_EMERGENCY_KEYWORDS:
        if kw in txt:
            print(f"[🔎 KEYWORD MATCH] {kw}")
            return True
    if model_ready and tokenizer and model:
        try:
            inputs = tokenizer(txt, return_tensors="pt", truncation=True, padding=True)
            with torch.no_grad():
                outputs = model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)
                emergency_prob = float(probs[0][1])
                print(f"[🔍 ML PROB] {emergency_prob:.3f}")
                return emergency_prob >= threshold
        except Exception as e:
            print("[❌ ML CHECK ERROR]", e)
    return False

# ----------------- TTS -----------------
engine = pyttsx3.init()

# ----------------- Expanded Rule-Based AI -----------------
def fallback_ai(text: str) -> str:
    t = text.lower()

    # Greetings
    if any(x in t for x in ["hello", "hi", "hey", "vanakkam"]):
        return random.choice(["Hello there!", "Vanakkam! How are you today?", "Hey! Nice to hear your voice."])
    if "good morning" in t: return "Good morning! Hope you had a restful sleep."
    if "good evening" in t: return "Good evening! How was your day?"
    if "good night" in t: return "Good night! Sweet dreams and take care."

    # Name & Identity
    if "your name" in t: return "I am your Elderly Voice Assistant, always here to help you."
    if "who are you" in t: return "I am your friendly assistant, here to keep you safe and company."

    # Well-being
    if "how are you" in t: return random.choice(["I’m doing well, thank you for asking!", "Feeling great! How about you?"])
    if "how do you feel" in t: return "I feel happy when I can help you."

    # Time & Date
    if "time" in t: return f"The current time is {datetime.now().strftime('%I:%M %p')}."
    if "date" in t: return f"Today’s date is {datetime.now().strftime('%B %d, %Y')}."

    # Weather (simulated)
    if "weather" in t: return "I can't feel the weather, but you can check your window for sunshine or rain!"

    # Health reminders
    if "drink water" in t: return "Yes, staying hydrated is important! Please drink a glass of water."
    if "medicine" in t: return "Please don’t forget to take your medicines on time."
    if "exercise" in t: return "Light exercise can keep you strong. Shall we stretch a bit?"

    # Jokes / Fun
    if "joke" in t: return random.choice([
        "Why did the robot go on vacation? Because it needed to recharge!",
        "I tried to eat a clock yesterday. It was very time-consuming!",
        "Why do computers sneeze? Because they have a virus!"
    ])

    # Music
    if "sing" in t or "song" in t: return "I can’t sing, but I can play your favorite song if you say 'play [song name]'."

    # Tamil-friendly responses
    if "saptiya" in t or "saaptiya" in t: return "Sapten! Neenga saptingala?"
    if "epdi iruka" in t or "epdi irukeenga" in t: return "Naan nalla iruken, neenga epdi irukeenga?"
    if "thank you" in t or "nandri" in t: return "You're welcome! Always happy to help."

    # Mood
    if "lonely" in t: return "Don’t worry, I’m here to keep you company. You are not alone."
    if "sad" in t: return "I’m sorry you feel that way. Want me to play some happy music?"
    if "happy" in t: return "That’s wonderful! Keep smiling, it suits you."

    # Default fallback
    return random.choice([
        "I'm here and listening.",
        "Could you say that again?",
        "I'm not sure I understood, but I'm here for you.",
        "That’s interesting! Tell me more."
    ])

# ----------------- AI Reply Generator -----------------
def generate_ai_reply(user_input: str) -> str:
    if not HF_TOKEN:
        return fallback_ai(user_input)
    try:
        r = requests.post(HF_API_URL, headers=HEADERS, json={"inputs": user_input}, timeout=20)
        data = r.json()
        if isinstance(data, list) and len(data) and "generated_text" in data[0]:
            return data[0]["generated_text"]
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"]
        return fallback_ai(user_input)
    except Exception as e:
        print("[❌ HF ERROR]", e)
        return fallback_ai(user_input)

# ----------------- YouTube -----------------
def get_first_youtube_video_url(query: str):
    opts = {'quiet': True, 'format': 'bestaudio/best', 'default_search': 'ytsearch1', 'extract_flat': 'in_playlist'}
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info and info['entries']:
                vid = info['entries'][0].get('id')
                return f"https://www.youtube.com/watch?v={vid}&autoplay=1" if vid else None
    except Exception as e:
        print("[❌ YT ERROR]", e)
    return None

# ----------------- Emergency Alerts -----------------
def send_emergency_alert(message_text: str, location_url: str | None = None) -> bool:
    global _alert_last_time
    if not TWILIO_AVAILABLE or client is None:
        print("[⚠️ TWILIO UNAVAILABLE]")
        return False

    now = time.time()
    if now - _alert_last_time < FALL_ALERT_COOLDOWN:
        print(f"[ℹ️ ALERT SUPPRESSED] Cooldown active.")
        return False

    sms_body = f"🚨 Emergency Alert 🚨\n{message_text}"
    if location_url:
        sms_body += f"\n📍 Location: {location_url}"

    try:
        sms = client.messages.create(body=sms_body, from_=TWILIO_NUMBER, to=VERIFIED_NUMBER)
        print(f"[✅ SMS SENT] {sms.sid}")
    except Exception as e:
        print("[❌ SMS ERROR]", e)
        return False

    try:
        twiml = f'<Response><Play>{VOICE_MP3_URL}</Play></Response>' if VOICE_MP3_URL else \
                f'<Response><Say voice="alice">Emergency detected. {message_text}</Say></Response>'
        call = client.calls.create(to=VERIFIED_NUMBER, from_=TWILIO_NUMBER, twiml=twiml)
        print(f"[✅ CALL PLACED] {call.sid}")
    except Exception as e:
        print("[⚠️ CALL ERROR]", e)

    _alert_last_time = now
    return True

# ----------------- Background Mic Monitor -----------------
def start_background_sound_monitor():
    if not SD_AVAILABLE:
        print("[⚠️ SOUNDDEVICE NOT AVAILABLE] Install 'sounddevice'.")
        return

    print(f"[🎧 MONITOR] Listening for loud sounds (Device ID={MIC_DEVICE_ID}) ...")
    last_alert_time = 0

    def callback(indata, frames, time_info, status):
        nonlocal last_alert_time
        volume_norm = np.linalg.norm(indata) * 10
        if random.random() < 0.002:
            logging.info(f"[🎙️ Monitoring... mic active]")
        if volume_norm > LOUD_AMPLITUDE_THRESHOLD:
            now = time.time()
            if now - last_alert_time > ALERT_COOLDOWN:
                logging.warning(f"[🚨 LOUD SOUND DETECTED] volume={volume_norm:.3f}")
                with latest_location_lock:
                    loc = latest_location_url
                send_emergency_alert("Loud sound detected — possible fall", loc)
                last_alert_time = now

    def sound_loop():
        try:
            with sd.InputStream(device=MIC_DEVICE_ID, channels=1, samplerate=MIC_SAMPLE_RATE, callback=callback):
                while True:
                    time.sleep(0.5)
        except Exception as e:
            print("[❌ SOUND MONITOR ERROR]", e)

    threading.Thread(target=sound_loop, daemon=True).start()

# ----------------- Flask Routes -----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/voice_input', methods=['POST'])
def voice_input():
    try:
        data = request.json or {}
        text = (data.get('text') or "").strip()
        location = data.get('location')
        location_url = None
        if isinstance(location, dict):
            lat = location.get("latitude")
            lng = location.get("longitude")
            if lat and lng:
                location_url = f"https://www.google.com/maps?q={lat},{lng}"
                with latest_location_lock:
                    global latest_location_url
                    latest_location_url = location_url

        print("[🔊 VOICE INPUT]", text)
        emergency_trigger = ml_emergency_check(text)
        if emergency_trigger:
            msg = f"Message: {text or 'Emergency detected'}"
            sent = send_emergency_alert(msg, location_url)
            status = "✅ Emergency alert sent!" if sent else "⚠️ Emergency detected but failed to send alert."
            return jsonify({"status": status})

        if text.lower().startswith("play "):
            query = text.split("play", 1)[1].strip()
            url = get_first_youtube_video_url(query)
            return jsonify({"status": f"🎵 Playing: {query}", "youtube_url": url}) if url else \
                   jsonify({"status": "❌ Couldn't find video."})

        reply = generate_ai_reply(text)
        try:
            engine.save_to_file(reply, OUTPUT_AUDIO)
            engine.runAndWait()
        except Exception as e:
            print("[⚠️ TTS ERROR]", e)

        return jsonify({"status": reply, "reply_audio": OUTPUT_AUDIO})
    except Exception as e:
        print("[❌ VOICE INPUT ERROR]", e)
        return jsonify({"status": f"Error: {str(e)}"}), 500

# ----------------- Run -----------------
if __name__ == '__main__':
    print("✅ Flask server starting... visit http://127.0.0.1:5000")
    threading.Thread(target=start_background_sound_monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)
