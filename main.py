import asyncio
from constants import INITIALIZASION_CODE, WRITECHARACTERISTICS, READCONFIRMATION, READDATA, convertDict, MASKLOW
from ChessnutAir import ChessnutAir
from GameOfChess import GameOfChess

class Test(ChessnutAir):
    async def piece_down(self, location, id):
        print(f"piece: {convertDict[id]} at {location} down")
        await self.connection.write_gatt_char(WRITECHARACTERISTICS,
                                              [0x0A, 0x08, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00, 0x08, 0x00])

    async def piece_up(self, location, id):
<<<<<<< HEAD
        print(f"piece: {id} at {location} up")
        await self.connection.write_gatt_char(WRITECHARACTERISTICS,
                                              [0x0A, 0x08, 0x08, 0x00, 0x00, 0x00, 0x08, 0x08, 0x00, 0x00])
=======
        print(f"piece: {convertDict[id]} at {location} up")
        await self.connection.write_gatt_char(WRITECHARACTERISTICS,
                                              [0x0A, 0x08, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00])
>>>>>>> ccbf894 (early in the morning!)

async def testf():
    t = Test()
    c = GameOfChess()
    await t.discover()
    await t.run()

asyncio.run(testf())

