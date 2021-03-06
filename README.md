# YellowBox-DataLogger

Software and hardware description of the YellowBox data logger, a custom-built data logger designed for acoustic recordings in research field campaigns.

![](https://github.com/theomouyen/YellowBox-DataLogger/blob/main/figures/YB_pic_all.png?raw=true)

The YB data logger can record two channels (BNC connectors, to allow different type of sensors) with a sampling rate up to 192 kHz. It also includes a pressure, temperature and humidity sensor, as well as a GPS module for accurate time and synchronisation.

## Hardware description

A Raspberry Pi 3 A+ powered by a power bank is connected to a HifiBerry DAC+ ADC Pro sound card. A GPS module (ADD BRAND) and an RTC module (ADD BRAND) are used. 

Here is an overview of the electrical cicuits:

![](https://github.com/theomouyen/YellowBox-DataLogger/blob/main/figures/OverviewEnglish.png?raw=true)
For more details on the electrical circuits, please refer to the Wiki.


<br />

## Software description

The Raspberry Pi is running a headless Raspbian. A Network Time Protocol is set up using the GPS module. The `/scripts/field_recording_v2.py` program runs at boot and waits for a GPIO input (button press). Pressing the button allows to start and stop the recordings.

More precisions on the `field_recording_v2.py` program can be found here. The steps to set up the Raspberry Pi with NTP protocol, the RTC clock and the HifiBerry sound card can be found here.


<br />

## Output of the recording

Recording with the YellowBox produces two types of outputs:

- WAV files (with 2 channels) containing the data recorded by the sound card,
- a binary file (Pickle file) containing data recorded by the BME sensor and GPS module.







