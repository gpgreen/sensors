#!/usr/bin/python3

#########################################################
# daemon process to monitor sensors on Boat Computer
#
# Requires an environment variable 'SENSOR_MONITOR_CONFIG'
# to be set with the path to the configuration file
# example configuration file included with all required
# fields
# Sends NMEA 0183 sentences via UDP to host and port
# specified in the configuration file
###########################################################
import socket
import time
import json
import os
import math

import pigpio
import ChartPlotterHatADC
import bmp085

class LM35:
    """Takes ADC readings and converts to temperature for an LM35 sensor"""
    def __init__(self):
        self._temp = 0

    def adc_reading(self, adc_value):
        if adc_value == 0:
            return
        self._temp = adc_value * 3300 / 1024.0 / 10.0
        #print("lm35 temp:", self._temp)

    def create_nmea0183_sentence(self, talker_id):
        nmea_sentence = '{}MTA,{:.1f},C'.format(talker_id, self._temp)
        # compute checksum
        checksum_value = 0
        for nmea_ch in nmea_sentence:
            checksum_value ^= ord(nmea_ch)
        nmea_sentence = '${}*{:02x}\r\n'.format(nmea_sentence, checksum_value)
        #print(nmea_sentence[:-2])
        return nmea_sentence

class Thermistor:
    """Takes ADC readings and converts to temperature for an Thermistor sensor"""
    def __init__(self):
        self._steinhart = 0

    def adc_reading(self, adc_value):
        if adc_value == 0:
            return
        resistance = 10000 / (1023.0 / adc_value - 1.0)
        #print("resistance:", resistance)
        steinhart = resistance / 10000.0
        steinhart = math.log(steinhart)
        steinhart = steinhart / 3950.0
        steinhart += 1.0 / (25 + 273.15)
        steinhart = 1.0 / steinhart
        self._steinhart = steinhart - 273.15
        #print("steinhart:", self._steinhart)

    def create_nmea0183_sentence(self, talker_id):
        nmea_sentence = '{}MTW,{:.1f},C'.format(talker_id, self._steinhart)
        # compute checksum
        checksum_value = 0
        for nmea_ch in nmea_sentence:
            checksum_value ^= ord(nmea_ch)
        nmea_sentence = '${}*{:02x}\r\n'.format(nmea_sentence, checksum_value)
        #print(nmea_sentence[:-2])
        return nmea_sentence

def read_config_file(fname):
    config = None
    with open(fname, "rt") as json_file:
        config = json.load(json_file)
    return config

def main():
    # get environment variable with config file path
    fname = os.environ['SENSOR_MONITOR_CONFIG']
    print("sensor_monitor.py: using config file at '{}'".format(fname))
    config = read_config_file(fname)

    sleepy = float(config['sleep_interval'])
    intf = config['udp_host']
    if intf == '':
        hoststr = 'any'
        udp_host = ''
    elif intf == 'any':
        udp_host = ''
        hoststr = intf
    else:
        udp_host = intf
        hoststr = intf
    udp_port = int(config['udp_port'])
    print("Sleep interval: {}\nOutput to {}:{}".format(sleepy, hoststr, udp_port))
    talker_id = config['nmea0183_talker_id']
    print("NMEA0183 Talker ID:", talker_id)

    # open pigpio connection
    my_pi = pigpio.pi()

    try:
        hatdev = ChartPlotterHatADC.ChartPlotterHatADC(my_pi,
                                                       int(config['hat_bus']),
                                                       int(config['hat_device']),
                                                       int(config['button_pin']))
        hatdev.open()
        barodev = bmp085.BMP085Device(my_pi,
                                      int(config['bmp085_i2c_bus']),
                                      int(config['bmp085_xclr_pin']),
                                      int(config['bmp085_eoc_pin']))

        thermistor = Thermistor()
        lm35 = LM35()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            while True:
                lm35.adc_reading(hatdev.read_adc_channel(0))
                thermistor.adc_reading(hatdev.read_adc_channel(1))
                barodev.read_sensor()
                sock.sendto(lm35.create_nmea0183_sentence(talker_id).encode(),
                            (udp_host, udp_port))
                sock.sendto(thermistor.create_nmea0183_sentence(talker_id).encode(),
                            (udp_host, udp_port))
                sock.sendto(barodev.create_nmea0183_sentence(talker_id).encode(),
                            (udp_host, udp_port))
                time.sleep(sleepy)

    finally:
        hatdev.close()
        barodev.close()
        my_pi.stop()

if __name__ == '__main__':
    main()
