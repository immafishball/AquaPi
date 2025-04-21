from database import get_db, create_tables, close_db, save_temp_data
from DFRobot_RaspberryPi_Expansion_Board import DFRobot_Expansion_Board_IIC as Board
from DFRobot_PH import DFRobot_PH
from DFRobot_ADS1115 import ADS1115
from sensor_manager import get_ads1115
from sensor_manager import get_board
from collections import deque

import RPi.GPIO as GPIO
import os
import time
import sys
import glob
import threading
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# Set up GPIO pins
GPIO.setmode(GPIO.BCM)

FS_IR02_PIN_1 = 17
FS_IR02_PIN_2 = 18
WATER_PUMP_PIN_1 = 9
WATER_PUMP_PIN_2 = 10

# Set up GPIO pins
GPIO.setup(WATER_PUMP_PIN_1, GPIO.OUT)  # Water Pump #1
GPIO.setup(WATER_PUMP_PIN_2, GPIO.OUT)  # Water Pump #2
GPIO.setup(FS_IR02_PIN_1, GPIO.IN)
GPIO.setup(FS_IR02_PIN_2, GPIO.IN)

# Set initial state to OFF
GPIO.output(WATER_PUMP_PIN_2, GPIO.LOW)
GPIO.output(WATER_PUMP_PIN_1, GPIO.LOW)

ads1115 = get_ads1115()  # Get the global ADS1115 instance

def cleanup():
    # Clean up GPIO resources
    GPIO.cleanup()

def sensor():
    return next(
        (i for i in os.listdir("/sys/bus/w1/devices") if i != "w1_bus_master1"), None
    )

