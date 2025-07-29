from TTS.api import TTS

tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)

def speak(text, output_path="static/audio/response.wav"):
    tts.tts_to_file(text=text, file_path=output_path)
