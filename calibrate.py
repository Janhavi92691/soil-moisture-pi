import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import time

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
channel = AnalogIn(ads, 0)

print("Reading sensor every second. Press Ctrl+C to stop.")
print("Note the value when DRY and when WET.\n")

while True:
    print("Raw value:", channel.value)
    time.sleep(1)