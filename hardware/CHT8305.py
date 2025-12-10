import machine
from utime import sleep_ms

class I2C_CHT8305:
    CHT8305_Address = 0x40
    I2C_Delay_time = 100 

    # Registers
    REG_TEMPERATURE = 0x00
    REG_HUMIDITY = 0x01
    REG_CONFIG = 0x02
    REG_ALERT_SETUP = 0x03
    REG_MANUFACTURE_ID = 0xFE
    REG_VERSION_ID = 0xFF

    BIT_T_RES = 2
    BIT_H_RES = 0
    BIT_BATTERY_OK = 3
    BIT_ACQ_MODE = 4
    BIT_HEATER = 5
    BIT_RESET = 7
    T_RES_14 = 0
    T_RES_11 = 1
    H_RES_14 = 0
    H_RES_11 = 1
    H_RES_8 = 2

    wLength = 0

    def __init__(self, ID, SCL, SDA):
        self.i2c = machine.I2C(id=ID, scl=machine.Pin(SCL), sda=machine.Pin(SDA), freq=400000)

    def get_CHT8305_CONFIG(self):
        ReadBuf_CHT8305_Config_Reg = bytes(self.wLength)
        com_CHT8305_Config_Reg = bytearray(2)
        com_CHT8305_Config_Reg[0] = 0x10
        com_CHT8305_Config_Reg[1] = 0x00
        sleep_ms(self.I2C_Delay_time)
        ReadBuf_CHT8305_Config_Reg = self.i2c.readfrom(self.CHT8305_Address, 2)
        print(
            "ReadBuf_CHT8305_Config_Reg Status: ",
            bin(ReadBuf_CHT8305_Config_Reg[0]),
            bin(ReadBuf_CHT8305_Config_Reg[1]),
        )

    def set_CHT8305_CONFIG_DEFAULT(self):
        ReadBuf_CHT8305_Config_Reg = bytes(self.wLength)
        com_CHT8305_Config_Reg = bytearray(2)
        com_CHT8305_Config_Reg[0] = 0x10
        com_CHT8305_Config_Reg[1] = 0x00
        self.i2c.writeto_mem(self.CHT8305_Address, self.REG_CONFIG, com_CHT8305_Config_Reg)
        sleep_ms(self.I2C_Delay_time)
        ReadBuf_CHT8305_Config_Reg = self.i2c.readfrom(self.CHT8305_Address, 2)
        print(
            "ReadBuf_CHT8305_Config_Reg Default: ",
            bin(ReadBuf_CHT8305_Config_Reg[0]),
            bin(ReadBuf_CHT8305_Config_Reg[1]),
        )

    def set_CHT8305_CONFIG_HEATER_ON(self):
        ReadBuf_CHT8305_Config_Reg = bytes(self.wLength)
        com_CHT8305_Config_Reg = bytearray(2)
        com_CHT8305_Config_Reg[0] = 0x30
        com_CHT8305_Config_Reg[1] = 0x00
        self.i2c.writeto_mem(self.CHT8305_Address, self.REG_CONFIG, com_CHT8305_Config_Reg)
        sleep_ms(self.I2C_Delay_time)
        ReadBuf_CHT8305_Config_Reg = self.i2c.readfrom(self.CHT8305_Address, 2)
        print(
            "ReadBuf_CHT8305_Config_Reg HEATER ON: ",
            bin(ReadBuf_CHT8305_Config_Reg[0]),
            bin(ReadBuf_CHT8305_Config_Reg[1]),
        )
    
    def send_CHT8305_SOFT_RESET(self):
        ReadBuf_CHT8305_Config_Reg = bytes(self.wLength)
        com_CHT8305_Config_Reg = bytearray(2)
        com_CHT8305_Config_Reg[0] = 0x80
        com_CHT8305_Config_Reg[1] = 0x00
        self.i2c.writeto_mem(self.CHT8305_Address, self.REG_CONFIG, com_CHT8305_Config_Reg)
        sleep_ms(self.I2C_Delay_time)
        ReadBuf_CHT8305_Config_Reg = self.i2c.readfrom(self.CHT8305_Address, 2)
        print(
            "SOFT RESET Sent to CHT8305: ",
            bin(ReadBuf_CHT8305_Config_Reg[0]),
            bin(ReadBuf_CHT8305_Config_Reg[1]),
        )

    def get_CHT8305_MANUFACTURE_ID(self):
        ReadBuf_CHT8305_Manufacture_ID_Reg = bytes(self.wLength)
        com_CHT8305_Manufacture_ID_Reg = bytearray(2)
        self.i2c.writeto_mem(self.CHT8305_Address,self.REG_MANUFACTURE_ID,com_CHT8305_Manufacture_ID_Reg,)
        sleep_ms(self.I2C_Delay_time)
        ReadBuf_CHT8305_Manufacture_ID_Reg = self.i2c.readfrom(self.CHT8305_Address, 2)
        print(
            "ReadBuf_CHT8305_Manufacture_ID_Reg: ",
            hex(ReadBuf_CHT8305_Manufacture_ID_Reg[0]),
            hex(ReadBuf_CHT8305_Manufacture_ID_Reg[1]),
        )

    def get_CHT8305_VERSION_ID(self):
        ReadBuf_CHT8305_Version_ID_Reg = bytes(self.wLength)
        com_CHT8305_Version_ID_Reg = bytearray(2)
        self.i2c.writeto_mem(
            self.CHT8305_Address, self.REG_VERSION_ID, com_CHT8305_Version_ID_Reg
        )
        sleep_ms(self.I2C_Delay_time)
        ReadBuf_CHT8305_Version_ID_Reg = self.i2c.readfrom(self.CHT8305_Address, 2)
        print(
            "ReadBuf_CHT8305_Version_ID_Reg: ",
            hex(ReadBuf_CHT8305_Version_ID_Reg[0]),
            hex(ReadBuf_CHT8305_Version_ID_Reg[1]),
        )

    def get_CHT8305_TEMPERATURE_HUMIDITY(self):
        Temperature = None
        Humidity = None
        try:
            self.i2c.writeto(self.CHT8305_Address, bytes([self.REG_TEMPERATURE]))
            sleep_ms(self.I2C_Delay_time)
            data = self.i2c.readfrom(self.CHT8305_Address, 4)
            temp_raw = (data[0] << 8) | data[1]
            Temperature = (temp_raw * 165 / 65535) - 40
            hum_raw = (data[2] << 8) | data[3]
            Humidity = (hum_raw / 65535) * 100
            # print(f"Temperature: {Temperature:.2f} °C, Humidity: {Humidity:.2f} %")
        except Exception as e:
            print("Error in get_CHT8305_TEMPERATURE_HUMIDITY function", " : {}".format(e))
            pass
        return Temperature, Humidity

    def req_CHT8305_TEMPERATURE_HUMIDITY(self):
        try:
            self.i2c.writeto(self.CHT8305_Address, bytes([self.REG_TEMPERATURE]))
            sleep_ms(self.I2C_Delay_time)
        except Exception as e:
            print("Error in req_CHT8305_TEMPERATURE_HUMIDITY function", " : {}".format(e))
            pass

    def read_CHT8305_TEMPERATURE_HUMIDITY(self):
        try:
            data = self.i2c.readfrom(self.CHT8305_Address, 4)
            temp_raw = (data[0] << 8) | data[1]
            Temperature = (temp_raw * 165 / 65535) - 40
            hum_raw = (data[2] << 8) | data[3]
            Humidity = (hum_raw / 65535) * 100
            # print(f"Temperature: {Temperature:.2f} °C, Humidity: {Humidity:.2f} %")
        except Exception as e:
            print("Error in read_CHT8305_TEMPERATURE_HUMIDITY function", " : {}".format(e))
            pass 
        return Temperature, Humidity