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
from pathlib import Path
import bme680

def read_config_file(fconfig):
    return json.load(fconfig.read_text())

def main():
    # get environment variable with config file path
    fconfig = Path(os.environ['SENSOR_MONITOR_CONFIG'])
    print("sensor_monitor.py: using config file at '{}'".format(fconfig))
    config = read_config_file(fconfig)

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

    bmedev = bme680.BME680()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        while True:
            bmedev.read_temperature()
            sock.sendto(bmedev.create_nmea0183_sentence(talker_id).encode(),
                        (udp_host, udp_port))
            time.sleep(sleepy)

if __name__ == '__main__':
    main()
