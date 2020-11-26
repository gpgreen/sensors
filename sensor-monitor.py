#!/usr/bin/python3

import socket
import time
import lm35
import bmp085

# open a socket
HOST = ''       # all available interfaces
PORT = 49898

lm35 = lm35.LM35("P9_39")
baro = bmp085.BMP085Device(2, "P9_12")

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    while True:
        lm35.read_sensor()
        baro.read_sensor()
        s.sendto(lm35.create_nmea0183_sentence().encode(), (HOST, PORT))
        s.sendto(baro.create_nmea0183_sentence().encode(), (HOST, PORT))
        time.sleep(5)
        
