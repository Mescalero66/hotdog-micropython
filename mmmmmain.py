import machine, time, ntptime, os
import esp32, network, onewire
import ds18x20 as OW_SENSOR
from machine import Pin, I2C, RTC
from hardware.CHT8305 import I2C_CHT8305 as I2C_SENSOR
# import hardware.WLAN_KEY as wlan_key

### CONSTANTS ###
# WIFI_SSID = wlan_key.ssid
# WIFI_PW = wlan_key.password
BLUE_LED = 8
SDA_PIN = 6
SCL_PIN = 7
ONEWIRE_PIN = 3
LOAD_RELAY_PIN = 5
UTC_OFFSET = 10 * 60 * 60
SLEEP_MINUTES = 0.5
LATEST_LOG_DATE = None
_current_log_filename = str(None)

### OBJ SETUP ###
wlan = network.WLAN(network.STA_IF)
led = Pin(BLUE_LED, Pin.OUT)
load_relay = Pin(LOAD_RELAY_PIN, Pin.OUT)
load_relay.off()
real_time_clock = RTC()  
ow_sensor_bus = OW_SENSOR.DS18X20(onewire.OneWire(Pin(ONEWIRE_PIN)))
ow_sensor_array = ow_sensor_bus.scan()
i2c_sensor = I2C_SENSOR(ID=0, SCL=Pin(SCL_PIN), SDA=Pin(SDA_PIN))

### FUNCTIONS ###
def blink_led():
    led.off()
    time.sleep_ms(100)
    led.on()

def create_daily_log_file():
    global _current_log_filename
    lt = time.localtime()
    filename = "logs/hotdog_{:04d}{:02d}{:02d}.csv".format(lt[0], lt[1], lt[2])
    if "logs" not in os.listdir():
        os.mkdir("logs")
    if _current_log_filename != filename:
        _current_log_filename = filename
        try:
            with open(_current_log_filename, "r"):
                pass
        except OSError:
            with open(_current_log_filename, "a") as text_file:
                text_file.write("Timestamp,InsideTemp,OutsideTemp,OutsideHumi,HeaterOn,SleepTime,CPUTemp\n")
    return _current_log_filename

def log(logline):
    lt = time.localtime()
    filename = create_daily_log_file()
    timestamp = "{:04d}{:02d}{:02d}-{:02d}{:02d}{:02d}".format(lt[0], lt[1], lt[2], lt[3], lt[4], lt[5])
    with open(filename, "a") as text_file:
        text_file.write(f"{timestamp},{(str(logline))} \n")
    

### HOUSEKEEPING ###
print(f"CPU Temp: {esp32.mcu_temperature()}°C")
# ## WIFI ##
# wlan.active(False)
# wlan.active(True)
# if not wlan.isconnected():
#     print('connecting to network...')
#     wlan.connect(WIFI_SSID, WIFI_PW)
#     while not wlan.isconnected():
#         time.sleep(2)
#         print("connection status:", wlan.status())
#     print('network config:', wlan.ipconfig('addr4'))
# ## CLOCK ##
# if time.localtime()[0] < 2024:
#     ntptime.settime()
#     local_time = time.localtime(time.time() + UTC_OFFSET)
#     real_time_clock.datetime(local_time)
# print(time.localtime())


i = 0
j = 0
ow_sensor_bus.convert_temp()
time.sleep_ms(1000)
while (i < 10):          
    while (j < 4):
        blink_led()
        for UID in ow_sensor_array:
            temp_value = ow_sensor_bus.read_temp(UID)
        Temp, Humi = i2c_sensor.get_CHT8305_TEMPERATURE_HUMIDITY()
        print(f"Time: {time.localtime()} - OW: {temp_value:.1f}°C - I2C: {Temp:.1f}°C - Humi: {Humi:.1f}%")
        log(f"OW: {temp_value:.1f}°C - I2C: {Temp:.1f}°C - Humi: {Humi:.1f}%")
        ow_sensor_bus.convert_temp()
        time.sleep(1)
        j += 1
    j = 0
    load_relay.off()
    log(f"SLEEP [CPU: {esp32.mcu_temperature()}°C]")
    # machine.lightsleep(int(SLEEP_MINUTES * 1000 * 60))
    log(f"WAKE! [CPU: {esp32.mcu_temperature()}°C]")
    load_relay.on()
    i += 1
