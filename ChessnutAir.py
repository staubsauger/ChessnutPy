"""
Discover and talk to chessnut Air devices.
See pdf file Chessnut_communications.pdf
for more information.
"""
import asyncio
import math
import time
import logging
from collections import namedtuple
from typing import Iterable, NamedTuple

import chess

import ChessnutAir_Helpers.constants as constants
from ChessnutAir_Helpers.constants import DEVICE_LIST, convertDict, BtCommands

from bleak import BleakScanner, BleakClient, BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak import BleakError
from bleak.exc import BleakDBusError

log = logging.getLogger("ChessnutPy")


def loc_to_pos(location: int, rev: bool = False) -> str:
    # noinspection SpellCheckingInspection
    return "hgfedcba"[location % 8] + str((8 - (location // 8)) if not rev else (location // 8))


SquareAndPiece = NamedTuple('SquareAndPiece', [('square', chess.Square), ('piece', chess.Piece)])



def board_state_as_square_and_piece(board_state: bytearray) -> Iterable[SquareAndPiece]:
    s_q = namedtuple("SquareAndPiece", "square, piece")
    for i in range(32):
        pair = board_state[i]
        left = pair & 0xf
        right = pair >> 4
        str_left = convertDict[left]
        yield s_q(63 - i * 2, chess.Piece.from_symbol(str_left) if str_left != ' ' else None)
        str_right = convertDict[right]
        yield s_q(63 - (i * 2 + 1), chess.Piece.from_symbol(str_right) if str_right != ' ' else None)


class ChessnutAir:
    """
    Class created to discover and connect to chessnut Air devices.
    It discovers the first device with a name that matches the names in DEVICE_LIST.
    """

    def __init__(self) -> None:
        self.deviceNameList = DEVICE_LIST  # valid device name list
        self._device = self._advertisement_data = self._connection = None
        self.is_connected = False
        self.board_state = bytearray(32)
        self._old_data = bytearray(32)
        self._led_command = bytearray([0x0A, 0x08])
        self._board_changed = False
        self.cur_fen = " "
        self.to_blink = chess.SquareSet()
        self.to_light = chess.SquareSet()
        self.tick = False
        self.charging = False
        self.charge_percent = 0
        self.last_change = 0
        self.bt_running = True

    async def blink_tick(self, sleep_time: float = 0.0) -> None:
        self.tick = not self.tick
        if self.tick:
            await self.change_leds(self.to_blink.union(self.to_light))
        else:
            await self.change_leds(self.to_light)
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)

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

    async def discover(self) -> None:
        """Scan for chessnut Air devices"""
        log.info("scanning, please wait...")
        await BleakScanner.find_device_by_filter(
                self._filter_by_name)
        if self._device is None:
            log.info("No chessnut Air devices found")
            return
        log.info("done scanning")

    async def connect(self) -> None:
        """Run discover() until device is found."""
        while not self._device:
            try:
                await self.discover()
            except BleakDBusError:
                log.error("DBus Error, waiting 15 seconds before retrying.\nYou probably need to restart the bluetooth stack.")
                await asyncio.sleep(15.0)
            except BleakError as e:
                log.error(f"BleakError during connect: {e}")
                await asyncio.sleep(15.0)

    async def piece_up(self, square: chess.Square, piece: chess.Piece) -> None:
        """Should be overriden with a function that handles piece up events."""
        raise NotImplementedError

    async def piece_down(self, square: chess.Square, piece: chess.Piece) -> None:
        """Should be overriden with a function that handles piece down events."""
        raise NotImplementedError

    async def button_pressed(self, button: int) -> None:
        """Should be overriden with a function that handles button events."""
        raise NotImplementedError

    async def game_loop(self) -> None:
        """Should be overriden with a function that creates an endless game loop."""
        raise NotImplementedError

    async def board_has_changed(self, timeout: float = 0.0, sleep_time: float = 0.4) -> bool:
        """Sleeps until the board has changed or until timeout (if timeout > 0)."""
        self._board_changed = False
        end_time = time.time() + timeout if timeout > 0 else math.inf
        while not self._board_changed:
            if time.time() >= end_time:
                return False
            await self.blink_tick(sleep_time=sleep_time if sleep_time < timeout or timeout == 0.0 else timeout)
        return True

    async def change_leds(self, list_of_pos: "list[str] | chess.SquareSet") -> None:
        """
        Turns on all LEDs in list_of_pos and turns off all others.
            list_of_pos := ["e3", "a4",...]
        """
        if not self.is_connected:
            log.warning("Can't change LEDs when disconnected!")
            return
        is_square_set = isinstance(list_of_pos, chess.SquareSet)
        if is_square_set:
            arr = chess.flip_horizontal(int(list_of_pos)).to_bytes(8, byteorder='big')
        else:
            conv_letter = {"a": 128, "b": 64, "c": 32, "d": 16, "e": 8, "f": 4, "g": 2, "h": 1}
            conv_number = {"1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0}
            arr = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            if list_of_pos is None:
                return
            for pos in list_of_pos:
                arr[conv_number[pos[1]]] |= conv_letter[pos[0]]
        try:
            await self._connection.write_gatt_char(constants.BtCharacteristics.write, self._led_command + arr)
        except Exception as e:
            if isinstance(e, BleakError):
                raise
            else:
                log.error(f"Couldnt send LED change! Exception: {type(e)} {e}")

    async def _run_cmd(self, cmd: bytearray):
        await self._connection.write_gatt_char(constants.BtCharacteristics.write, cmd)

    async def play_animation(self, list_of_frames: list["list[str] | chess.SquareSet"], sleep_time: float = 0.5) -> None:
        """
        changes LED to a frame popped from beginning of list_of_frames
        waits for sleep_time and repeats until no more frames
        """
        for frame in list_of_frames:
            await self.change_leds(chess.SquareSet(map(lambda s: chess.parse_square(s), frame)))
            await asyncio.sleep(sleep_time)

    async def _board_handler(self, _: BleakGATTCharacteristic, data: bytearray) -> None:
        if data[:2] != constants.BtResponses.head_buffer:
            log.warning(f'Other data recieved: {data}')

        rdata = data[2:34]
        time_stamp = int.from_bytes(data[34:], byteorder="little")
        if rdata != self._old_data:
            delay_slot = []
            async def send_message(loc, old, new):
                if old != new:
                    if new == 0:
                        await self.piece_up(loc, chess.Piece.from_symbol(convertDict[old]))
                    else:
                        delay_slot.append((loc, chess.Piece.from_symbol(convertDict[new])))
            self.last_change = time_stamp
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
                    await send_message(63 - i * 2, old_left, cur_left)  # 63-i since we get the data backwards
                    await send_message(63 - (i * 2 + 1), old_right, cur_right)
            for loc, p in delay_slot:
                await self.piece_down(loc, p)


    async def _misc_handler(self, _: BleakGATTCharacteristic, data: bytearray) -> None:
        if data == constants.BtResponses.heartbeat_code:
            return
        elif data == constants.BtResponses.board_not_ready:
            log.warning('Board not ready!')
        elif data.startswith(constants.BtResponses.otb_count_prefix):
            log.warning(f'OTB count = {data[2]}')
        elif data.startswith(constants.BtResponses.file_size_prefix):
            log.warning(f'File size = {int.from_bytes(data[2:6], byteorder="little")} ({data[2:]})')
        elif data == constants.BtResponses.file_start:
            log.warning('OTB File Start')
        elif data == constants.BtResponses.file_end:
            log.warning('OTB File End')
        elif data[0] == 0xf:  # this is a button event
            button = data[2]
            await self.button_pressed(button)
        elif data[0] == 0x2A:
            self.charging = data[3] == 1  # 1 if charging
            self.charge_percent = min(data[2], 100)
        else:
            log.warning(f"unknown data recieved: {[hex(p) for p in data]} {int.from_bytes(data[2:], byteorder='little')} {data}")
        # if data[0] 0x32 -> unknown, 0x37 -> otb_start or end

    async def _otb_handler(self, _: BleakGATTCharacteristic, data: bytearray) -> None:
        fen = self.board_state_as_fen(board_state=data[2:34])
        log.info(fen)

    async def run(self) -> None:
        """
        Connect to the device, start the notification handler (which calls self.piece_up() and self.piece_down())
        and wait for self.game_loop() to return.
        """
        while self.bt_running:
            log.info(f"device.address: {self._device.address}")

            try:
                async with BleakClient(self._device.address) as client:
                    self._connection = client
                    log.info(f"Connected: {client.is_connected}")
                    self.is_connected = True
                    await client.start_notify(constants.BtCharacteristics.read_board_data,
                                            self._board_handler)  # start board handler
                    await client.start_notify(constants.BtCharacteristics.read_misc_data,
                                            self._misc_handler)  # start misc handler
                    await client.start_notify(constants.BtCharacteristics.read_otb_data,
                                            self._otb_handler)  # start otb handler
                    # send initialisation string
                    await client.write_gatt_char(constants.BtCharacteristics.write,
                                                constants.BtCommands.init_code)
                    log.info("Initialized")
                    await self.game_loop()  # call user game loop
            except BleakError as e:
                self.is_connected = False
                self._connection = None
#                self._device = None
                log.error(f"Board disconnected! stange things may occur!\nException: {type(e)} {e}")
                await asyncio.sleep(1)
#                await self.connect() # <- loops until connection
        await self.stop_handlers()

    async def stop_handlers(self) -> None:
        """Allow stopping of the handler from outside."""
        if self._connection:
            # stop the notification handlers
            await self._connection.stop_notify(constants.BtCharacteristics.read_board_data)
            await self._connection.stop_notify(constants.BtCharacteristics.read_misc_data)
            await self._connection.stop_notify(constants.BtCharacteristics.read_otb_data)

    async def request_battery_status(self) -> None:
        if self.is_connected:
            try:
                await self._connection.write_gatt_char(constants.BtCharacteristics.write,
                                                       BtCommands.get_battery_status)
            except Exception as e:
                log.error(f"Error while requesting Battery! Exception: {type(e)} {e}")

    def board_state_as_fen(self, board_state=None) -> str:
        fen = ''
        empty_count = 0

        def handle_empties():
            nonlocal empty_count, fen
            if empty_count > 0:
                fen += str(empty_count)
                empty_count = 0

        for square, piece in board_state_as_square_and_piece(board_state if board_state else self.board_state):
            if piece:
                handle_empties()
                fen += piece.symbol()
            else:
                empty_count += 1
            if square in chess.SquareSet(chess.BB_FILE_A):
                handle_empties()
                fen += '/'
        self.cur_fen = '/'.join(map(lambda row: ''.join(reversed(row)), fen[:-1].split('/')))
        return self.cur_fen

    def compare_board_state_to_fen(self, target_fen):
        # noinspection SpellCheckingInspection
        """
        takes target_fen and cur_fen and returns which pieces are wrong on fen2
        fen like "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        return like [['P','d4'],['1', d2']] -> '1' = empty field,  'letters' = piece
        """

        def convert_fen(fen):
            # noinspection SpellCheckingInspection
            """
            convert "r1bqkbnr/pppppppp/2n5/8/2P5/8/PP1PPPPP/RNBQKBNR w KQkq c6 0 2"
            to "r1bqkbnr/pppppppp/11n11111/11111111/11P11111/11111111/PP1PPPPP/RNBQKBNR"
            """
            fen = fen.split()[0]
            return ''.join(map(lambda p: "1" * int(p) if p.isdigit() and p != '1' else p, fen))

        target = ''.join(reversed(convert_fen(target_fen).split("/")))
        differences = []
        for square, piece in board_state_as_square_and_piece(self.board_state):
            new_piece = chess.Piece.from_symbol(target[square]) if target[square] != '1' else None
            if piece != new_piece:
                differences.append((piece, square, new_piece))
        return differences
