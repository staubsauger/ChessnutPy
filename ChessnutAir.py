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


class ChessnutAir:
    """Class created to discover chessnut Air devices.
    It returns the first device with a name that maches
    the names in DEVICELIST.
    """
    def __init__(self, timeout=10.0):
        self.deviceNameList = DEVICELIST # valid device name list
        self.device = self.advertisement_data = self.connection = None
        self.running = False
        self.old_data = []

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

    def piece_up(self, location, id):
        raise NotImplementedError

    def piece_down(self, location, id): # location -> pos: x = location%8, y = location//8
        raise NotImplementedError

    async def handler(self, char, data):
        rdata = data[2:34]
        if rdata != self.old_data:
            self.old_data = rdata
            for i in range(32):
                if rdata[i] != self.old_data[i]:
                    clow = rdata[i] & 0xf
                    olow = self.old_data[i] & 0xf
                    if clow != olow:
                        if clow == 0:
                            self.piece_up(i*2, olow)
                        else:
                            self.piece_down(i*2, clow)
                    else:
                        if rdata[i] >> 4 == 0:
                            self.piece_up(i*2+1, self.old_data[i] >> 4)
                        else:
                            self.piece_down(i*2+1, rdata[i] >> 4)


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
                await asyncio.sleep(1.0)
            await client.stop_notify(READDATA)  # stop the notification handler

