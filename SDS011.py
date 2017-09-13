#!/usr/bin/python
# -*- coding: UTF-8 -*-

# working period
#0ï¼continuous(default)
#1-30 minuteï¼woork 30 seconds and sleep n*60-30 seconds

import serial, time, struct, array
from datetime import datetime
from enum import Enum
import logging


class TARGET_DEVICE:
    def __init__(self, l:int, h:int):
        self.l_byte = l
        self.h_byte = h

    @staticmethod
    def any():
       return TARGET_DEVICE(0xFF, 0xFF)

    def __str__(self):
       return "[0x{:02X},0x{:02X}]".format(self.l_byte,self.h_byte)


class SDS011_CMD(Enum):
    DATA_REPORTING_MODE = 2
    QUERY_DATA = 4
    DEVICE_ID = 5
    SLEEP_AND_WORK = 6
    CHECK_FIRMWARE_VERSION = 7
    WORKING_PERIOD = 8


class REPORTING_MODE(Enum):
    ACTIVE = 0
    QUERY = 1


class ReadingMessage:

    def __init__(self, data):

      self.date = datetime.now()

      s = struct.unpack('<cchhcccc', data) # Decode the packet - big endian, byte head0, byte head1, short for pm2.5, short for pm10, byte: sensor ID low, byte: sensor ID high, checksum, message tail

      self.raw = data[:]

      assert s[0]==b'\xAA', "incorrect header0 {}".format(data)
      assert s[1]==b'\xC0', "incorrect header1 {}".format(data)

      self.pm_25 = s[2]/10.0

      self.pm_10 = s[3]/10.0

      self.sensorID = TARGET_DEVICE(int.from_bytes(s[4], byteorder='big', signed=False),
                                    int.from_bytes(s[5], byteorder='big', signed=False))

      #checksum
      self.checksum = int.from_bytes(s[6], byteorder='big', signed=False)
      cs = 0
      for i in range(2, len(data)-2):
        cs += data[i]
      cs = cs  % 256
      assert cs == self.checksum

      assert s[7], b'\xAB' #message tail

    def __str__(self):
      return "{}: SENSOR: {} PM 2.5: {} Î¼g/m^3  PM 10: {} Î¼g/m^3".format(self.date.strftime("%d%b%Y %H:%M:%S"),
                                                                           self.sensorID,
                                                                           self.pm_25,
                                                                           self.pm_10)



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
    for i in range(2, 17): # skip prefix+code and checksum+postfix
       checksum += cmd[i]
    checksum = checksum % 256

    cmd[17] = checksum

    return cmd


class SDS011:

  def __init__(self, target=TARGET_DEVICE.any()):
     self.enabled=False
     self.serial=self.openSerial()
     self.target=target

  def openSerial(self) -> serial.Serial:
    ###
    #Serial Port: 5V TTL, 9600bpsÂwithÂ8 dataÂ bit, no parity, one stopÂ bit. 
    #Data Packetï¼19bytesï¼Head+Command_ID+Data(15bytes)+checksum+Tail
    #Checksum: Low 8bit of the sum result of Data Bytesïnot including packet head, tail and Command ID.
    ###
    ser = serial.Serial()
    ser.port = "/dev/ttyUSB0" # Set this to your serial port
    ser.baudrate = 9600
    ser.write_timeout = ser.timeout = 5
    ser.open()
    ser.flushInput()
    logging.debug("serial: {} at {}".format(ser.port, ser.baudrate))
    return ser

  def _request(self, cmd:SDS011_CMD, values=None):
    req=generate_cmd(cmd, values, self.target)
    self.serial.write(req)
    logging.debug("request: {} name:{} values:{}".format(' '.join('{:02X}'.format(x) for x in req), cmd, values))
    resp = self._response()
    assert req[2] == resp[2]
    return resp

  def _response(self) -> bytes:
    resp = self.serial.read(size=10) # Read 10 bytes
    logging.debug("response: {}".format( (' '.join('{:02X}'.format(x) for x in resp) if resp else "<None>")))

    assert len(resp) != 0, "no response"
    assert len(resp) == 10, "unexpected response length: {}".format(len(resp))
    assert resp[0] == 0xAA
    assert resp[9] == 0xAB
    cs = 0
    for i in range(2, 8):
      cs += resp[i]
    cs = cs  % 256
    assert cs == resp[8]

    return resp

  #note: does not work
  def get_sleep_work(self) -> int:
     # ret 1 if working
     resp = self._request(SDS011_CMD.SLEEP_AND_WORK)
     logging.info("get_sleep_work: {}".format("sleep" if resp[4] == 0 else "work"))
     return resp[4]

  def is_sleeping(self) -> bool:
     return self.get_sleep_work()==0

  def is_working(self) -> bool:
     return self.get_sleep_work()==1

  #CMD_START           = bytearray([ 0xAA, 0xB4, 0x06, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x05, 0xAB ])
  def start(self):
     resp = self._request(SDS011_CMD.SLEEP_AND_WORK, [1])
     enabled=False
     return resp

  #CMD_STOP            = bytearray([ 0xAA, 0xB4, 0x06, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x05, 0xAB ])
  def stop(self):
     #fan and laser stop
     resp=self._request(SDS011_CMD.SLEEP_AND_WORK, [0])
     enabled=False
     assert resp[1] == 0xC5
     logging.info("device has: {}".format("stopped" if resp[4] == 0 else "started"))
     return resp

  #CMD_GET_VERSION     = bytearray([ 0xAA, 0xB4, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x05, 0xAB ])
  def get_version(self):
     resp = self._request(SDS011_CMD.CHECK_FIRMWARE_VERSION)

     return datetime(year = 2000+resp[3],
                     month = resp[4],
                     day = resp[5])


  def get_working_period(self) -> int:
     #0ï¼continuous(default)
     #1-30minute - work 30 seconds and sleep n*60-30 seconds
     resp = self._request(SDS011_CMD.WORKING_PERIOD)
     return resp[4]

  #CMD_SET_DUTY        = bytearray([ 0xAA, 0xB4, 0x08, 0x01, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x0A, 0xAB ]) #note: byte[4] = duty
  def set_working_period(self, duty_minutes:int):
     #0ï¼continuous(default)
     #1-30minute - work 30 seconds and sleep n*60-30 seconds
     assert 0 <= duty_minutes <= 30
     resp = self._request(SDS011_CMD.WORKING_PERIOD, [duty_minutes])
     return resp

  def query_data(self) -> ReadingMessage:
     resp = self._request(SDS011_CMD.QUERY_DATA)
     return ReadingMessage(resp)

  def get_reporting_mode(self):
     resp = self._request(SDS011_CMD.DATA_REPORTING_MODE)
     return REPORTING_MODE.ACTIVE if resp[4]==0 else REPORTING_MODE.QUERY

  def set_reporting_mode(self, mode:REPORTING_MODE):
     resp = self._request(SDS011_CMD.DATA_REPORTING_MODE, [0 if mode==REPORTING_MODE.ACTIVE else 0])
     return resp


if __name__ == "__main__":
  logging.getLogger().setLevel(logging.DEBUG)

  sds011 = SDS011()

  r = sds011.get_version()
  print("firmware:", r)

  r = sds011.is_working()
  print("working: ",r)

  r = sds011.set_working_period(3)
  r = sds011.get_working_period()
  if r==0:
    print("working period: continous")
  else:
    print("working period: work 30 seconds and sleep {} seconds".format(r*60-30))


  ###########READ STATUS###############
  while True:
    try:
      r = sds011._response()
      logging.info(ReadingMessage(r))
    except AssertionError as e:
      pass
  #####################################
