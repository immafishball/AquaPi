import sys
import time

sys.path.append('../')

from sensor_manager import get_ads1115

ads1115 = ADS1115()
while True :
    #Get the Digital Value of Analog of selected channel
    adc0 = ads1115.readVoltage(0)
    time.sleep(0.2)
    adc1 = ads1115.readVoltage(1)
    time.sleep(0.2)
    adc2 = ads1115.readVoltage(2)
    time.sleep(0.2)
    adc3 = ads1115.readVoltage(3)
    print ("A0:%dmV A1:%dmV A2:%dmV A3:%dmV"%(adc0['r'],adc1['r'],adc2['r'],adc3['r']))
