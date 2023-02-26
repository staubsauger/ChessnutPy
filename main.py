from devices import ChessnutAirDevice
import asyncio
from bleak import BleakClient
from constants import INITIALIZASION_CODE, WRITECHARACTERISTICS, READCONFIRMATION, READDATA, convertDict, MASKLOW
from virtualeboard import Eboard

old_data = None
CLIENT = None
eboard = Eboard()


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


async def leds(bytearr):
    await CLIENT.write_gatt_char(WRITECHARACTERISTICS, bytearr)


async def display_move(move):
    pass


def generate_move():
    return "e2e4"


async def run(device, debug=False):
    """ Connect to the device and run the notification handler.
    then read the data from the device. after 100 seconds stop the notification handler."""
    print("device.adress: ", device.device.address)

    async def notification_handler(state, characteristic, data):
        """Handle the notification from the device and print the board."""
        # print("data: ", ''.join('{:02x}'.format(x) for x in data))
        global old_data
        if data[2:34] != old_data:
            print_board(data[2:34])
            eboard.boardstatus = data
            # bytearray(b'\x01$X#1\x85DDDD\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00wwww\xa6\xc9\x9bj\xc9\xe2G\x00')
            print(eboard.boardstatus)
            await leds(eboard.onleds)
            old_data = data[2:34].copy()
            state["player1"] = True

    global CLIENT
    async with BleakClient(device.device) as client:
        # TODO: this global variable is a dirty trick
        CLIENT = client
        print(f"Connected: {client.is_connected}")
        # send initialisation string
        await client.write_gatt_char(WRITECHARACTERISTICS, INITIALIZASION_CODE)  # send initialisation string

        # Add game loop
        game_over = False
        player_state = {"player1": False, "player2": False}

        test = lambda char, data: (await notification_handler(player_state, char, data)).__anext__()
        while not game_over:
            await client.start_notify(READDATA, test)  # start the notification handler
            print("Player1 Move!")
            while not player_state["player1"]:
                await asyncio.sleep(1.0)  # wait 1 second
            print("done!")
            await client.stop_notify(READDATA)  # stop the notification handler
            await client.start_notify(READDATA, lambda char, data:  notification_handler(player_state, char, data))  # start another notification handler
            move = generate_move()
            await display_move(move)
            while not player_state["player2"]:
                await asyncio.sleep(1.0)
            # TODO: check if game over
        await client.stop_notify(READDATA)  # stop the notification handler


device = ChessnutAirDevice()
# get device
asyncio.run(device.discover())
# connect to device
asyncio.run(run(device))
