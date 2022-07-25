# read data from a BME680 environmental sensor

from pathlib import Path

IIO_PATH = Path("/sys/bus/ii0/devices")

class BME680:
    # device name
    device_name = b"bme680"

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
                if dev_entry == 'name':
                    dev_name = dev_entry.read_bytes()
                    if dev_name == BME680.device_name:
                        self._device_path = devdir
                        break
            if self._device_path is not None:
                break
        if self._device_path is None:
            raise OSError("no matching bme680 device on iio bus")
        self.init_channels()

    def init_channels(self):
        """ initialize the channels of the device as Path objects """
        self._resistance_ch = self._device_path / "in_resistance_input"
        self._temperature_ch = self._device_path / "in_temp_input"
        self._humidity_ch = self._device_path / "in_humidityrelative_input"
        self._pressure_ch = self._device_path / "in_pressure_input"

    def read_resistance(self):
        """ read voc resistance """
        val = self._resistance_ch.read_bytes()
        self._resistance = float(val)

    def read_temperature(self):
        """ read temperature """
        val = self._temperature_ch.read_bytes()
        self._temp = float(val) / 1000.0

    def read_pressure(self):
        """ read pressure """
        val = self._pressure_ch.read_bytes()
        self._press = float(val)

    def read_humidity(self):
        """ read relative humidity """
        val = self._humidity_ch.read_bytes()
        self._humidity = float(val)

    def create_nmea0183_sentence(self, talker_id):
        """ create a nmea0183 sentence with a given talker_id """
        nmea_sentence = '{}MTA,{:.1f},C'.format(talker_id, self._temp)
        # compute checksum
        checksum_value = 0
        for nmea_ch in nmea_sentence:
            checksum_value ^= ord(nmea_ch)
        nmea_sentence = '${}*{:02x}\r\n'.format(nmea_sentence, checksum_value)
        #print(nmea_sentence[:-2])
        return nmea_sentence
