# Read/Write a bmp085 barometric sensor on i2c

import smbus
import time
import struct
import Adafruit_BBIO.GPIO as GPIO

# i2c address
baro = 0x77

# pin for XCLR
xclr_pin = "P9_12"

class BMP085Device:

    def __init__(self, busno, xclr_pin):
        self._xclr = xclr_pin

        GPIO.setup(self._xclr, GPIO.OUT)
        GPIO.output(self._xclr, GPIO.HIGH)

        self.reset()
        
        self._bus = smbus.SMBus(busno)
    
        self._oversampling = 2
        
        self._rt = 0
        self._rp = 0
        self._b5 = 0
        
        # read the chip id
        self._chip_id = self._bus.read_byte_data(baro, 0xD0)
        print("BMP085 Barometric Sensor found on i2c-{} at address {}".format(busno,baro))
        print("XCLR pin={}".format(self._xclr))
        print("oversampling:",self._oversampling)
        print("ChipID:0x{:x}".format(self._chip_id))
        # read the version
        version_id = self._bus.read_byte_data(baro, 0xD1)
        self._ml_version = version_id & 0xF
        self._al_version = (version_id & 0xF0) >> 4
        print("Version:{}.{}".format(self._ml_version,self._al_version))
        # read calibration parameter information
        data = bytes(self._bus.read_i2c_block_data(baro, 0xaa, 22))
        #print(data,len(data))
        self._ac1, self._ac2, self._ac3, self._ac4, self._ac5, self._ac6, \
          self._b1, self._b2, self._mb, self._mc, self._md = struct.unpack('>hhhHHHhhhhh', data)
        print('calibration parameters')
        print('\tac1:{} ac2:{} ac3:{}'.format(self._ac1,self._ac2,self._ac3))
        print('\tac4:{} ac5:{} ac6:{}'.format(self._ac4,self._ac5,self._ac6))
        print('\tb1:{} b2:{}'.format(self._b1,self._b2))
        print('\tmb:{} mc:{} md:{}'.format(self._mb,self._mc,self._md))

    def reset(self):
        GPIO.output(xclr_pin, GPIO.LOW)
        time.sleep(0.5)
        GPIO.output(xclr_pin, GPIO.HIGH)
        time.sleep(1)

    def read_sensor(self):
        self.read_temp()
        self.read_press()

    def create_nmea0183_sentence(self):
        t = self.calc_temp()
        p = self.calc_press()
        nmea_sentence = 'WIMDA,,I,{:5.4f},B,,C,,C,,,,C,,T,,M,,N,,M'.format(p/100000.0)
        # compute checksum
        checksum_value = 0
        for c in nmea_sentence:
            checksum_value ^= ord(c)
        nmea_sentence = '${}*{:02x}\r\n'.format(nmea_sentence, checksum_value)
        #print(nmea_sentence[:-2])
        return nmea_sentence
    
    def read_press(self):
        self._bus.write_byte_data(baro, 0xF4, 0x34 + (self._oversampling<<6))
        if self._oversampling == 0:
            time.sleep(0.002)
        elif self._oversampling == 1:
            time.sleep(0.01)
        elif self._oversampling == 2:
            time.sleep(0.018)
        else:
            time.sleep(0.026)
        sample = self._bus.read_i2c_block_data(baro, 0xF6, 3)
        #print('sample {:x}{:x}{:x}'.format(sample[0],sample[1],sample[2]))
        self._rp = ((sample[0] << 16) + (sample[1] << 8) + sample[2]) >> (8 - self._oversampling)
        #print("raw press:{}".format(self._rp))
        
    def read_temp(self):
        self._bus.write_byte_data(baro, 0xF4, 0x2E)
        time.sleep(0.045)
        sample = bytes(self._bus.read_i2c_block_data(baro, 0xF6, 2))
        #print('sample {:x}{:x}'.format(sample[0],sample[1]))
        self._rt = struct.unpack('>h', sample)[0]
        #print("raw temp:{}".format(self._rt))

    def calc_temp(self):
        x1 = ((self._rt - self._ac6) * self._ac5) >> 15
        #print('x1',x1)
        x2 = int((self._mc << 11) / (x1 + self._md))
        #print('x2',x2)
        self._b5 = x1 + x2
        #print('b5',self._b5)
        temp = float((self._b5 + 8) >> 4)
        #print('temp',temp)
        return temp
        
    def calc_press(self):
        b6 = self._b5 - 4000
        #print('b6',b6)
        x1 = (self._b2 * ((b6 * b6) >> 12)) >> 11
        #print('x1',x1)
        x2 = (self._ac2 * b6) >> 11
        #print('x2',x2)
        x3 = x1 + x2
        #print('x3',x3)
        b3 = ((self._ac1 * 4 + x3) << self._oversampling) + 2 >> 2
        #print('b3',b3)
        x1 = (self._ac3 * b6) >> 13
        #print('x1',x1)
        x2 = (self._b1 * ((b6 * b6) >> 12)) >> 16
        #print('x2',x2)
        x3 = ((x1 + x2) + 2) >> 2
        #print('x3',x3)
        b4 = (self._ac4 * (x3 + 32768)) >> 15
        #print('b4',b4)
        b7 = (self._rp - b3) * (50000 >> self._oversampling)
        #print('b7',b7)
        if b7 < 0x80000000:
            p = int((b7 << 1) / b4)
        else:
            p = (b7 / b4) << 1
        #print('p',p)
        x1 = p >> 8
        x1 *= x1
        x1 = (x1 * 3038) >> 16
        #print('x1',x1)
        x2 = (p * -7357) >> 16
        #print('x2',x2)
        p += (x1 + x2 + 3791) >> 4
        return p
        
    def do_fake(self):
        self._oversampling = 0
        self._ac1 = 408
        self._ac2 = -72
        self._ac3 = -14383
        self._ac4 = 32741
        self._ac5 = 32757
        self._ac6 = 23153
        self._b1 = 6190
        self._b2 = 4
        self._mb = -32768
        self._mc = -8711
        self._md = 2868
        self._rt = 27898
        self._rp = 23843
        # sb 150
        print('T',self.calc_temp())
        # sb 69964
        print('P',self.calc_press())
