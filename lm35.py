#//////////////////////////////////////
#	lm35.py
# 	Reads the analog value of the temperature sensor.
#//////////////////////////////////////
import Adafruit_BBIO.ADC as ADC

pin = "P9_39"        # light sensor

class LM35(object):

    def __init__(self, pin):
        ADC.setup()
        self._pin = pin
        self._temp = 0
        print("LM35 Temperature sensor initialized on pin {}".format(self._pin))
        
    def read_sensor(self):
        x = ADC.read(self._pin)
        self._temp = x * 1.8 * 100

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
