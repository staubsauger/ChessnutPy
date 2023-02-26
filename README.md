# chessnutair
python script able to connect to the chessnut air board using bluetooth

Here you will find a script able to read the position of the pieces in the chess board and print the board on the PC screen. Additionally it will switch on the leds of those squares that are not empty. If a piece is moved a new board will be printed on the screen and the corresponding leds switched off/on.
The connection are made by bluetooth using the library bleak and no driver is needed. Regarding supported systems I believe the only limitations are those imposed by the bleak library that are (https://bleak.readthedocs.io/en/latest/):

 * Supports Windows 10, version 16299 (Fall Creators Update) or greater
 * Supports Linux distributions with BlueZ >= 5.43 (See Linux backend for more details)
 * OS X/macOS support via Core Bluetooth API, from at least OS X version 10.11

So far, I have only tested this shofware in Ubuntu 18.

## Installation and execution
 1. download code
 1. install dependencies (pip3 install -r requeriments.txt
 1. Execute python3 ./main.py
 
 The chessnut air board need to be paired to the PC in which you are running this.
 
