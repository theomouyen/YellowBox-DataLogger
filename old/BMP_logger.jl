#! /usr/bin/julia

using PyCall
using Dates
gpsd=pyimport("gpsd")
# Connect to the local gpsd
gpsd.connect()
smbus=pyimport("smbus")
bus=smbus.SMBus(1)
bmp280=pyimport("bmp280")
sensor=bmp280.BMP280(i2c_dev=bus)
STARTDATE=string(now())
open("/home/pi/$STARTDATE-BMPData.csv","a+") do logger
 while  true 
  packet = gpsd.get_current()
  alt=packet.alt
  lat=packet.lat
  lon=packet.lon
  NOW=string(now())
  sensor.update_sensor()
  T=round(sensor.temperature,digits=2)
  p=round(sensor.pressure,digits=3)
  println(logger,"$NOW,$lon,$lat,$alt,$p,$T")
#  println("$NOW,$lon,$lat,$alt,$p,$T")
  flush(logger)
  sleep(60)
 end
end
