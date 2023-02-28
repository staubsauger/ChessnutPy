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
    """Class created to discover and connect to chessnut Air devices.
    It discovers the first device with a name that maches the names in DEVICELIST.
    """
    def __init__(self):
        self.deviceNameList = DEVICELIST  # valid device name list
        self.device = self.advertisement_data = self.connection = None
        self.boardstate = [0]*32
        self.old_data = [0]*32
        self.led_command = [0x0A, 0x08]

    def filter_by_name(
        self,
        device: BLEDevice,
        advertisement_data: AdvertisementData,
    ) -> bool:
        """Callback for each discovered device.
        return True if the device name is in the list of 
        valid device names otherwise it returns False"""
        if any(ext in device.name for ext in self.deviceNameList):
            self.device = device
            return True
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

    def boardstate_fen(self):
        fen = data2fen.get_fen(self.boardstate)
        # print(fen)
        return fen

    async def piece_up(self, location, id):
        raise NotImplementedError

    async def piece_down(self, location, id):  # location -> pos: x = location%8, y = location//8
        raise NotImplementedError

    async def game_loop(self):
        raise NotImplementedError

    async def change_leds(self, list_of_pos):
        """Turns on all LEDs in list_of_pos and turns off all others.
            list_of_pos := ["e3", "a4",...]"""
        conv_letter = {"a": 128, "b": 64, "c": 32, "d": 16, "e": 8, "f": 4, "g": 2, "h": 1}
        conv_number = {"1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0}
        arr = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        for pos in list_of_pos:
            arr[conv_number[pos[1]]] += conv_letter[pos[0]]
        await self.connection.write_gatt_char(WRITECHARACTERISTICS, self.led_command + arr)

    async def handler(self, char, data):
        async def send_message(loc, old, new):
            if old != new:
                if new == 0:
                    await self.piece_up(loc, old)
                else:
                    await self.piece_down(loc, new)
        rdata = data[2:34]
        if rdata != self.old_data:
            self.boardstate = rdata
            for i in range(32):
                if rdata[i] != self.old_data[i]:
                    cur_left = rdata[i] & 0xf
                    old_left = self.old_data[i] & 0xf
                    await send_message(i*2, old_left, cur_left)
                    cur_right = rdata[i] >> 4
                    old_right = self.old_data[i] >> 4
                    await send_message(i*2+1, old_right, cur_right)
            self.old_data = rdata

    async def run(self, debug=False):
        """ Connect to the device and run the notification handler."""
        print("device.address: ", self.device.address)

        async with BleakClient(self.device) as client:
            self.connection = client
            print(f"Connected: {client.is_connected}")
            # send initialisation string
            await client.write_gatt_char(WRITECHARACTERISTICS, INITIALIZASION_CODE)  # send initialisation string
            print("Initialized")
            await client.start_notify(READDATA, self.handler)  # start another notification handler
            await self.game_loop()  # call user game loop
            await client.stop_notify(READDATA)  # stop the notification handler

