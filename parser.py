'''
Python 3
Written for Windows.
Written as a part of Course 11427 Arctic Technology at DTU (Techincal University of Denmark).

Usage: parser.py [-h] [-p PORT] [-b N_BASE_READINGS]

Display relative altitude from u-blox GPS module.

This script computes a relative altitude using data from a u-blox GPS unit and prints it in a readable format.
It starts off by measuring a number of datapoints which are averaged for the ground altitude.
Then the relative altitude is computed and displayed.

Input should come from a COM serial port. The program will display available COM ports by looking in the registry.
If nothing is received from the GPS, the program will probably hang.

Optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  COM port to listen on.
  -b N_BASE_READINGS, --base_readings N_BASE_READINGS
                        Number of readings for ground altitude.

Explanation for parameters in GPGGA raw GPS output:
https://www.u-blox.com/images/downloads/Product_Docs/GPS_Compendium%28GPS-X-02007%29.pdf
'''

import serial
import sys
import os
import argparse
import itertools
import winreg
import time

def enumerate_serial_ports():
    """ Uses the Win32 registry to return an
        iterator of serial (COM) ports
        existing on this computer.
    """
    path = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
    except WindowsError:
        raise IterationError

    for i in itertools.count():
        try:
            val = winreg.EnumValue(key, i)
            yield str(val[1])
        except EnvironmentError:
            break

def get_geoid_altitude(GPGGA):
    geoid_altitude = float(GPGGA[9])
    unit = GPGGA[10]
    if unit != 'M':
        print_and_log('Alert! Output from GPS was not as expected! Altitude was not given in meters, the unit was:', unit)
    return geoid_altitude

def get_n_satelites(GPGGA):
    n_satelites = GPGGA[7]
    return n_satelites

def get_GPGGA(ser):
    # Read from the raw GPS output, and find the GPGGA line.
    while True:
        try:
            line = ser.readline().strip()
        except Exception as e:
            print_and_log('Failed to read from COM port.')
            continue
        try:
            line_dec = line.decode('utf-8')
        except Exception as e:
            print_and_log('Failed to decode bytestring.')
            continue
        if line_dec[0:6] == '$GPGGA':
            ### Validate checksum (see the pdf linked at the top) ###
            try:
                # Get stuff inbetween $ and *
                trimmed = line_dec[1:]
                data, checksum = trimmed.split('*')
                c = 0
                for char in data:
                    # XOR:
                    c = c ^ ord(char)
                nibble1 = c // 2 ** 4
                nibble2 = c % 2 ** 4

                checkhex1 = hex(nibble1)[-1]
                checkhex2 = hex(nibble2)[-1]

                if checkhex1.lower() == checksum[0].lower() and checkhex2.lower() == checksum[1].lower():
                    ### Validate that there is a GPS signal ###
                    GPGGA_list = line_dec.split(',')
                    GPS_quality = GPGGA_list[6]
                    if GPS_quality == '1' or GPS_quality == '2':
                        ### Return ###
                        return GPGGA_list
                    else:
                        print_and_log('No GPS signal.')
                else:
                    print_and_log('Received corrupt data. Weak signal.')
            except Exception as e:
                print_and_log('Received corrupt data. Weak signal.')

def print_and_log(*args, **kwargs):
    print(*args, **kwargs)
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    with open(log, 'a') as f:
        print(*args, file=f, **kwargs)

parser = argparse.ArgumentParser(description='Display relative altitude from u-blox GPS module.')
parser.add_argument(
    '-p',
    dest='com_port',
    action='store',
    help='COM port to listen on.')
parser.add_argument(
    '-g',
    dest='ground_measurements',
    default='50',
    action='store',
    help='Number of readings for ground altitude.')
args = parser.parse_args()

# Logging output to a file
script_dir = os.path.dirname(os.path.realpath(__file__))
log_filename = str(time.time()) + '.txt'
log_folder = os.path.join(script_dir, 'logs')
log = os.path.join(log_folder, log_filename)

# Figure out COM port number to listen on:
if args.com_port != None:
    port = int(args.com_port)
else:
    print_and_log('Listing available COM ports:\n')
    # Get available COM ports from registry:
    com_ports = list(enumerate_serial_ports())

    # Present user with com ports found in the registry:
    n_com_ports = 0
    for com_port in com_ports:
        print_and_log(com_port)
        n_com_ports += 1

    # If only one is found, that one is suggested as the deafult one
    if n_com_ports == 1:
        default_port = com_ports[0]
        default_port = int(default_port[3]) # grab the integer from 'COMx'
        user_input = input('\nSpecify COM port to use (as integer) or press ENTER to use port {}: '.format(default_port))
        if user_input == '':
            port = default_port
        else:
            port = int(user_input)
    else:
        user_input = input('\nSpecify COM port to use (as integer): ')
        port = int(user_input)

# COM ports in Windows are 1-indexed but in Python they are 0-indexed:
port -= 1
try:
    ser = serial.Serial(port=port, baudrate=9600)
except Exception as e:
    print_and_log('Error: Could not connect to COM port.')
    return

n_base_readings = int(args.ground_measurements)

# Collect measurements at ground level:
print_and_log('\nData is altitude data (geoid altitude)')
print_and_log('Collecting', n_base_readings, 'base readings to establish ground altitude.')
base_readings = []
for base_reading in range(n_base_readings):
    GPGGA = get_GPGGA(ser)
    geoid_altitude = get_geoid_altitude(GPGGA)
    base_readings.append(geoid_altitude)
    n_satelites = get_n_satelites(GPGGA)
    print_and_log('Base reading {:02d}/{}... '.format(base_reading + 1, n_base_readings), end='')
    print_and_log('Sat:', n_satelites, end = ', ')
    print_and_log('Ground altitude:', geoid_altitude, 'm')

# Average the ground altitude measurements:
base_altitude_avg = sum(base_readings) / len(base_readings)
print_and_log('\nGround altitude average set to', round(base_altitude_avg, 2), 'm')

# Sample standard deviation for ground altitude measurements:
var = sum((base_reading - base_altitude_avg) ** 2 for base_reading in base_readings) / (len(base_readings) - 1)
std_dev = var ** 0.5
print_and_log('Sample variance:', round(var, 3), 'm^2')
print_and_log('Sample standard deviation:', round(std_dev, 3), 'm', '\n')

# Start outputting relative altitudes:
print_and_log('Program is ready for flight.')
while True:
    GPGGA = get_GPGGA(ser)
    geoid_altitude = get_geoid_altitude(GPGGA)
    n_satelites = get_n_satelites(GPGGA)

    rel_altitude = geoid_altitude - base_altitude_avg
    rel_altitude = round(rel_altitude, 2)

    print_and_log('Sat:', n_satelites, end = ', ')
    print_and_log('Relative altitude:', rel_altitude, 'm')