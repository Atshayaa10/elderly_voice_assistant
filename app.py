from flask import Flask, request, jsonify, render_template
import os
from utils import speech_to_text, text_to_speech, intent_classifier, reminder_manager, emergency_alert
from utils.speech_to_text import listen_and_process  # Ensure recognize_speech is defined
from utils.emergency_alert import send_emergency_alert

app = Flask(__name__)

# -------------------- Configuration -------------------- #
UPLOAD_FOLDER = 'audio'
INPUT_AUDIO = os.path.join(UPLOAD_FOLDER, 'input.wav')
OUTPUT_AUDIO = os.path.join('static', 'output.wav')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static', exist_ok=True)

# -------------------- ROUTES -------------------- #
@app.route('/')
def index():
    return render_template('index.html')  # Landing page with "Get Started"

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/reminders')
def reminders():
    return render_template('reminders.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

# ------------------ AUDIO FILE UPLOAD ROUTE ------------------ #
@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files['file']
        file.save(INPUT_AUDIO)
        print(f"[INFO] Audio file saved to: {INPUT_AUDIO}")

        # 1. Transcribe
        text = speech_to_text.transcribe(INPUT_AUDIO)
        print(f"[TRANSCRIBED] You said: {text}")

        # 2. Emergency keyword detection
        emergency_keywords = ['help', 'emergency', 'save me', 'danger', 'i need help']
        if any(keyword in text.lower() for keyword in emergency_keywords):
            print("[EMERGENCY] Triggering alert...")
            send_emergency_alert()
            print("[EMERGENCY] SMS & Call sent.")

        # 3. Intent classification
        intent = intent_classifier.classify(text)
        print(f"[INTENT] Detected: {intent}")

        # 4. Response generation
        response = intent_classifier.handle_intent(intent, text)
        print(f"[RESPONSE] {response}")

        # 5. Text-to-speech
        text_to_speech.speak(response, OUTPUT_AUDIO)
        print(f"[AUDIO] Response saved to: {OUTPUT_AUDIO}")

        return jsonify({
            'response': response,
            'audio': '/' + OUTPUT_AUDIO.replace('\\', '/')
        })

    except Exception as e:
        print("[ERROR]", e)
        return jsonify({'error': str(e)}), 500

# ------------------ SPEECH FROM MIC (JS "Speak" button) ------------------ #
@app.route('/speech-to-text', methods=['POST'])
def speech_to_text_route():
    try:
        text = recognize_speech()
        print(f"[MIC TRANSCRIBED] {text}")

        # Check for emergency
        emergency_keywords = ['help', 'emergency', 'save me', 'danger', 'i need help']
        if any(keyword in text.lower() for keyword in emergency_keywords):
            print("[EMERGENCY] Triggering alert...")
            send_emergency_alert()
            print("[EMERGENCY] SMS & Call sent.")

        return jsonify({'transcript': text})
    except Exception as e:
        print("[ERROR]", e)
        return jsonify({'error': str(e)}), 500

# ------------------ LISTEN VIA BUTTON ------------------ #
@app.route('/listen', methods=['POST'])
def listen():
    result = listen_and_process()
    return jsonify({"output": result})
@app.route('/voice_input', methods=['POST'])
def voice_input():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'status': 'No text received'}), 400

    user_input = data['text'].strip().lower()
    print("🗣️ User input received:", user_input)

    # ✅ Emergency Trigger Condition
    if any(keyword in user_input for keyword in ['help', 'emergency', 'sos']):
        send_emergency_alert()
        reply = "🚨 Emergency detected. Help is on the way!"
    else:
        reply = f"I understand you said: {user_input}"  # Normal assistant response

    return jsonify({'status': reply})
# ------------------ RUN APP ------------------ #
if __name__ == '__main__':
    app.run(debug=True)
