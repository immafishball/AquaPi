import sqlite3
import time
import RPi.GPIO as GPIO
import os
import time
import sys
from sensor_manager import get_board

DATABASE = '/home/pi/Projects/AquaPi/sensor_data.db'

SERVO_PIN = 5
GPIO.setmode(GPIO.BCM)

def create_table():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS feeding_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Add the following line to ensure the table exists
create_table()

board = get_board()

def feed_now():
    try:
        print("Enabling PWM output")
        board.set_pwm_enable()
        board.set_pwm_frequency(1000)

        print("Setting PWM duty to 60% (Feeding)")
        board.set_pwm_duty(0, 60)   # Set all pwm channels duty
        time.sleep(5)

        print("Stopping PWM (Feeding done)")
        board.set_pwm_duty(0, 0)   # Stop PWM by setting duty to 0%
        board.set_pwm_disable()   # Set pwm0 channels duty
        time.sleep(1)
    except Exception as e:
        raise e
        
def feed_now_old():
    try:
        # Code to control servo motor here
        GPIO.setup(SERVO_PIN, GPIO.OUT)
        pwm = GPIO.PWM(SERVO_PIN, 50)
        pwm.start(0)
        pwm.ChangeDutyCycle(50)
        time.sleep(2)
        pwm.stop()
    except Exception as e:
        raise e
        
def add_schedule(time):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('INSERT INTO feeding_schedule (time) VALUES (?)', (time,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(str(e))
        return False

def remove_schedule(schedule_id):
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('DELETE FROM feeding_schedule WHERE id = ?', (schedule_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(str(e))
        return False

def get_schedules():
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('SELECT id, time FROM feeding_schedule ORDER BY id')
        schedules = [{'id': row[0], 'time': row[1]} for row in c.fetchall()]
        conn.close()
        return schedules
    except Exception as e:
        print(str(e))
        return []

# ... other logic functions if needed
def cleanup():
    if GPIO.getmode() is not None:  # Check if GPIO channels have been set up
        GPIO.cleanup()
