from langdetect import detect
from transformers import MarianMTModel, MarianTokenizer

def detect_language(text):
    return detect(text)

def translate_to_english(text, src_lang_code):
    model_name = f"Helsinki-NLP/opus-mt-{src_lang_code}-en"
    model = MarianMTModel.from_pretrained(model_name)
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    batch = tokenizer.prepare_seq2seq_batch([text], return_tensors="pt")
    translated = model.generate(**batch)
    return tokenizer.decode(translated[0], skip_special_tokens=True)
