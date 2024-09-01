from database import get_db, create_tables, close_db, save_temp_data
from DFRobot_RaspberryPi_Expansion_Board import DFRobot_Expansion_Board_IIC as Board
from DFRobot_PH import DFRobot_PH

import RPi.GPIO as GPIO
import os
import time
import sys
import glob

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# Set up GPIO pins
GPIO.setmode(GPIO.BCM)
FS_IR02_PIN_1 = 18
FS_IR02_PIN_2 = 17
TURB_PIN = 12
WATER_PUMP_PIN_1 = 9
WATER_PUMP_PIN_2 = 10

# Set up GPIO pins
GPIO.setup(WATER_PUMP_PIN_1, GPIO.OUT)  # Water Pump #1
GPIO.setup(WATER_PUMP_PIN_2, GPIO.OUT)  # Water Pump #2
GPIO.setup(TURB_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Turbidity
GPIO.setup(FS_IR02_PIN_1, GPIO.IN)
GPIO.setup(FS_IR02_PIN_2, GPIO.IN)

# Set initial state to OFF
GPIO.output(WATER_PUMP_PIN_2, GPIO.LOW)
GPIO.output(WATER_PUMP_PIN_1, GPIO.LOW)

board = Board(1, 0x10)    # Select i2c bus 1, set address to 0x10
    
def board_detect():
  l = board.detecte()
  '''print("Board list conform:")'''
  '''print(l)'''

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
    
def cleanup():
    # Clean up GPIO resources
    GPIO.cleanup()


def sensor():
    return next(
        (i for i in os.listdir("/sys/bus/w1/devices") if i != "w1_bus_master1"), None
    )


def read_water_temperature():
    ds18b20 = sensor()
    if ds18b20:
        location = f"/sys/bus/w1/devices/{ds18b20}/w1_slave"
        try:
            with open(location) as tfile:
                secondline = tfile.readlines()[1]
                temperaturedata = secondline.split(" ")[9]
                temperature = float(temperaturedata[2:]) / 1000
                timestamp = time.time() * 1000
                celsius = temperature
                fahrenheit = (celsius * 1.8) + 32
                return timestamp, celsius, fahrenheit
        except FileNotFoundError:
            return None, None, None
    return None, None, None


def read_water_sensor():
    # Read water level
    water_level_gpio17 = GPIO.input(FS_IR02_PIN_1)
    water_level_gpio18 = GPIO.input(FS_IR02_PIN_2)

    if water_level_gpio17 == GPIO.HIGH and water_level_gpio18 == GPIO.LOW:
        return "OK"
    elif water_level_gpio17 == GPIO.LOW and water_level_gpio18 == GPIO.LOW:
        return "Low"
    elif water_level_gpio17 == GPIO.HIGH and water_level_gpio18 == GPIO.HIGH:
        return "High"
    else:
        return "Unknown"


def read_pump_status(pump_number):
    # Assuming you have separate GPIO pins for each water pump
    pump_pin = WATER_PUMP_PIN_1 if pump_number == 1 else WATER_PUMP_PIN_2

    # Read pump status
    pump_status = GPIO.input(pump_pin)

    return "On" if pump_status == GPIO.HIGH else "Off"


def fill_water_on():
    # Turn on water pump
    GPIO.output(WATER_PUMP_PIN_1, GPIO.HIGH)


def fill_water_off():
    # Turn off water pump
    GPIO.output(WATER_PUMP_PIN_1, GPIO.LOW)


def read_turbidity():
    # Read Turbidity
    input_state = GPIO.input(TURB_PIN)
    if input_state == False:
        return "High"
    else:
        return "Low"

board_detect()
board.set_adc_enable()
    
ph = DFRobot_PH()

def read_ph_level():
    ph.begin()
    
    val = board.get_adc_value(board.A3)
    pH = ph.read_PH(val, 25)
    return pH    
    
def calibrate_ph_level():
    val = board.get_adc_value(board.A3)
    ph.calibration(val)

def reset_ph_level():
    ph.reset()