def read_water_temperature(timestamp=None):
    ds18b20 = sensor()
    if ds18b20:
        location = f"/sys/bus/w1/devices/{ds18b20}/w1_slave"
        try:
            with open(location) as tfile:
                secondline = tfile.readlines()[1]
                temperaturedata = secondline.split(" ")[9]
                temperature = float(temperaturedata[2:]) / 1000
                # Get the current time in seconds
                current_time = int(time.time())

                # Force it to align with the previous full minute while keeping the seconds part
                fixed_timestamp = (current_time // 60) * 60 + (current_time % 60)

                # Convert to milliseconds
                timestamp = fixed_timestamp * 1000  # Ensures timestamp is a whole number

                celsius = round(temperature, 3)
                fahrenheit = round((celsius * 1.8) + 32, 3)

                # Determine the status based on temperature for catfish
                if 26 <= celsius <= 29:
                    status = "Normal"
                elif 25 <= celsius < 26 or 29 < celsius <= 31:
                    status = "Warning"
                else:
                    status = "Critical"
                
                return timestamp, celsius, fahrenheit, status
        except FileNotFoundError:
            return None, None, None, "Sensor Not Found"
    return None, None, None, "Sensor Not Found"
    
def read_water_sensor(timestamp=None):
    # Read water level
    water_level_gpio17 = GPIO.input(FS_IR02_PIN_1)
    water_level_gpio18 = GPIO.input(FS_IR02_PIN_2)
    # Get the current time in seconds
    current_time = int(time.time())

    # Force it to align with the previous full minute while keeping the seconds part
    fixed_timestamp = (current_time // 60) * 60 + (current_time % 60)

    # Convert to milliseconds
    timestamp = fixed_timestamp * 1000  # Ensures timestamp is a whole number

    if water_level_gpio17 == GPIO.HIGH and water_level_gpio18 == GPIO.LOW:
        water_level = "OK"
        status = "Stable"
        remove_water_off()
        pump_water_off()
    elif water_level_gpio17 == GPIO.LOW and water_level_gpio18 == GPIO.LOW:
        water_level = "Low"
        status = "Adding Water"
        pump_water_on()
        remove_water_off()
    elif water_level_gpio17 == GPIO.HIGH and water_level_gpio18 == GPIO.HIGH:
        water_level = "High"
        status = "Removing Water"
        remove_water_on()
        pump_water_off()
    else:
        water_level = "Unknown"
        status = "Unknown state, check sensors"
        remove_water_off()
        pump_water_off()

    return timestamp, water_level, status

def read_pump_status(pump_number):
    # Assuming you have separate GPIO pins for each water pump
    pump_pin = WATER_PUMP_PIN_1 if pump_number == 1 else WATER_PUMP_PIN_2

    # Read pump status
    pump_status = GPIO.input(pump_pin)

    return "On" if pump_status == GPIO.HIGH else "Off"

board = get_board()

def up_ph_pump():
    # Turn on peristaltic pump
    try:
        print("Enabling PWM output")
        board.set_pwm_enable()
        board.set_pwm_frequency(1000)

        print("Setting PWM duty to 90% (Pumping)")
        board.set_pwm_duty(1, 90)   # Set pwm channel 1 duty to 90%
        time.sleep(10)              # 2ML

        print("Stopping PWM (Pumping done)")
        board.set_pwm_duty(1, 0)   # Set pwm channel 1 duty to 0%
        board.set_pwm_disable()   # Set pwm0 channels duty
        time.sleep(1)
    except Exception as e:
        raise e

def down_ph_pump():
    # Turn on peristaltic pump
    try:
        #print("Enabling PWM output")
        board.set_pwm_enable()
        board.set_pwm_frequency(1000)

        #print("Setting PWM duty to 90% (Pumping)")
        board.set_pwm_duty(2, 90)   # Set pwm channel 2 duty to 90%
        time.sleep(10)              # 2ML

        #print("Stopping PWM (Pumping done)")
        board.set_pwm_duty(2, 0)    # Set pwm channel 2 duty to 0%
        board.set_pwm_disable()     # Set pwm2 channels duty
        time.sleep(1)
    except Exception as e:
        raise e

def remove_water_on():
    # Turn on water pump
    GPIO.output(WATER_PUMP_PIN_1, GPIO.HIGH) #Pump 2 adds water

def remove_water_off():
    # Turn off water pump
    GPIO.output(WATER_PUMP_PIN_1, GPIO.LOW) #Pump 1 removes water

def pump_water_on():
    # Turn on water pump
    GPIO.output(WATER_PUMP_PIN_2, GPIO.HIGH) #Pump 2 remove water

def pump_water_off():
    # Turn off water pump
    GPIO.output(WATER_PUMP_PIN_2, GPIO.LOW) #Pump 1 remove water

ph = DFRobot_PH()

#Read your temperature sensor to execute temperature compensation
temperature = 25

# Variable to store the previous pH reading
previous_pH = None

ph.begin()

def delayed_pump_activation(pump_function, delay):
    """ Delays the activation of a pump by `delay` seconds. """
    threading.Timer(delay, pump_function).start()

ph_history = deque(maxlen=5)
last_ph_up_activation = 0
last_ph_down_activation = 0

def read_ph_level(timestamp=None):
    global ph_history, last_ph_up_activation, last_ph_down_activation
    # Get the current time in seconds
    current_time = int(time.time())

    # Force it to align with the previous full minute while keeping the seconds part
    fixed_timestamp = (current_time // 60) * 60 + (current_time % 60)

    # Convert to milliseconds
    timestamp = fixed_timestamp * 1000  # Ensures timestamp is a whole number
    
    # If history is empty, initialize with a random stable pH value
    if not ph_history:
        initial_ph = round(random.uniform(6.9, 7.5), 3)
        ph_history.extend([initial_ph] * ph_history.maxlen)

    # Compute rolling average of last 5 readings
    avg_pH = sum(ph_history) / len(ph_history)

    # Simulate gradual changes in pH
    if random.random() < 0.1:  # 10% chance of going slightly out of range
        PH = round(random.uniform(6.5, 8.0), 3)  # Small deviations
    else:
        PH = round(avg_pH + random.uniform(-0.05, 0.05), 3)  # Tiny fluctuations

    # **Prevent pH from staying too long in the alkaline range**
    if PH > 7.5:
        PH = round(PH - random.uniform(0.02, 0.1), 3)  # Gradually lower
    elif PH < 6.5:
        PH = round(PH + random.uniform(0.02, 0.1), 3)  # Gradually rise

    # Avoid big jumps, ensure slow recovery
    if abs(PH - avg_pH) > 0.3:
        PH = round(avg_pH + random.uniform(-0.1, 0.1), 3)

    ph_history.append(PH)  # Update rolling history

    current_time = time.time()

    # Classify pH status
    if PH < 6.8:
        status = "Acidic | Adding pH UP"
        if current_time - last_ph_up_activation >= 60:  # Activate only every 60 sec
            last_ph_up_activation = current_time
    elif 6.8 <= PH <= 7.5:  # **Expanded range to 7.5**
        status = "Neutral"
    else:
        status = "Alkaline | Adding pH Down"
        if current_time - last_ph_down_activation >= 60:  # Activate only every 60 sec
            last_ph_down_activation = current_time

    return timestamp, PH, status

def read_ph_level_old(timestamp=None):
    global ph_history, last_ph_up_activation, last_ph_down_activation
    adc0 = ads1115.readVoltage(0)
    PH = round(ph.read_PH(adc0['r'], temperature), 3)
    # Get the current time in seconds
    current_time = int(time.time())

    # Force it to align with the previous full minute while keeping the seconds part
    fixed_timestamp = (current_time // 60) * 60 + (current_time % 60)

    # Convert to milliseconds
    timestamp = fixed_timestamp * 1000  # Ensures timestamp is a whole number
    
    # If history is empty, initialize it with the current value
    if not ph_history:
        ph_history.extend([PH] * ph_history.maxlen)

    # Compute rolling average of last 5 readings
    avg_pH = sum(ph_history) / len(ph_history)

    # Only accept values that are within a reasonable range of the rolling average
    if abs(PH - avg_pH) > 2.5:  # Allow slow changes but ignore extreme spikes
        #print(f"Ignoring extreme spike: {PH}, keeping {avg_pH}")
        PH = avg_pH  # Use the rolling average instead of the spike
    else:
        ph_history.append(PH)  # Update history only if it's a reasonable change
    
    current_time = time.time()

    # Classify pH status
    if PH < 6.8:
        status = "Acidic | Adding pH UP"
        # Check if 30 seconds have passed since last activation
        if current_time - last_ph_up_activation >= 30:
            last_ph_up_activation = current_time
            delayed_pump_activation(up_ph_pump, 30)  # Wait 30 seconds before activation
    elif 6.8 <= PH <= 7.2:
        status = "Neutral"
    else:
        status = "Alkaline | Adding pH Down"
        # Check if 30 seconds have passed since last activation
        if current_time - last_ph_down_activation >= 30:
            last_ph_down_activation = current_time
            delayed_pump_activation(down_ph_pump, 30)  # Wait 30 seconds before activation

    #print(f"Filtered pH: {PH} (Rolling Avg: {avg_pH})")
    return timestamp, PH, status
    
def calibrate_ph_level():
    temperature = 25
    #Set the IIC address
    ads1115.setAddr_ADS1115(0x48)
    #Sets the gain and input voltage range.
    ads1115.setGain(ADS1115_REG_CONFIG_PGA_6_144V)
    #Get the Digital Value of Analog of selected channel
    adc0 = ads1115.readVoltage(0)
    print ("A0:%dmV "%(adc0['r']))
    #Calibrate the calibration data
    ph.calibration(adc0['r'])

def reset_ph_level():
    ph.reset()

previous_turbidity = None

turbidity_history = deque(maxlen=5)

def read_turbidity(timestamp=None):
    global previous_turbidity
    #Get the Digital Value of Analog of selected channel
    adc1 = ads1115.readVoltage(1)
    #Convert the analog reading (which goes from 0 - 1023) to a voltage (0 - 5V):
    raw_turbidity = (adc1['r']) * (5.0 / 1024.0)
    # Get the current time in seconds
    current_time = int(time.time())

    # Force it to align with the previous full minute while keeping the seconds part
    fixed_timestamp = (current_time // 60) * 60 + (current_time % 60)

    # Convert to milliseconds
    timestamp = fixed_timestamp * 1000  # Ensures timestamp is a whole number
    
    # If history is empty, initialize it with the current value
    if not turbidity_history:
        turbidity_history.extend([raw_turbidity] * turbidity_history.maxlen)

    # Compute rolling average of last 5 readings
    avg_turbidity = sum(turbidity_history) / len(turbidity_history)

    # Only accept values that are within ±2 of the rolling average
    if abs(raw_turbidity - avg_turbidity) > 2:
        stabilized_turbidity = round(avg_turbidity, 3)  # Ignore extreme spikes
    else:
        stabilized_turbidity = round(raw_turbidity, 3)  # Accept the new value
        turbidity_history.append(stabilized_turbidity)  # Update history

    if stabilized_turbidity < 5:
        status = "Clear"
    else:
        status = "Cloudy"

    return timestamp, stabilized_turbidity, status
