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

    def __init__(self, my_pi, bus, device):
        self._gpiod = my_pi
        self._spi_bus = bus
        if bus != 0:
            raise ValueError("SPI bus 1 not implemented yet")
        self._spi_dev = device
        if device < 0 or device > 1:
            raise ValueError("Illegal channel:{}".format(device))
        self._spi_handle = None
        print("ChartPlotterHat initialized on SPI bus {} channel {}".format(
            self._spi_bus, self._spi_dev))

    def open(self):
        self._spi_handle = self._gpiod.spi_open(self._spi_dev, 32000, 0)
        time.sleep(0.00002)
        # read firmware version
        fwver = self._spi_write([0x4, 0x0, 0x0])
        print("firmware:{}.{}".format(fwver[0], fwver[1]))
        # specify which channel to get
        self._spi_write([0x1, 0x3, 0x00])
        print("channels:", self._spi_write([0x2, 0x0, 0x0])[0])

    def close(self):
        self._gpiod.spi_close(self._spi_handle)

    def read_adc_channel(self, channel):
        if channel < 0 or channel > 7:
            raise ValueError("Illegal ADC Channel: {}".format(channel))
        res = self._spi_write([channel + 0x10, 0, 0])
        raw = res[0] + (res[1] << 8)
        return raw

    def _spi_write(self, data):
        self._gpiod.write(8, 0)
        time.sleep(0.00005)
        # now write to the dev
        self._gpiod.spi_xfer(self._spi_handle, data[:1])
        time.sleep(0.00004)
        data = self._gpiod.spi_xfer(self._spi_handle, data[1:])[1]
        self._gpiod.write(8, 1)
        return data
