import machine, time, ntptime, os
import esp32, network, onewire
import ds18x20 as OW_SENSOR
from machine import Pin, I2C, RTC
from hardware.CHT8305 import I2C_CHT8305 as I2C_SENSOR
import hardware.WLAN_KEY as wlan_key

### WIFI ###
WIFI_SSID = wlan_key.ssid
WIFI_PW = wlan_key.password
### CONSTANTS ###
BLUE_LED = 8
SDA_PIN = 6
SCL_PIN = 7
ONEWIRE_PIN = 3
LOAD_RELAY_PIN = 5
### PARAMETERS ###
UTC_OFFSET = 60 * 60 * 10
MAX_LOG_FILES = 14
SLEEP_MINUTES = 1
AVERAGE_READS = 4
OFF_READ_INTERVAL = 15
ON_READ_INTERVAL = 30
### SETPOINTS ###
OUTSIDE_TEMP_LOW = 12
OUTSIDE_TEMP_HIGH = 16
INSIDE_TEMP_LOW = 12
INSIDE_TEMP_HIGH = 21
### VARIABLES ###
_loop_state = 0
_current_log_filename = None
_sleep_duration = 0
_actual_inside_temp = 0
_actual_outside_temp = 0
_actual_outside_humi = 0
_actual_heater_status = 0

### OBJECT SETUP ###
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

def connect_wifi():
    wlan.active(True)
    if not wlan.isconnected():
        #wlan.connect(WIFI_SSID, WIFI_PW)
        pass

def disconnect_wifi():
    wlan.active(False)

def create_daily_log_file():
    global _current_log_filename
    lt = time.localtime()
    filename = "logs/hotdog_{:04d}{:02d}{:02d}.csv".format(lt[0], lt[1], lt[2])
    timestamp = "{:04d}{:02d}{:02d}-{:02d}{:02d}{:02d}".format(lt[0], lt[1], lt[2], lt[3], lt[4], lt[5])
    if "logs" not in os.listdir():
        os.mkdir("logs")
    if _current_log_filename != filename:
        cleanup_old_logs()
        _current_log_filename = filename
        try:
            with open(_current_log_filename, "r"):
                pass
        except OSError:
            with open(_current_log_filename, "a") as text_file:
                text_file.write("Timestamp,InsideTemp,OutsideTemp,OutsideHumi,HeaterOn,SleepDuration,CPUTemp\n")
    return _current_log_filename, timestamp

def cleanup_old_logs():
    if "logs" not in os.listdir():
        return
    files = [f for f in os.listdir("logs") if f.startswith("hotdog_") and f.endswith(".csv")]
    files.sort()
    while len(files) > MAX_LOG_FILES:
        oldest = files.pop(0)
        os.remove(f"logs/{oldest}")
        print(f"Deleted old log: {oldest}")

def log():
    filename, timestamp = create_daily_log_file()
    logline = (f"{_actual_inside_temp:.1f},{_actual_outside_temp:.1f},{_actual_outside_humi:.1f},{_actual_heater_status},{_sleep_duration},{esp32.mcu_temperature():.1f}")
    with open(filename, "a") as text_file:
        text_file.write(f"{timestamp},{(str(logline))} \n")
    print(f"{timestamp},{(str(logline))} ")

def close_relay():
    global _actual_heater_status
    load_relay.on()
    _actual_heater_status = 1
    time.sleep_ms(100)
    log()

def open_relay():
    global _actual_heater_status
    load_relay.off()
    _actual_heater_status = 0
    time.sleep_ms(100)
    log()

def go_to_sleep():
    global _sleep_duration
    sleeptime = time.time()
    disconnect_wifi()
    led.off()
    machine.lightsleep(int(SLEEP_MINUTES * 1000 * 60))
    awaketime = time.time()
    _sleep_duration = int(awaketime - sleeptime)
    log()
    _sleep_duration = 0
    connect_wifi()    

def off_loop():
    global _loop_state, _sleep_duration, _actual_inside_temp, _actual_outside_temp, _actual_outside_humi
    open_relay()
    outside_ave = []
    inside_ave = []
    while True:
        ow_sensor_bus.convert_temp()
        time.sleep(1)
        _actual_outside_temp, _actual_outside_humi = i2c_sensor.get_CHT8305_TEMPERATURE_HUMIDITY()
        for UID in ow_sensor_array:
            _actual_inside_temp = ow_sensor_bus.read_temp(UID)
        outside_ave.append(_actual_outside_temp)
        inside_ave.append(_actual_inside_temp)
        log()
        if (len(outside_ave)) >= AVERAGE_READS or (len(inside_ave)) >= AVERAGE_READS:
            outside_mean = int((sum(outside_ave)) / (len(outside_ave)))
            inside_mean = int((sum(inside_ave)) / (len(inside_ave)))
            outside_ave = []
            inside_ave = []
            if (outside_mean <= OUTSIDE_TEMP_LOW) or (inside_mean <= INSIDE_TEMP_LOW):
                _loop_state = 1
            else:
                go_to_sleep()
        yield OFF_READ_INTERVAL

def on_loop():
    global _loop_state, _actual_inside_temp, _actual_outside_temp, _actual_outside_humi
    close_relay()
    outside_ave = []
    inside_ave = []
    while True:
        ow_sensor_bus.convert_temp()
        time.sleep(1)
        _actual_outside_temp, _actual_outside_humi = i2c_sensor.get_CHT8305_TEMPERATURE_HUMIDITY()
        for UID in ow_sensor_array:
            _actual_inside_temp = ow_sensor_bus.read_temp(UID)
        outside_ave.append(_actual_outside_temp)
        inside_ave.append(_actual_inside_temp)
        log()
        if (len(outside_ave)) >= AVERAGE_READS or (len(inside_ave)) >= AVERAGE_READS:
            outside_mean = int((sum(outside_ave)) / (len(outside_ave)))
            inside_mean = int((sum(inside_ave)) / (len(inside_ave)))
            outside_ave = []
            inside_ave = []
            if (outside_mean >= OUTSIDE_TEMP_HIGH) or (inside_mean >= INSIDE_TEMP_HIGH):
                _loop_state = 0
        yield ON_READ_INTERVAL

### HOUSEKEEPING ###
## WIFI ##
wlan.active(False)
wlan.active(True)
wlan.config(reconnects=3)
if not wlan.isconnected():
    print('connecting to network...')
    wlan.connect(WIFI_SSID, WIFI_PW)
    print("connection status:", wlan.status())
    print('network config:', wlan.ipconfig('addr4'))
## CLOCK ##
if time.localtime()[0] < 2024:
    ntptime.settime()
    local_time = time.localtime(time.time() + UTC_OFFSET)
    real_time_clock.datetime(local_time)

state = off_loop()
current_loop = 0
### MAIN LOOP ###
while True:
    try:
        interval = next(state)
        # time.sleep(interval)
        for i in range(int(interval)):
            blink_led()
            time.sleep(1)
        if _loop_state != current_loop:
            current_loop = _loop_state
            if current_loop == 0:
                state = off_loop()
            else:
                state = on_loop()
    except KeyboardInterrupt:
        print("User stopped process.")
        break
    except Exception as e:
        print("Exception during execution of main loop: {}".format(e))
        break