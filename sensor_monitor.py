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

import lm35
import bmp085

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

    tempdev = lm35.LM35(int(config['lm35_channel']),
                        int(config['lm35_bus']),
                        int(config['lm35_device']))
    tempdev.open()
    barodev = bmp085.BMP085Device(int(config['bmp085_i2c_bus']),
                                  int(config['bmp085_xclr_pin']),
                                  int(config['bmp085_eoc_pin']))

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        while True:
            tempdev.read_sensor()
            barodev.read_sensor()
            sock.sendto(tempdev.create_nmea0183_sentence(talker_id).encode(), (udp_host, udp_port))
            sock.sendto(barodev.create_nmea0183_sentence(talker_id).encode(), (udp_host, udp_port))
            time.sleep(sleepy)

    tempdev.close()

if __name__ == '__main__':
    main()
