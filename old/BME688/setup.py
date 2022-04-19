from distutils.core import setup, Extension

bme = Extension('bme',
    extra_compile_args = ['-Wno-unused-but-set-variable', '-Wno-unused-variable', '-Wno-unused-result'],
	include_dirs = ['/usr/local/include', './BME68x-Sensor-API'],
	libraries = ['pthread', 'wiringPi', 'm', 'rt'],
    depends = ['./BME68x-Sensor-API/bme68x.h', './BME68x-Sensor-API/bme68x.c', './BME68x-Sensor-API/bme68x_defs.h'],
	sources =['bme688.c', './BME68x-Sensor-API/bme68x.c'])

setup (name = 'bme',
	version = '1.0',
	description = 'Python interface for BME68X sensor',
	author = 'Nathan',
	url = 'https://pi3g.com',
    headers = ['./BME68x-Sensor-API/bme68x.h', './BME68x-Sensor-API/bme68x_defs.h'], 
	ext_modules = [bme])