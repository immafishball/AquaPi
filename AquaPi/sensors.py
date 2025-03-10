from database import get_db, create_tables, close_db, save_temp_data
from DFRobot_RaspberryPi_Expansion_Board import DFRobot_Expansion_Board_IIC as Board
from DFRobot_PH import DFRobot_PH
from DFRobot_ADS1115 import ADS1115
from sensor_manager import get_ads1115
from sensor_manager import get_board

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
        print("Enabling PWM output")
        board.set_pwm_enable()
        board.set_pwm_frequency(1000)

        print("Setting PWM duty to 90% (Pumping)")
        board.set_pwm_duty(2, 90)   # Set pwm channel 2 duty to 90%
        time.sleep(10)              # 2ML

        print("Stopping PWM (Pumping done)")
        board.set_pwm_duty(2, 0)    # Set pwm channel 2 duty to 0%
        board.set_pwm_disable()     # Set pwm2 channels duty
        time.sleep(1)
    except Exception as e:
        raise e
    
def read_operation_status(timestamp=None):
    global pump_in_active, pump_out_active  # Use global variables to track pump state

    if timestamp is None:
        timestamp = time.time() * 1000  # Get the current timestamp

    # Read sensor values
    _, celsius, fahrenheit, temp_status = read_water_temperature()
    _, water_level = read_water_sensor()
    _, ph, ph_status = read_ph_level()
    _, turbidity, status = read_turbidity()
    #_, operation, status = read_operation_status()

    # pH threshold range for stability
    ph_min = 6.8  # Lower bound
    ph_max = 7.2  # Upper bound

    # Initialize operation status
    operation = "No Operation"
    status = "Stable"

    operation_performed = False  # Track if any operation is performed

    # Logic for controlling pH pumps
    if ph < ph_min:  
        operation = "pH too low, activating pH UP pump"
        status = "Ongoing"
        print(f"[{timestamp}] pH too low ({ph}), activating up_pH_pump to increase pH")
        up_ph_pump()  # Increase pH
        operation_performed = True
    elif ph > ph_max:
        operation = "pH too high, activating pH DOWN pump"
        status = "Ongoing"
        print(f"[{timestamp}] pH too high ({ph}), activating down_pH_pump to decrease pH")
        down_ph_pump()  # Decrease pH
        operation_performed = True
    else:
        # Initialize operation status
        operation = "No Operation"
        status = "Stable"
        operation_performed = False
        print(f"[{timestamp}] pH is stable ({ph}), ensuring pumps are OFF.")

    # Logic for controlling water pumps
    if water_level == "Low":
        operation = "Water level low, adding water"
        status = "Ongoing"
        if not pump_in_active:  # Only turn on if not already active
            print(f"[{timestamp}] Water level is LOW. Turning ON pump to ADD water.")
            GPIO.output(WATER_PUMP_PIN_1, GPIO.HIGH)  # Turn ON water-adding pump
            pump_in_active = True
        operation_performed = True
    elif water_level == "High":
        operation = "Water level high, removing water"
        status = "Ongoing"
        if not pump_out_active:  # Only turn on if not already active
            print(f"[{timestamp}] Water level is HIGH. Turning ON pump to REMOVE water.")
            GPIO.output(WATER_PUMP_PIN_2, GPIO.HIGH)  # Turn ON water-removal pump
            pump_out_active = True
        operation_performed = True
    else:
        print(f"[{timestamp}] Water level is OK. Ensuring pumps are OFF.")
        if pump_in_active:
            GPIO.output(WATER_PUMP_PIN_1, GPIO.LOW)  # Turn OFF water-adding pump
            print(f"[{timestamp}] Turning OFF pump for adding water.")
            pump_in_active = False
        if pump_out_active:
            GPIO.output(WATER_PUMP_PIN_2, GPIO.LOW)  # Turn OFF water-removal pump
            print(f"[{timestamp}] Turning OFF pump for removing water.")
            pump_out_active = False

     # If no action was performed, set operation and status to default
    if not operation_performed:
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

    if current_pH <= 5:
        status = "Acidic"
    elif 6 <= current_pH <= 8:
        if current_pH == 7.0:
            status = "Neutral (Ideal for Freshwater)"
        elif current_pH == 8.2:
            status = "Neutral (Ideal for Saltwater)"
        else:
            status = "Neutral"
    else:  # 9-14
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
