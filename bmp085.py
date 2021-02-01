# Read/Write a bmp085 barometric sensor on i2c

import time
import struct

# raspberry pi imports
import pigpio

# i2c address
BARO = 0x77

AC1 = 0
AC2 = 1
AC3 = 2
AC4 = 3
AC5 = 4
AC6 = 5
B1 = 6
B2 = 7
MB = 8
MC = 9
MD = 10
B5 = 11

class BMP085Device:

    """ BMP085 barometric pressure sensor device. """

    def __init__(self, my_pi, busno, xclr_pin, eoc_pin):
        self._gpiod = my_pi
        # XCLR is active low to reset the device
        self._xclr_pin = xclr_pin
        self._gpiod.set_mode(self._xclr_pin, pigpio.OUTPUT)
        self._gpiod.write(self._xclr_pin, 1)
        self.reset()
        # EOC is active high, if calculation is done
        self._eoc_pin = eoc_pin
        self._gpiod.set_mode(self._eoc_pin, pigpio.INPUT)

        self._i2c_handle = self._gpiod.i2c_open(busno, BARO, 0)
        self._oversampling = 2

        # read the chip id
        chip_id = self._gpiod.i2c_read_byte_data(self._i2c_handle, 0xD0)
        print("BMP085 Barometric Sensor initialized on i2c-{} at address 0x{:02x}".format(
            busno, BARO))
        print("XCLR pin={} EOC pin={}".format(self._xclr_pin, self._eoc_pin))
        print("Oversampling:", self._oversampling)
        print("ChipID:0x{:02x}".format(chip_id))
        # read the version
        version_id = self._gpiod.i2c_read_byte_data(self._i2c_handle, 0xD1)
        ml_version = version_id & 0xF
        al_version = (version_id & 0xF0) >> 4
        print("Version:{}.{}".format(ml_version, al_version))
        # read calibration parameter information
        data = bytes(self._gpiod.i2c_read_i2c_block_data(self._i2c_handle, 0xaa, 22))
        self._calib = list(struct.unpack('>hhhHHHhhhhh', data))
        self._calib.append(0)
        print('Calibration parameters')
        print('\tac1:{} ac2:{} ac3:{}'.format(self._calib[AC1], self._calib[AC2], self._calib[AC3]))
        print('\tac4:{} ac5:{} ac6:{}'.format(self._calib[AC4], self._calib[AC5], self._calib[AC6]))
        print('\tb1:{} b2:{}'.format(self._calib[B1], self._calib[B2]))
        print('\tmb:{} mc:{} md:{}'.format(self._calib[MB], self._calib[MC], self._calib[MD]))
        self._raw_values = []
        
    def close(self):
        """ release the pigpio resources """
        self._gpiod.i2c_close(self._i2c_handle)

    def reset(self):
        """ reset the bmp085 device """
        self._gpiod.write(self._xclr_pin, 0)
        time.sleep(0.5)
        self._gpiod.write(self._xclr_pin, 1)
        time.sleep(1)

    def read_sensor(self):
        self.read_temp()
        #print("raw temp:{}".format(self._raw_values[0]))
        self.read_press()
        #print("raw press:{}".format(self._raw_values[1]))

    def create_nmea0183_sentence(self, talker_id):
        self.calc_temp()
        pressure = self.calc_press()
        nmea_sentence = '{}MDA,,I,{:5.4f},B,,C,,C,,,,C,,T,,M,,N,,M'.format(
            talker_id, pressure/100000.0)
        # compute checksum
        checksum_value = 0
        for nmea_ch in nmea_sentence:
            checksum_value ^= ord(nmea_ch)
        nmea_sentence = '${}*{:02x}\r\n'.format(nmea_sentence, checksum_value)
        #print(nmea_sentence[:-2])
        return nmea_sentence

    def read_press(self):
        self._gpiod.i2c_write_byte(self._i2c_handle, 0xF4, 0x34 + (self._oversampling<<6))
        if self._oversampling == 0:
            time.sleep(0.002)
        elif self._oversampling == 1:
            time.sleep(0.01)
        elif self._oversampling == 2:
            time.sleep(0.018)
        else:
            time.sleep(0.026)
        sample = self._gpiod.i2c_read_i2c_block_data(self._i2c_handle, 0xF6, 3)
        #print('sample {:x}{:x}{:x}'.format(sample[0],sample[1],sample[2]))
        self._raw_values[1] = ((sample[0] << 16) + (sample[1] << 8) + sample[2]) \
            >> (8 - self._oversampling)

    def read_temp(self):
        self._gpiod.i2c_write_byte(self._i2c_handle, 0xF4, 0x2E)
        time.sleep(0.045)
        sample = bytes(self._gpiod.i2c_read_i2c_block_data(self._i2c_handle, 0xF6, 2))
        #print('sample {:x}{:x}'.format(sample[0],sample[1]))
        self._raw_values[0] = struct.unpack('>h', sample)[0]

    def calc_temp(self):
        # pylint: disable=C0103
        x1 = ((self._raw_values[0] - self._calib[AC6]) * self._calib[AC5]) >> 15
        #print('x1',x1)
        x2 = int((self._calib[MC] << 11) / (x1 + self._calib[MD]))
        #print('x2',x2)
        self._calib[B5] = x1 + x2
        #print('b5',self._calib[B5])
        temp = float((self._calib[B5] + 8) >> 4)
        #print('temp',temp)
        return temp

    def calc_press(self):
        # pylint: disable=C0103
        b6 = self._calib[B5] - 4000
        #print('b6',b6)
        x1 = (self._calib[B2] * ((b6 * b6) >> 12)) >> 11
        #print('x1',x1)
        x2 = (self._calib[AC2] * b6) >> 11
        #print('x2',x2)
        x3 = x1 + x2
        #print('x3',x3)
        b3 = ((self._calib[AC1] * 4 + x3) << self._oversampling) + 2 >> 2
        #print('b3',b3)
        x1 = (self._calib[AC3] * b6) >> 13
        #print('x1',x1)
        x2 = (self._calib[B1] * ((b6 * b6) >> 12)) >> 16
        #print('x2',x2)
        x3 = ((x1 + x2) + 2) >> 2
        #print('x3',x3)
        b4 = (self._calib[AC4] * (x3 + 32768)) >> 15
        #print('b4',b4)
        b7 = (self._raw_values[1] - b3) * (50000 >> self._oversampling)
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
        """ Method to calculate temperature and pressure using fake raw values.
        This is per the datasheet to test that the calculations are correct """
        self._oversampling = 0
        self._calib[AC1] = 408
        self._calib[AC2] = -72
        self._calib[AC3] = -14383
        self._calib[AC4] = 32741
        self._calib[AC5] = 32757
        self._calib[AC6] = 23153
        self._calib[B1] = 6190
        self._calib[B2] = 4
        self._calib[MB] = -32768
        self._calib[MC] = -8711
        self._calib[MD] = 2868
        # put in the fake raw values
        self._raw_values = [27898, 23843]
        # sb 150
        print('T', self.calc_temp())
        # sb 69964
        print('P', self.calc_press())
