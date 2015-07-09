Python 3
Written for Windows.
Written as a part of Course 11427 Arctic Technology at DTU (Techincal University of Denmark).

### Usage: parser.py [-h] [-p PORT] [-b N_BASE_READINGS]

Display relative altitude from u-blox GPS module.

This script computes a relative altitude using data from a u-blox GPS unit and prints it in a readable format.
It starts off by measuring a number of datapoints which are averaged for the ground altitude.
Then the relative altitude is computed and displayed.

Input should come from a COM serial port. The program will display available COM ports by looking in the registry.
If nothing is received from the GPS, the program will probably hang.

### Optional arguments:
//  -h, --help            show this help message and exit
//  -p PORT, --port PORT  COM port to listen on.
//  -b N_BASE_READINGS, --base_readings N_BASE_READINGS
//                        Number of readings for ground altitude.

### Explanation for parameters in GPGGA raw GPS output:
https://www.u-blox.com/images/downloads/Product_Docs/GPS_Compendium%28GPS-X-02007%29.pdf