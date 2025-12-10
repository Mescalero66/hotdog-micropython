import machine, time, ntptime
import esp32, network, onewire
import ds18x20 as OW_SENSOR
from machine import Pin, I2C, RTC
from hardware.CHT8305 import I2C_CHT8305 as I2C_SENSOR
import hardware.WLAN_KEY as wlan_key

### CONSTANTS ###
WIFI_SSID = wlan_key.ssid
WIFI_PW = wlan_key.password
SDA_PIN = 6
SCL_PIN = 7
ONEWIRE_PIN = 3
UTC_OFFSET = 10 * 60 * 60

### OBJ SETUP ###
wlan = network.WLAN(network.STA_IF)
real_time_clock = RTC()  
ow_sensor_bus = OW_SENSOR.DS18X20(onewire.OneWire(Pin(ONEWIRE_PIN)))
ow_sensor_array = ow_sensor_bus.scan()
i2c_sensor = I2C_SENSOR(ID=0, SCL=Pin(SCL_PIN), SDA=Pin(SDA_PIN))

### HOUSEKEEPING ###
print(f"CPU Temp: {esp32.mcu_temperature()}°C")
# WIFI ##
wlan.active(False)
wlan.active(True)
if not wlan.isconnected():
    print('connecting to network...')
    wlan.connect(WIFI_SSID, WIFI_PW)
    while not wlan.isconnected():
        time.sleep(2)
        print("connection status:", wlan.status())
    print('network config:', wlan.ipconfig('addr4'))
# CLOCK ##
if time.localtime()[0] < 2024:
    ntptime.settime()
    local_time = time.localtime(time.time() + UTC_OFFSET)
    real_time_clock.datetime(local_time)
print(time.localtime())

i = 0
while (i < 30):
    ow_sensor_bus.convert_temp()            
    time.sleep_ms(1000)
    for UID in ow_sensor_array:
        temp_value = ow_sensor_bus.read_temp(UID)
    time.sleep(1)
    Temp, Humi = i2c_sensor.get_CHT8305_TEMPERATURE_HUMIDITY()
    print(f"OW: {temp_value:.1f} I2C: {Temp:.1f} Humi: {Humi:.1f}")
    i += 1
