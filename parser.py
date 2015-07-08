'''
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

import argparse
import serial, sys, os
import winreg as winreg
import itertools

def main(args):
    # Figure out COM port number to listen on:
    if args.com_port != None:
        port = int(args.com_port)
    else:
        print('Listing available COM ports:\n')
        # Get available COM ports from registry:
        com_ports = list(enumerate_serial_ports())

        # Present user with com ports found in the registry:
        n_com_ports = 0
        for com_port in com_ports:
            print(com_port)
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
    except:
        print('Error: Could not connect to COM port.')
        return

    n_base_readings = int(args.ground_measurements)

    # Collect measurements at ground level:
    print('\nData is altitude data (geoid altitude)')
    print('Collecting', n_base_readings, 'base readings to establish ground altitude.')
    base_readings = []
    for base_reading in range(n_base_readings):
        print('Base reading {:02d}/{}... '.format(base_reading + 1, n_base_readings), end='')
        GPGGA = get_GPGGA(ser)
        geoid_altitude = get_geoid_altitude(GPGGA)
        base_readings.append(geoid_altitude)
        n_satelites = get_n_satelites(GPGGA)
        GPS_quality = get_GPS_quality(GPGGA)
        print(GPS_quality, end = ' ')
        print('Sat:', n_satelites, end = ', ')
        print('Ground altitude:', geoid_altitude)

    # Average the ground altitude measurements:
    base_altitude_avg = sum(base_readings) / len(base_readings)
    print('\nGround altitude average set to', round(base_altitude_avg, 2))

    # Sample standard deviation for ground altitude measurements:
    var = sum((base_reading - base_altitude_avg) ** 2 for base_reading in base_readings) / (len(base_readings) - 1)
    std_dev = var ** 0.5
    print('Sample variance:', round(var, 3))
    print('Sample standard deviation:', round(std_dev, 3), '\n')

    # Start outputting relative altitudes:
    print('Program is ready for flight.')
    while True:
        GPGGA = get_GPGGA(ser)
        geoid_altitude = get_geoid_altitude(GPGGA)
        n_satelites = get_n_satelites(GPGGA)
        GPS_quality = get_GPS_quality(GPGGA)

        rel_altitude = geoid_altitude - base_altitude_avg
        rel_altitude = round(rel_altitude, 2)

        print(GPS_quality, end = ' ')
        print('Sat:', n_satelites, end = ', ')
        print('Relative altitude:', rel_altitude)

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
        print('Alert! Output from GPS was not as expected! Altitude was not given in meters, the unit was:', unit)
    return geoid_altitude

def get_GPS_quality(GPGGA):
    GPS_quality = GPGGA[6] # GPS quality details (0= no GPS, 1= GPS, 2=DGPS)
    if GPS_quality == '0':
        return 'No GPS'
    elif GPS_quality == '1':
        return 'GPS   '
    elif GPS_quality == '2':
        return 'DGPS  '
    else:
        return 'Error '

def get_n_satelites(GPGGA):
    n_satelites = GPGGA[7]
    return n_satelites

def get_GPGGA(ser):
    # Read from the raw GPS output, and find the GPGGA line.
    while True:
        line = ser.readline()
        line_dec = line.decode('utf-8')
        if line_dec[0:6] == '$GPGGA':
            line_split = line_dec.split(',')
            return line_split

if __name__ == '__main__':
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
    main(args)