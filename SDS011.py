#!/usr/bin/python
# -*- coding: UTF-8 -*-

import serial, time, struct, array
from datetime import datetime

ser = serial.Serial()
ser.port = "/dev/ttyUSB0" # Set this to your serial port
ser.baudrate = 9600

ser.open()
ser.flushInput()

byte, lastbyte = "\x00", "\x00"
cnt = 0
while True:
    lastbyte = byte
    byte = ser.read(size=1)
    print("{:3} {}".format(ord(byte),byte))
#    print("Got byte %x" %ord(byte))
    # We got a valid packet header
    if lastbyte == b'\xaa' and byte == b'\xC0':
        sentence = ser.read(size=8) # Read 8 more bytes
        readings = struct.unpack('<hhxxcc',sentence) # Decode the packet - big endian, short for pm2.5, short for pm10, 2 bytes: sensor ID, checksum, message tail
        print( array.array('B',sentence) )
        pm_25 = readings[0]/10.0
        pm_10 = readings[1]/10.0
        # ignoring the checksum and message tail
        b'\xAB'
        if (cnt == 0 ):
            line = "PM 2.5: {} μg/m^3  PM 10: {} μg/m^3".format(pm_25, pm_10)
            print(datetime.now().strftime("%d %b %Y %H:%M:%S.%f: ")+line)
        cnt += 1
        if (cnt == 5):
            cnt = 0
