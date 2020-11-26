#!/usr/bin/python3

#########################################################
# daemon process to monitor sensors on BBB
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
import lm35
import bmp085
import json
import sys
import os

def read_config_file(fname):
    config = None
    with open(fname, "rt") as f:
        config = json.load(f)
    return config

def main(args):
    # get environment variable with config file path
    fname = os.environ['SENSOR_MONITOR_CONFIG']
    print("sensor_monitor.py: using config file at '{}'".format(fname))
    config = read_config_file(fname)

    sleepy = float(config['sleep_interval'])
    intf = config['udp_host']
    if intf == '':
        hoststr = 'any'
        HOST = ''
    elif intf == 'any':
        HOST = ''
        hoststr = intf
    else:
        HOST = intf
        hoststr = intf
    PORT = int(config['udp_port'])
    print("Sleep interval: {}\nOutput to {}:{}".format(sleepy, hoststr, PORT))

    temp = lm35.LM35(config['lm35_pin'])
    baro = bmp085.BMP085Device(int(config['bmp085_i2c_bus']),
                               config['bmp085_xclr_pin'])
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        while True:
            temp.read_sensor()
            baro.read_sensor()
            s.sendto(temp.create_nmea0183_sentence().encode(), (HOST, PORT))
            s.sendto(baro.create_nmea0183_sentence().encode(), (HOST, PORT))
            time.sleep(sleepy)

if __name__ == '__main__':
    main(sys.argv)
