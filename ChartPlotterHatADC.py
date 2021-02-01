#//////////////////////////////////////
#	ChartPlotterHatADC.py
#   Reads the analog channels of the
#   ChartPlotterHat
#//////////////////////////////////////
import time

# raspberry pi imports
import pigpio

class ChartPlotterHatADC:
    """ Read ADC channels from chart plotter hat"""

    def __init__(self, my_pi, bus, device, button):
        self._gpiod = my_pi
        self._spi_bus = bus
        if bus != 0:
            raise ValueError("SPI bus 1 not implemented yet")
        self._spi_dev = device
        self._spi_handle = None
        self._temp = 0
        self._button = button
        print("ChartPlotterHat initialized on SPI bus {} device {}".format(
            self._spi_bus, self._spi_dev))

    def open(self):
        self._spi_handle = self._gpiod.spi_open(self._spi_dev, 100000, 0)
        time.sleep(0.00002)
        # read firmware version
        fwver = self._spi_write([0x4, 0x0, 0x0])
        print("firmware:{}.{}".format(fwver[0], fwver[1]))
        # specify which channel to get
        self._spi_write([0x1, 0x2, 0x00])
        print("channels:", self._spi_write([0x2, 0x0, 0x0])[0])

    def close(self):
        self._gpiod.spi_close(self._spi_handle)

    def read_lm35(self):
        res = self._spi_write(self._send(0))
        raw = res[0] + (res[1] << 8)
        self._temp = raw * 3.3 / 1023.0 * 100
        print("raw temp:", raw)

    def read_thermistor(self):
        res = self._spi_write(self._send(1))
        raw = res[0] + (res[1] << 8)
        print("raw thermistor:", raw)

    def _send(self, channel):
        return [channel + 0x10, 0, 0]

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
        time.sleep(0.000005)
        self._gpiod.write(self._button, 1)
        self._gpiod.set_mode(self._button, pigpio.INPUT)
        time.sleep(0.00005)
        # now write to the dev
        self._gpiod.spi_xfer(self._spi_handle, data[:1])
        time.sleep(0.00004)
        return self._gpiod.spi_xfer(self._spi_handle, data[1:])[1]
