import sys
import os
import time
from sensor_manager import get_board

if __name__ == "__main__":

  board = get_board()

  board.set_pwm_enable()                # Pwm channel need external power
  # board.set_pwm_disable()
  board.set_pwm_frequency(1000)         # Set frequency to 1000HZ, Attention: PWM voltage depends on independent power supply
  
  board.set_pwm_duty(0, 90)
  time.sleep(10) #2ml
  
  board.set_pwm_duty(0, 0)
  board.set_pwm_disable()