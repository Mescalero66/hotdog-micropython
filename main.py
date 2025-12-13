import machine, time, ntptime, os
import esp32, network, onewire, socket
import ds18x20 as OW_SENSOR
from machine import Pin, I2C, RTC
from bluetooth import BLE
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
UTC_OFFSET = 60 * 60 * 11   # DST
MAX_LOG_FILES = 14
SLEEP_MINUTES = 15
AVERAGE_READS = 4
OFF_READ_INTERVAL = 15
ON_READ_INTERVAL = 15
### SETPOINTS ###
OUTSIDE_TEMP_LOW = 12
OUTSIDE_TEMP_HIGH = 16
INSIDE_TEMP_LOW = 12
INSIDE_TEMP_HIGH = 18
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
wlan.active(True)
ble = BLE()
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

def blink_led_wifi():
    for i in range(10):
        led.off()
        time.sleep_ms(100)
        led.on()
        time.sleep_ms(100)
        i +=1

def current_spike():
    ble.active(True)
    adv_payload = bytes([0x02, 0x01, 0x06])
    interval_us = 20000
    ble.gap_advertise(interval_us, adv_payload, connectable=False)
    time.sleep_ms(50)
    ble.gap_advertise(0, adv_payload, connectable=False)
    ble.active(False)

def connect_wifi(timeout=10):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.disconnect()
    time.sleep(0.2)

    print("Connecting to:", WIFI_SSID)
    wlan.connect(WIFI_SSID, WIFI_PW)

    t0 = time.ticks_ms()
    while True:
        status = wlan.status()
        print("connection status:", status)

        if status in (5, 1010):   # GOT_IP / CONNECTED
            print("Connected:", wlan.ifconfig())
            return True

        if status == 2:  # AUTH FAILED
            print("Authentication failed")
            return False

        if time.ticks_diff(time.ticks_ms(), t0) > timeout * 1000:
            print("Connection timeout")
            return False

        time.sleep(0.2)

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
                text_file.write("Timestamp,InsideTemp,OutsideTemp,OutsideHumi,HeaterOnOff\n")
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
    if filename.startswith("hotdog_2000"):
        return
    logline = (f"{_actual_inside_temp:.1f},{_actual_outside_temp:.1f},{_actual_outside_humi:.1f},{_actual_heater_status}")
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
    # disconnect_wifi()
    led.off()
    machine.lightsleep(int(SLEEP_MINUTES * 1000 * 60))
    awaketime = time.time()
    _sleep_duration = int(awaketime - sleeptime)
    log()
    _sleep_duration = 0
    # connect_wifi()    

def off_loop():
    global _loop_state, _sleep_duration, _actual_inside_temp, _actual_outside_temp, _actual_outside_humi
    open_relay()
    outside_ave = []
    inside_ave = []
    humi_ave = []
    while True:
        ow_sensor_bus.convert_temp()
        time.sleep(1)
        outside_temp, outside_humi = i2c_sensor.get_CHT8305_TEMPERATURE_HUMIDITY()
        for UID in ow_sensor_array:
            inside_temp = ow_sensor_bus.read_temp(UID)
        outside_ave.append(outside_temp)
        inside_ave.append(inside_temp)
        humi_ave.append(outside_humi)
        current_spike()
        if (len(outside_ave)) >= AVERAGE_READS or (len(inside_ave)) >= AVERAGE_READS:
            outside_mean = int((sum(outside_ave)) / (len(outside_ave)))
            inside_mean = int((sum(inside_ave)) / (len(inside_ave)))
            humi_mean = int((sum(humi_ave)) / (len(humi_ave)))
            outside_ave = []
            inside_ave = []
            humi_ave = []
            _actual_inside_temp = inside_mean
            _actual_outside_temp = outside_mean
            _actual_outside_humi = humi_mean
            log()
            if (outside_mean <= OUTSIDE_TEMP_LOW) or (inside_mean <= INSIDE_TEMP_LOW):
                _loop_state = 1
            else:
                # go_to_sleep()
                pass
        yield OFF_READ_INTERVAL

def on_loop():
    global _loop_state, _actual_inside_temp, _actual_outside_temp, _actual_outside_humi
    close_relay()
    outside_ave = []
    inside_ave = []
    while True:
        ow_sensor_bus.convert_temp()
        time.sleep(1)
        outside_temp, outside_humi = i2c_sensor.get_CHT8305_TEMPERATURE_HUMIDITY()
        for UID in ow_sensor_array:
            inside_temp = ow_sensor_bus.read_temp(UID)
        outside_ave.append(outside_temp)
        inside_ave.append(inside_temp)
        humi_ave.append(outside_humi)
        current_spike()
        if (len(outside_ave)) >= AVERAGE_READS or (len(inside_ave)) >= AVERAGE_READS:
            outside_mean = int((sum(outside_ave)) / (len(outside_ave)))
            inside_mean = int((sum(inside_ave)) / (len(inside_ave)))
            humi_mean = int((sum(humi_ave)) / (len(humi_ave)))
            outside_ave = []
            inside_ave = []
            humi_ave = []
            _actual_inside_temp = inside_mean
            _actual_outside_temp = outside_mean
            _actual_outside_humi = humi_mean
            log()
            if (outside_mean >= OUTSIDE_TEMP_HIGH) or (inside_mean >= INSIDE_TEMP_HIGH):
                _loop_state = 0
        yield ON_READ_INTERVAL

## WIFI ##
wlan.active(False)
wlan.active(True)
if not wlan.isconnected():
    wlan.config(txpower=8)
    wlan.PM_NONE
    wlan.config(reconnects=-1)
    print('connecting to network:', WIFI_SSID)
    wlan.connect(WIFI_SSID, WIFI_PW)
    while not wlan.isconnected():
        blink_led_wifi()
        print("WLAN Status:", wlan.status())
    print('network config:', wlan.ipconfig('addr4'))
try:
    print(socket.getaddrinfo("google.com", 80))
    print("DNS OK")
except Exception as e:
    print("DNS failed:", e)
    pass
## CLOCK ##
ntptime.settime()
yy, mm, dd, hr, min, sec, wd, yd = time.localtime(time.time() + UTC_OFFSET)
real_time_clock.datetime((yy, mm, dd, wd, hr, min, sec, 0))

## HOUSEKEEPING ##
print(f"Local: {time.localtime()} RTC: {real_time_clock.datetime()}")
state = off_loop()
current_loop = 0

### MAIN LOOP ###
while True:
    try:
        interval = next(state)
        for i in range(int(interval)):
            blink_led()
            time.sleep_ms(900)
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