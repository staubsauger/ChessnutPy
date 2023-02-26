from devices import ChessnutAirDevice
from data2fen import get_fen
import asyncio
from bleak import BleakClient
from constants import INITIALIZASION_CODE, WRITECHARACTERISTICS, READCONFIRMATION, READDATA, convertDict, MASKLOW
from virtualeboard import Eboard
import chess


CLIENT = None
eboard = Eboard()

def fen_add(fen, move):
    board = chess.Board(fen)
    board.push_san(move)
    return board.fen()


def print_board(data):
    """Print the board in a human-readable format.
    first two bytes should be 0x01 0x24.
    The next 32 bytes specify the position. 

    Each square has a value specifying the piece:
Value 0 1 2 3 4 5 6 7 8 9 A B C
Piece . q k b p n R P r B N Q K

        q k b p n R P r B N Q K

Each of the 32 bytes represents two squares with the order being the squares labelled
H8,G8,F8...C1,B1,A1. Within each byte the lower 4 bits represent the first square and the
higher 4 bits represent the second square. This means that if the 32 bits were written out in
normal hex characters the pairs would actually appear reversed.
For example, the 32 bytes for the normal starting position with black on the 7th and 8th ranks
would be shown as:
58 23 31 85 44 44 44 44 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 77 77 77 77 A6 C9 9B 6A
So the first byte's value of 0x58 means a black rook (0x8) on H8 and a black knight (0x5) on
G8 and the second byte's value of 0x23 means a black bishop (0x3) on F8 and a black king (0x2)
on E8.
    """
    for counterColum in range(0, 8):
        print(8 - counterColum, " ", end=" ")
        row = reversed(data[counterColum * 4:counterColum * 4 + 4])
        for b in row:
            print(convertDict[b >> 4], convertDict[b & MASKLOW], end=" ")
        print("")
    print("    a b c d e f g h\n\n")


async def leds(byte_array):
    await CLIENT.write_gatt_char(WRITECHARACTERISTICS, byte_array)


async def display_move(move):
    """Display the correct LEDs for a given move as a string."""
    await leds(eboard.onleds)


def generate_move():
    return "e2e4"


class PlayerState:
    def __init__(self):
        self.p1 = False
        self.p1_legal_fens = []
        self.p2 = False
        self.p2_new_fen = None
        self.old_data = None

    async def p1_handler(self, char, data):
        if data[2:34] != self.old_data:
            self.old_data = data[2:34]
            print_board(data[2:34])
            self.p1 = True

    async def p2_handler(self, char, data):
        rdata = data[2:34]
        if rdata != self.old_data:
            self.old_data = rdata
            cur_fen = get_fen(rdata)
            print(f"compare fens!\n{cur_fen}\n{self.p2_new_fen}")
            if cur_fen == self.p2_new_fen:
                self.p2 = True


async def run(device, debug=False):
    """ Connect to the device and run the notification handler.
    then read the data from the device. after 100 seconds stop the notification handler."""
    print("device.adress: ", device.device.address)

    global CLIENT
    async with BleakClient(device.device) as client:
        # TODO: this global variable is a dirty trick
        CLIENT = client
        print(f"Connected: {client.is_connected}")
        # send initialisation string
        await client.write_gatt_char(WRITECHARACTERISTICS, INITIALIZASION_CODE)  # send initialisation string

        # Add game loop
        game_over = False
        state = PlayerState()
        cur_fen = chess.Board().fen()

        while not game_over:
            state.p1 = False
            await client.start_notify(READDATA, state.p1_handler)  # start the notification handler
            print("Player1 Move!")
            while not state.p1:
                await asyncio.sleep(1.0)  # wait 1 second
            cur_fen = get_fen(state.old_data)
            print("done!")
            await client.stop_notify(READDATA)  # stop the notification handler
            state.p2 = False
            await client.start_notify(READDATA, state.p2_handler)  # start another notification handler
            move = generate_move()
            state.p2_new_fen = fen_add(cur_fen, move).split()[0]
            await display_move(move)
            while not state.p2:
                await asyncio.sleep(1.0)
            print("correct move done")
            # TODO: check if game over
            await client.stop_notify(READDATA)  # stop the notification handler


device = ChessnutAirDevice()
# get device
asyncio.run(device.discover())
# connect to device
asyncio.run(run(device))

from ChessnutAir import ChessnutAir

class Test (ChessnutAir):
    async def piece_down(self, location, id):
        print(f"piece: {id} at {location} down")

    async def piece_up(self, location, id):
        print(f"piece: {id} at {location} up")

async def testf():
    t = Test()
    await t.discover()
    await t.run()

asyncio.run(testf())

