#//////////////////////////////////////
#	lm35.py
# 	Reads the analog value of the temperature sensor.
#   Uses the hat power monitor
#//////////////////////////////////////
import time

# raspberry pi imports
import pigpio

class LM35:

    def __init__(self, channel, bus, device):
        if not 0 <= channel < 6:
            raise ValueError('channel must be in range: 0-5')
        self._gpiod = pigpio.pi()
        self._spi_bus = bus
        if bus != 0:
            raise ValueError("SPI bus 1 not implemented yet")
        self._spi_dev = device
        self._channel = channel
        self._spi_handle = None
        self._raw = 0
        self._temp = 0
        print("LM35 Temperature sensor initialized on channel {}".format(self._channel))

    def open(self):
        self._spi_handle = self._gpiod.spi_open(self._spi_dev, 100000, 0)
        time.sleep(0.00002)
        # specify which channel to get
        self._gpiod.spi_write(self._spi_handle, [0x1, 0x1, 0x00])
        print("channels:", self._gpiod.spi_write(self._spi_handle, [0x2, 0x0, 0x0])[0])

    def close(self):
        self._gpiod.spi_stop()

    def read_sensor(self):
        self._gpiod.spi_write(self._spi_handle, [0x2, 0, 0])
        res = self._gpiod.spi_xfer(self._spi_handle, self._send())
        self._raw = res[0] + (res[1] << 8)
        self._temp = self._raw * 1.8 / 1024.0 * 100
        #print("raw:", res[0], res[1])

    def _send(self):
        return [self._channel + 0x10, 0, 0]

    def temperature(self):
        return self._temp

    def create_nmea0183_sentence(self, talker_id):
        nmea_sentence = '{}MTA,{:.1f},C'.format(talker_id, self._temp)
        # compute checksum
        checksum_value = 0
        for nmea_ch in nmea_sentence:
            checksum_value ^= ord(nmea_ch)
        nmea_sentence = '${}*{:02x}\r\n'.format(nmea_sentence, checksum_value)
        #print(nmea_sentence[:-2])
        return nmea_sentence

    def _spi_write(self, data):
        self._gpiod.spi_xfer(self._spi_handle, data[:1], 100000, 50)
        return self._gpiod.spi_xfer(self._spi_handle, data[1:], 100000, 10)
