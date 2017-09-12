#!/usr/bin/python
# -*- coding: UTF-8 -*-
import serial, time, struct, array
from datetime import datetime



class ReadingMessage:

    def __init__(self, data):

      self.date = datetime.now()

      s = struct.unpack('<cchhHcc', data) # Decode the packet - big endian, byte head0, byte head1, short for pm2.5, short for pm10, short: sensor ID, checksum, message tail

      self.raw = data[:]

      assert s[0]==b'\xAA'
      assert s[1]==b'\xC0'

      self.pm_25 = s[2]/10.0

      self.pm_10 = s[3]/10.0

      self.sensorID = s[4]

      #checksum
      self.checksum = int.from_bytes(s[5], byteorder='big', signed=False)
      cs = 0
      for i in range(2, len(data)-2):
        cs += data[i]
      cs = cs  % 256
      assert cs == self.checksum

      assert s[6], b'\xAB' #message tail

    def __str__(self):
      return "{}: [{}] SENSOR_ID: {} PM 2.5: {} μg/m^3  PM 10: {} μg/m^3".format(self.date.strftime("%d %b %Y %H:%M:%S.%f"),
                                                                                   ' '.join('{:02x}'.format(x) for x in self.raw),
                                                                                   self.sensorID,
                                                                                   self.pm_25,
                                                                                   self.pm_10)



ser = serial.Serial()
ser.port = "/dev/ttyUSB0" # Set this to your serial port
ser.baudrate = 9600

ser.open()
ser.flushInput()

byte = lastbyte = b'\x00'

while True:
    lastbyte = byte
    byte = ser.read(size=1)
    if lastbyte == b'\xAA' and byte == b'\xC0':
        sentence = ser.read(size=8) # Read 8 more bytes
        r = ReadingMessage(b'\xAA\xC0'+sentence)
        print(r)
