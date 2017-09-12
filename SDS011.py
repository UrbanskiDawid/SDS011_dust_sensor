#!/usr/bin/python
# -*- coding: UTF-8 -*-
import serial, time, struct, array
from datetime import datetime
from enum import Enum


class TARGET_DEVICE:
    def __init__(self, l:int, h:int):
        self.l_byte = l
        self.h_byte = h

    @staticmethod
    def any():
       return TARGET_DEVICE(0xFF, 0xFF)


class SDS011_CMD(Enum):
    DATA_REPORTING_MODE = 2
    QUERY_DATA = 4
    DEVICE_ID = 5
    SLEEP_AND_WORK = 6
    CHECK_FIRMWARE_VERSION = 7
    WORKING_PERIOD = 8


def generate_cmd(code:SDS011_CMD, values=None, target=TARGET_DEVICE.any()):
    #CMD 19 bytes
    #byte[0] = 0xAA
    #byte[1] = 0xB4
    #byte[2] = CMD_CODE (duty cycle: 0x08)
    #byte[3] = 1 - write, 0 - read
    #byte[4] = WRITE_VALUE
    #byte[5,6,7,8,9,10,11,12,13,14] = 0x0
    #byte[15,16] - sensor ID,  [0xFF, 0xFF] = ANY
    #byte[17] - checksum
    #byte[18] - 0xAB
    assert isinstance(code, SDS011_CMD)
    assert values is None or isinstance(values, list)

    write_or_read = 0 if values is None else 1

    cmd = bytearray([ 0xAA, 0xB4, # cmd prefix
                      code.value, # cmd code
                      write_or_read, # write flag: 0 - read, 1 - write
                      0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, #data
                      target.l_byte, target.h_byte, # target device
                      0x05, # checksum
                      0xAB ]) # postfix

    if values:
        for i in range(len(values)):
            cmd[4+i] = values[i]

    checksum = 0
    for i in range(2, 17): # skip prefix and checksum+postfix
       checksum += cmd[i]
    checksum = checksum % 256

    cmd[17] = checksum

    return cmd


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
      return "{}: [{}] SENSOR_ID: {} PM 2.5: {} Î¼g/m^3  PM 10: {} Î¼g/m^3".format(self.date.strftime("%d %b %Y %H:%M:%S.%f"),
                                                                                   ' '.join('{:02X}'.format(x) for x in self.raw),
                                                                                   self.sensorID,
                                                                                   self.pm_25,
                                                                                   self.pm_10)

class SDS011:

  def __init__(self):
     self.enabled=False
     self.serial=self.openSerial()

  def openSerial(self) -> serial.Serial:
    ###
    #Serial Port: 5V TTL, 9600bpsÂwithÂ8 dataÂ bit, no parity, one stopÂ bit. 
    #Data Packetï¼19bytesï¼Head+Command_ID+Data(15bytes)+checksum+Tail
    #Checksum: Low 8bit of the sum result of Data Bytesïnot including packet head, tail and Command ID.
    ###
    ser = serial.Serial()
    ser.port = "/dev/ttyUSB0" # Set this to your serial port
    ser.baudrate = 9600

    ser.open()
    ser.flushInput()
    return ser


sds011 = SDS011()


###########READ STATUS
byte = lastbyte = b'\x00'

while True:
    lastbyte = byte
    byte = sds011.serial.read(size=1)
    if lastbyte == b'\xAA' and byte == b'\xC0':
        sentence = sds011.serial.read(size=8) # Read 8 more bytes
        r = ReadingMessage(b'\xAA\xC0'+sentence)
        print(r)
