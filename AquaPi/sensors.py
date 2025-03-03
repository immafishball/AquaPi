from database import get_db, create_tables, close_db, save_temp_data
from DFRobot_RaspberryPi_Expansion_Board import DFRobot_Expansion_Board_IIC as Board
from DFRobot_PH import DFRobot_PH
from DFRobot_ADS1115 import ADS1115
from sensor_manager import get_ads1115

import RPi.GPIO as GPIO
import os
import time
import sys
import glob

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
                timestamp = time.time() * 1000
                celsius = temperature
                fahrenheit = (celsius * 1.8) + 32

                # Determine the status based on temperature for catfish
                if (celsius>23 and celsius<27):
                    status = "Normal"
                elif (celsius>21 and celsius<23) or (celsius>27 and celsius<29):
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
    timestamp = time.time() * 1000  # Get current timestamp in milliseconds

    if water_level_gpio17 == GPIO.HIGH and water_level_gpio18 == GPIO.LOW:
        water_level = "OK"
    elif water_level_gpio17 == GPIO.LOW and water_level_gpio18 == GPIO.LOW:
        water_level = "Low"
    elif water_level_gpio17 == GPIO.HIGH and water_level_gpio18 == GPIO.HIGH:
        water_level = "High"
    else:
        water_level = "Unknown"

    return timestamp, water_level

def read_pump_status(pump_number):
    # Assuming you have separate GPIO pins for each water pump
    pump_pin = WATER_PUMP_PIN_1 if pump_number == 1 else WATER_PUMP_PIN_2

    # Read pump status
    pump_status = GPIO.input(pump_pin)

    return "On" if pump_status == GPIO.HIGH else "Off"

def read_operation_status(timestamp=None):
    # Read sensor values
    _, celsius, fahrenheit, temp_status = read_water_temperature()
    _, water_level = read_water_sensor()
    _, ph, ph_status = read_ph_level()
    _, turbidity, status = read_turbidity()
    #_, operation, status = read_operation_status()

    # Control logic based on thresholds
    ph_threshold = 7.0
    temp_upper_threshold = 28.0
    temp_lower_threshold = 22.0
    water_level_high = 'High'
    water_level_low = 'Low'

    # Logic for controlling pumps
    if ph > ph_threshold:
        pump_water_on()
        remove_water_on()
        operation = "Replacing Water"
        status = "Ongoing"
    elif celsius > temp_upper_threshold or celsius < temp_lower_threshold:
        pump_water_on()
        remove_water_on()
        operation = "Replacing Water"
        status = "Ongoing"
    elif water_level == water_level_high:
        pump_water_off()
        remove_water_on()
        operation = "Reducing Water"
        status = "Ongoing"
    elif water_level == water_level_low:
        pump_water_on()
        remove_water_off()
        operation = "Adding Water"
        status = "Ongoing"
    else:
        pump_water_off()
        remove_water_off()  # Turn off pumps
        operation = "No Operation"
        status = "Stable"
    
    return timestamp, operation, status

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

def read_ph_level(timestamp=None):
    global previous_pH
    #Get the Digital Value of Analog of selected channel
    adc0 = ads1115.readVoltage(0)
    #Convert voltage to PH with temperature compensation
    PH = ph.read_PH(adc0['r'],temperature)

    current_pH = PH
    timestamp = time.time() * 1000

    if previous_pH is None:
        previous_pH = current_pH

    # Check if the fluctuation is within ±2 of the previous reading
    if abs(current_pH - previous_pH) > 2:
        current_pH = previous_pH # -> Ignore value if there is sudden fluctuation in pH
    else:
        previous_pH = current_pH # -> Temporary fix for fluctuations

    if current_pH < 7:
        status = "Acidic"
    elif current_pH == 7:
        status = "Neutral"
    else:
        status = "Alkaline"

    return timestamp, current_pH, status
    
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

def read_turbidity(timestamp=None):
    global previous_turbidity
    #Get the Digital Value of Analog of selected channel
    adc1 = ads1115.readVoltage(1)
    #Convert the analog reading (which goes from 0 - 1023) to a voltage (0 - 5V):
    turbidity = (adc1['r']) * (5.0 / 1024.0)

    current_turbidity = turbidity
    timestamp = time.time() * 1000  # Get current timestamp in milliseconds

    if previous_turbidity is None:
        previous_turbidity = current_turbidity

    # Check if the fluctuation is within ±5 of the previous reading
    if abs(current_turbidity - previous_turbidity) > 2:
        current_turbidity = previous_turbidity
    else:
        previous_turbidity = current_turbidity
        
    if current_turbidity < 5:
        status = "Clear"
    else:
        status = "Cloudy"

    return timestamp, current_turbidity, status
