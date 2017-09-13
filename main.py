#!/usr/bin/python
# -*- coding: UTF-8 -*-
###########READ STATUS###############################
# THIS EXAMPLE READS DATA + PUSHES IT TO THINGSPEAK #
#####################################################

import logging
from SDS011 import SDS011, ReadingMessage
import thingspeak
import os


if __name__ == "__main__":

  logging.getLogger().setLevel(logging.DEBUG)


  channel_id = "329953"

  assert 'thingspeak_channels_329953_key' in os.environ, "you have to set 'thingspeak_channels_329953_key' enviroment variable1"
  write_key = os.environ['thingspeak_channels_329953_key']

  channel = thingspeak.Channel(id=channel_id,write_key=write_key)



  sds011 = SDS011()

  r = sds011.get_version()
  print("firmware:", r)

  r = sds011.is_working()
  print("working: ",r)

  r = sds011.set_working_period(1)
  r = sds011.get_working_period()
  if r==0:
    print("working period: continous")
  else:
    print("working period: work 30 seconds and sleep {} seconds".format(r*60-30))



  while True:
    try:
      r = sds011._response()
      data = ReadingMessage(r)
      logging.info(data)
      TS_resp = channel.update({1:data.pm_25, 2:data.pm_10})
      print(TS_resp)
    except AssertionError as e:
      pass
