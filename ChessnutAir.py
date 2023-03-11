"""
Discover and talk to chessnut Air devices.
See pdf file Chessnut_communications.pdf
for more information.
"""

import asyncio
import math
import time

from constants import WRITE_CHARACTERISTIC, INITIALIZATION_CODE, READ_DATA_CHARACTERISTIC

from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from constants import DEVICE_LIST


def loc_to_pos(location, rev=False):
    # noinspection SpellCheckingInspection
    return "hgfedcba"[location % 8]+str((8-(location//8)) if not rev else (location//8))


class ChessnutAir:
    # noinspection SpellCheckingInspection
    """
    Class created to discover and connect to chessnut Air devices.
    It discovers the first device with a name that matches the names in DEVICE_LIST.
    """
    def __init__(self):
        self.deviceNameList = DEVICE_LIST  # valid device name list
        self._device = self._advertisement_data = self._connection = None
        self.board_state = [0] * 32
        self._old_data = [0] * 32
        self._led_command = bytearray([0x0A, 0x08])
        self._board_changed = False

    def _filter_by_name(self, device: BLEDevice, _: AdvertisementData) -> bool:
        """
        Callback for each discovered device.
        return True if the device name is in the list of 
        valid device names otherwise it returns False
        """
        if any(ext in device.name for ext in self.deviceNameList):
            self._device = device
            return True
        return False

    async def discover(self):
        """Scan for chessnut Air devices"""
        print("scanning, please wait...")
        await BleakScanner.find_device_by_filter(
            self._filter_by_name)
        if self._device is None:
            print("No chessnut Air devices found")
            return
        print("done scanning")

    async def connect(self):
        """Run discover() until device is found."""
        while not self._device:
            await self.discover()

    async def piece_up(self, location, piece_id):
        """Should be overriden with a function that handles piece up events."""
        raise NotImplementedError

    async def piece_down(self, location, piece_id):
        """Should be overriden with a function that handles piece up events."""
        raise NotImplementedError

    async def game_loop(self):
        """Should be overriden with a function that creates an endless game loop."""
        raise NotImplementedError

    async def board_has_changed(self, timeout=0.0):
        """Sleeps until the board has changed or until timeout (if >0)."""
        self._board_changed = False
        end_time = time.time()+timeout if timeout > 0 else math.inf
        while not self._board_changed:
            if time.time() >= end_time:
                return False
            await asyncio.sleep(0.1)
        return True

    async def change_leds(self, list_of_pos):
        """
        Turns on all LEDs in list_of_pos and turns off all others.
            list_of_pos := ["e3", "a4",...]
        """
        conv_letter = {"a": 128, "b": 64, "c": 32, "d": 16, "e": 8, "f": 4, "g": 2, "h": 1}
        conv_number = {"1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0}
        arr = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        if list_of_pos is None:
            return
        for pos in list_of_pos:
            arr[conv_number[pos[1]]] |= conv_letter[pos[0]]
        await self._connection.write_gatt_char(WRITE_CHARACTERISTIC, self._led_command + arr)

    async def play_animation(self, list_of_frames, sleep_time=0.5):
        """
            changes LED to a frame popped from beginning of list_of_frames
            waits for sleep_time and repeats until no more frames
        """
        list_of_frames = list(reversed(list_of_frames.copy()))
        while list_of_frames:
            frame = list_of_frames.pop()
            await self.change_leds(frame)
            await asyncio.sleep(sleep_time)

    async def _handler(self, _, data):
        async def send_message(loc, old, new):
            if old != new:
                if new == 0:
                    await self.piece_up(loc, old)
                else:
                    await self.piece_down(loc, new)
        rdata = data[2:34]
        if rdata != self._old_data:
            self._board_changed = True
            self.board_state = rdata
            od = self._old_data
            self._old_data = rdata
            for i in range(32):
                if rdata[i] != od[i]:
                    cur_left = rdata[i] & 0xf
                    old_left = od[i] & 0xf
                    cur_right = rdata[i] >> 4
                    old_right = od[i] >> 4
                    await send_message(i*2, old_left, cur_left)
                    await send_message(i*2+1, old_right, cur_right)

    async def run(self):
        """
        Connect to the device, start the notification handler (self.piece_up(), self.piece_down())
        and wait for self.game_loop() to return.
        """
        print("device.address: ", self._device.address)

        async with BleakClient(self._device) as client:
            self._connection = client
            print(f"Connected: {client.is_connected}")
            # send initialisation string!
            await client.write_gatt_char(WRITE_CHARACTERISTIC, INITIALIZATION_CODE)  # send initialisation string
            print("Initialized")
            await client.start_notify(READ_DATA_CHARACTERISTIC, self._handler)  # start notification handler
            await self.game_loop()  # call user game loop
            await self.stop_handler()

    async def stop_handler(self):
        """Allow stopping of the handler from outside."""
        if self._connection:
            await self._connection.stop_notify(READ_DATA_CHARACTERISTIC)  # stop the notification handler
