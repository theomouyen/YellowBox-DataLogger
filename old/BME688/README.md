**BME68X for C and Python by pi3g**


Install and run the application in C

- make sure your circuit is set up correctly, refer to the corresponding pictures in the assets directory
- open terminal cd into this folder
- execute: git clone https://github.com/BoschSensortec/BME68x-Sensor-API
- alternatively you can download the github repository and unzip it into this folder
- this will download the BME68X API by BOSCH (BSD-3 License)
- open make.sh and change PYTHON_DIR to the path of the Python.h file that corresponds to your Python version
- save and close make.sh, execute: sudo bash ./make.sh
- the application should be compiled
- execute ./bme688 to run the program


This application can also be used as a Python extension

- execute: sudo python3 setup.py install
- this will build and install the application
- to import in Python use: import bme
- see PythonDocumentation.txt for reference
- to test the installation, set up the circuit correctly (refer to corresponding pictures in assets directory)
- if you are not using the default i2c_port ("/dev/i2c-1") and i2c_addr (119) change the inputs of bme.init accordingly
- change the input of bme.set_timezone to your timezone (or delete this line to set timezone to default "TZ=Europe/Berlin")
- execute: python3 forced_mode_demo.py