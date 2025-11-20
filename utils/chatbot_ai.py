# utils/chatbot_ai.py
"""
AI reply engine for Elderly Voice Assistant
- Uses Facebook BlenderBot 400M (distilled) for higher-quality, on-topic replies
- Keeps a short conversation memory
- Speaks replies via pyttsx3 (local TTS)
"""

from collections import deque
import re
import pyttsx3

import torch
from transformers import (
    BlenderbotTokenizer,
    BlenderbotForConditionalGeneration,
)

# ----------------------- Model Load -----------------------
MODEL_NAME = "facebook/blenderbot-400M-distill"

print("[INFO] Loading conversational model:", MODEL_NAME)
tokenizer = BlenderbotTokenizer.from_pretrained(MODEL_NAME)
model = BlenderbotForConditionalGeneration.from_pretrained(MODEL_NAME)

# Use CUDA if available for faster generation
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(DEVICE)

# ------------------- Conversation Memory -------------------
# Keep the last few user/assistant turns to give context
MAX_TURNS = 6  # total pairs kept (user -> assistant)
history = deque(maxlen=MAX_TURNS * 2)  # store alternating strings

# --------------------- Text-to-Speech ----------------------
engine = pyttsx3.init()
engine.setProperty("rate", 165)
engine.setProperty("volume", 0.95)

# --------------------- Safety Helpers ----------------------
_BLOCKLIST = [
    r"\b(self\s*harm|suicide|kill\s*myself)\b",
    r"\b(bomb|make\s*weapon|explosive)\b",
]
def looks_unsafe(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in _BLOCKLIST)

def safe_reply_fallback() -> str:
    return ("I'm here to help. For your safety, I can't assist with that. "
            "If this is an emergency, please contact local authorities or a trusted caregiver.")

# --------------------- Core Functions ----------------------
def _build_context(user_input: str) -> str:
    """
    Turn short memory into a single context string for BlenderBot.
    Format: 'user: ...\nassistant: ...\nuser: ...\nassistant: ...\nuser: <new>'
    """
    lines = list(history) + [f"user: {user_input.strip()}"]
    return "\n".join(lines)

@torch.inference_mode()
def generate_ai_reply(user_input: str) -> str:
    """
    Generate an AI reply using BlenderBot with brief conversation memory.
    """
    if not user_input or not user_input.strip():
        return "I didn’t catch that. Could you please say it again?"

    if looks_unsafe(user_input):
        return safe_reply_fallback()

    # Build context and tokenize
    context = _build_context(user_input)
    inputs = tokenizer([context], return_tensors="pt", padding=True, truncation=True)
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

    # Generate a response (tuned for helpful but concise replies)
    gen_ids = model.generate(
        **inputs,
        max_new_tokens=120,
        do_sample=True,
        top_p=0.92,
        temperature=0.8,
        repetition_penalty=1.12,
        no_repeat_ngram_size=3,
        eos_token_id=tokenizer.eos_token_id,
    )

    reply = tokenizer.decode(gen_ids[0], skip_special_tokens=True).strip()

    # Update memory
    history.append(f"user: {user_input.strip()}")
    history.append(f"assistant: {reply}")

    # Last polish: avoid empty or echo-y replies
    if not reply:
        reply = "Alright. How can I assist you next?"
    return reply

def speak_reply(reply: str):
    """
    Speak out the AI reply using local text-to-speech.
    """
    say = reply if reply else "I'm here, but I didn't catch that."
    print("[AI REPLY]:", say)
    engine.say(say)
    engine.runAndWait()

# ------------------ Quick standalone test ------------------
if __name__ == "__main__":
    print("Chatbot ready. Type 'exit' to quit.\n")
    while True:
        msg = input("You: ").strip()
        if msg.lower() in {"exit", "quit", "bye"}:
            print("Goodbye 👋")
            break
        ans = generate_ai_reply(msg)
        print("Bot:", ans)
        speak_reply(ans)
