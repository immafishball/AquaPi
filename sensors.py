from database import get_db, create_tables, close_db, save_temp_data

import RPi.GPIO as GPIO
import os
import time

# Set up GPIO pins
GPIO.setmode(GPIO.BCM)
FS_IR02_PIN_1 = 17
FS_IR02_PIN_2 = 18
TURB_PIN = 8


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
    # Set up GPIO pins
    GPIO.setup(FS_IR02_PIN_1, GPIO.IN)
    GPIO.setup(FS_IR02_PIN_2, GPIO.IN)

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


def read_turbidity():
    # Set up GPIO pins
    GPIO.setup(TURB_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Read Turbidity
    input_state = GPIO.input(TURB_PIN)
    if input_state == False:
        return "High"
    else:
        return "Low"


def cleanup():
    if GPIO.getmode() is not None:  # Check if GPIO channels have been set up
        GPIO.cleanup()
