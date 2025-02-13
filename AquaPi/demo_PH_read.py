import sys
import time

sys.path.append('../')

from DFRobot_PH      import DFRobot_PH
from sensor_manager import get_ads1115

ads1115 = ADS1115()

ph      = DFRobot_PH()

ph.begin()
while True :
	#Read your temperature sensor to execute temperature compensation
	temperature = 25
	#Get the Digital Value of Analog of selected channel
	adc0 = ads1115.readVoltage(0)
	#Convert voltage to PH with temperature compensation
	PH = ph.read_PH(adc0['r'],temperature)
	print ("Temperature:%.1f ^C PH:%.2f" %(temperature,PH))
	time.sleep(1.0)
