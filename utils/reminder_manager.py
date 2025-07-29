import schedule
import time
import threading

reminders = []

def add_reminder(time_str, message):
    schedule.every().day.at(time_str).do(trigger_reminder, message)
    reminders.append((time_str, message))

def trigger_reminder(message):
    print(f"[Reminder] {message}")

def run_reminders():
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_reminder_loop():
    t = threading.Thread(target=run_reminders)
    t.daemon = True
    t.start()
