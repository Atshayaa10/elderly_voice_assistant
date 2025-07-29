import whisper
import os
import wave
import pyaudio
from utils.emergency_alert import send_emergency_alert

# Load the Whisper model once
model = whisper.load_model("base")

def record_audio(duration=5, filename="output.wav"):
    chunk = 1024
    sample_format = pyaudio.paInt16
    channels = 1
    fs = 16000
    p = pyaudio.PyAudio()

    print("🎙️ Listening...")

    stream = p.open(format=sample_format,
                    channels=channels,
                    rate=fs,
                    frames_per_buffer=chunk,
                    input=True)

    frames = []

    for _ in range(0, int(fs / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(sample_format))
    wf.setframerate(fs)
    wf.writeframes(b''.join(frames))
    wf.close()

    return filename

def transcribe(audio_path):
    try:
        result = model.transcribe(audio_path)
        text = result['text'].strip()
        if not text:
            return "No speech detected."
        return text
    except Exception as e:
        return f"❌ Transcription failed: {str(e)}"

def listen_and_process():
    print("🎙️ Listening...")
    audio = record_audio()
    print("⏳ Transcribing...")
    result = transcribe(audio)
    print("📝 Output:", result)

    emergency_keywords = ["help", "emergency", "call", "message", "save me"]
    if any(word in result.lower() for word in emergency_keywords):
        send_emergency_alert()
        return f"🆘 Emergency detected! Message and call sent. ➡️ {result}"
    else:
        return f"🎤 You said: {result}"

# Optional standalone usage
if __name__ == "__main__":
    audio_file = record_audio(duration=6)
    print("⏳ Transcribing...")
    result = transcribe(audio_file)
    print("📝 Output:", result)

    if any(keyword in result.lower() for keyword in ["help", "emergency", "call now", "send message", "save me"]):
        send_emergency_alert()
    else:
        print("ℹ️ No emergency command detected.")
