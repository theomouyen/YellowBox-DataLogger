#! /usr/bin/env python3

'''field_recorder.py
Provides WAV recording functionality for the YellowBox data logger:

This script is being run at boot when an external disk is detected.

Non-blocking mode is being started/stopped when the GPIO button is pressed.

'''

import os
import sh
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


disk_mountpoint = '/mnt/usb'


class Recording(object):
    def __init__(self, fname, mode = 'wb', channels = 2, 
                rate = 48000, frames_per_buffer = 1024):
        global bme280

        self.fname = fname
        self.mode = mode
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer
        self.part_length = frames_per_buffer*(536870912//frames_per_buffer)
        self.length = 0
        self.nparts = 0
        self._pa = pyaudio.PyAudio()
        self._stream = None

        self.data = dict()
        self.data["audio"] = dict()
        self.data["bme"] = dict()
        self.data["gps"] = dict()
        self.data["filename"] = []

        self.data["bme"]["temperature"] = deque()
        self.data["bme"]["pressure"] = deque()
        self.data["bme"]["humidity"] = deque()
        self.data["bme"]["time"] = deque()

        self.data["gps"]["latitude"] = deque()
        self.data["gps"]["altitude"] = deque()
        self.data["gps"]["longitude"] = deque()
        self.data["gps"]["time"] = deque()

        self.data["audio"]["time"] = deque()
        self.data["audio"]["part"] = deque()
        
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
        self._stream.close()
        self._pa.terminate()
        self._wavefile.close()
        return self

    def get_callback(self):
        def callback(in_data, frame_count, time_info, status):
            if self.length % self.part_length == 0:
                if self.length == 0:
                    part_fname = self.fname
                else:
                    self._wavefile.close()
                    part_fname = "%s_%s" % (self.fname, self.nparts) 
                    self.data["filename"].append(part_fname)
                self._wavefile = self._prepare_file(part_fname + '.wav', self.mode)
                self.nparts += 1

            self._wavefile.writeframes(in_data) 
            t = datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S:%f')[:-3] 
            self.data["audio"]["time"].append(t)
            self.data["audio"]["part"].append(self.nparts - 1)
            self.length += frame_count

            return in_data, pyaudio.paContinue
        return callback

    def _prepare_file(self, fname, mode):
        wavefile = wave.open(fname, mode)
        wavefile.setnchannels(self.channels)
        wavefile.setsampwidth(self._pa.get_sample_size(pyaudio.paInt16))
        wavefile.setframerate(self.rate)
        return wavefile

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

def get_sensors(data):
    
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


def dumping(path_data, data):
    with open(path_data + '.pkl', 'wb') as pkl_file:
        pickle.dump(data, pkl_file)

def main():
    
    # Check if disk is mounted 
    if os.path.ismount(disk_mountpoint):

        # GPIO pins settings
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(24, GPIO.OUT, initial=GPIO.LOW)

        # Timers settings
        SENSOR_SAMPLING_RATE    = 2
        DUMPING_RATE            = SENSOR_SAMPLING_RATE*1.1
        
        rec                     = None

        try:
            while True:
                if (GPIO.input(17) and rec is None):

                    # Name of recording
                    date        = datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S:%f')[:-3]
                    path_audio  = os.path.join(disk_mountpoint, date)
                    path_data   = os.path.join(disk_mountpoint, date)
                    
                    # Start PyAudio callback function
                    rec = Recording(fname = path_audio, mode = 'wb', channels = 2, rate = 96000)
                    rec.start_recording()

                    print(""" * recording """)
                    GPIO.output(24, GPIO.HIGH) 
                    
                    # BME and GPS data
                    timer_sensor = RepeatTimer(SENSOR_SAMPLING_RATE, get_sensors, args=(rec.data,))
                    timer_sensor.start()
                    #get_sensors(gpsd,BME,SENSOR_SAMPLING_RATE)

                    # Regular dumping of the Meta Data
                    #dumping(DUMPING_RATE,path_data)
                    timer_dump = RepeatTimer(DUMPING_RATE, dumping, args=(path_data, rec.data))
                    timer_dump.start()
                    sleep(2)

                elif (GPIO.input(17) and rec is not None):

                    # Stop PyAudio recoring
                    rec.stop_recording()

                    # Stop sensors threads
                    timer_sensor.cancel()

                    #Save data (last dumping)
                    timer_dump.cancel()
                    dumping(path_data, rec.data)
                    
                    print(""" stopped recording """)
                    GPIO.output(24, GPIO.LOW)
                    
                    rec = None
                    sleep(1)
                    print(""" ready to record again """)

                sleep(0.2)

        finally:
            GPIO.cleanup()

    else:
        print("nothing is mounted on " + disk_mountpoint + ": exiting", file=sys.stderr)
        sys.exit(1)

#if __name__ == '__main__':
#main()


if __name__ == "__main__":
    try:
        processes = [Process(target=Recording, args=(3,4)),
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

