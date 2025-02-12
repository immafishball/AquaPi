import sqlite3
import time
import RPi.GPIO as GPIO
import os
import time
import sys

DATABASE = '/home/pi/Projects/AquaPi/sensor_data.db'

SERVO_PIN = 5
GPIO.setmode(GPIO.BCM)

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from DFRobot_RaspberryPi_Expansion_Board import DFRobot_Expansion_Board_IIC as Board

board = Board(1, 0x10)    # Select i2c bus 1, set address to 0x10

def board_detect():
  l = board.detecte()
  print("Board list conform:")
  print(l)

''' print last operate status, users can use this variable to determine the result of a function call. '''
def print_board_status():
  if board.last_operate_status == board.STA_OK:
    print("board status: everything ok")
  elif board.last_operate_status == board.STA_ERR:
    print("board status: unexpected error")
  elif board.last_operate_status == board.STA_ERR_DEVICE_NOT_DETECTED:
    print("board status: device not detected")
  elif board.last_operate_status == board.STA_ERR_PARAMETER:
    print("board status: parameter error")
  elif board.last_operate_status == board.STA_ERR_SOFT_VERSION:
    print("board status: unsupport board framware version")

board_detect()
# Pwm channel need external power
board.set_pwm_enable()        
# board.set_pwm_disable()
board.set_pwm_frequency(1000) 

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

def feed_now():
    try:
        print("set all pwm channels duty to 30%")
        board.set_pwm_duty(0, 60)   # Set all pwm channels duty
        time.sleep(2)

        print("set part pwm channels duty to 60%")
        board.set_pwm_duty(0, 0)   # Set pwm0 channels duty
        #board.set_pwm_duty(1, 70)  # Set pwm1 channels duty
        #board.set_pwm_duty(2, 80)  # Set pwm2 channels duty
        #board.set_pwm_duty(3, 90)  # Set pwm3 channels duty
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
