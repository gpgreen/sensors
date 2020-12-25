#//////////////////////////////////////
#	lm35.py
# 	Reads the analog value of the temperature sensor.
#   Uses the hat power monitor
#//////////////////////////////////////
import spidev
import time

class LM35(object):

    def __init__(self, channel, bus, device):
        if not 0 <= channel < 6:
            raise ValueError('channel must be in range: 0-5')
        # setup CS
        if device == 0:
            pin = 8
        else:
            pin = 7
        self._spi = spidev.SpiDev()
        self._spi_bus = bus
        self._spi_dev = device
        self._channel = channel
        self._raw = 0
        self._temp = 0
        print("LM35 Temperature sensor initialized on channel {}".format(self._channel))

    def open(self):
        self._spi.open(self._spi_bus, self._spi_dev)
        # specify which channel to get
        self._spi_write([0x1, 0x3, 0x00])
        time.sleep(0.001)
        print("channels:", self._spi_write([0x2, 0x0, 0x0])[0])

    def close(self):
        self._spi.close()

    def read_sensor(self):
        res = self._spi_write([0x2,0,0])
        time.sleep(0.00005)
        res = self._spi_write(self._send())
        self._raw = res[0] + (res[1] << 8)
        self._temp = self._raw * 1.8 / 1024.0 * 100
        #print("raw:", res[0], res[1])

    def _send(self):
        return [self._channel + 0x10, 0, 0]

    def temperature(self):
        return self._temp

    def create_nmea0183_sentence(self):
        nmea_sentence = 'WIMTA,{:.1f},C'.format(self._temp)
        # compute checksum
        checksum_value = 0
        for c in nmea_sentence:
            checksum_value ^= ord(c)
        nmea_sentence = '${}*{:02x}\r\n'.format(nmea_sentence, checksum_value)
        #print(nmea_sentence[:-2])
        return nmea_sentence

    def _spi_write(self, data):
        self._spi.xfer(data[:1], 100000)
        time.sleep(0.00015)
        return self._spi.xfer(data[1:], 100000)
