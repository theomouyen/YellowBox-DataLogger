
'''field_recorder.py
Provides WAV recording functionality for the YellowBox in FIELD CASE:

This script is being run at boot when an external disk is detected (cue that the YellowBox is being used in the field)

Non-blocking mode is being started/stopped when the GPIO button is pressed.

'''

import os
import RPi.GPIO as GPIO
import subprocess
import sys
import signal
from time import sleep
import time
import pyaudio
import wave
from datetime import datetime
from collections import deque
import pickle
import smbus2
import bme280
import sched
from multiprocessing import Process
from threading import Timer
#import threading
#from gps import *
import gpsd




class Recorder(object):
    '''A recorder class for recording audio to a WAV file.
    Records in stereo by default.
    '''

    def __init__(self, channels=2, rate=48000, frames_per_buffer=1024):
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer

    def open(self, fname, mode='wb'):
        return RecordingFile(fname, mode, self.channels, self.rate,
                            self.frames_per_buffer)

class RecordingFile(object):
    def __init__(self, fname, mode, channels, 
                rate, frames_per_buffer):
        global data, bme280
        self.fname = fname
        self.mode = mode
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer
        self._pa = pyaudio.PyAudio()
        self.wavefile = self._prepare_file(self.fname, self.mode)
        self._stream = None
        
        data = dict()
        data["audio"] = dict()
        data["bme"] = dict()
        data["gps"] = dict()
        
        data["bme"]["temperature"] = deque()
        data["bme"]["pressure"] = deque()
        data["bme"]["humidity"] = deque()
        data["bme"]["time"] = deque()
        
        data["gps"]["latitude"] = deque()
        data["gps"]["altitude"] = deque()
        data["gps"]["longitude"] = deque()
        data["gps"]["time"] = deque()

        data["audio"]["time"] = deque()
        
    def __enter__(self):
        return self

    def __exit__(self, exception, value, traceback):
        self.close()


    def start_recording(self):
        # Use a stream with a callback in non-blocking mode
        self._stream = self._pa.open(format=pyaudio.paInt16,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        input_device_index=0,
                                        frames_per_buffer=self.frames_per_buffer,
                                        stream_callback=self.get_callback())
        self._stream.start_stream()
        return self

    def stop_recording(self):
        self._stream.stop_stream()
        return self

    def get_callback(self):
        def callback(in_data, frame_count, time_info, status):

            self.wavefile.writeframes(in_data) 
            t = datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S:%f')[:-3] 
            data["audio"]["time"].append(t)

            return in_data, pyaudio.paContinue
        return callback


    def close(self):
        self._stream.close()
        self._pa.terminate()
        self.wavefile.close()

    def _prepare_file(self, fname, mode='wb'):
        wavefile = wave.open(fname, mode)
        wavefile.setnchannels(self.channels)
        wavefile.setsampwidth(self._pa.get_sample_size(pyaudio.paInt16))
        wavefile.setframerate(self.rate)
        return wavefile

def reset_data():
    global data
    del data, time

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

def get_sensors():
    
    # Reading BME sensor
    bus     = smbus2.SMBus(0)
    BME     = bme280.sample(bus, address=0x76)
    t_bme   = datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S')[:] 
    T       = BME.temperature
    P       = BME.pressure
    H       = BME.humidity
    print("BME data retrieved")
    
    # Reading GPS
    gpsd.connect()
    packet = gpsd.get_current()

    lat     = packet.lat
    lon     = packet.lon
    alt     = packet.alt
    t_gps   = packet.time
    print("GPS data retrieved")
   
    # Apending BME data
    data["bme"]["temperature"].append(T)
    data["bme"]["pressure"].append(P)
    data["bme"]["humidity"].append(H)
    data["bme"]["time"].append(t_bme)

    # Apending GPS data
    data["gps"]["latitude"].append(lat)
    data["gps"]["altitude"].append(alt)
    data["gps"]["longitude"].append(lon)
    data["gps"]["time"].append(t_gps)


def dumping(path_data):

    pkl_file = open(path_data, 'wb')
    pickle.dump(data, pkl_file)

# def init_name: function to intialize name of the recordings (the idea: restart recording every hour)

def main():
    
    # Detetect if external disk is connected
    # if so, you are in the field configuration

    result = subprocess.run(['lsusb'], stdout=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    disks = output.splitlines()
    nbDisks = len(disks)

    if "SanDisk" in disks[0]:
        
        # Paths and extensions
        data_ext    = '.pkl' 
        audio_ext   = '.wav' 
        disk_path   = '/mnt/usb/'

        # GPIO pins settings
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(24, GPIO.OUT, initial=GPIO.LOW)

        # Timers settings
        SENSOR_SAMPLING_RATE    = 2
        DUMPING_RATE            = SENSOR_SAMPLING_RATE*1.1
        
        rec_proc                = None

        try:
            while True:
                if (GPIO.input(17) and rec_proc is None):

                    # Name of recording
                    date        = datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S:%f')[:-3]
                    path_audio  = disk_path + date + audio_ext
                    path_data   = disk_path + date + data_ext 
                    
                    # Start PyAudio callback function
                    rec_proc    = Recorder(channels=2, rate=96000) 
                    recfile     = rec_proc.open(path_audio, 'wb')
                    recfile.start_recording()

                    print(""" * recording """)
                    GPIO.output(24, GPIO.HIGH) 
                    
                    # BME and GPS data
                    timer_sensor = RepeatTimer(SENSOR_SAMPLING_RATE, get_sensors)
                    timer_sensor.start()
                    #get_sensors(gpsd,BME,SENSOR_SAMPLING_RATE)

                    # Regular dumping of the Meta Data
                    #dumping(DUMPING_RATE,path_data)
                    timer_dump = RepeatTimer(DUMPING_RATE, dumping, args=(path_data,))
                    timer_dump.start()
                    sleep(2)

                elif (GPIO.input(17) and rec_proc is not None):

                    # Stop PyAudio recoring
                    recfile.stop_recording()
                    recfile.close()

                    # Stop sensors threads
                    timer_sensor.cancel()

                    #Save data (last dumping)
                    timer_dump.cancel()
                    pkl_file = open(path_data, 'wb')
                    pickle.dump(data, pkl_file)
                    
                    print(""" stoped recording """)
                    GPIO.output(24, GPIO.LOW)
                    
                    rec_proc = None
                    sleep(1)
                    print(""" ready to record again """)

                sleep(0.2)

        finally:
            GPIO.cleanup()

    else:
        sys.exit()

#if __name__ == '__main__':
#main()


if __name__ == "__main__":
    try:
        processes = [Process(target=RecordingFile, args=(3,4)),
                Process(target=main(),args=(2,4))]
        for process in processes:
            process.start()
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
            GPIO.cleanup()
        except SystemExit:
            os._exit(0)

