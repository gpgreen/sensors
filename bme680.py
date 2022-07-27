# read data from a BME680 environmental sensor
# assuming device is on linux as a iio driver

from pathlib import Path

IIO_PATH = Path("/sys/bus/iio/devices")

class BME680:
    # device name
    device_name = b'bme680'

    temperature = 0
    pressure = 1
    humidity = 2
    resistance = 3

    def __init__(self):
        """Environmental IIO sensor. Temp, Press, Humidity, and VOC air quality"""
        if not IIO_PATH.exists():
            raise OSError("no iio sensor bus on this machine")
        self._device_path = None
        self._resistance = 0
        self._temp = 0
        self._humidity = 0
        self._press = 0
        # list device directories on bus
        for devdir in IIO_PATH.iterdir():
            if not devdir.is_dir():
                continue
            # find the name entry, looking to find the bme device
            for dev_entry in devdir.iterdir():
                if dev_entry.name == r'name':
                    dev_name = dev_entry.read_bytes().strip(b'\n')
                    if dev_name.find(BME680.device_name) >= 0:
                        self._device_path = devdir
                        break
            if self._device_path is not None:
                break
        else:
            raise OSError("no matching bme680 device on iio bus")
        self.init_channels()

    def init_channels(self):
        """ initialize the channels of the device as Path objects """
        self._resistance_ch = self._device_path / "in_resistance_input"
        self._temperature_ch = self._device_path / "in_temp_input"
        self._humidity_ch = self._device_path / "in_humidityrelative_input"
        self._pressure_ch = self._device_path / "in_pressure_input"

    def read_channel(self, ch):
        """ read voc resistance """
        val = 0.0
        while True:
            chptr = None
            if ch == BME680.temperature:
                chptr = self._temperature_ch
            elif ch == BME680.pressure:
                chptr = self._pressure_ch
            elif ch == BME680.humidity:
                chptr = self._pressure_ch
            else:
                chptr = self._resistance_ch
            try:
                val = chptr.read_bytes()
                break
            except OSError as e:
                if e.errno == 22:
                    continue
                raise e
        return float(val)

    def read_resistance(self):
        self.resistance = self.read_channel(BME680.resistance)

    def read_temperature(self):
        """ read temperature """
        self._temp = self.read_channel(BME680.temperature) / 1000.0

    def read_pressure(self):
        """ read pressure """
        self._press = self.read_channel(BME680.pressure)

    def read_humidity(self):
        """ read relative humidity """
        self._humidity = self.read_channel(BME680.humidity)

    def create_nmea0183_sentence(self, talker_id):
        """ create a nmea0183 sentence with a given talker_id """
        nmea_sentence = '{}MDA,,I,{:.1f},B,{:.1f},C,,C,{:.1f},,,C,,T,,M,,N,,M'.format(
            talker_id, self.press, self._temp, self._humidity)
        # compute checksum
        checksum_value = 0
        for nmea_ch in nmea_sentence:
            checksum_value ^= ord(nmea_ch)
        nmea_sentence = '${}*{:02x}\r\n'.format(nmea_sentence, checksum_value)
        #print(nmea_sentence[:-2])
        return nmea_sentence
