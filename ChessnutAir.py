"""Discover chessnut Air devices.
See pdf file Chessnut_comunications.pdf 
for more information."""

import asyncio
import logging
from constants import WRITECHARACTERISTICS, INITIALIZASION_CODE, READDATA


from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from constants import DEVICELIST
import data2fen
from setledhelpers import turnOffat, turnOnat

class ChessnutAir:
    """Class created to discover chessnut Air devices.
    It returns the first device with a name that maches
    the names in DEVICELIST.
    """
    def __init__(self, timeout=10.0):
        self.deviceNameList = DEVICELIST # valid device name list
        self.device = self.advertisement_data = self.connection = None
        self.running = False
        self.old_data = [0]*32
        self.boardstate = ""
        self.onledsarr = [0x0A, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        self.onledstack = []
        self.tick = 1
        self.to_blink = [["e", "4"]]
        self.to_light = [["e", "2"]]

    def filter_by_name(
        self,
        device: BLEDevice,
        advertisement_data: AdvertisementData,
    ) -> None:
        """Callback for each discovered device.
        return True if the device name is in the list of 
        valid device names otherwise it returns False"""
        if any(ext in device.name for ext in self.deviceNameList):
            self.device = device            
            return True
        else:
            return False

    async def discover(self, timeout=10.0):
        """Scan for chessnut Air devices"""
        print("scanning, please wait...")
        await BleakScanner.find_device_by_filter(
            self.filter_by_name)
        if self.device is None:
            print("No chessnut Air devices found")
            return
        print("done scanning")

    def returnboardstate(self):
        fen = data2fen.get_fen(self.boardstate)
        print(fen)
        return fen

    async def piece_up(self, location, id):
        raise NotImplementedError

    async def piece_down(self, location, id): # location -> pos: x = location%8, y = location//8
        raise NotImplementedError
    
    async def showmoveonboard(self, bytearr):
        raise NotImplementedError
    
    def add_square_to_leds(self, move1, move2):
        if move1 + move2 not in self.onledstack:
            # print("nicht drin")
            self.onledsarr = turnOnat(move1, move2, self.onledsarr)
            self.onledstack.append(move1+move2)

    def rem_square_from_leds(self, move1, move2):
        if move1 + move2 not in self.onledstack:
            print("nicht drin, kann nicht ausschalten")
        else:
            self.onledsarr = turnOffat(move1, move2, self.onledsarr)
            self.onledstack.remove(move1+move2)

    def blink_on(self, move1, move2):
        if self.tick == 1:
            self.add_square_to_leds(move1, move2)
        else:
            self.rem_square_from_leds(move1, move2)

    def turnLedOnOn(self, square):
        # square like "e2"
        if [square[0], square[1]] not in self.to_light:
            self.to_light.append([square[0], square[1]])
        print("on", self.to_light)

    def turnLefOffOn():
        pass

    def blinkLedOn(self, square):
        self.to_blink.append([square[0], square[1]])
        
    def blinkLedOff():
        pass

    async def handler(self, char, data):
        self.boardstate = data[2:34]
        rdata = data[2:34]
        if rdata != self.old_data:
            for i in range(32):
                if rdata[i] != self.old_data[i]:
                    clow = rdata[i] & 0xf
                    olow = self.old_data[i] & 0xf
                    if clow != olow:
                        if clow == 0:
                            await self.piece_up(i*2, olow)
                            print("clow == 0")
                        else:
                            await self.piece_down(i*2, clow)
                            print("clow != 0")
                    else:
                        if rdata[i] >> 4 == 0:
                            await self.piece_up(i*2+1, self.old_data[i] >> 4)
                            print("rdata[i] >> 4 == 0")
                        else:
                            await self.piece_down(i*2+1, rdata[i] >> 4)
                            print("rdata[i] >> 4 != 0")
            self.old_data = rdata

    async def run(self, debug=False):
        """ Connect to the device and run the notification handler."""
        print("device.adress: ", self.device.address)

        async with BleakClient(self.device) as client:
            self.connection = client
            print(f"Connected: {client.is_connected}")
            self.running = True
            # send initialisation string
            await client.write_gatt_char(WRITECHARACTERISTICS, INITIALIZASION_CODE)  # send initialisation string
            print("Initialized")
            await client.start_notify(READDATA, self.handler)  # start another notification handler
            while self.running:
                
                if self.tick == 1:
                    self.tick = 0
                else:
                    self.tick = 1
                print("Tick: ", self.tick)
                for i in self.to_light:
                    self.add_square_to_leds(i[0], i[1])
                for i in self.to_blink:
                    self.blink_on(i[0], i[1])
                await self.showmoveonboard(self.onledsarr)
                await asyncio.sleep(1)
            await client.stop_notify(READDATA)  # stop the notification handler

