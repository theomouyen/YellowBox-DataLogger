#!/bin/sh

#set -x
set  -eu

BME68X_DIR="BME68x-Sensor-API"

PYTHON_DIR="/usr/include/python3.7m"

echo 'Compiling'
gcc -Wall -Wno-unused-but-set-variable -Wno-unused-variable \
  -std=c99 -pedantic \
  -I"${PYTHON_DIR}" \
  "${BME68X_DIR}"/bme68x.c \
  ./bme688.c \
  -lm -lrt -lwiringPi -lpython3.7m \
  -o bme688
echo 'Compiled'

