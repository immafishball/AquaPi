# cron_script.py
from datetime import datetime
from feeder import feed_now
import sqlite3
import os

current_dir = os.getcwd()
LOG_FILE = '/home/pi/Projects/AquaPi/cron_log.txt'
DATABASE = '/home/pi/Projects/AquaPi/sensor_data.db'

def log(message):
    with open(LOG_FILE, 'a') as f:
        f.write(f"{datetime.now()} - {message}\n")

def check_schedules():
    try:
        now_str = datetime.now().strftime('%H:%M')  # Format current time as string

        log(f"Checking schedules at {now_str}") #off print

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        #Select schedules where the time is less than or equal to the current time
        cursor.execute("SELECT * FROM feeding_schedule WHERE time <= ?", (now_str,))
        schedules = cursor.fetchall()

        found_schedule = False  # Flag to track if a schedule is found

        for schedule in schedules:
            if now_str == schedule[1]:  # Compare time strings directly
                feed_now()
                log(f"Feeding triggered for schedule ID {schedule[0]} at {now_str}")
                found_schedule = True  # Set the flag to True if a schedule is found

        if not found_schedule:
            log(f"No schedule found at {now_str}")

        conn.close()
    except Exception as e:
        log(f"Error checking schedules: {str(e)}")

if __name__ == '__main__':
    check_schedules()
