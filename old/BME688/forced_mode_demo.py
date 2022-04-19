import bme

bme.init("/dev/i2c-1", 119)
bme.set_timezone("TZ=Europe/London")   # other options include "TZ=Asia/Singapore" or "TZ=US/Denver"
bme.forced_mode()
print(" year mon day h min sec  Tmp degC            Prs Pa         Hum %rH           GsR Ohm   Status")
data = bme.get_data()
print(data)
print("Installation succeeded")