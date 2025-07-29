from transformers import pipeline
summarizer = pipeline("summarization", model="t5-small")

def summarize(text):
    if len(text.split()) > 30:
        return summarizer(text, max_length=40, min_length=15, do_sample=False)[0]['summary_text']
    return text
