import json
import datetime

def save_to_log(user_text, system_reply, log_file='data/chat_history.json'):
    with open(log_file, 'a') as f:
        entry = {
            "time": str(datetime.datetime.now()),
            "user": user_text,
            "assistant": system_reply
        }
        f.write(json.dumps(entry) + "\n")
