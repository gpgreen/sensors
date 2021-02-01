#//////////////////////////////////////
#	lm35.py
# 	Reads the analog value of the temperature sensor.
#   Uses the hat power monitor
#//////////////////////////////////////
import time

# raspberry pi imports
import pigpio

class LM35:
    """ Read ADC channels from chart plotter hat"""

    def __init__(self, my_pi, channel, bus, device, button):
        if not 0 <= channel < 6:
            raise ValueError('channel must be in range: 0-5')
        self._gpiod = my_pi
        self._spi_bus = bus
        if bus != 0:
            raise ValueError("SPI bus 1 not implemented yet")
        self._spi_dev = device
        self._channel = channel
        self._spi_handle = None
        self._temp = 0
        self._button = button
        print("LM35 Temperature sensor initialized on channel {}".format(self._channel))

    def open(self):
        self._spi_handle = self._gpiod.spi_open(self._spi_dev, 100000, 0)
        time.sleep(0.00002)
        # specify which channel to get
        self._spi_write([0x1, 0x1, 0x00])
        print("channels:", self._spi_write([0x2, 0x0, 0x0])[0])

    def close(self):
        self._gpiod.spi_close(self._spi_handle)

    def read_sensor(self):
        self._spi_write([0x2, 0, 0])
        res = self._spi_write(self._send())
        raw = res[0] + (res[1] << 8)
        self._temp = raw * 3.3 / 1023.0 * 100
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
        # pulse button pin, to wake up device
        self._gpiod.set_mode(self._button, pigpio.OUTPUT)
        self._gpiod.write(self._button, 0)
        time.sleep(0.00005)
        self._gpiod.write(self._button, 1)
        self._gpiod.set_mode(self._button, pigpio.INPUT)
        # now write to the dev
        self._gpiod.spi_xfer(self._spi_handle, data[:1])
        time.sleep(0.00005)
        return self._gpiod.spi_xfer(self._spi_handle, data[1:])[1]
